"""Dataset catalog + preview built with pandas on the REAL files in raw/ (CSV / XLS / XLSX only).
Nothing here invents a column, a unit or a value:
  - columns, dtypes, counts and the first 50 rows come straight from the parsed file
  - a unit is reported only when the column header itself states one, e.g. "Burn Time (s)" or "Flow [cm/s]"
  - large files are read up to ROW_CAP rows, and the response says so (truncated=True)
"""
import hashlib
import json
import math
import re
from datetime import date, datetime

import pandas as pd

import config as C

ROW_CAP = 20000          # rows scanned for a preview
EXPORT_CAP = 200000      # rows written by the CSV export
CACHE_DIR = C.DATA_DIR / "cache"
EXT = {".csv": "csv", ".xls": "xls", ".xlsx": "xlsx"}

_CATALOG = None
_INDEX = None


def _index_files():
    global _INDEX
    if _INDEX is None:
        p = C.DATA_DIR / "index_files.json"
        _INDEX = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _INDEX


def _skipped_sheets():
    """file -> number of skipped sheets (build/excel_skipped.csv) and dropped sheets (excel_dropped.csv)"""
    import csv
    out = {}
    for name, key in (("excel_skipped.csv", "skipped"), ("excel_dropped.csv", "dropped")):
        p = C.BUILD_DIR / name
        if p.exists():
            with open(p, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    out.setdefault(r["file"], {"skipped": 0, "dropped": 0})[key] += 1
    return out


def _category(name):
    m = re.match(r"PSI-\d+_([^_]+)_", name)
    return m.group(1) if m else "Other"


def catalog():
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    idx, sk = _index_files(), _skipped_sheets()
    exps = json.loads((C.KB_DATA / "experiments.json").read_text(encoding="utf-8"))
    out = []
    for d in sorted(C.RAW_DIR.glob("PSI-*"), key=lambda p: int(p.name.split("-")[1])):
        for f in sorted(d.iterdir()):
            fmt = EXT.get(f.suffix.lower())
            if not fmt:
                continue
            chunks = idx.get(f.name, {})
            s = sk.get(f.name, {})
            if chunks:
                status = "indexed" if not s.get("skipped") and not s.get("dropped") else "partly indexed"
                detail = f"{sum(chunks.values())} rows/summaries in the search index"
                if s.get("skipped") or s.get("dropped"):
                    detail += f"; {s.get('skipped', 0)} sheet(s) skipped (empty or no header) and {s.get('dropped', 0)} dropped (placeholder column names)"
            else:
                status = "not indexed"
                detail = "Not in the search index. It can still be previewed here."
            out.append({
                "id": d.name + "~" + hashlib.sha1(f.name.encode()).hexdigest()[:8],
                "psi": d.name, "acronym": exps.get(d.name, {}).get("acronym", ""), "file_name": f.name,
                "display_name": re.sub(r"^PSI-\d+_", "", f.name), "format": fmt, "category": _category(f.name),
                "size_kb": round(f.stat().st_size / 1024, 1), "path": str(f),
                "extraction_status": status, "extraction_detail": detail,
                "indexed_chunks": sum(chunks.values()),
            })
    _CATALOG = out
    return out


def find(ds_id):
    return next((d for d in catalog() if d["id"] == ds_id), None)


def public(d):
    return {k: v for k, v in d.items() if k != "path"}


def list_datasets(psi="", q="", fmt="", category=""):
    out = []
    for d in catalog():
        if psi and d["psi"].lower() != psi.lower():
            continue
        if fmt and d["format"] != fmt:
            continue
        if category and d["category"] != category:
            continue
        if q and q.lower() not in d["file_name"].lower():
            continue
        out.append(public(d))
    return out


# ------------------------------------------------------------------ parsing
def _read(path, fmt, sheet, nrows):
    if fmt == "csv":
        last = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(path, encoding=enc, nrows=nrows, low_memory=False), ["(csv)"]
            except UnicodeDecodeError as e:
                last = e
            except pd.errors.EmptyDataError:
                return pd.DataFrame(), ["(csv)"]
        raise last  # pragma: no cover
    engine = "openpyxl" if fmt == "xlsx" else "xlrd"
    xl = pd.ExcelFile(path, engine=engine)
    names = list(xl.sheet_names)
    use = sheet if sheet in names else names[0]
    return xl.parse(use, nrows=nrows), names, use


def _py(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (datetime, date, pd.Timestamp)):
        return str(v)
    if hasattr(v, "item"):
        try:
            return _py(v.item())
        except Exception:
            return str(v)
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def documented_unit(col):
    """a unit only if the header says one: 'Name (unit)' or 'Name [unit]'"""
    m = re.search(r"[(\[]([^)\]]{1,24})[)\]]\s*$", str(col))
    return m.group(1).strip() if m else None


def _cache_path(ds_id, sheet):
    return CACHE_DIR / (re.sub(r"[^A-Za-z0-9_.-]", "_", f"{ds_id}__{sheet or 'first'}") + ".json")


def preview(ds_id, sheet=""):
    d = find(ds_id)
    if not d:
        return None
    cp = _cache_path(ds_id, sheet)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    res = {"dataset": public(d), "ok": False, "sheets": [], "sheet": None, "error": None}
    try:
        got = _read(d["path"], d["format"], sheet, ROW_CAP + 1)
        df, names = got[0], got[1]
        used = got[2] if len(got) > 2 else None
    except Exception as e:
        res["error"] = f"This file could not be parsed ({type(e).__name__}). It is listed but not previewable."
        return res
    res["sheets"], res["sheet"] = (names if d["format"] != "csv" else []), used
    truncated = len(df) > ROW_CAP
    df = df.iloc[:ROW_CAP]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all") if not df.empty else df
    n = len(df)
    cols = []
    for c in df.columns:
        s = df[c]
        miss = int(s.isna().sum())
        nn = s.dropna()
        info = {
            "name": str(c), "dtype": str(s.dtype), "unit": documented_unit(c),
            "missing": miss, "missing_pct": round(100 * miss / n, 1) if n else 0.0,
            "unique": int(nn.nunique()) if n else 0,
            "examples": [_py(x) for x in nn.head(3).tolist()],
        }
        if pd.api.types.is_numeric_dtype(s) and len(nn):
            info["min"], info["max"] = _py(nn.min()), _py(nn.max())
        cols.append(info)
    unnamed = sum(1 for c in df.columns if str(c).startswith("Unnamed"))
    notes = []
    if n == 0:
        notes.append("The sheet has no rows with data.")
    if cols and unnamed / len(cols) > 0.5:
        notes.append("Most column names are 'Unnamed': the header row is probably not the first row of this sheet. Names are shown exactly as parsed.")
    if cols and not any(c["unit"] for c in cols):
        notes.append("No column header states a unit, so none is shown. Check the original document before using values.")
    if truncated:
        notes.append(f"Large sheet: only the first {ROW_CAP:,} rows were scanned, so counts cover those rows.")
    res.update({
        "ok": True, "rows": n, "columns_count": len(cols), "truncated": truncated, "row_cap": ROW_CAP,
        "columns": cols, "rows_preview": [[_py(v) for v in row] for row in df.head(50).itertuples(index=False, name=None)],
        "quality_notes": notes,
        "ml_readiness": ml_readiness(n, cols, truncated),
    })
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


def ml_readiness(n, cols, truncated):
    """Honest checklist (spec 4.6). It can never make a prediction; the verdict is about the data only."""
    numeric = [c for c in cols if c["dtype"].startswith(("int", "float"))]
    with_unit = [c for c in numeric if c["unit"]]
    checks = [
        {"id": "target", "question": "Is the target variable defined?", "status": "fail",
         "detail": "No file in the PSI record documents a prediction target. One would have to be chosen and justified first."},
        {"id": "size", "question": "Are there enough observations?",
         "status": "pass" if n >= 500 else "warn" if n >= 50 else "fail",
         "detail": f"{n:,} usable rows" + (" (first rows only)" if truncated else "") + ". Reliable models usually need several hundred independent runs, not rows of one time series."},
        {"id": "features", "question": "Are features documented?",
         "status": "pass" if numeric and len(with_unit) / len(numeric) >= 0.7 else "warn" if with_unit else "fail",
         "detail": f"{len(with_unit)} of {len(numeric)} numeric columns state a unit in the header; no data dictionary is provided."},
        {"id": "units", "question": "Are units consistent?", "status": "warn" if with_unit else "fail",
         "detail": "Consistency cannot be verified from this file alone; undocumented units are not assumed."},
        {"id": "conditions", "question": "Are experimental conditions comparable?", "status": "warn",
         "detail": "Different tests use different materials, flow and oxygen levels. Conditions must be matched before pooling runs."},
        {"id": "eval", "question": "Is there a valid evaluation method?", "status": "fail" if n < 50 else "warn",
         "detail": "Needs a split by experiment run (not by row) to avoid leakage. None is defined here."},
    ]
    fails = [c for c in checks if c["status"] == "fail" and c["id"] in ("target", "size", "eval")]
    verdict = ("not_ready" if fails else "exploratory")
    return {
        "checks": checks, "verdict": verdict,
        "message": ("Not enough suitable data for reliable prediction." if verdict == "not_ready"
                    else "May support exploratory analysis only. A target, matched conditions and a run-level validation plan are still needed. No model is trained here."),
        "note": "FlameIntel shows a data-readiness assessment, never a prediction.",
    }


def export_csv(ds_id, sheet=""):
    d = find(ds_id)
    if not d:
        return None
    got = _read(d["path"], d["format"], sheet, EXPORT_CAP)
    df = got[0].dropna(axis=1, how="all").dropna(axis=0, how="all")
    return df.to_csv(index=False), re.sub(r"[^A-Za-z0-9_.-]", "_", d["display_name"].rsplit(".", 1)[0]) + (f"__{sheet}" if sheet else "") + ".csv"
