"""FlameIntel API. Run from the project root:  uvicorn api.main:app --port 8000
The LLM key lives in .env and is read by chat.py on the server only; nothing here ever returns it."""
import collections
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(Path(__file__).resolve().parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import config as C  # noqa: E402
import errors  # noqa: E402
import datasets  # noqa: E402
import report  # noqa: E402
import store  # noqa: E402
import chat as rag  # noqa: E402  (project root chat.py; loads .env itself)

_chat_lock = threading.Lock()          # chat.py keeps module-level state (last_call): one answer at a time
_hits = collections.defaultdict(collections.deque)
STATE = {"ready": False, "error": None, "started": time.time()}


@asynccontextmanager
async def lifespan(app):
    store.load()  # investigation records (cheap, so a failure here should stop the API)
    try:  # load the embedding model and the ChromaDB index once, at startup
        rag._load()
        rag._experiments()
        STATE["ready"] = True
    except Exception as e:  # keep the API up so the UI can show a clear message
        STATE["error"] = rag._scrub(f"{type(e).__name__}: {e}")
    yield


app = FastAPI(title="FlameIntel API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=C.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    scenario: str | None = None


def _rate_limit(ip):
    now, q = time.time(), _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= C.RATE_LIMIT_PER_MIN:
        return int(60 - (now - q[0])) + 1
    q.append(now)
    return 0


@app.get("/api/health")
def health():
    return {"ready": STATE["ready"], "error": STATE["error"], "uptime_s": int(time.time() - STATE["started"]),
            "model": (rag._models(rag.os.environ.get("LLM_PROVIDER", "anthropic").lower()) if STATE["ready"] else None)}


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    ip = request.client.host if request.client else "?"
    wait = _rate_limit(ip)
    if wait:
        return JSONResponse(status_code=429, headers={"Retry-After": str(wait)}, content={
            "error": {"type": "rate_limit", "message": f"Too many questions. Please wait {wait} s and try again.", "retry_after": wait}})
    if not STATE["ready"]:
        return JSONResponse(status_code=503, content={"error": {"type": "not_ready", "message": "The knowledge base is still loading or failed to load. " + (STATE["error"] or "Try again in a few seconds.")}})
    scenario = body.scenario if body.scenario in C.SCENARIOS else ""
    t0 = time.time()
    try:
        with _chat_lock:
            res = rag.answer(body.question.strip(), mission=scenario)
    except Exception as e:  # QuotaError, StallError, RuntimeError("Every model failed ...") and friends
        status, err = errors.describe(e, rag._scrub)
        return JSONResponse(status_code=status, content={"error": err})
    res["timing_s"] = round(time.time() - t0, 2)
    res["cache_hit"] = bool(res.get("cached"))
    res["scenario"] = scenario
    for s in res.get("sources", []):  # attach acronym/title so the UI can name each source
        acr, title = rag._meta(s["psi"])
        s["acronym"], s["title"] = acr, title
        s["distance"] = round(float(s["distance"]), 4)
    return res


# ----------------------------------------------------------------------------- discovery
def _scn(s):
    return s if s in C.SCENARIOS else ""


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": C.SCENARIOS, "weights": C.RANK_WEIGHTS, "scenario_topics": C.SCENARIO_TOPICS, "disclaimer": store.DISCLAIMER}


@app.get("/api/coverage")
def coverage():
    return {"coverage": store.coverage()}


@app.get("/api/overview")
def overview(scenario: str = "Lunar Habitat"):
    return store.overview(_scn(scenario) or "Lunar Habitat")


@app.get("/api/investigations")
def investigations(q: str = "", topic: str = "", environment: str = "", availability: str = "", scenario: str = "", sort: str = ""):
    cards = store.search(q.strip(), topic, environment, availability, _scn(scenario), sort)
    return {"total": len(cards), "items": cards, "facets": store.facets(), "scenario": _scn(scenario),
            "disclaimer": store.DISCLAIMER}


@app.get("/api/investigations/{psi}")
def investigation(psi: str, scenario: str = ""):
    d = store.detail(psi, _scn(scenario))
    if not d:
        raise HTTPException(404, f"No investigation {psi}")
    return d


@app.get("/api/rank")
def rank(scenario: str = "Lunar Habitat", q: str = ""):
    scn = _scn(scenario)
    if not scn:
        raise HTTPException(400, "Unknown scenario. Use one of: " + ", ".join(C.SCENARIOS))
    cards = store.search(q.strip(), "", "", "", scn)
    return {"scenario": scn, "query": q, "weights": C.RANK_WEIGHTS, "label": store.DISCLAIMER,
            "results": [{"id": c["id"], "name": c["name"], "title": c["title"], **c["rank"]} for c in cards]}


@app.get("/api/compare")
def compare(ids: str, scenario: str = ""):
    lst = [x.strip() for x in ids.split(",") if x.strip()]
    if not 2 <= len(lst) <= 3:
        raise HTTPException(400, "Choose 2 or 3 investigations, e.g. ids=PSI-25,PSI-98")
    r = store.compare(lst, _scn(scenario))
    if not r:
        raise HTTPException(404, "Investigations not found")
    return r


# ----------------------------------------------------------------------------- data explorer
@app.get("/api/datasets")
def list_datasets(psi: str = "", q: str = "", format: str = "", category: str = ""):
    items = datasets.list_datasets(psi, q, format, category)
    cat = datasets.catalog()
    return {"total": len(items), "datasets": items,
            "facets": {"formats": sorted({d["format"] for d in cat}), "categories": sorted({d["category"] for d in cat}),
                       "psi": sorted({d["psi"] for d in cat}, key=lambda s: int(s.split("-")[1]))},
            "note": "Only real CSV / Excel files from the downloaded PSI records are listed. PDFs and Word files are in the search index but are not tables."}


@app.get("/api/datasets/{ds_id}/preview")
def dataset_preview(ds_id: str, sheet: str = ""):
    r = datasets.preview(ds_id, sheet)
    if r is None:
        raise HTTPException(404, "Unknown dataset")
    return r


@app.get("/api/datasets/{ds_id}/export")
def dataset_export(ds_id: str, sheet: str = ""):
    try:
        r = datasets.export_csv(ds_id, sheet)
    except Exception as e:
        raise HTTPException(422, f"This file cannot be exported ({type(e).__name__}).")
    if r is None:
        raise HTTPException(404, "Unknown dataset")
    text, name = r
    return Response(text, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ----------------------------------------------------------------------------- insights (built offline by build_insights.py)
@app.get("/api/insights")
def insights():
    p = C.DATA_DIR / "insights.json"
    if not p.exists():
        return {"generated_at": None, "insights": [], "note": "Not generated yet. Run: python api/build_insights.py"}
    import json
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- report
@app.get("/api/report")
def report_export(scenario: str = "Lunar Habitat", ids: str = "", format: str = "html"):
    scn = _scn(scenario) or "Lunar Habitat"
    r = report.build(scn, [x.strip() for x in ids.split(",") if x.strip()] or None)
    if format == "md":
        return PlainTextResponse(report.to_markdown(r), media_type="text/markdown; charset=utf-8",
                                 headers={"Content-Disposition": 'attachment; filename="flameintel-report.md"'})
    return HTMLResponse(report.to_html(r))
