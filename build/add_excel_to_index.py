import os
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
import json, time
import importlib

from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
INDEX_DIR = str(INDEX)
COLLECTION = "nasa_kb"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
SRC = str(HERE / "excel_rows_trimmed.jsonl")
LOG = str(HERE / "excel_add_log.txt")
B = 128

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


def say(msg, log):
    print(msg, flush=True)
    log.write(msg + "\n")
    log.flush()


def main():
    t0 = time.time()
    items = []
    for line in open(SRC, encoding="utf-8"):
        r = json.loads(line)
        summ = r["row"] == "summary"
        items.append((r["text"], {"psi": r["psi"],
                                  "doc_type": "Excel summary" if summ else "Excel row",
                                  "file": r["source_file"],
                                  "loc": f"{r['sheet']} " + ("summary" if summ else f"row {r['row']}")}))
    chromadb = importlib.import_module("chromadb")
    client = chromadb.PersistentClient(path=INDEX_DIR)
    col = client.get_collection(COLLECTION)          # existing collection, never recreated
    with open(LOG, "a", encoding="utf-8") as log:
        say(f"collection has {col.count()} items; adding {len(items)} excel records", log)
        for i in range(0, len(items), B):
            batch = items[i:i + B]
            # upsert: re-running after an interruption just overwrites ids x0.. instead of failing
            col.upsert(ids=[f"x{i + j}" for j in range(len(batch))],
                       documents=[b[0] for b in batch],
                       embeddings=embed_texts([b[0] for b in batch]),
                       metadatas=[b[1] for b in batch])
            say(f"  added {min(i + B, len(items))}/{len(items)}  ({round(time.time() - t0)}s)", log)
        say(f"DONE: collection now {col.count()} items, {round((time.time() - t0) / 60, 1)} min", log)


if __name__ == "__main__":
    main()
