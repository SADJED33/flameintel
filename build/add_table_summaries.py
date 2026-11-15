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
EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # must match build_index.py / chat.py
SRC = str(HERE / "table_summaries.jsonl")
LOG = str(HERE / "table_summaries_add_log.txt")

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
    items = []
    for line in open(SRC, encoding="utf-8"):
        r = json.loads(line)
        items.append((r["text"], {"psi": r["psi"], "doc_type": "Table summary",
                                  "file": r["source_file"], "loc": "summary"}))
    chromadb = importlib.import_module("chromadb")
    client = chromadb.PersistentClient(path=INDEX_DIR)
    col = client.get_collection(COLLECTION)          # existing collection: never deleted or recreated
    with open(LOG, "a", encoding="utf-8") as log:
        before = col.count()
        say(f"collection has {before} items; upserting {len(items)} table summaries", log)
        # upsert with ids t0..: re-running overwrites the same ids instead of duplicating
        col.upsert(ids=[f"t{i}" for i in range(len(items))],
                   documents=[t for t, _ in items],
                   embeddings=embed_texts([t for t, _ in items]),
                   metadatas=[m for _, m in items])
        after = col.count()
        say(f"DONE: collection now {after} items (+{after - before})", log)


if __name__ == "__main__":
    main()
