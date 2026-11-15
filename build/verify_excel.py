import os
os.environ["HF_HUB_DISABLE_XET"]="1"
import sys, collections, chromadb
from fastembed import TextEmbedding
MAXD, FETCH_K, PER_FILE, KEEP = 0.40, 40, 3, 8
model = TextEmbedding("BAAI/bge-small-en-v1.5")
def open_col(p): return chromadb.PersistentClient(path=p).get_collection("nasa_kb")
def retr(col, q):
    qv = next(iter(model.query_embed(q))).tolist()
    res = col.query(query_embeddings=[qv], n_results=FETCH_K, include=["documents","metadatas","distances"])
    out, per = [], {}
    for doc, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if d > MAXD: continue
        k = (m["psi"], m["file"])
        if per.get(k,0) >= PER_FILE: continue
        per[k] = per.get(k,0)+1
        out.append((m, d, doc))
        if len(out) >= KEEP: break
    return out
from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
new = open_col(str(INDEX)); old = open_col(str(ROOT_DIR / "_archive" / "kb_index_pre_tablesum"))  # live index vs the backup
print("count new", new.count(), "old", old.count())
r = new.get(include=["metadatas"])
print(collections.Counter(m["doc_type"] for m in r["metadatas"]).most_common())
print("\n=== EXCEL QUESTIONS (top 5) ===")
for q in ["what channels did the SAFFIRE smoke detector record","oxygen concentration range in SAFFIRE-III",
          "flame spread rate measured in SAME-R","radiometer data in SAFFIRE experiments"]:
    print("\nQ:", q)
    for m,d,doc in retr(new,q)[:5]:
        print(f"  {m['psi']} | {m['doc_type']} | {m['file'][:50]} | {m['loc'][:30]} | {d:.3f} | {doc[:150]!r}")
print("\n=== REGRESSION ===")
for q in ["cotton fiberglass flammability","smoke detectors in low gravity","limiting oxygen index of cotton",
          "Mars trap","kitchen fire trap","What is the capital of France?"]:
    a, b = retr(old,q), retr(new,q)
    nx = sum(1 for m,_,_ in b if m["doc_type"].startswith("Excel"))
    print(f"\nQ: {q}\n  old kept={len(a)} best={a[0][1]:.3f}" if a else f"\nQ: {q}\n  old kept=0", end="")
    print(f" | new kept={len(b)} best={b[0][1]:.3f} excel_in_kept={nx}" if b else f" | new kept=0 excel=0")
    oa = [(m["psi"],m["file"],m["loc"]) for m,_,_ in a]; nb = [(m["psi"],m["file"],m["loc"]) for m,_,_ in b]
    print("  same top-8 sources:", oa == nb, "| old-only:", len(set(oa)-set(nb)), "new-only:", len(set(nb)-set(oa)))
    for m,d,_ in b:
        if m["doc_type"].startswith("Excel"): print(f"   excel in kept: {m['psi']} {m['doc_type']} {m['loc'][:30]} {d:.3f}")
