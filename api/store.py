"""Investigation records, keyword search, filters, scenario ranking and comparison.
Everything here works from api/data/investigations.json (built from real PSI metadata by build_investigations.py)."""
import json
import re
from collections import Counter

import config as C

DISCLAIMER = "App-generated relevance, not an official NASA score. It is an aid for deciding what to read first, not proof of applicability or safety."
STOP = set("a an the of in on for to and or with by at from is are was were be this that these those what which who how does do did into over under about as it its their there any can may might should would could using use used study studies research experiment experiments investigation investigations data".split())
TABLE_TYPES = ("Table row", "Excel row", "Excel summary", "Table summary")

_DB = {"coverage": {}, "items": []}


def load():
    p = C.DATA_DIR / "investigations.json"
    if not p.exists():
        raise RuntimeError("api/data/investigations.json is missing. Run: python api/build_investigations.py")
    d = json.loads(p.read_text(encoding="utf-8"))
    _DB["coverage"] = d["coverage"]
    _DB["items"] = d["investigations"]
    for i in _DB["items"]:
        i["_blob"] = " ".join([i["title"], i["acronym"], i["objective"], i["approach"], i["hypothesis"], i["description"],
                               " ".join(i["topics"]), " ".join(i["materials"]), " ".join(p["title"] for p in i["publications"])]).lower()
        i["_title_blob"] = f"{i['title']} {i['acronym']} {' '.join(i['topics'])}".lower()
    return len(_DB["items"])


def items():
    return _DB["items"]


def coverage():
    return _DB["coverage"]


def get(psi):
    return next((i for i in _DB["items"] if i["id"].lower() == psi.lower()), None)


def _stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(q):
    return [_stem(t) for t in re.findall(r"[a-z0-9][a-z0-9\-]+", (q or "").lower()) if t not in STOP and len(t) > 2]


def query_match(inv, toks):
    """fraction of query words found in the record text (title/topics count double). Returns (score 0..1, matched words)."""
    if not toks:
        return 0.0, []
    got, pts = [], 0.0
    for t in toks:
        if t in inv["_title_blob"]:
            pts += 1.0; got.append(t)
        elif t in inv["_blob"]:
            pts += 0.6; got.append(t)
    return pts / len(toks), got


def table_chunks(inv):
    return sum(inv["index_chunks"].get(t, 0) for t in TABLE_TYPES)


def snippet(text, n=300):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def rank_of(inv, scenario, q=""):
    """Score = 100 * sum(weight * component); every weight is in config.RANK_WEIGHTS."""
    W = C.RANK_WEIGHTS
    scn_topics = C.SCENARIO_TOPICS.get(scenario) or {}
    hits = sorted([(scn_topics[t], t) for t in inv["topics"] if t in scn_topics], reverse=True)
    best3 = sum(sorted(scn_topics.values(), reverse=True)[:3]) or 1
    topic_scn = min(1.0, sum(w for w, _ in hits[:3]) / best3)
    qm, got = query_match(inv, tokens(q))
    topic = topic_scn if not tokens(q) else 0.5 * topic_scn + 0.5 * qm
    env = (C.SCENARIO_ENV.get(scenario) or {}).get(inv["environment"], 0.3)
    tab, tchunks = inv["tabular_file_count"], table_chunks(inv)
    data = 0.4 * inv["has_dataset"] + 0.3 * min(1, tab / 10) + 0.3 * min(1, tchunks / 100)
    cov = 0.4 * min(1, inv["index_chunk_total"] / 500) + 0.3 * min(1, len(inv["index_chunks"]) / 6) + 0.3 * min(1, len(inv["publications"]) / 10)
    comps = {"topic": topic, "environment": env, "data": data, "coverage": cov}
    score = round(100 * sum(W[k] * v for k, v in comps.items()))

    why = []
    if hits:
        why.append(f"The source text covers {', '.join(t for _, t in hits[:3])}, which {scenario} questions usually look for (app-tagged from the record text).")
    else:
        why.append(f"The record text has no strong match to the main {scenario} topics.")
    if got:
        why.append(f"Your search words matched this record: {', '.join(dict.fromkeys(got))}.")
    why.append(f"Platform: {inv['environment']} ({inv['gravity_condition'].split(' (')[0].lower()}).")
    if inv["has_dataset"]:
        why.append(f"{tab} tabular data file(s) are available, plus {tchunks} indexed table rows or summaries.")
    else:
        why.append("No tabular data file is available for this record.")
    why.append(f"{inv['index_chunk_total']} indexed passages across {len(inv['index_chunks'])} document types and {len(inv['publications'])} listed publication(s).")

    micro = inv["gravity_condition"].startswith("Microgravity")
    gnote = C.GRAVITY_NOTE.get(scenario, "") if micro else "Ground-based or computational study: check how its conditions relate to the scenario."
    return {"score": score, "components": {k: round(v, 3) for k, v in comps.items()}, "weights": W,
            "why": why, "gravity_note": gnote, "disclaimer": DISCLAIMER}


def card(inv, scenario=None, q=""):
    c = {
        "id": inv["id"], "acronym": inv["acronym"], "title": inv["title"], "name": inv["name"],
        "description": snippet(inv["objective"] or inv["description"]),
        "topics": inv["topics"], "environment": inv["environment"], "gravity_condition": inv["gravity_condition"],
        "availability": inv["availability"], "tabular_file_count": inv["tabular_file_count"],
        "publication_count": len(inv["publications"]), "source_url": inv["source_url"], "source_url_note": inv["source_url_note"],
        "materials": inv["materials"][:4], "index_chunk_total": inv["index_chunk_total"],
    }
    if scenario:
        c["rank"] = rank_of(inv, scenario, q)
    return c


def search(q="", topic="", environment="", availability="", scenario="", sort=""):
    toks = tokens(q)
    out = []
    for inv in _DB["items"]:
        if topic and topic not in inv["topics"]:
            continue
        if environment and inv["environment"] != environment:
            continue
        if availability:
            a = inv["availability"]
            if availability == "has_data" and not inv["has_dataset"]:
                continue
            if availability not in ("has_data",) and a != availability:
                continue
        if toks:
            qm, _ = query_match(inv, toks)
            if qm < 0.34:  # at least a third of the query words must appear in the record
                continue
        out.append(inv)
    cards = [card(i, scenario or None, q) for i in out]
    if scenario and sort != "name":
        cards.sort(key=lambda c: -c["rank"]["score"])
    else:
        cards.sort(key=lambda c: int(c["id"].split("-")[1]))
    return cards


def facets():
    its = _DB["items"]
    return {
        "topics": Counter(t for i in its for t in i["topics"]).most_common(),
        "environments": Counter(i["environment"] for i in its).most_common(),
        "availability": Counter(i["availability"] for i in its).most_common(),
    }


def overview(scenario):
    its = _DB["items"]
    ranked = sorted(((rank_of(i, scenario), i) for i in its), key=lambda t: -t[0]["score"])
    matches = [i for r, i in ranked if r["score"] >= 50]
    f = facets()
    return {
        "scenario": scenario,
        "kpis": {
            "indexed_investigations": len(its),
            "with_data": sum(1 for i in its if i["has_dataset"]),
            "topics_represented": len(f["topics"]),
            "scenario_matches": len(matches),
            "indexed_chunks": _DB["coverage"].get("indexed_chunks", 0),
            "tabular_files": sum(i["tabular_file_count"] for i in its),
        },
        "scenario_match_rule": "Scenario matches = investigations whose app-generated relevance score is 50 or more (see ranking weights).",
        "charts": {"topics": f["topics"], "environments": f["environments"], "availability": f["availability"]},
        "featured": [card(i, scenario) for _, i in ranked[:4]],
        "disclaimer": DISCLAIMER,
    }


def detail(psi, scenario=""):
    inv = get(psi)
    if not inv:
        return None
    d = {k: v for k, v in inv.items() if not k.startswith("_")}
    if scenario:
        d["rank"] = rank_of(inv, scenario)
    cite = lambda field: f"{inv['id']} record metadata ({field})"  # noqa: E731
    reported = []
    for label, field, key in (("Objective", "objective", "objective"), ("Approach", "approach", "approach"), ("Hypothesis", "hypothesis", "hypothesis"),
                              ("Description", "description", "description"), ("Research impacts", "research_impacts", "research_impacts"), ("Hardware", "hardware", "hardware")):
        if inv.get(key):
            reported.append({"label": label, "text": inv[key], "citation": cite(field), "url": inv["source_url"]})
    topics = inv["topics"]
    interp = [f"FlameIntel tagged this record with: {', '.join(topics) or 'no topic'} (keyword rules over the source text, not an official classification)."]
    if scenario:
        r = d["rank"]
        interp += r["why"]
        interp.append(r["gravity_note"])
    apps = [{"topic": t, "text": C.POTENTIAL_APPLICATIONS[t]} for t in topics if t in C.POTENTIAL_APPLICATIONS and t != "combustion behavior"][:4]
    d["evidence"] = {
        "source_reported": reported,
        "app_interpretation": interp,
        "potential_application": apps,
        "potential_application_note": "Curated by FlameIntel, not stated by NASA. Each needs validation and none certifies equipment or materials.",
    }
    d["measured_variables_note"] = ("Column names come from the experimental-table CSV of this record; units appear only where the file's headers state them."
                                    if inv["condition_columns"] else "No experimental-table columns were found for this record.")
    return d


# ------------------------------------------------------------------ comparison
def _unit(col):
    m = re.search(r"\(([^)]+)\)\s*$", col)
    return m.group(1).strip() if m else None


def compare(ids, scenario=""):
    invs = [get(i) for i in ids]
    invs = [i for i in invs if i]
    if len(invs) < 2:
        return None
    rows = []

    def add(label, vals, note=""):
        rows.append({"label": label, "values": vals, "note": note})

    add("Research objective", [snippet(i["objective"], 380) for i in invs])
    add("Topics (app-tagged)", [", ".join(i["topics"]) or "none" for i in invs], "Keyword tags over source text.")
    add("Platform / environment", [i["environment"] for i in invs])
    add("Gravity condition", [i["gravity_condition"] for i in invs])
    add("Materials / fuels in the experimental table", [", ".join(i["materials"][:6]) or "not stated in a table" for i in invs])
    add("Table columns (variables recorded)", [", ".join(i["condition_columns"][:14]) or "no table" for i in invs],
        "Column names as written in each file. Units are shown only when in the header.")
    add("Data availability", [f"{i['availability'].replace('_', ' ')} · {i['tabular_file_count']} tabular file(s)" for i in invs])
    add("Publications listed", [str(len(i["publications"])) for i in invs])
    if scenario:
        add(f"Relevance to {scenario} (app-generated)", [f"{rank_of(i, scenario)['score']} / 100" for i in invs], DISCLAIMER)

    # mismatches
    mism = []
    envs = {i["environment"] for i in invs}
    if len(envs) > 1:
        mism.append("The studies ran on different platforms (" + ", ".join(sorted(envs)) + "), so conditions are not interchangeable.")
    grav = {i["gravity_condition"] for i in invs}
    if len(grav) > 1:
        mism.append("Gravity conditions differ: flight experiments are in microgravity; ground or computational studies follow the record's own conditions.")
    mats = [set(m.lower() for m in i["materials"]) for i in invs]
    if not set.intersection(*mats) if all(mats) else True:
        mism.append("No fuel or material appears in all the experimental tables, so outcomes are not like-for-like.")
    col_sets = [{re.sub(r"\s*\(.*\)\s*$", "", c).strip().lower() for c in i["condition_columns"]} for i in invs]
    shared = set.intersection(*col_sets) if all(col_sets) else set()
    units_ok = False
    if shared:
        by = {s: [{_unit(c) for c in i["condition_columns"] if re.sub(r"\s*\(.*\)\s*$", "", c).strip().lower() == s} for i in invs] for s in shared}
        units_ok = all(len(set.union(*u)) <= 1 and all(x != {None} for x in u) for u in by.values())
        mism.append(f"Columns with the same name in all studies: {', '.join(sorted(shared)[:8])}. " + ("Their units agree." if units_ok else "Units are missing or differ, so values are not directly comparable."))
    else:
        mism.append("There are no column names shared by all the tables, so no variable can be compared directly.")
    comparable = bool(shared) and units_ok and len(envs) == 1 and len(grav) == 1 and bool(set.intersection(*mats) if all(mats) else False)
    return {
        "investigations": [{"id": i["id"], "name": i["name"], "title": i["title"], "source_url": i["source_url"]} for i in invs],
        "rows": rows, "mismatches": mism,
        "numeric_comparison_allowed": comparable,
        "numeric_comparison_note": ("Units, conditions and materials look compatible, but check the source files before comparing any numbers." if comparable else
                                    "Numeric results are NOT compared: units, definitions or experimental conditions do not match. This is a qualitative comparison only."),
    }
