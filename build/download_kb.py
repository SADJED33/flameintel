import csv, os, re, sys, time
import requests

BASE = "https://psi.nasa.gov/geode-py/ws"
from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
OUT = str(RAW)
PLAN = str(HERE / "plan.csv")
MODE = sys.argv[1] if len(sys.argv) > 1 else "pass1"   # test | pass1 | all

def safe(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)

rows = list(csv.DictReader(open(PLAN, encoding="utf-8")))
if MODE in ("test", "pass1"):
    rows = [r for r in rows if not r["file"].lower().endswith(".txt")]
if MODE == "test":
    rows = rows[:3]

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (NASA Space Apps research)"

def fetch(pid, name, dest):
    url = f"{BASE}/studies/{pid}/download"
    err = ""
    for attempt in range(1, 4):
        try:
            with session.get(url, params={"file": name}, stream=True,
                             timeout=(30, 300)) as r:
                if r.status_code in (429, 500, 502, 503, 504):
                    err = f"http {r.status_code}"
                    time.sleep(5 * attempt)
                    continue
                if r.status_code != 200:
                    return f"http {r.status_code}"
                tmp = dest + ".part"
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1024 * 256):
                        f.write(chunk)
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:
            err = "error " + str(e)[:80]
            time.sleep(5 * attempt)
    return err

def folder_size():
    total = 0
    for root, _, files in os.walk(OUT):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total

log, done, fail, skipped = [], 0, 0, 0
total = len(rows)
print(f"mode={MODE}, files in this run: {total}")

try:
    for i, r in enumerate(rows, 1):
        pid, name = r["psi"], r["file"]
        folder = os.path.join(OUT, pid)
        os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, safe(name))

        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            skipped += 1
            continue

        status = fetch(pid, name, dest)
        if status == "ok":
            done += 1
        else:
            fail += 1
            log.append([pid, name, status])
            print(f"  FAIL {pid} | {name[:60]} | {status}")

        if i % 25 == 0 or i <= 3:
            print(f"[{i}/{total}] ok={done} fail={fail} skipped={skipped}")

        if done == 0 and fail >= 15:
            print("\nSTOP: first 15 downloads all failed. Copy the FAIL lines above and send them to me.")
            break
        time.sleep(0.2)
except KeyboardInterrupt:
    print("\nInterrupted. Run the same command again and it will resume.")

with open(HERE / "download_log.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["psi", "file", "status"])
    w.writerows(log)

print(f"\nFINISHED: ok={done} fail={fail} skipped(already had)={skipped}")
print(f"kb_raw size: {folder_size() / 1e9:.2f} GB")
print("failures are listed in download_log.csv")