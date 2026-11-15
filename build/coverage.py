import requests, json, os, csv, sys, time

BASE = "https://psi.nasa.gov/geode-py/ws"
IDS = [10,20,21,22,23,25,26,39,47,60,62,68,69,98,99,100,101,102,106,107,115,117,142,159]
PRIORITY = {25,26,98,99,100,101,102,107,68,69,47,60,62,115}   # fire-safety direct
CAP = 5 * 1024**3                 # 5 GB total
DOC_EXT  = {".pdf", ".docx", ".pptx", ".txt"}
DATA_EXT = {".csv", ".xlsx", ".xls"}
DOC_MAX, DATA_MAX, PER_EXP_DATA = 100*1024**2, 50*1024**2, 300*1024**2
from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
OUT = str(RAW)
os.makedirs(OUT, exist_ok=True)

def meta(pid):
    path = os.path.join(OUT, pid, "metadata.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    for a in range(4):
        try:
            d = requests.get(f"{BASE}/repo/investigations/{pid}", timeout=600).json()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            return d
        except Exception as e:
            print("  retry", a+1, str(e)[:70]); time.sleep(10)
    return None

plan = []
for n in IDS:
    pid = f"PSI-{n}"
    print("planning", pid)
    d = meta(pid)
    if not d:
        print("  FAILED", pid); continue
    used_data = 0
    for f in (d.get("experimentalTable") or []):
        plan.append((pid, f["file_name"], f.get("file_size") or 0, "A-table"))
    for f in (d.get("added") or []):
        name, size = f.get("file_name",""), f.get("file_size") or 0
        ext = os.path.splitext(name)[1].lower()
        if ext in DOC_EXT and size <= DOC_MAX:
            plan.append((pid, name, size, "B-doc"))
        elif ext in DATA_EXT and size <= DATA_MAX and n in PRIORITY and used_data + size <= PER_EXP_DATA:
            used_data += size
            plan.append((pid, name, size, "C-data"))

order = {"A-table": 0, "B-doc": 1, "C-data": 2}
plan.sort(key=lambda r: order[r[3]])
total, keep = 0, []
for r in plan:
    if total + r[2] <= CAP:
        keep.append(r); total += r[2]

with open(HERE / "plan.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["psi","file","bytes","tier"]); w.writerows(keep)
for t in order:
    s = sum(r[2] for r in keep if r[3] == t)
    print(f"{t}: {sum(1 for r in keep if r[3]==t)} files, {s/1e6:.1f} MB")
print(f"TOTAL planned: {total/1e9:.2f} GB (cap 5 GB)")

if len(sys.argv) > 1 and sys.argv[1] == "download":
    for pid, name, size, tier in keep:
        dest = os.path.join(OUT, pid, name)
        if os.path.exists(dest): continue
        try:
            r = requests.get(f"{BASE}/studies/{pid}/download", params={"file": name}, timeout=600)
            if r.status_code == 200:
                open(dest, "wb").write(r.content)
            else:
                print("  http", r.status_code, pid, name)
        except Exception as e:
            print("  error", pid, name, str(e)[:70])
        time.sleep(0.2)
    print("download finished")