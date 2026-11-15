"""Printable report (HTML or Markdown): scenario, ranked investigations with reasons, source summaries,
data availability, a qualitative comparison, insights, citations, evidence labels and limitations."""
import html
import json
from datetime import datetime

import config as C
import store

LABELS = {"source_reported": "Source-reported", "app_interpretation": "FlameIntel interpretation", "potential_application": "Potential application"}


def _insights():
    p = C.DATA_DIR / "insights.json"
    return json.loads(p.read_text(encoding="utf-8")).get("insights", []) if p.exists() else []


def build(scenario, ids=None, top=6):
    ranked = store.search("", "", "", "", scenario)
    chosen = [c for c in ranked if (not ids or c["id"] in ids)][: (len(ids) if ids else top)]
    cmp_ids = [c["id"] for c in chosen[:3]]
    cmp = store.compare(cmp_ids, scenario) if len(cmp_ids) >= 2 else None
    return {"scenario": scenario, "generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "chosen": chosen,
            "details": {c["id"]: store.get(c["id"]) for c in chosen}, "compare": cmp, "insights": _insights(),
            "coverage": store.coverage()}


def to_markdown(r):
    L = [f"# FlameIntel report: {r['scenario']}", f"_Generated {r['generated']}. Organizes existing NASA PSI research; not a NASA product, not a safety certification._", "",
         "## How to read this report", "- **Source-reported**: stated in a NASA PSI source (citation given).",
         "- **FlameIntel interpretation**: the app's relevance analysis.", "- **Potential application**: a possible use that needs validation.",
         f"- Relevance scores are app-generated, not official NASA scores. {store.DISCLAIMER}", "", "## Ranked investigations"]
    for c in r["chosen"]:
        d = r["details"][c["id"]]
        rk = c["rank"]
        L += [f"### {c['id']} {c['name']}: {c['title']} (relevance {rk['score']}/100)",
              f"- Source-reported objective: {store.snippet(d['objective'], 500)} (Source: {d['source_url']})",
              f"- Platform: {d['environment']}; {d['gravity_condition']}", f"- Data: {d['availability'].replace('_', ' ')}; {d['tabular_file_count']} tabular file(s); {len(d['publications'])} publication(s)",
              f"- Why relevant (FlameIntel interpretation): " + " ".join(rk["why"]), f"- Gravity note: {rk['gravity_note']}",
              "- Limitations: " + " ".join(d["limitations"]), ""]
    if r["compare"]:
        cp = r["compare"]
        L += ["## Comparison (qualitative)", "| | " + " | ".join(i["name"] for i in cp["investigations"]) + " |", "|---|" + "---|" * len(cp["investigations"])]
        for row in cp["rows"]:
            L.append(f"| {row['label']} | " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in row["values"]) + " |")
        L += ["", "Mismatches: " + " ".join(cp["mismatches"]), "", cp["numeric_comparison_note"], ""]
    if r["insights"]:
        L += ["## Fire-safety insights"]
        for i in r["insights"]:
            L += [f"### {i['theme']}: {i['title']}", f"**{LABELS['source_reported']}**"]
            for cl in i["claims"]:
                L.append(f"- {cl['text']} " + " ".join(f"[{c['psi']} {c['doc_type']}, {c['file']}, {c['loc']}]" for c in cl["citations"]))
            L += [f"**{LABELS['app_interpretation']}**: {i['app_interpretation']['text']}", f"**{LABELS['potential_application']}**: {i['potential_application']['text']}",
                  "Limitations: " + " ".join(i["limitations"]), f"Validation required: {i['validation_required']}", ""]
    cv = r["coverage"]
    L += ["## About the data", f"{cv.get('investigations')} investigations, {cv.get('indexed_chunks'):,} indexed passages. {cv.get('skipped_files_total')} files skipped "
          f"({cv.get('skipped_raw_lab_sheet_or_plot')} raw lab sheets/plots, {cv.get('pdf_no_extractable_text_or_error')} PDFs with no extractable text), "
          f"{cv.get('failed_downloads')} failed downloads. The free language-model quota is limited."]
    return "\n".join(L)


def to_html(r):
    e = html.escape
    p = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><title>FlameIntel report</title><style>",
         "body{font:15px/1.55 Georgia,serif;max-width:860px;margin:32px auto;padding:0 20px;color:#111}h1,h2,h3{font-family:system-ui,sans-serif}",
         "h1{border-bottom:3px solid #ff6b1f;padding-bottom:6px}.tag{font:600 11px system-ui;padding:2px 7px;border-radius:5px;border:1px solid;text-transform:uppercase;margin-right:6px}",
         ".sr{color:#0a7a56;background:#e6f7f0}.ai{color:#1f4fb3;background:#e8effc}.pa{color:#8a5a00;background:#fff4dc}",
         "table{border-collapse:collapse;width:100%;font:13px system-ui}td,th{border:1px solid #ccc;padding:6px;vertical-align:top}.note{background:#fff4dc;border:1px solid #e6c36a;padding:8px 12px;font:13px system-ui}",
         ".card{border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:14px 0;page-break-inside:avoid}small{color:#555}@media print{.noprint{display:none}}</style></head><body>",
         f"<h1>FlameIntel report: {e(r['scenario'])}</h1><p><small>Generated {e(r['generated'])}. Organizes existing NASA PSI research; not a NASA product and not a safety certification.</small></p>",
         "<p class='note'>Evidence labels: <span class='tag sr'>Source-reported</span> stated in a NASA PSI source (cited); <span class='tag ai'>FlameIntel interpretation</span> the app's analysis; "
         f"<span class='tag pa'>Potential application</span> needs validation. {e(store.DISCLAIMER)}</p>", "<h2>Ranked investigations</h2>"]
    for c in r["chosen"]:
        d, rk = r["details"][c["id"]], c["rank"]
        p.append(f"<div class='card'><h3>{e(c['id'])} {e(c['name'])} <small>relevance {rk['score']}/100 (app-generated)</small></h3><p><small>{e(c['title'])}</small></p>"
                 f"<p><span class='tag sr'>Source-reported</span>{e(store.snippet(d['objective'], 500))} <small>Source: <a href='{e(d['source_url'])}'>{e(d['id'])} PSI record</a></small></p>"
                 f"<p><small>{e(d['environment'])} · {e(d['gravity_condition'])} · data: {e(d['availability'].replace('_', ' '))}, {d['tabular_file_count']} tabular file(s), {len(d['publications'])} publication(s)</small></p>"
                 f"<p><span class='tag ai'>FlameIntel interpretation</span>{e(' '.join(rk['why']))}</p><p class='note'>{e(rk['gravity_note'])}</p>"
                 f"<p><small><b>Limitations:</b> {e(' '.join(d['limitations']))}</small></p></div>")
    cp = r["compare"]
    if cp:
        p.append("<h2>Comparison (qualitative)</h2><table><tr><th></th>" + "".join(f"<th>{e(i['name'])}</th>" for i in cp["investigations"]) + "</tr>")
        for row in cp["rows"]:
            p.append(f"<tr><td><b>{e(row['label'])}</b></td>" + "".join(f"<td>{e(str(v))}</td>" for v in row["values"]) + "</tr>")
        p.append("</table><ul>" + "".join(f"<li>{e(m)}</li>" for m in cp["mismatches"]) + f"</ul><p class='note'>{e(cp['numeric_comparison_note'])}</p>")
    if r["insights"]:
        p.append("<h2>Fire-safety insights</h2>")
        for i in r["insights"]:
            p.append(f"<div class='card'><h3>{e(i['theme'])}: {e(i['title'])}?</h3><p><span class='tag sr'>Source-reported</span></p><ul>")
            for cl in i["claims"]:
                cites = "; ".join(f"{c['psi']} {c['acronym']} · {c['doc_type']} · {c['file']} · {c['loc']}" for c in cl["citations"])
                p.append(f"<li>{e(cl['text'])} <small>[{e(cites)}]</small></li>")
            p.append(f"</ul><p><span class='tag ai'>FlameIntel interpretation</span>{e(i['app_interpretation']['text'])}</p>"
                     f"<p><span class='tag pa'>Potential application</span>{e(i['potential_application']['text'])}</p>"
                     f"<p><small><b>Limitations:</b> {e(' '.join(i['limitations']))}<br><b>Validation required:</b> {e(i['validation_required'])}</small></p></div>")
    cv = r["coverage"]
    p.append(f"<h2>About the data</h2><p>{cv.get('investigations')} investigations and {cv.get('indexed_chunks'):,} indexed passages. {cv.get('skipped_files_total')} files were skipped "
             f"({cv.get('skipped_raw_lab_sheet_or_plot')} raw lab sheets or plots, {cv.get('pdf_no_extractable_text_or_error')} PDFs with no extractable text), {cv.get('failed_downloads')} downloads failed. "
             "The free language-model quota is limited.</p><p class='noprint'><button onclick='print()'>Print / save as PDF</button></p></body></html>")
    return "".join(p)
