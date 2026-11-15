import csv, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE = "https://psi.nasa.gov/geode-py/ws"
from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
OUT, PLAN = str(RAW), str(HERE / "plan.csv")
MODE = sys.argv[1] if len(sys.argv) > 1 else "core"      # core | data | rest
WORKERS = 6
EXT = {"core": {".csv", ".pdf", ".docx"},
       "data": {".xlsx", ".xls"},
       "rest": {".pptx", ".txt"}}[MODE]

def safe(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)

def fetch(pid, name, dest):
    err = ""
    for attempt in range(1, 4):
        try:
            with requests.get(f"{BASE}/studies/{pid}/download", params={"file": name},
                              stream=True, timeout=(30, 300)) as r:
                if r.status_code in (429, 500, 502, 503, 504):
                    err = f"http {r.status_code}"; time.sleep(5 * attempt); continue
                if r.status_code != 200:
                    return f"http {r.status_code}"
                with open(dest + ".part", "wb") as f:
                    for chunk in r.iter_content(1024 * 256):
                        f.write(chunk)
            os.replace(dest + ".part", dest)
            return "ok"
        except Exception as e:
            err = "error " + str(e)[:80]; time.sleep(5 * attempt)
    return err

def work(r):
    pid, name = r["psi"], r["file"]
    folder = os.path.join(OUT, pid)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, safe(name))
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return r, "skipped", 0
    st = fetch(pid, name, dest)
    return r, st, (os.path.getsize(dest) if st == "ok" else 0)

rows = [r for r in csv.DictReader(open(PLAN, encoding="utf-8"))
        if os.path.splitext(r["file"])[1].lower() in EXT]
print(f"mode={MODE}, files: {len(rows)}, workers: {WORKERS}")

ok = fail = skipped = 0
mb = 0.0
log = []
t0 = time.time()
ex = ThreadPoolExecutor(max_workers=WORKERS)
try:
    futs = [ex.submit(work, r) for r in rows]
    for n, fu in enumerate(as_completed(futs), 1):
        r, st, size = fu.result()
        if st == "ok":
            ok += 1; mb += size / 1e6
        elif st == "skipped":
            skipped += 1
        else:
            fail += 1; log.append([r["psi"], r["file"], st])
            print(f"  FAIL {r['psi']} | {r['file'][:55]} | {st}")
        if n % 10 == 0:
            print(f"[{n}/{len(rows)}] ok={ok} fail={fail} skipped={skipped} "
                  f"{mb:.0f} MB in {(time.time()-t0)/60:.1f} min")
        if ok == 0 and fail >= 15:
            print("STOP: first 15 downloads failed. Send me the FAIL lines.")
            break
except KeyboardInterrupt:
    print("Interrupted. Run the same command again to resume.")
finally:
    ex.shutdown(wait=False, cancel_futures=True)

with open(HERE / f"download_log_{MODE}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["psi", "file", "status"]); w.writerows(log)
print(f"FINISHED {MODE}: ok={ok} fail={fail} skipped={skipped}, {mb:.0f} MB in {(time.time()-t0)/60:.1f} min")