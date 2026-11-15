import csv, glob, json, os, re, collections

from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
ROOT = str(RAW)

def read_csv(path):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.reader(f))
        except Exception:
            continue
    return []

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

out = []
for path in sorted(glob.glob(f"{ROOT}/*/*Experimental table*.csv")):
    fname = os.path.basename(path)
    psi = fname.split("_")[0]
    exp = fname.split("_Experimental table_")[-1].rsplit(".csv", 1)[0]
    data = read_csv(path)
    if len(data) < 2:
        continue
    header = [clean(h) for h in data[0]]
    for i, r in enumerate(data[1:], start=2):      # line 1 = header
        vals = {header[j]: clean(r[j])
                for j in range(min(len(header), len(r)))
                if header[j] and clean(r[j])}
        if len(vals) < 2:
            continue
        text = f"{psi} {exp} (row {i}): " + "; ".join(f"{k}: {v}" for k, v in vals.items())
        out.append({"psi": psi, "experiment": exp, "source_file": fname,
                    "row": i, "fields": vals, "text": text})

with open(HERE / "runs.jsonl", "w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

counts = collections.Counter((r["psi"], r["experiment"]) for r in out)
for (psi, exp), n in sorted(counts.items(), key=lambda x: int(x[0][0].split("-")[1])):
    print(f"{psi:8} {exp[:40]:40} {n} rows")
print("TOTAL", len(out), "rows -> runs.jsonl")