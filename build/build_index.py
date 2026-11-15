import os
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
import csv, hashlib, json, logging, os, re, time
import importlib
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)

from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
ROOT = str(RAW)
RUNS = str(HERE / "runs.jsonl")
INDEX_DIR = str(INDEX)
COLLECTION = "nasa_kb"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
CHUNK_CHARS, OVERLAP = 1200, 150
# raw lab sheets / plots: scanned or axis labels only, they add noise
SKIP_NAME = re.compile(r"flow traces|test sheets?|tests sheets|test parameter|test point log", re.I)
TAG = re.compile(r"<[^>]+>")

_model = None
def embed_texts(texts):
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        for attempt in range(1, 6):
            try:
                _model = TextEmbedding(EMBED_MODEL)
                break
            except Exception as e:
                print(f"model load attempt {attempt}/5 failed: {e}", flush=True)
                if attempt == 5:
                    raise
                time.sleep(5 * attempt)
    return [v.tolist() for v in _model.embed(texts, batch_size=32)]

def doc_type(name):
    m = re.match(r"PSI-\d+_([^_]+)_", name)
    return m.group(1) if m else "Other"

def chunk_text(t):
    t = re.sub(r"[ \t]+", " ", t).strip()
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    if len(t) <= CHUNK_CHARS:
        return [t] if len(t) >= 30 else []
    out, start = [], 0
    while start < len(t):
        end = min(start + CHUNK_CHARS, len(t))
        if end < len(t):
            cut = max(t.rfind("\n", start, end), t.rfind(". ", start, end))
            if cut > start + CHUNK_CHARS // 2:
                end = cut + 1
        piece = t[start:end].strip()
        if len(piece) >= 30:
            out.append(piece)
        if end >= len(t):
            break
        start = max(end - OVERLAP, start + 1)
    return out

def flat(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return "; ".join(x for x in (flat(i) for i in v) if x)
    if isinstance(v, dict):
        return "; ".join(str(x) for x in v.values() if isinstance(x, (str, int, float)) and x)
    return re.sub(r"\s+", " ", TAG.sub(" ", str(v))).strip()

META_FIELDS = [("objective", "Objective"), ("approach", "Approach"), ("hypothesis", "Hypothesis"),
               ("description", "Description"), ("researchImpacts", "Research impacts"),
               ("experimentHardware", "Hardware")]

def main():
    t0 = time.time()
    items, skipped, seen = [], [], set()
    names = {}

    def add(raw, prefix, psi, dtype, fname, loc, key=None):
        h = hashlib.md5(re.sub(r"\s+", " ", key or raw).strip().lower().encode("utf-8")).hexdigest()
        if h in seen:
            return False
        seen.add(h)
        items.append((prefix + raw, {"psi": psi, "doc_type": dtype, "file": fname, "loc": loc}))
        return True

    # 1. metadata documents
    for mp in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, mp, "metadata.json")
        if not os.path.exists(path):
            continue
        d = json.load(open(path, encoding="utf-8"))
        psi = mp
        title = flat(d.get("title"))
        acr = flat(d.get("investigationAcronym"))
        names[psi] = acr or title[:50]
        prefix = f"[{psi} | {names[psi]} | Metadata] "
        parts = [(label, flat(d.get(key))) for key, label in META_FIELDS]
        parts.insert(0, ("Title", title + (f" ({acr})" if acr else "")))
        for label, val in parts:
            for c in chunk_text(val):
                add(c, prefix + f"{label}: ", psi, "Metadata", "metadata.json", label)
        pubs = d.get("publications") or []
        lines = []
        for p in pubs:
            s = flat(p)[:300]
            if s:
                lines.append(s)
        for i in range(0, len(lines), 5):
            add("\n".join(lines[i:i + 5]), prefix + "Publications: ", psi, "Metadata",
                "metadata.json", f"publications {i + 1}-{min(i + 5, len(lines))}")
    n_meta = len(items)
    print(f"metadata chunks: {n_meta}", flush=True)

    # 2. table rows
    n0 = len(items)
    if os.path.exists(RUNS):
        for line in open(RUNS, encoding="utf-8"):
            r = json.loads(line)
            add(r["text"], "", r["psi"], "Table row", r["source_file"], f"row {r['row']}",
                key=r["psi"] + r["experiment"] + json.dumps(r["fields"], sort_keys=True))
    print(f"table-row chunks: {len(items) - n0}", flush=True)

    # 3. PDFs
    pdfs = sorted(p for p in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, p)))
    files = []
    for folder in pdfs:
        for f in sorted(os.listdir(os.path.join(ROOT, folder))):
            if f.lower().endswith(".pdf"):
                files.append((folder, f))
    n0 = len(items)
    for k, (psi, f) in enumerate(files, 1):
        if SKIP_NAME.search(f):
            skipped.append((f, "raw lab sheet/plot"))
            continue
        try:
            rd = PdfReader(os.path.join(ROOT, psi, f))
            if rd.is_encrypted:
                rd.decrypt("")
            pages = []
            for i, pg in enumerate(rd.pages, 1):
                try:
                    pages.append((i, pg.extract_text() or ""))
                except Exception:
                    pages.append((i, ""))
        except Exception as e:
            skipped.append((f, "error: " + str(e)[:60]))
            continue
        if sum(len(t) for _, t in pages) < 200:
            skipped.append((f, "no extractable text"))
            continue
        dt = doc_type(f)
        prefix = f"[{psi} | {names.get(psi, psi)} | {dt} | {f[:70]}] "
        for pno, txt in pages:
            for c in chunk_text(txt):
                add(c, prefix, psi, dt, f, f"p.{pno}")
        if k % 20 == 0:
            print(f"  pdf {k}/{len(files)} chunks so far: {len(items)}", flush=True)
    print(f"pdf chunks: {len(items) - n0}  (skipped files: {len(skipped)})", flush=True)

    with open(HERE / "index_skipped.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "reason"])
        w.writerows(skipped)

    # 4. embed + store
    try:
        chromadb = importlib.import_module("chromadb")
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is required to build the index; install it with 'pip install chromadb'."
        ) from exc
    client = chromadb.PersistentClient(path=INDEX_DIR)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    B = 128
    print(f"embedding {len(items)} chunks (first run downloads the model)...", flush=True)
    for i in range(0, len(items), B):
        batch = items[i:i + B]
        col.add(ids=[f"c{i + j}" for j in range(len(batch))],
                documents=[b[0] for b in batch],
                embeddings=embed_texts([b[0] for b in batch]),
                metadatas=[b[1] for b in batch])
        if (i // B) % 10 == 0:
            print(f"  embedded {min(i + B, len(items))}/{len(items)}", flush=True)

    counts = {}
    for _, m in items:
        counts[m["doc_type"]] = counts.get(m["doc_type"], 0) + 1
    print("\nDONE:", len(items), "chunks in", round((time.time() - t0) / 60, 1), "min")
    for k2, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k2:24} {v}")
    print("skipped files are listed in index_skipped.csv")

if __name__ == "__main__":
    main()