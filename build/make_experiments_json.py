"""Rebuild experiments.json (psi -> acronym, title) from the kb_raw/<psi>/metadata.json files.

Run from anywhere:  python build/make_experiments_json.py
Reads raw/ (or _archive/kb_raw/ if the raw files are archived) and writes data/experiments.json. Uses chat.py's own text cleaning so the values are the same ones chat.py used to read.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = next((p for p in (os.path.join(ROOT, "raw"), os.path.join(ROOT, "_archive", "kb_raw")) if os.path.isdir(p)), None)
if RAW is None:
    sys.exit("raw/ not found (looked in raw/ and _archive/kb_raw)")

def flat(v):  # same cleaning as chat._flat
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", "" if v is None else str(v))).strip()

out = {}
for psi in sorted((d for d in os.listdir(RAW) if d.startswith("PSI-")), key=lambda x: int(x.split("-")[1])):
    path = os.path.join(RAW, psi, "metadata.json")
    if not os.path.exists(path):
        print("no metadata.json for", psi)
        continue
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    out[psi] = {"acronym": flat(d.get("investigationAcronym")), "title": flat(d.get("title"))}
with open(os.path.join(ROOT, "data", "experiments.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"wrote data/experiments.json with {len(out)} experiments from {RAW}")
