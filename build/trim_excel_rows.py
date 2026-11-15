import csv, json, re, random, collections
BAD = re.compile(r"^col\d+$|\s#\d+$|unnamed", re.I)
def spaced(lst, n):
    if len(lst) <= n: return lst
    return [lst[int(i * len(lst) / n)] for i in range(n)]
from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
recs = [json.loads(l) for l in open(HERE / "excel_rows.jsonl", encoding="utf-8")]
dropped, keep_sum, rows = [], [], collections.defaultdict(lambda: collections.defaultdict(list))
for r in recs:
    bad_psi = r["psi"] in ("PSI-25", "PSI-26")
    if r["row"] == "summary":
        cols = [c.strip() for c in r["fields"].get("columns", "").split(", ")]
        if bad_psi and any(BAD.search(c) for c in cols):
            dropped.append((r["psi"], r["source_file"], r["sheet"], "summary", "placeholder column names")); continue
        keep_sum.append(r)
    else:
        if bad_psi and any(BAD.search(k) for k in r["fields"]):
            dropped.append((r["psi"], r["source_file"], r["sheet"], r["row"], "placeholder column names")); continue
        rows[r["psi"]][(r["source_file"], r["sheet"])].append(r)
kept_rows = []
for psi, sheets in rows.items():
    sel = []
    for k, lst in sheets.items():
        sel += spaced(lst, 25)
    kept_rows += spaced(sel, 150)
out = keep_sum + kept_rows
for r in out: r["text"] = r["text"][:1500]
with open(HERE / "excel_rows_trimmed.jsonl", "w", encoding="utf-8") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
# dropped csv: summarise per (file, sheet)
agg = collections.Counter((d[0], d[1], d[2], d[3] == "summary") for d in dropped)
with open(HERE / "excel_dropped.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["psi", "file", "sheet", "type", "records_dropped", "reason"])
    for (p, fi, s, isum), n in sorted(agg.items()):
        w.writerow([p, fi, s, "summary" if isum else "rows", n, "placeholder column names"])
print("total", len(out), "| summaries", len(keep_sum), "| rows", len(kept_rows), "| dropped records", len(dropped))
c = collections.Counter((r["psi"], "summary" if r["row"] == "summary" else "row") for r in out)
for (p, t), n in sorted(c.items(), key=lambda x: (int(x[0][0][4:]), x[0][1])): print(f"{p:8}{t:8}{n}")
print("dropped summaries:", sum(1 for d in dropped if d[3] == "summary"))
random.seed(1)
for r in random.sample(out, 5): print("-", r["text"][:300])
