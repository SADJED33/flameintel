import csv, os, glob, logging
from pypdf import PdfReader
logging.getLogger("pypdf").setLevel(logging.ERROR)

from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
ROOT = str(RAW)

# 1. preview every experimental table
with open(HERE / "tables_preview.txt", "w", encoding="utf-8") as out:
    for path in sorted(glob.glob(f"{ROOT}/*/*Experimental table*.csv")):
        rows = []
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(path, encoding=enc, newline="") as f:
                    rows = list(csv.reader(f))
                break
            except Exception:
                continue
        out.write(f"\n=== {os.path.basename(path)} | data rows: {max(len(rows)-1, 0)}\n")
        for r in rows[:4]:
            out.write(" | ".join(c[:40] for c in r[:40]) + "\n")
print("wrote tables_preview.txt")

# 2. check that PDFs contain extractable text
rep = []
for path in sorted(glob.glob(f"{ROOT}/*/*.pdf")):
    psi = os.path.basename(os.path.dirname(path))
    name = os.path.basename(path)
    size = os.path.getsize(path)
    try:
        rd = PdfReader(path)
        n = len(rd.pages)
        chars = sum(len(rd.pages[i].extract_text() or "") for i in range(min(3, n)))
        rep.append([psi, name, n, chars, size, ""])
    except Exception as e:
        rep.append([psi, name, "", 0, size, "error: " + str(e)[:60]])

with open(HERE / "pdf_report.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["psi", "file", "pages", "chars_first_3_pages", "bytes", "error"])
    w.writerows(rep)

total = len(rep)
errors = sum(1 for r in rep if r[5])
scanned = sum(1 for r in rep if not r[5] and r[3] < 50)
print(f"PDFs: {total} | readable text: {total - errors - scanned} | scanned/no text: {scanned} | errors: {errors}")