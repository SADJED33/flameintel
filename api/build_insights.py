"""Build api/data/insights.json OFFLINE by running a fixed list of questions through chat.answer().
Only sentences that carry a valid [S#] citation are kept. The 'source_reported' claims come from the model's
cited answer; the 'app_interpretation' and 'potential_application' texts are FlameIntel's own, fixed per theme.

Run:  python api/build_insights.py          (needs the LLM key in .env; answers are cached in data/llm_cache.jsonl)
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chat as rag  # noqa: E402
import config as C  # noqa: E402

QUESTIONS = [
    ("Suppression systems", "suppression & extinguishment", "What do the experiments report about extinguishing or suppressing flames, and under which conditions?"),
    ("Suppression systems", "suppression & extinguishment", "Which experiments studied the effect of fire suppressants or extinguishment limits on flames?"),
    ("Smoke / fire detection", "smoke & detection", "What smoke or aerosol measurements were made, and in which experiments?"),
    ("Smoke / fire detection", "smoke & detection", "What did the SAFFIRE smoke detector channels record?"),
    ("Fire-resistant materials", "flammability", "Which solid materials were burned in the experiments, and how did they burn?"),
    ("Fire-resistant materials", "flame spread", "How did airflow or oxygen concentration affect flame spread over solid materials?"),
    ("Crew protection", "flammability", "What do the sources say about fire risk to spacecraft or crew safety?"),
    ("Crew protection", "flammability", "What do the sources say about how fires behave differently in low gravity than in normal gravity?"),
    ("Monitoring / control systems", "modeling & simulation", "What sensors, cameras or instruments were used to monitor the flames and the environment?"),
    ("Monitoring / control systems", "modeling & simulation", "How were flame spread rates or flame size measured in the experiments?"),
    ("Potential terrestrial applications", "diffusion flames", "Do the sources mention benefits of this research for combustion or fire safety on Earth?"),
    ("Potential terrestrial applications", "soot & smoke point", "What do the sources say about soot or smoke formation that matters beyond spacecraft?"),
]

LIMITS = [
    "Microgravity flight results are not directly valid for lunar, Mars or Earth gravity.",
    "Test materials, airflow and atmosphere in the experiments may differ from a real habitat.",
    "The claims come from retrieved passages only; other passages and documents may add or contradict them.",
]
APP_INTERP = {
    "suppression & extinguishment": "FlameIntel reads these results as background for future suppression research, not as proof that any suppression system works in a habitat.",
    "smoke & detection": "FlameIntel reads these measurements as input for thinking about how smoke detection might be evaluated in microgravity.",
    "flammability": "FlameIntel reads these results as relevant to how materials might be screened for enclosed habitats.",
    "flame spread": "FlameIntel reads these results as relevant to how materials might be screened for flame spread in enclosed habitats.",
    "modeling & simulation": "FlameIntel reads these results as relevant to what a monitoring or simulation tool would need to measure or reproduce.",
    "diffusion flames": "FlameIntel reads these results as basic flame science that fire-safety models can build on.",
    "soot & smoke point": "FlameIntel reads these results as relevant to smoke and soot behaviour, which matters for detection and air quality.",
}


def strip_claim(line):
    t = re.sub(r"^[*\-•]\s+", "", line.strip())
    label = "Observed" if re.search(r"\*\*Observed", t) else "Context"
    t = re.sub(r"\*\*(Observed|Context):?\*\*:?\s*", "", t)
    ids = re.findall(r"\[(S\d+)\]", t)
    text = re.sub(r"\s*(\[S\d+\])+", "", t).replace("**", "").strip()
    return text, label, list(dict.fromkeys(ids))


def main():
    out, t0 = [], time.time()
    for n, (theme, topic, q) in enumerate(QUESTIONS, 1):
        try:
            r = rag.answer(q, mission="")
        except Exception as e:
            print(f"[{n}/{len(QUESTIONS)}] FAILED ({type(e).__name__}): {rag._scrub(str(e))[:160]}")
            continue
        by = {s["id"]: s for s in r["sources"]}
        claims = []
        for line in r["answer"].split("\n"):
            if not re.search(r"\[S\d+\]", line):
                continue
            text, label, ids = strip_claim(line)
            ids = [i for i in ids if i in by]
            if not ids or not text:
                continue  # claims without a valid citation are dropped
            claims.append({"text": text, "kind": label, "citations": [
                {"id": i, "psi": by[i]["psi"], "acronym": rag._meta(by[i]["psi"])[0], "doc_type": by[i]["doc_type"],
                 "file": by[i]["file"], "loc": by[i]["loc"], "distance": round(float(by[i]["distance"]), 4),
                 "excerpt": by[i]["text"][:500]} for i in ids]})
        print(f"[{n}/{len(QUESTIONS)}] {r['outcome']:8} {len(claims)} cited claims | {q[:70]}")
        if r["outcome"] == "refused" or not claims:
            continue
        psis = list(dict.fromkeys(c["psi"] for cl in claims for c in cl["citations"]))
        out.append({
            "id": f"ins-{n:02d}", "theme": theme, "topic": topic, "question": q,
            "title": q.rstrip("?"),
            "summary": claims[0]["text"],
            "evidence_label": "source_reported",
            "outcome": r["outcome"],
            "claims": claims,
            "supporting": psis,
            "app_interpretation": {"label": "app_interpretation", "text": APP_INTERP.get(topic, "")},
            "potential_application": {"label": "potential_application", "text": C.POTENTIAL_APPLICATIONS.get(topic, "")},
            "limitations": LIMITS + (["Part of the question is not supported by the sources: see the Not in the data line in the assistant."] if r["outcome"] == "partial" else []),
            "validation_required": "Yes. This does not validate a complete habitat system, certify any material or equipment, or predict real-world fire behaviour.",
            "warnings": r["warnings"], "model": r.get("model"),
        })
    res = {"generated_at": datetime.now().isoformat(timespec="seconds"), "method": "Fixed questions run through the RAG assistant; only sentences with valid [S#] citations kept.",
           "questions_run": len(QUESTIONS), "insights": out}
    (C.DATA_DIR / "insights.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(out)} insights in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
