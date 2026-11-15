import csv, datetime, glob, json, os, re, collections, hashlib

from pathlib import Path
HERE = Path(__file__).resolve().parent     # build/: scripts and their intermediate files
ROOT_DIR = HERE.parent                     # project root
RAW = ROOT_DIR / "raw"                     # full downloaded NASA data
INDEX = ROOT_DIR / "data" / "kb_index"     # live index
ROOT = str(RAW)
OUT = str(HERE / "excel_rows.jsonl")
SKIPPED = str(HERE / "excel_skipped.csv")
MAX_ROWS_PER_SHEET = 300
CAP = 3000
FIRE = ["PSI-25", "PSI-26", "PSI-98", "PSI-99", "PSI-100", "PSI-101", "PSI-102", "PSI-47",
        "PSI-68", "PSI-69", "PSI-107", "PSI-60", "PSI-115", "PSI-62"]


def clean(s):
    return re.sub(r"\s+", " ", str(s if s is not None else "")).strip()


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


def fmt(v):
    """normalise one cell to a short string ('' if empty)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        if v != v:
            return ""
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return repr(float(f"{v:.4g}"))
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    return clean(v)


def sig(x):
    return repr(float(f"{x:.4g}"))


def load_sheets(path):
    """yield (sheet_name, list_of_rows(list of raw values)); raises on unreadable file."""
    if path.lower().endswith(".xls"):
        import xlrd
        wb = xlrd.open_workbook(path, on_demand=True)
        for sh in wb.sheets():
            rows = []
            for r in range(sh.nrows):
                row = []
                for c in range(sh.ncols):
                    cell = sh.cell(r, c)
                    v = cell.value
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        try:
                            v = xlrd.xldate_as_datetime(v, wb.datemode)
                        except Exception:
                            pass
                    elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        v = None
                    elif cell.ctype == xlrd.XL_CELL_ERROR:
                        v = None
                    row.append(v)
                rows.append(row)
            yield sh.name, rows
            wb.unload_sheet(sh.name)
        wb.release_resources()
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for ws in wb.worksheets:           # chartsheets are not in .worksheets
                yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]
        finally:
            wb.close()


def find_header(rows):
    for i, r in enumerate(rows):
        n = sum(1 for v in r if isinstance(v, str) and clean(v))
        if n >= 3:
            return i
    return None


def looks_like_units(row, nxt):
    cells = [(j, v) for j, v in enumerate(row) if v not in (None, "")]
    if len(cells) < 2:
        return False
    strs = [(j, v) for j, v in cells if isinstance(v, str) and len(clean(v)) <= 14]
    if len(strs) < 0.7 * len(cells):
        return False
    if nxt is None:
        return False
    return any(is_num(nxt[j]) for j, _ in strs if j < len(nxt))


def process_sheet(rows):
    """returns (columns, data) where data = list of (excel_row_no, list_of_raw_values) or None."""
    h = find_header(rows)
    if h is None:
        return None
    header = rows[h]
    start = h + 1
    units = {}
    if start < len(rows):
        nxt = rows[start + 1] if start + 1 < len(rows) else None
        if looks_like_units(rows[start], nxt):
            units = {j: clean(v) for j, v in enumerate(rows[start]) if v not in (None, "")}
            start += 1
    ncol = max((len(r) for r in rows[h:]), default=0)
    data = [(i + 1, r) for i, r in enumerate(rows[start:], start=start)
            if any(v not in (None, "") and fmt(v) != "" for v in r)]
    if not data:
        return None
    keep = [j for j in range(ncol)
            if any(j < len(r) and fmt(r[j]) != "" for _, r in data)]
    names, seen = {}, collections.Counter()
    for j in keep:
        base = clean(header[j]) if j < len(header) and header[j] not in (None, "") else f"col{j + 1}"
        if j in units and units[j] and units[j].lower() not in base.lower():
            base = f"{base} [{units[j]}]"
        seen[base] += 1
        names[j] = base if seen[base] == 1 else f"{base} #{seen[base]}"
    return [(j, names[j]) for j in keep], data


def numeric_stats(cols, data):
    stats = {}
    for j, name in cols:
        vals = [r[j] for _, r in data if j < len(r) and r[j] not in (None, "")]
        nums = [v for v in vals if is_num(v)]
        if nums and len(nums) >= 0.8 * len(vals):
            stats[name] = (min(nums), max(nums), sum(nums) / len(nums))
    return stats


def main():
    out, skipped, seen = [], [], set()
    names = {}
    for mp in os.listdir(ROOT):
        p = os.path.join(ROOT, mp, "metadata.json")
        if os.path.exists(p):
            try:
                d = json.load(open(p, encoding="utf-8"))
                a = d.get("investigationAcronym")
                a = "; ".join(map(str, a)) if isinstance(a, list) else (a or "")
                names[mp] = clean(a) or clean(d.get("title"))[:50] or mp
            except Exception:
                pass

    files = sorted(set(glob.glob(f"{ROOT}/PSI-*/*.xlsx") + glob.glob(f"{ROOT}/PSI-*/*.xls")))
    print("excel files found:", len(files), flush=True)
    for k, path in enumerate(files, 1):
        fname = os.path.basename(path)
        psi = os.path.basename(os.path.dirname(path))
        exp = names.get(psi, psi)

        def skip(sheet, reason):
            skipped.append((fname, sheet, reason))

        if os.path.getsize(path) < 1024:
            skip("", "under 1 KB")
            continue
        try:
            n_sheets = 0
            for sname, rows in load_sheets(path):
                n_sheets += 1
                res = process_sheet(rows)
                if res is None:
                    skip(sname, "empty sheet or no header row")
                    continue
                cols, data = res
                if len(data) <= MAX_ROWS_PER_SHEET:
                    for rno, r in data:
                        vals = {}
                        for j, name in cols:
                            s = fmt(r[j]) if j < len(r) else ""
                            if s:
                                vals[name] = s
                        if len(vals) < 2:
                            continue
                        key = hashlib.md5((psi + exp + json.dumps(vals, sort_keys=True)).encode()).hexdigest()
                        if key in seen:
                            continue
                        seen.add(key)
                        text = f"{psi} {exp} (sheet {sname}, row {rno}): " + \
                               "; ".join(f"{a}: {b}" for a, b in vals.items())
                        out.append({"psi": psi, "experiment": exp, "source_file": fname, "sheet": sname,
                                    "row": rno, "fields": vals, "text": text})
                else:
                    stats = numeric_stats(cols, data)
                    colnames = [n for _, n in cols]
                    first = []
                    for rno, r in data[:3]:
                        first.append("; ".join(f"{n}: {fmt(r[j])}" for j, n in cols
                                               if j < len(r) and fmt(r[j]))[:400])
                    fields = {"file": fname, "sheet": sname, "columns": ", ".join(colnames),
                              "row count": str(len(data))}
                    for n, (lo, hi, mean) in list(stats.items())[:40]:
                        fields[n] = f"min {sig(lo)}, max {sig(hi)}, mean {sig(mean)}"
                    for i, s in enumerate(first, 1):
                        fields[f"first row {i}"] = s
                    key = hashlib.md5((psi + exp + json.dumps(fields, sort_keys=True)).encode()).hexdigest()
                    if key in seen:
                        continue
                    seen.add(key)
                    text = (f"{psi} {exp} (sheet {sname}, summary): file {fname}; {len(data)} data rows; "
                            f"columns: {', '.join(colnames)[:700]}; "
                            + "; ".join(f"{n}: min {sig(lo)}, max {sig(hi)}, mean {sig(mean)}"
                                        for n, (lo, hi, mean) in list(stats.items())[:40])
                            + "; first 3 rows: " + " | ".join(first))
                    out.append({"psi": psi, "experiment": exp, "source_file": fname, "sheet": sname,
                                "row": "summary", "fields": fields, "text": text})
            if n_sheets == 0:
                skip("", "no worksheets (charts only?)")
        except Exception as e:
            skip("", "cannot open: " + str(e)[:80])
        if k % 20 == 0:
            print(f"  file {k}/{len(files)} records so far: {len(out)}", flush=True)

    # cap: summaries first, then fire-safety rows, then the rest
    total = len(out)
    if total > CAP:
        rank = {p: i for i, p in enumerate(FIRE)}
        summ = [r for r in out if r["row"] == "summary"]
        rows = [r for r in out if r["row"] != "summary"]
        rows.sort(key=lambda r: rank.get(r["psi"], len(FIRE)))   # stable
        out = (summ + rows)[:CAP]
        print(f"cap applied: {total} -> {len(out)}")

    with open(OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(SKIPPED, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "sheet", "reason"])
        w.writerows(skipped)

    ns = sum(1 for r in out if r["row"] == "summary")
    print(f"TOTAL {len(out)} records -> {OUT}  (rows {len(out) - ns}, summaries {ns}); "
          f"skipped entries: {len(skipped)} -> {SKIPPED}")
    for (psi, exp), n in sorted(collections.Counter((r["psi"], r["experiment"]) for r in out).items(),
                                key=lambda x: int(re.sub(r"\D", "", x[0][0]) or 0)):
        print(f"{psi:8} {exp[:40]:40} {n}")


if __name__ == "__main__":
    main()
