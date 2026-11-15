"""Automatic evaluation for the chatbot.

  python eval.py retrieval --label NAME            (no LLM calls)
  python eval.py full --label NAME                 (calls answer(); uses the LLM)
  python eval.py full --subset core20 --label NAME (the fixed 20-question subset)
  python eval.py full --label NAME --resume        (continue a run, skipping finished questions)
  python eval.py full --label NAME --no-cache      (bypass llm_cache.jsonl)

Reads eval/eval_questions.jsonl, appends a row to eval/eval_history.csv and overwrites eval/eval_last.csv.
In full mode every finished question is saved at once to eval/eval_partial_<label>.jsonl. If the LLM quota
runs out (every model answers 429) the run stops without recording the remaining questions as failures.
"""
import argparse, collections, csv, datetime, json, os, re, sys, time
from pathlib import Path

import chat  # retrieve() and answer() are reused, not duplicated

BASE_DIR = Path(__file__).resolve().parent  # project root: paths never depend on the working directory
EVAL_DIR = BASE_DIR / "eval"                # questions, history, last details, partial files
QFILE, HISTORY, LAST = EVAL_DIR / "eval_questions.jsonl", EVAL_DIR / "eval_history.csv", EVAL_DIR / "eval_last.csv"
HIST_COLS = ["timestamp", "mode", "label", "n_questions", "recall@8", "MRR",
             "refusal_accuracy", "answered_rate", "warnings_per_answered", "errors", "partial_rate",
             "retrieve_s", "status"]
DETAIL_COLS = ["id", "type", "question", "expect_psi", "refused", "refusal_ok", "kept", "hit",
               "rank", "dist_min", "dist_max", "n_excel", "n_table", "n_tsum", "n_pdf", "n_meta", "n_routed",
               "returned_psi", "kept_detail", "best_rerank", "retrieve_s", "outcome", "model", "model_switched",
               "cached", "tokens", "seconds", "citations_valid", "invalid_tags", "warnings",
               "warnings_detail", "related", "n_claims",
               "error", "note", "answer"]
# the 10 original questions (base-01..10, Q8 = base-08), the 3 Excel questions, 6 failing experiment questions, 1 injection
CORE20 = ["base-01", "base-02", "base-03", "base-04", "base-05", "base-06", "base-07", "base-08", "base-09",
          "base-10", "xl-01", "xl-02", "xl-03", "exp-10", "exp-20", "exp-21", "exp-69", "exp-98", "exp-106",
          "trap-03"]

def load_questions():
    out = []
    with open(QFILE, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{QFILE} line {n}: invalid JSON ({e})")
    return out

def kind_counts(sources):
    c = {"n_excel": 0, "n_table": 0, "n_tsum": 0, "n_pdf": 0, "n_meta": 0,
         "n_routed": sum(1 for s in sources if s.get("routed"))}
    for s in sources:
        dt = s["doc_type"]
        if dt.startswith("Excel"):
            c["n_excel"] += 1
        elif dt == "Table row":
            c["n_table"] += 1
        elif dt == "Table summary":
            c["n_tsum"] += 1
        elif dt == "Metadata":
            c["n_meta"] += 1
        else:
            c["n_pdf"] += 1
    return c

def retrieval_fields(q, sources):
    """recall/MRR inputs and chunk-mix stats for one question."""
    rr = [s["rerank_score"] for s in sources if "rerank_score" in s]
    d = {"kept_detail": " ; ".join(f"{s['psi']}|{s['doc_type']}|{s['loc']}|{s['distance']:.3f}"
                                   + (f"|r{s['rerank_score']:.2f}" if "rerank_score" in s else "") for s in sources),
         "best_rerank": round(max(rr), 3) if rr else "",
         "kept": len(sources), "returned_psi": " ".join(dict.fromkeys(s["psi"] for s in sources))}
    d.update(kind_counts(sources))
    if sources:
        ds = [s["distance"] for s in sources]
        d["dist_min"], d["dist_max"] = round(min(ds), 3), round(max(ds), 3)
    exp = set(q.get("expect_psi") or [])
    if q["type"] == "answer" and exp:
        rank = next((i for i, s in enumerate(sources, 1) if s["psi"] in exp), None)
        d["hit"], d["rank"] = rank is not None, rank
    return d

def outcome_of(res):
    """answered | partial | refused. Falls back to the old rules if 'outcome' is missing."""
    o = res.get("outcome")
    if o in ("answered", "partial", "refused"):
        return o
    return "refused" if is_refused(res) else "answered"

def is_refused(res):
    if res.get("outcome") in ("answered", "partial"):
        return False
    if res.get("outcome") == "refused":
        return True
    r = res.get("refused")
    if r is None:
        r = (res.get("answer") or "").strip().lower().replace("**", "").startswith("not in the data")
    return bool(r)

def run_answer(question):
    """answer(); a short per-minute quota error (every model limited) gets one wait and retry.
    A daily limit, or a wait over 2 minutes, raises chat.QuotaError to the caller."""
    for attempt in range(2):
        try:
            return chat.answer(question)
        except chat.QuotaError as e:
            if attempt == 0 and not e.daily and (e.retry_after is None or e.retry_after <= 120):
                time.sleep((e.retry_after or 20) + 1)
                continue
            raise

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None

def fmt(v, nd=3):
    return "" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))

def fmt_dur(sec):
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return (f"{h}h " if h else "") + (f"{m}m " if m or h else "") + f"{s}s"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["retrieval", "full"])
    ap.add_argument("--label", default="run")
    ap.add_argument("--subset", choices=["core20"], help="run only a fixed subset of questions")
    ap.add_argument("--resume", action="store_true", help="continue a label, skipping finished questions")
    ap.add_argument("--no-cache", action="store_true", help="bypass llm_cache.jsonl")
    ap.add_argument("--single-model", action="store_true", help="answer with LLM_MODEL only: ignore LLM_FALLBACK_MODELS")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    EVAL_DIR.mkdir(exist_ok=True)
    if args.no_cache:
        os.environ["LLM_CACHE"] = "off"
    if args.single_model:
        os.environ["LLM_FALLBACK_MODELS"] = ""  # chat._models() then has the primary model only
    if args.mode == "full":
        print(f"LLM setup: model={os.environ.get('LLM_MODEL')} | reasoning effort={os.environ.get('LLM_REASONING_EFFORT') or '(not set)'} | "
              f"fallback models={os.environ.get('LLM_FALLBACK_MODELS') or 'none'}{' (--single-model)' if args.single_model else ''} | "
              f"timeout={os.environ.get('LLM_TIMEOUT', '30')} s | cache={'off' if os.environ.get('LLM_CACHE', 'on').lower() == 'off' else 'on'}", flush=True)

    qs = load_questions()
    if args.subset == "core20":
        by_id = {q["id"]: q for q in qs}
        missing = [i for i in CORE20 if i not in by_id]
        if missing:
            sys.exit(f"core20 questions missing from {QFILE}: {missing}")
        qs = [by_id[i] for i in CORE20]
    if args.mode == "retrieval":
        chat.retrieve("warm up")  # load models once, untimed

    partial_path = EVAL_DIR / f"eval_partial_{args.label}.jsonl"
    done = {}
    if args.mode == "full":
        if args.resume and os.path.exists(partial_path):
            with open(partial_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        done[r["id"]] = r
            print(f"resuming '{args.label}': {len(done)} finished questions loaded from {partial_path}")
        else:
            open(partial_path, "w", encoding="utf-8").close()  # fresh run

    rows, stopped = [], None
    tokens_total = sum(int(r.get("tokens") or 0) for r in done.values())
    for k, q in enumerate(qs, 1):
        if q["id"] in done:
            rows.append(done[q["id"]])
            print(f"[{k:2d}/{len(qs)}] {q['id']:9} {q['type']:6} -> (already finished)", flush=True)
            continue
        row = {c: "" for c in DETAIL_COLS}
        row.update(id=q["id"], type=q["type"], question=q["question"],
                   expect_psi=" ".join(q.get("expect_psi") or []), note=q.get("note", ""))
        fresh_llm = False
        try:
            if args.mode == "retrieval":
                t0 = time.perf_counter()
                sources = chat.retrieve(q["question"])
                row["retrieve_s"] = round(time.perf_counter() - t0, 2)
                row.update(retrieval_fields(q, sources))
                row["refused"] = (len(sources) == 0)  # pre-LLM refusal only
            else:
                t_q = time.perf_counter()
                res = run_answer(q["question"])
                row["seconds"] = round(time.perf_counter() - t_q, 1)
                sources = res.get("sources") or []
                text = res.get("answer") or ""
                row.update(retrieval_fields(q, sources))
                row["outcome"] = outcome_of(res)
                row["refused"] = row["outcome"] == "refused"
                # type "answer": answered and partial both count as answered; type "refuse": only refused is correct
                row["refusal_ok"] = (row["refused"] == (q["type"] == "refuse"))
                row["model"] = res.get("model") or ""
                row["model_switched"] = bool(res.get("model_switched"))
                row["cached"] = bool(res.get("cached"))
                row["tokens"] = int((res.get("usage") or {}).get("total_tokens") or 0)
                fresh_llm = bool(res.get("model")) and not row["cached"]
                tokens_total += row["tokens"]
                ids = {s["id"] for s in sources}
                tags = re.findall(r"\[(S\d+)\]", text)
                bad = sorted({t for t in tags if t not in ids})
                row["invalid_tags"] = " ".join(bad)
                row["citations_valid"] = (not bad) if not row["refused"] else ""
                row["warnings"] = len(res.get("warnings") or [])
                row["warnings_detail"] = json.dumps(res.get("warnings") or [], ensure_ascii=False)
                row["related"] = " ; ".join(f"{r['psi']} {r['acronym']}" for r in (res.get("related") or []))
                row["n_claims"] = len(res.get("claims") or [])
                row["answer"] = text
        except chat.QuotaError as qe:
            stopped = qe  # not a failure of this question: it is simply not recorded
            break
        except Exception as e:
            row["error"] = str(e)[:300]
        rows.append(row)
        if args.mode == "full" and not row["error"]:  # save at once (errored rows are retried on --resume)
            with open(partial_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        flag = "ERR" if row["error"] else (row["outcome"] if args.mode == "full" else ("refused" if row["refused"] else "answered"))
        extra = ""
        if args.mode == "full" and row["model"]:
            extra = (f"  [{row['model']}{' FALLBACK' if row['model_switched'] else ''}"
                     f"{' cached' if row['cached'] else ''}, {row['seconds']} s, {row['tokens']} tok, total {tokens_total}]")
        print(f"[{k:2d}/{len(qs)}] {q['id']:9} {q['type']:6} -> {flag}{extra}", flush=True)
        if args.mode == "full" and fresh_llm and k < len(qs):
            time.sleep(3)

    # ---- aggregate (only over the questions that finished) ----
    ok_rows = [r for r in rows if not r["error"]]
    exp_rows = [r for r in ok_rows if r["type"] == "answer" and r["expect_psi"]]
    recall = mean(1.0 if r["hit"] else 0.0 for r in exp_rows)
    mrr = mean((1.0 / r["rank"]) if r["rank"] else 0.0 for r in exp_rows)
    ref_acc = ans_rate = wpa = partial_rate = None
    if args.mode == "full" and ok_rows:
        ref_acc = mean(1.0 if r["refusal_ok"] else 0.0 for r in ok_rows)
        answered = [r for r in ok_rows if not r["refused"]]
        ans_rate = len(answered) / len(ok_rows)
        wpa = mean(r["warnings"] for r in answered)
        partial_rate = sum(1 for r in ok_rows if r["outcome"] == "partial") / len(ok_rows)
    n_err = len(rows) - len(ok_rows)
    rt = [r["retrieve_s"] for r in ok_rows if r["retrieve_s"] != ""]
    retr_s = mean(rt) if rt else None
    status = "partial-quota" if stopped else "complete"

    new = not os.path.exists(HISTORY)
    if not new:
        with open(HISTORY, newline="", encoding="utf-8") as f:
            old_rows = list(csv.reader(f))
        if old_rows and old_rows[0] != HIST_COLS:  # old header: rewrite with the new columns
            with open(HISTORY, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(HIST_COLS)
                for r in old_rows[1:]:
                    w.writerow(r + [""] * (len(HIST_COLS) - len(r)))
    with open(HISTORY, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HIST_COLS)
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), args.mode,
                    args.label + (f" ({args.subset})" if args.subset else ""),
                    len(rows), fmt(recall), fmt(mrr), fmt(ref_acc), fmt(ans_rate), fmt(wpa), n_err,
                    fmt(partial_rate), fmt(retr_s, 2), status])
    with open(LAST, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=DETAIL_COLS)
        w.writeheader()
        w.writerows(rows)

    # ---- summary ----
    print("\n=== SUMMARY:", args.mode, "|", args.label, "|", status, "===")
    print(f"questions finished: {len(rows)} of {len(qs)}   errors: {n_err}   scored for recall: {len(exp_rows)}")
    print(f"recall@8: {fmt(recall)}   MRR: {fmt(mrr)}" + (f"   mean retrieve time: {fmt(retr_s, 2)} s" if retr_s else ""))
    if args.mode == "full":
        print(f"refusal accuracy: {fmt(ref_acc)}   answered rate: {fmt(ans_rate)}   "
              f"partial rate: {fmt(partial_rate)}   warnings/answered: {fmt(wpa, 2)}")
        inv = [r for r in ok_rows if r["citations_valid"] is False]
        print(f"answers with invalid citation tags: {len(inv)}")
        llm_rows = [r for r in ok_rows if r["model"]]
        fb = [r for r in llm_rows if r["model_switched"]]
        print(f"answers from the LLM: {len(llm_rows)} ({sum(1 for r in llm_rows if r['cached'])} from cache); "
              f"from a FALLBACK model: {len(fb)}"
              + (" -> " + ", ".join(f"{m} x{n}" for m, n in collections.Counter(r['model'] for r in fb).items()) if fb else ""))
        print(f"models used: " + (", ".join(f"{m} x{n}" for m, n in collections.Counter(r['model'] for r in llm_rows).items()) or "none"))
        print(f"tokens used (fresh calls only; cached = 0): {tokens_total}")
        secs = [r["seconds"] for r in ok_rows if r["seconds"] != ""]
        llm_secs = [r["seconds"] for r in llm_rows if r["seconds"] != ""]
        if secs:
            print(f"seconds per question: average {mean(secs):.1f} over {len(secs)} questions (max {max(secs):.1f}); "
                  f"average {mean(llm_secs):.1f} over the {len(llm_secs)} that called the LLM")
    if stopped:
        left = [q["id"] for q in qs if q["id"] not in {r["id"] for r in rows}]
        ra = stopped.retry_after
        when = (f"about {fmt_dur(ra)} from now (~{(datetime.datetime.now() + datetime.timedelta(seconds=ra)).strftime('%H:%M')} local)"
                if ra else "unknown")
        print(f"\n*** STOPPED: LLM quota exhausted on every model ({'daily limit' if stopped.daily else 'rate limit'}). "
              f"{len(rows)} of {len(qs)} questions finished; the {len(left)} remaining are NOT recorded as failures: {', '.join(left)}")
        print(f"*** next request could be accepted: {when}. A daily window refills gradually (it is a rolling window).")
        print(f"*** continue with: python eval.py full {'--subset ' + args.subset + ' ' if args.subset else ''}--label {args.label} --resume")
    print("history ->", HISTORY, "| details ->", LAST, "| partial ->", partial_path if args.mode == "full" else "-")

if __name__ == "__main__":
    main()
