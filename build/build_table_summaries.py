"""Build table_summaries.jsonl: one summary record per (psi, source_file) table in runs.jsonl.
Reads runs.jsonl and raw/<psi>/metadata.json only; touches no index."""
import json, os, re, collections

from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
RUNS, OUT, MAXCHARS = str(HERE / "runs.jsonl"), str(HERE / "table_summaries.jsonl"), 1500
NUM = re.compile(r"^[<>~≈]?\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*)$")
# a unit after the number: starts with a letter or %/degree sign and has no digits (rejects dates,
# times, identifiers such as 193F001, and lists such as "0.17; 0.21")
UNIT = re.compile(r"^(?:|[A-Za-z%°µ][A-Za-z/%°µ·.^-]*)$")

def acronym(psi, fallback):
    try:
        d = json.load(open(os.path.join(str(RAW), psi, "metadata.json"), encoding="utf-8"))
        return (d.get("investigationAcronym") or "").strip() or fallback
    except Exception:
        return fallback

def g(x):
    return f"{x:.4g}"

def column_stat(name, values):
    vals = [str(v).strip() for v in values if v is not None and str(v).strip() != ""]
    if not vals:
        return None
    nums, units = [], collections.Counter()
    for v in vals:
        m = NUM.match(v)
        if m and UNIT.match(m.group(2).strip()):
            nums.append(float(m.group(1)))
            if m.group(2).strip():
                units[m.group(2).strip()] += 1
    if len(nums) >= 0.7 * len(vals) and nums:
        unit = ""
        if units and not re.search(r"\(.*\)|\[.*\]", name):
            unit = " " + units.most_common(1)[0][0]
        return (f"{name}: min {g(min(nums))}, max {g(max(nums))}, mean {g(sum(nums) / len(nums))}{unit}"
                f" ({len(nums)} values)")
    cnt = collections.Counter(vals)
    top = cnt.most_common(12)
    if len(cnt) > 12 and top[0][1] <= max(2, 0.05 * len(vals)):  # identifier/date-like: counts carry no information
        return f"{name}: {len(cnt)} distinct values, e.g. " + "; ".join(v[:20] for v, _ in top[:4])
    return f"{name}: " + "; ".join(f"{v[:30]} ({n})" for v, n in top)

def main():
    tables = collections.OrderedDict()
    for line in open(RUNS, encoding="utf-8"):
        r = json.loads(line)
        tables.setdefault((r["psi"], r["source_file"]), []).append(r)
    out = []
    for (psi, f), rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r["fields"]))
        acr = acronym(psi, rows[0].get("experiment", ""))
        head = f"{psi} {acr} | Table summary | {f}: {len(rows)} rows. Columns: {', '.join(cols)}."
        stats = [s[:150] for s in (column_stat(c, [r["fields"].get(c) for r in rows]) for c in cols) if s]
        samples = []
        for r in rows[:3]:
            samples.append(f"row {r['row']}: " + "; ".join(f"{k}: {v}" for k, v in r["fields"].items() if str(v).strip()))
        text = head + " " + " | ".join(stats) + " | Sample rows: " + " || ".join(s[:130] for s in samples)
        out.append({"psi": psi, "experiment": acr, "source_file": f, "rows": len(rows),
                    "columns": cols, "text": text[:MAXCHARS], "full_length": len(text)})
    with open(OUT, "w", encoding="utf-8") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} records to {OUT}")
    for rec in out:
        flag = " TRUNCATED" if rec["full_length"] > MAXCHARS else ""
        print(f"  {rec['psi']:8} {rec['rows']:4} rows {len(rec['columns']):3} cols  len={rec['full_length']}{flag}")

if __name__ == "__main__":
    main()
