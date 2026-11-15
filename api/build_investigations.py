"""Build api/data/investigations.json from REAL local sources only:
   data/experiments.json, raw/<PSI>/metadata.json, raw/<PSI>/*.csv|xls|xlsx, build/runs.jsonl,
   build/index_skipped.csv, build/excel_skipped.csv, data/known_gaps.txt and the ChromaDB index metadata.
   Topic tags are app-generated keyword tags over the SOURCE text (labelled as such in the UI).

   Run:  python api/build_investigations.py
"""
import collections
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

TABULAR = {".csv", ".xls", ".xlsx"}


def clean(v):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", v or "")).strip() if isinstance(v, str) else ""


def clean_block(v):
    """keep paragraph breaks but drop HTML tags / stray whitespace"""
    if not isinstance(v, str):
        return ""
    v = re.sub(r"<br\s*/?>|</p>", "\n", v, flags=re.I)
    v = re.sub(r"<[^>]+>", " ", v)
    v = re.sub(r"[ \t]+", " ", v)
    return re.sub(r"\n\s*\n+", "\n", v).strip()


def environment_of(meta):
    fp = (meta.get("flightProgram") or "").strip()
    if "ISS" in fp or "International Space Station" in fp:
        return "ISS"
    if "Cygnus" in fp:
        return "Spacecraft (Cygnus)"
    return "Ground / modeling"


def gravity_of(meta):
    if (meta.get("projectType") or "").startswith("Microgravity"):
        return "Microgravity (flight experiment)"
    return "Ground-based / computational (Earth gravity unless the record states otherwise)"


def topics_of(text):
    t = text.lower()
    tags = [name for name, words in C.TOPIC_RULES.items() if any(w in t for w in words)]
    # 'combustion behavior' is a catch-all; keep it only when nothing more specific matched
    if len(tags) > 1 and "combustion behavior" in tags:
        tags.remove("combustion behavior")
    return tags


def read_known_gaps():
    out = collections.defaultdict(list)
    p = C.KB_DATA / "known_gaps.txt"
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) == 3 and parts[0].startswith("PSI-"):
            out[parts[0]].append({"file": parts[1], "problem": parts[2]})
    return out


def read_skipped():
    per = collections.defaultdict(list)
    p = C.BUILD_DIR / "index_skipped.csv"
    if p.exists():
        with open(p, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                m = re.match(r"(PSI-\d+)_", r.get("file", ""))
                if m:
                    per[m.group(1)].append({"file": r["file"], "reason": r.get("reason", "")})
    return per


def read_excel_skipped():
    per = collections.Counter()
    p = C.BUILD_DIR / "excel_skipped.csv"
    if p.exists():
        with open(p, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                m = re.match(r"(PSI-\d+)_", r.get("file", ""))
                if m:
                    per[m.group(1)] += 1
    return per


def index_stats():
    """chunk counts per psi / doc_type from the ChromaDB index; None if chromadb is unavailable"""
    try:
        import chromadb
        col = chromadb.PersistentClient(path=str(C.ROOT / "data" / "kb_index")).get_collection("nasa_kb")
        metas = col.get(include=["metadatas"])["metadatas"]
    except Exception as e:  # pragma: no cover
        print("WARNING: could not read the index:", e)
        return {}, 0
    per = collections.defaultdict(collections.Counter)
    files = collections.defaultdict(collections.Counter)  # tabular file -> {doc_type: chunks}
    for m in metas:
        per[m["psi"]][m["doc_type"]] += 1
        if m["doc_type"] in ("Table row", "Excel row", "Excel summary", "Table summary"):
            files[m["file"]][m["doc_type"]] += 1
    (C.DATA_DIR).mkdir(parents=True, exist_ok=True)
    (C.DATA_DIR / "index_files.json").write_text(json.dumps(files, indent=0), encoding="utf-8")
    return per, len(metas)


def table_summary(psi_dir, meta):
    """materials + condition columns straight from the experimental-table CSV(s) of the record"""
    mats, cols = collections.Counter(), []
    for et in meta.get("experimentalTable") or []:
        fp = psi_dir / et.get("file_name", "")
        if not fp.exists():
            continue
        rows = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(fp, encoding=enc, newline="") as f:
                    rows = list(csv.DictReader(f))
                break
            except Exception:
                continue
        if not rows:
            continue
        for c in rows[0].keys():
            c = (c or "").strip()
            if c and c not in cols:
                cols.append(c)
        mkey = next((k for k in rows[0] if k and re.search(r"material|fuel|sample type", k, re.I)), None)
        if mkey:
            for r in rows:
                v = (r.get(mkey) or "").strip()
                if v and len(v) < 60 and not re.fullmatch(r"[\d.\s%/-]+", v) and not re.search(r"data|pre-test|calibration", v, re.I):
                    mats[v] += 1
    return [m for m, _ in mats.most_common(12)], cols[:40]


def main():
    experiments = json.loads((C.KB_DATA / "experiments.json").read_text(encoding="utf-8"))
    gaps, skipped, xskip = read_known_gaps(), read_skipped(), read_excel_skipped()
    idx, total_chunks = index_stats()
    out, excluded = [], []

    for psi in sorted(experiments, key=lambda s: int(s.split("-")[1])):
        d = C.RAW_DIR / psi
        mp = d / "metadata.json"
        meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
        ex = experiments[psi]
        title = ex.get("title") or clean(meta.get("title"))
        acr = ex.get("acronym") or clean(meta.get("investigationAcronym"))
        blob = " ".join(clean(meta.get(k)) for k in ("title", "objective", "approach", "hypothesis", "description"))
        if any(t in blob.lower() for t in C.EXCLUDE_TERMS):
            excluded.append(psi)
            continue

        files = [p for p in d.iterdir() if p.is_file()] if d.exists() else []
        ext = collections.Counter(p.suffix.lower() for p in files if p.name != "metadata.json")
        tabular = [p for p in files if p.suffix.lower() in TABULAR]
        pubs = [{"title": clean(p.get("title")), "authors": clean(p.get("authorList")),
                 "doi": clean(p.get("doi")), "pubmed_id": clean(p.get("pubMedID"))}
                for p in (meta.get("publications") or []) if clean(p.get("title"))]
        has_data, has_pub = bool(tabular), bool(pubs)
        availability = ("both" if has_data and has_pub else "dataset" if has_data
                        else "publication" if has_pub else "metadata_only")
        materials, cond_cols = table_summary(d, meta)
        doc_types = dict(idx.get(psi, {}))
        pdfs_skipped = skipped.get(psi, [])
        unreadable = [s for s in pdfs_skipped if "extractable" in s["reason"] or s["reason"].startswith("error")]
        doi = clean(meta.get("doi"))
        pi = next((c for c in (meta.get("contacts") or []) if any(
            "Principal" in (r.get("annotationValue") or "") for r in c.get("roles") or [])), None)

        limitations = []
        if meta.get("projectType", "").startswith("Microgravity"):
            limitations.append("Flight experiment in microgravity: results are not directly valid for lunar, Mars or Earth gravity.")
        else:
            limitations.append("Ground-based or computational study: check the record for how it relates to flight conditions.")
        if not has_data:
            limitations.append("No tabular data file was downloaded for this record (metadata and documents only).")
        for g in gaps.get(psi, []):
            limitations.append(f"File not available: {g['file']} ({g['problem']}).")
        if unreadable:
            limitations.append(f"{len(unreadable)} PDF file(s) had no extractable text and are not searchable.")
        if xskip.get(psi):
            limitations.append(f"{xskip[psi]} Excel sheet(s) were skipped (empty or no header row).")
        if psi in ("PSI-68", "PSI-69", "PSI-20"):
            limitations.append("Most of this experiment's data lives in tables/spreadsheets; the text index covers it less deeply than PDFs.")
        if psi in ("PSI-98", "PSI-99", "PSI-100"):
            limitations.append("SAFFIRE-I/II/III documents are very similar; check which experiment a passage belongs to.")

        out.append({
            "id": psi,
            "psi_record_id": psi,
            "acronym": acr,
            "title": title,
            "name": acr or title,
            "description": clean_block(meta.get("description")),
            "objective": clean_block(meta.get("objective")),
            "approach": clean_block(meta.get("approach")),
            "hypothesis": clean_block(meta.get("hypothesis")),
            "research_impacts": clean_block(meta.get("researchImpacts")),
            "hardware": clean(meta.get("experimentHardware")),
            "flight_program": clean(meta.get("flightProgram")),
            "project_type": clean(meta.get("projectType")),
            "environment": environment_of(meta),
            "gravity_condition": gravity_of(meta),
            "research_area": clean(meta.get("researchArea")),
            "managing_center": clean(meta.get("managingNasaCenter")),
            "start_date": clean(meta.get("investigationStartDate")),
            "end_date": clean(meta.get("investigationEndDate")),
            "source_updated_at": clean(meta.get("modifiedDate")),
            "license": clean(meta.get("licenseName")),
            "doi": doi,
            "source_url": f"https://doi.org/{doi}" if doi else "https://psi.nasa.gov/",
            "source_url_note": ("DOI of the PSI record" if doi else f"No DOI in the record; search '{psi}' in the PSI repository"),
            "principal_investigator": (f"{clean(pi.get('firstName'))} {clean(pi.get('lastName'))}".strip() +
                                       (f" ({clean(pi.get('affiliation'))})" if clean(pi.get('affiliation')) else "")) if pi else "",
            "topics": topics_of(blob),
            "materials": materials,
            "condition_columns": cond_cols,
            "publications": pubs,
            "availability": availability,
            "has_dataset": has_data,
            "has_publication": has_pub,
            "file_counts": dict(ext),
            "tabular_file_count": len(tabular),
            "index_chunks": doc_types,
            "index_chunk_total": sum(doc_types.values()),
            "known_gaps": gaps.get(psi, []),
            "unreadable_pdfs": len(unreadable),
            "skipped_files": len(pdfs_skipped),
            "limitations": limitations,
        })

    # ---- global coverage notes (computed, not typed) ----
    all_skipped = [s for v in skipped.values() for s in v]
    unreadable_all = [s for s in all_skipped if "extractable" in s["reason"] or s["reason"].startswith("error")]
    raw_sheet = [s for s in all_skipped if s["reason"].startswith("raw lab")]
    coverage = {
        "investigations": len(out),
        "indexed_chunks": total_chunks,
        "skipped_files_total": len(all_skipped),
        "skipped_raw_lab_sheet_or_plot": len(raw_sheet),
        "pdf_no_extractable_text_or_error": len(unreadable_all),
        "failed_downloads": sum(len(v) for v in gaps.values()),
        "failed_download_files": [dict(psi=k, **g) for k, v in gaps.items() for g in v],
        "excel_sheets_skipped": sum(xskip.values()),
        "excluded_rocket_propellant": excluded,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }
    (C.DATA_DIR).mkdir(parents=True, exist_ok=True)
    (C.DATA_DIR / "investigations.json").write_text(
        json.dumps({"coverage": coverage, "investigations": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(out)} investigations; excluded {excluded or 'none'}; coverage: {json.dumps(coverage)[:400]}")


if __name__ == "__main__":
    main()
