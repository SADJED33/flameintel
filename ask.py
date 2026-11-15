import os
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
import sys
from pathlib import Path
import chromadb
from fastembed import TextEmbedding

INDEX_DIR = str(Path(__file__).resolve().parent / "data" / "kb_index")
COLLECTION = "nasa_kb"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # must match build_index.py
TOP_K = 6

def main():
    if len(sys.argv) < 2:
        print('usage: python ask.py "your question"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    model = TextEmbedding(EMBED_MODEL)
    qv = next(iter(model.query_embed(question))).tolist()
    col = chromadb.PersistentClient(path=INDEX_DIR).get_collection(COLLECTION)
    res = col.query(query_embeddings=[qv], n_results=TOP_K,
                    include=["documents", "metadatas", "distances"])
    for doc, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"[{m['psi']} | {m['doc_type']} | {m['file']} | {m['loc']}] distance={dist:.3f}")
        print(doc[:400].replace("\n", " "))
        print()

if __name__ == "__main__":
    main()
