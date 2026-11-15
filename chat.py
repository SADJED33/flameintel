import os
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    """minimal .env loader: KEY=VALUE lines; terminal variables win; empty values skipped."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("\"'").strip()
            if k and v and k not in os.environ:
                os.environ[k] = v
    return True

ENV_FOUND = _load_env()
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse
import requests
import chromadb
from fastembed import TextEmbedding

BASE_DIR = Path(__file__).resolve().parent  # project root: no path below depends on the working directory
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = str(DATA_DIR / "kb_index")
COLLECTION = "nasa_kb"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # must match build_index.py / ask.py
MAX_DISTANCE = float(os.environ.get("MAX_DISTANCE", "0.40"))
FETCH_K, PER_FILE, KEEP = 40, 3, 8
CHUNK_SHOW = int(os.environ.get("CHUNK_SHOW", "1500"))  # characters of each source sent to the model
N_CONTEXT = int(os.environ.get("N_CONTEXT", "8"))      # number of sources sent to the model
CHUNK_CHARS = CHUNK_SHOW                                # old name, kept for compatibility

NOT_IN_DATA = ("Not in the data. The knowledge base (24 NASA microgravity combustion "
               "experiments) has nothing relevant to this question.")

SYSTEM_PROMPT = """You answer questions about NASA microgravity combustion experiments using ONLY the numbered SOURCES in the user message.

Rules:
- Use only the SOURCES. No outside knowledge, no guessing, no filling gaps.
- Every sentence stating a fact ends with source tags like [S2] or [S1][S4].
- Begin each factual statement with a label: **Observed** (a measurement, result or test condition stated in the sources) or **Context** (background, objective or description that is not a result).
- NO predictions, forecasts, extrapolations or recommendations. If asked what will or should happen in a situation the sources did not test, say the data does not cover it, then state what the sources do show (such questions are outcome C below).
- Choose exactly one OUTCOME for every question:
  (A) The sources answer the question: give a normal answer with labels and tags.
  (B) The sources describe what an experiment studies, how it works or its hardware (objectives, approach, descriptions) but contain NO results for what was asked: write only **Context** statements, each with source tags, and end with exactly this final line: Results are not in the retrieved sources.
  (C) Nothing in the sources is relevant to the question, or it asks for a prediction or recommendation: write only "Not in the data." (a program adds the related experiments after it).
- Quote numbers and units exactly as written. Name the experiment (PSI id + acronym) when citing.
- At most 8 short bullets. Say when sources differ by test conditions.
- The user's MISSION is background for choosing relevant points. It is never evidence.
- A tag must point to a source whose text itself states that sentence. Never add a material, number, condition, comparison or cause that the cited text does not state (for example, do not say what a material "is" or what happens "on Earth" unless the cited text says so). If a fact is only in a different source, cite that source instead.
- Never describe the situation in the question (a planet, a place, a person's activity) with facts of your own; refer to it only as "the conditions asked about". Do not write concluding or summary sentences: every sentence is either a tagged fact or one of the two fixed lines ("Not in the data." or "Results are not in the retrieved sources.").
- **Observed** is only for a bullet whose cited chunk itself states a result: a measurement, an observation or a finding that a source reports for its own experiment, including numerical results. Text from Metadata chunks (the source header says type=Metadata; locations Objective, Approach, Hypothesis, Description, Research impacts, Hardware, Title) describes what is planned or intended, so it is always **Context**, never **Observed**. Anything described as known, conventional, proposed, planned, an objective or a requirement is **Context**.
- Use quotation marks only for words copied exactly from the cited source.
- For outcome (B) never use **Observed**, never state or imply a result, and give at most 6 short bullets. For outcome (C) write nothing after "Not in the data." Do not list loosely related items to fill space.
- Never print scaffolding: no outcome letters such as "(A)", "(B)", "(C)" or "Outcome A", and no lead-ins such as "The sources answer the question:" or "Answering the question based on the provided sources:". Start directly with the first bullet (or with "Not in the data.").
- Answer only what the question asks. When the question lists materials, fuels, samples or conditions, include only findings about those items. Leave out findings about other materials or conditions (for example wax candles or other fuels) unless the question asks for them.
- If some of the items the question lists have no supporting source, answer for the supported items and add one final line: Not in the data: <the unsupported items, in the user's words, separated by commas>. If outcome (B) also applies, put that line just before the final line "Results are not in the retrieved sources."
- When two findings could conflict (different values or effects for the same quantity), state the condition of each in its own bullet (oxygen level, airflow speed, pressure, material form), or leave one of them out. Never give two bullets with different values for the same quantity without their conditions."""

_model = None
_col = None

def _load():
    global _model, _col
    if _model is None:
        _model = TextEmbedding(EMBED_MODEL)
    if _col is None:
        _col = chromadb.PersistentClient(path=INDEX_DIR).get_collection(COLLECTION)
    return _model, _col

ROUTE_PSI, ROUTE_META_K, ROUTE_PER_PSI_K, PER_PSI = 3, 12, 6, 4

def _routing_on():
    return os.environ.get("ROUTING", "off").strip().lower() not in ("off", "0", "false", "no")

def _route_psi(col, qv, n=None):
    """Stage 1: best-matching experiments by their Metadata chunks (best distance per psi)."""
    n = n or ROUTE_PSI
    r = col.query(query_embeddings=[qv], n_results=ROUTE_META_K, where={"doc_type": "Metadata"},
                  include=["metadatas", "distances"])
    best = {}
    for m, d in zip(r["metadatas"][0], r["distances"][0]):
        if d <= MAX_DISTANCE and d < best.get(m["psi"], 9):
            best[m["psi"]] = d
    return [p for p, _ in sorted(best.items(), key=lambda kv: kv[1])[:n]]

# ---- optional cross-encoder reranking (RERANK=on); RERANK=off keeps retrieve() exactly as before ----
RR_PSI, RR_PER_PSI_K, RR_PER_PSI_CAP, RR_CHARS = 5, 5, 5, 1500
RERANK_MODEL_DEFAULT = "Xenova/ms-marco-MiniLM-L-6-v2"
_rr, _rr_name = None, None

def _rerank_on():
    return os.environ.get("RERANK", "off").strip().lower() in ("on", "1", "true", "yes")

def _load_reranker():
    global _rr, _rr_name
    name = os.environ.get("RERANK_MODEL", "").strip() or RERANK_MODEL_DEFAULT
    if _rr is None or _rr_name != name:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        for attempt in range(1, 4):
            try:
                _rr = TextCrossEncoder(model_name=name)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(5 * attempt)
        _rr_name = name
    return _rr

def _retrieve_rerank(question, col, qv):
    """Pool = global top FETCH_K + best RR_PER_PSI_K chunks of the top RR_PSI experiments (Metadata
    stage 1). MAX_DISTANCE gates on the bi-encoder distance first; survivors are re-ranked by a
    cross-encoder; caps: PER_FILE per (psi,file), RR_PER_PSI_CAP per psi; keep the best KEEP."""
    res = col.query(query_embeddings=[qv], n_results=FETCH_K,
                    include=["documents", "metadatas", "distances"])
    pool = {}  # chunk id -> [doc, meta, distance, routed]
    for cid, doc, m, dist in zip(res["ids"][0], res["documents"][0],
                                 res["metadatas"][0], res["distances"][0]):
        pool[cid] = [doc, m, dist, False]
    for psi in _route_psi(col, qv, RR_PSI):
        r2 = col.query(query_embeddings=[qv], n_results=RR_PER_PSI_K, where={"psi": psi},
                       include=["documents", "metadatas", "distances"])
        for cid, doc, m, dist in zip(r2["ids"][0], r2["documents"][0],
                                     r2["metadatas"][0], r2["distances"][0]):
            if cid in pool:
                pool[cid][3] = True
            else:
                pool[cid] = [doc, m, dist, True]
    cand = [v for v in pool.values() if v[2] <= MAX_DISTANCE]  # unchanged gate: refusals behave as before
    if not cand:
        return []
    scores = [float(x) for x in _load_reranker().rerank(question, [v[0][:RR_CHARS] for v in cand])]
    out, per_file, per_psi = [], {}, {}
    for (doc, m, dist, routed), sc in sorted(zip(cand, scores), key=lambda t: -t[1]):
        key = (m["psi"], m["file"])
        if per_file.get(key, 0) >= PER_FILE or per_psi.get(m["psi"], 0) >= RR_PER_PSI_CAP:
            continue
        per_file[key] = per_file.get(key, 0) + 1
        per_psi[m["psi"]] = per_psi.get(m["psi"], 0) + 1
        out.append({"id": f"S{len(out) + 1}", "text": doc, "psi": m["psi"],
                    "doc_type": m["doc_type"], "file": m["file"], "loc": m["loc"],
                    "distance": dist, "routed": routed, "rerank_score": sc})
        if len(out) >= KEEP:
            break
    return out

def retrieve(question):
    model, col = _load()
    qv = next(iter(model.query_embed(question))).tolist()
    if _rerank_on():
        return _retrieve_rerank(question, col, qv)
    res = col.query(query_embeddings=[qv], n_results=FETCH_K,
                    include=["documents", "metadatas", "distances"])
    pool = {}  # chunk id -> [doc, meta, distance, routed]
    for cid, doc, m, dist in zip(res["ids"][0], res["documents"][0],
                                 res["metadatas"][0], res["distances"][0]):
        pool[cid] = [doc, m, dist, False]
    routing = _routing_on()
    if routing:
        for psi in _route_psi(col, qv):
            r2 = col.query(query_embeddings=[qv], n_results=ROUTE_PER_PSI_K, where={"psi": psi},
                           include=["documents", "metadatas", "distances"])
            for cid, doc, m, dist in zip(r2["ids"][0], r2["documents"][0],
                                         r2["metadatas"][0], r2["distances"][0]):
                if cid in pool:
                    pool[cid][3] = True
                else:
                    pool[cid] = [doc, m, dist, True]
    out, per_file, per_psi = [], {}, {}
    for cid, (doc, m, dist, routed) in sorted(pool.items(), key=lambda kv: kv[1][2]):
        if dist > MAX_DISTANCE:
            continue
        key = (m["psi"], m["file"])
        if per_file.get(key, 0) >= PER_FILE:
            continue
        if routing and per_psi.get(m["psi"], 0) >= PER_PSI:
            continue
        per_file[key] = per_file.get(key, 0) + 1
        per_psi[m["psi"]] = per_psi.get(m["psi"], 0) + 1
        out.append({"id": f"S{len(out) + 1}", "text": doc, "psi": m["psi"],
                    "doc_type": m["doc_type"], "file": m["file"], "loc": m["loc"],
                    "distance": dist, "routed": routed})
        if len(out) >= KEEP:
            break
    return out

class QuotaError(RuntimeError):
    """Every configured model answered HTTP 429. daily: it was a per-day limit; retry_after: the
    smallest wait (seconds) any model asked for, or None."""
    def __init__(self, message, daily=False, retry_after=None, details=()):
        super().__init__(message)
        self.daily, self.retry_after, self.details = daily, retry_after, list(details)

class StallError(RuntimeError):
    """A model accepted the request but sent no reply within the timeout (LLM_TIMEOUT)."""
    def __init__(self, message, host="", timeout=None):
        super().__init__(message)
        self.host, self.timeout = host, timeout

def _raise(r):
    raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:400]}")

_progress = None  # set by main(): a callable that prints a progress line; library use stays silent

def _say(msg):
    if _progress:
        _progress(msg)

def _post(url, **kw):
    """requests.post with retries: 4 attempts, waits 2s/5s/10s. Retries on connection errors and
    HTTP 429/500/502/503; other statuses are returned as-is. A timeout is a stall: StallError at once,
    no retry on the same model (call_llm moves on to the next model in LLM_FALLBACK_MODELS)."""
    waits = (2, 5, 10)
    host = urlparse(url).netloc
    for attempt in range(4):
        try:
            r = requests.post(url, **kw)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if isinstance(e, requests.exceptions.Timeout):
                t = kw.get("timeout")
                raise StallError(f"No response from {host} within {t:g} s: the model looks stalled or overloaded."
                                 if isinstance(t, (int, float)) else f"No response from {host}: the model looks stalled.",
                                 host, t) from None
            if attempt == 3:
                raise RuntimeError(f"Network problem reaching {host}. Check internet/DNS. "
                                   f"({type(e).__name__}; the service may have closed the connection)") from None
            _say(f"[llm] {type(e).__name__} talking to {host}; retrying (attempt {attempt + 2} of 4) ...")
        else:
            if r.status_code not in (429, 500, 502, 503) or attempt == 3:
                return r  # last attempt: caller reports the HTTP status and body
        time.sleep(waits[attempt])

_DAILY = re.compile(r"per day|\(TPD\)|\(RPD\)", re.I)

def _retry_after(r):
    """Seconds to wait, from the retry-after header or a 'try again in 2m32.4s' sentence; None if unknown."""
    h = r.headers.get("retry-after")
    if h:
        try:
            return float(h)
        except ValueError:
            pass
    m = re.search(r"try again in\s+((?:\d+h)?(?:\d+m(?!s))?(?:[\d.]+s)?)", r.text)
    if not m or not m.group(1):
        return None
    sec = sum(float(v) * {"h": 3600, "m": 60, "s": 1}[u] for v, u in re.findall(r"([\d.]+)(h|m(?!s)|s)", m.group(1)))
    return sec or None

def _models(provider):
    """[primary] + LLM_FALLBACK_MODELS (comma list; same provider and base URL)."""
    primary = os.environ.get("LLM_MODEL", "").strip()
    if provider == "anthropic" and not primary:
        primary = "claude-haiku-5-5"
    if not primary:
        raise RuntimeError("LLM_MODEL is required when LLM_PROVIDER=openai")
    fb = [m.strip() for m in os.environ.get("LLM_FALLBACK_MODELS", "").split(",") if m.strip()]
    return [primary] + [m for m in fb if m != primary]

def _timeout():
    return float(os.environ.get("LLM_TIMEOUT", "30"))

def _request(provider, model, system, user):
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key or key == "PASTE_NEW_KEY_HERE":
            raise RuntimeError("Put your key in the .env file (ANTHROPIC_API_KEY=...)")
        return _post("https://api.anthropic.com/v1/messages", timeout=_timeout(),
                     headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                              "content-type": "application/json"},
                     json={"model": model, "max_tokens": 900, "temperature": 0, "system": system,
                           "messages": [{"role": "user", "content": user}]})
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key or key == "PASTE_NEW_KEY_HERE":
            raise RuntimeError("Put your key in the .env file (OPENAI_API_KEY=...)")
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        payload = {"model": model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        temp = os.environ.get("LLM_TEMPERATURE", "").strip()
        if temp:  # sent only when LLM_TEMPERATURE is set
            payload["temperature"] = float(temp)
        effort = os.environ.get("LLM_REASONING_EFFORT", "").strip().lower()
        if effort:  # sent only when set, OpenAI path only (Gemini: Google's OpenAI-compatibility docs)
            if effort not in ("minimal", "low", "medium", "high"):
                raise RuntimeError("LLM_REASONING_EFFORT must be minimal, low, medium or high")
            payload["reasoning_effort"] = effort
        return _post(base + "/chat/completions", timeout=_timeout(),
                     headers={"Authorization": "Bearer " + key, "content-type": "application/json"},
                     json=payload)
    raise RuntimeError(f"unknown LLM_PROVIDER: {provider}")

def _parse(provider, r):
    j = r.json()
    u = j.get("usage") or {}
    finish = None
    if provider == "anthropic":
        finish = j.get("stop_reason")
        text = "".join(b.get("text", "") for b in j["content"] if b.get("type") == "text")
        usage = {"prompt_tokens": u.get("input_tokens", 0), "completion_tokens": u.get("output_tokens", 0)}
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    else:
        text = j["choices"][0]["message"].get("content") or ""
        finish = j["choices"][0].get("finish_reason")
        usage = {k: u.get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return text, usage, finish

last_call = {}  # model / usage / switched / cached of the most recent call_llm() or _llm()

def call_llm(system, user):
    """One LLM call with fallback models (LLM_FALLBACK_MODELS). The next model is tried when a model
    answers HTTP 429 (after _post's retries; a short per-minute limit is waited out once first, a daily
    limit switches at once) or when it stalls (no reply within LLM_TIMEOUT: one try, no retries)."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    models = _models(provider)
    failures = []  # dicts: model, kind ("quota" | "stall"), daily, retry_after, body, host
    for idx, model in enumerate(models):
        _say(f"...thinking ({model}; gives up after {_timeout():g} s without a reply)")
        try:
            r = _request(provider, model, system, user)
            ra = _retry_after(r) if r.status_code == 429 else None
            if r.status_code == 429 and not _DAILY.search(r.text) and ra is not None and ra <= 65:
                time.sleep(ra + 0.5)
                r = _request(provider, model, system, user)
        except StallError as e:
            failures.append({"model": model, "kind": "stall", "daily": False, "retry_after": None,
                             "body": str(e), "host": e.host})
            if idx + 1 < len(models):
                print(f"[llm] {model} stalled, switching to {models[idx + 1]}", file=sys.stderr)
            continue
        if r.status_code == 200:
            text, usage, finish = _parse(provider, r)
            last_call.clear()
            last_call.update(model=model, usage=usage, switched=idx > 0, cached=False, finish=finish)
            return text
        if r.status_code != 429:
            _raise(r)
        failures.append({"model": model, "kind": "quota", "daily": bool(_DAILY.search(r.text)),
                         "retry_after": _retry_after(r), "host": "",
                         "body": re.sub(r"org_\w+", "org_[hidden]", r.text)[:300]})
        if idx + 1 < len(models):
            print(f"[llm] HTTP 429 on {model} ({'daily limit' if failures[-1]['daily'] else 'rate limit persisted'}); "
                  f"switching to {models[idx + 1]}", file=sys.stderr)
    stalls = [f for f in failures if f["kind"] == "stall"]
    if not stalls:  # every model was rate limited
        ras = [f["retry_after"] for f in failures if f["retry_after"] is not None]
        summary = "; ".join(f"{f['model']} ({'daily' if f['daily'] else 'rate'} limit)" for f in failures)
        raise QuotaError(f"LLM HTTP 429 on every model: {summary}. Last response: {failures[-1]['body']}",
                         daily=all(f["daily"] for f in failures), retry_after=min(ras) if ras else None,
                         details=failures)
    names = ", ".join(f["model"] for f in failures)
    if len(stalls) == len(failures):  # every model stalled
        who = names if len(failures) == 1 else f"any model ({names})"
        raise StallError(f"No response from {stalls[0]['host']} within {_timeout():g} s from {who}: the service "
                         f"looks stalled or overloaded. Try again later, or change LLM_MODEL / LLM_FALLBACK_MODELS.",
                         stalls[0]["host"], _timeout())
    summary = "; ".join(f"{f['model']} ({'stalled' if f['kind'] == 'stall' else 'rate-limited'})" for f in failures)
    raise RuntimeError(f"Every model failed: {summary}. Try again later.")

# ---- disk cache: key = sha256(model + system prompt + user message); the user message holds the sources ----
CACHE_FILE = str(DATA_DIR / "llm_cache.jsonl")
_CACHE = None

def _cache_on():
    return os.environ.get("LLM_CACHE", "on").strip().lower() not in ("off", "0", "false", "no")

def _cache_key(model, system, user):
    return hashlib.sha256((model + "\n" + system + "\n" + user).encode("utf-8")).hexdigest()

def _cache_entries():
    global _CACHE
    if _CACHE is None:
        _CACHE = {}
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        _CACHE[e["key"]] = e
                    except Exception:
                        continue
        except FileNotFoundError:
            pass
    return _CACHE

def _cache_put(key, text, model):
    e = {"key": key, "text": text, "model": model, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    _cache_entries()[key] = e

def _llm(system, user):
    """call_llm() behind the disk cache. A hit for the primary model or any fallback model is reused."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    models = _models(provider)
    if _cache_on():
        cache = _cache_entries()
        for m in models:
            e = cache.get(_cache_key(m, system, user))
            if e:
                used = e.get("model", m)
                last_call.clear()
                last_call.update(model=used, usage={"total_tokens": 0}, switched=used != models[0], cached=True)
                return e["text"]
    text = call_llm(system, user)
    if _cache_on() and text and text.strip():  # never cache an empty answer
        used = last_call.get("model") or models[0]
        _cache_put(_cache_key(used, system, user), text, used)
    return text

def build_user_message(question, mission, sources):
    blocks = [f"[{s['id']}] experiment={s['psi']} | type={s['doc_type']} | file={s['file']} "
              f"| location={s['loc']}\n{s['text'][:CHUNK_SHOW]}" for s in sources]
    return (f"MISSION: {mission or '(none given)'}\n\nSOURCES:\n\n" + "\n\n".join(blocks)
            + f"\n\nQUESTION: {question}")

INJECTION_TEXT = ("I can only answer questions about the NASA microgravity combustion data. "
                  "I can't follow instructions that change my rules.")
PARTIAL_LINE = "Results are not in the retrieved sources."
_INJECTION = re.compile(
    r"ignore\s+(?:all|your|any|previous)\b.{0,40}?\b(?:instructions?|rules)\b"
    r"|system\s+prompt|reveal\s+your\s+(?:rules|prompt|instructions)|jailbreak"
    r"|pretend\s+(?:to\s+be|you\s+are)|\bact\s+as\b", re.I)
_PARTIAL_END = re.compile(r"results are not in the retrieved sources\.?[\s*_]*$", re.I)
_BASE = str(BASE_DIR)
# psi -> {"acronym", "title"} for the "Related experiments" block (built from the raw metadata.json files)
EXPERIMENTS_FILE = str(DATA_DIR / "experiments.json")
_EXPERIMENTS = None

def _result(text, sources, outcome, warnings=None, related=None, meta=None):
    r = {"answer": text, "sources": sources, "outcome": outcome, "refused": outcome == "refused",
         "warnings": warnings or [], "related": related or [],
         "model": None, "model_switched": False, "cached": False, "usage": {"total_tokens": 0}}
    if meta:
        r.update(meta)
    return r

def _flat(v):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", "" if v is None else str(v))).strip()

def _experiments():
    """Load experiments.json once. A missing or broken file is a clear error, not blank names."""
    global _EXPERIMENTS
    if _EXPERIMENTS is None:
        try:
            with open(EXPERIMENTS_FILE, encoding="utf-8") as f:
                _EXPERIMENTS = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"experiments.json not found at {EXPERIMENTS_FILE}. It maps each PSI id to its acronym "
                               f"and title (used for 'Related experiments'). Copy it next to chat.py, or rebuild it "
                               f"with build/make_experiments_json.py.") from None
        except ValueError as e:
            raise RuntimeError(f"experiments.json is not valid JSON: {e}") from None
    return _EXPERIMENTS

def _meta(psi):
    e = _experiments().get(psi) or {}
    return e.get("acronym", ""), e.get("title", "")

def related_experiments(sources, n=3):
    out, seen = [], set()
    for s in sources:
        if s["psi"] in seen:
            continue
        seen.add(s["psi"])
        acr, title = _meta(s["psi"])
        out.append({"psi": s["psi"], "acronym": acr, "title": title})
        if len(out) >= n:
            break
    return out

# A line "Not in the data: <items>" lists the items of the question that no source supports (outcome partial).
_MISSING = re.compile(r"^\s*(?:[-*\u2022]\s+)?[*_]{0,2}\s*not in the data\s*[*_]{0,2}\s*:\s*[*_]{0,2}\s*(\S.*?)\s*[*_]*\s*$", re.I)

def _missing_items(text):
    for line in text.split("\n"):
        m = _MISSING.match(line)
        if m and m.group(1).strip(" .*_"):
            return m.group(1).strip(" *_")
    return None

def _classify(text):
    t = text.strip().replace("**", "").strip()
    if t.lower().startswith("not in the data"):
        return "refused"
    return "partial" if (_PARTIAL_END.search(text.strip()) or _missing_items(text)) else "answered"

def _finish_partial(text):
    """Partial answers end with the unsupported items line (if any) and then the exact closing line (if any)."""
    items, keep = None, []
    for line in text.rstrip().split("\n"):
        m = _MISSING.match(line)
        if m and m.group(1).strip(" .*_"):
            items = m.group(1).strip(" *_")
            continue
        keep.append(line)
    body = "\n".join(keep).strip()
    has_results_line = bool(_PARTIAL_END.search(body))
    if has_results_line:
        body = _PARTIAL_END.sub("", body).rstrip()
    tail = ([f"Not in the data: {items}"] if items else []) + ([PARTIAL_LINE] if has_results_line else [])
    return body + ("\n\n" + "\n".join(tail) if tail else "")

# Scaffolding the model must never print: outcome letters and lead-ins (the prompt forbids it; this strips what slips through)
_SCAFF_OUTCOME = re.compile(r"^\s*[*_]{0,2}\s*(?:outcome\s*\(?\s*[ABC]\s*\)?|\(\s*[ABC]\s*\))\s*[*_]{0,2}\s*[:.\u2013\u2014]?\s*", re.I)
_SCAFF_LEADIN = re.compile(
    r"^\s*[*_]{0,2}\s*(?:the sources answer the question|answering the question(?: based on (?:the )?(?:provided )?sources)?"
    r"|based on the (?:provided )?sources|here (?:is|are) the (?:answer|findings))\s*[*_]{0,2}\s*:\s*[*_]{0,2}\s*", re.I)

def strip_scaffolding(text):
    out = []
    for orig in text.split("\n"):
        line, prev = orig, None
        while prev != line:
            prev = line
            line = _SCAFF_OUTCOME.sub("", line, count=1)
            line = _SCAFF_LEADIN.sub("", line, count=1)
        if line.strip() == "" and orig.strip() != "":
            continue  # the whole line was scaffolding
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()

_OBSERVED = re.compile(r"\*\*Observed(\s*:)?\*\*", re.I)

def fix_labels(text, sources):
    """Observed means a cited chunk states a result. Metadata chunks (Objective, Approach, Hypothesis, ...) say
    what is planned or intended, so a bullet that cites any Metadata chunk is relabelled Context."""
    by_id = {s["id"]: s for s in sources}
    out = []
    for line in text.split("\n"):
        cited = [by_id[i] for i in re.findall(r"\[(S\d+)\]", line) if i in by_id]
        if any(c["doc_type"] == "Metadata" for c in cited):
            line = _OBSERVED.sub(lambda m: "**Context" + (m.group(1) or "") + "**", line)
        out.append(line)
    return "\n".join(out)

# a number must not touch a letter/digit before it ("CO2", "FLEX-2", "PSI-98", "cm2" are names, not values)
_NUM = re.compile(r"(?<![A-Za-z0-9.])(?<![A-Za-z]-)([-+]?(?:\d+(?:\.\d+)?|\.\d+))")

def _numbers(text):
    """Absolute values of the numbers in text; ignores [S#] tags; normalizes %, unicode minus, 1,234."""
    # NFKC turns U+2011 (non-breaking hyphen, which models love) into U+2010, so map every hyphen/dash/minus
    # variant to "-"; otherwise "PSI-25" or "FLEX-2" written with one of them leaks "25"/"2" as numbers
    t = re.sub("[\u2010-\u2015\u2212]", "-", unicodedata.normalize("NFKC", text))
    t = re.sub(r"\[S\d+\]", " ", t)
    t = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", t)
    out = set()
    for m in _NUM.finditer(t):
        try:
            out.add(round(abs(float(m.group(1))), 6))
        except ValueError:
            pass
    return out

def check_numbers(text, sources):
    """Warnings for bullets whose numbers are absent from the cited chunks, or that cite unknown ids."""
    by_id = {s["id"]: s for s in sources}
    cache, warnings = {}, []
    for line in text.split("\n"):
        line = line.strip()
        ids = re.findall(r"\[(S\d+)\]", line)
        if not ids:
            continue
        unknown = sorted({i for i in ids if i not in by_id})
        if unknown:
            warnings.append({"text": line[:300], "numbers": [], "issue": "unknown source id " + ", ".join(unknown)})
        body = re.sub(r"^(?:[-*\u2022]|\d+[.)])\s+", "", line)
        nums = _numbers(body)
        if not nums:
            continue
        pool = set()
        for i in ids:
            if i in by_id:
                if i not in cache:  # the model only sees the first CHUNK_SHOW characters of each source
                    cache[i] = _numbers(by_id[i]["text"][:CHUNK_SHOW])
                pool |= cache[i]
        missing = sorted(n for n in nums if n not in pool)
        if missing:
            warnings.append({"text": line[:300], "numbers": [f"{n:g}" for n in missing],
                             "issue": "number not in cited sources"})
    return warnings

def answer(question, mission=""):
    if _INJECTION.search(question):  # before retrieval; no LLM call
        return _result(INJECTION_TEXT, [], "refused")
    _experiments()  # fail early (before any LLM call) if experiments.json is missing
    sources = retrieve(question)[:N_CONTEXT]  # N_CONTEXT = how many sources the model sees (default 8)
    if not sources:
        return _result(NOT_IN_DATA, [], "refused")
    msg = build_user_message(question, mission, sources)
    text = (_llm(SYSTEM_PROMPT, msg) or "").strip()
    if not text:  # reasoning models can return empty content: retry once
        text = (_llm(SYSTEM_PROMPT, msg) or "").strip()
    if not text:
        raise RuntimeError(f"The LLM ({last_call.get('model')}) returned an empty answer twice "
                           f"(finish_reason={last_call.get('finish')}). If this is a Gemini thinking model, set "
                           f"LLM_REASONING_EFFORT=low, or change LLM_MODEL.")
    meta = {"model": last_call.get("model"), "model_switched": bool(last_call.get("switched")),
            "cached": bool(last_call.get("cached")), "usage": dict(last_call.get("usage") or {})}
    text = fix_labels(strip_scaffolding(normalize_tags(text)), sources)
    outcome = _classify(text)
    if outcome == "refused":  # keep only the first sentence; the related block is built from the sources
        related = related_experiments(sources)
        lines = "".join(f"\n- {r['psi']} {r['acronym']}: {r['title']}".rstrip(": ") for r in related)
        return _result("Not in the data." + ("\n\nRelated experiments:" + lines if lines else ""),
                       sources, "refused", related=related, meta=meta)
    if outcome == "partial":  # unsupported-items line, then the exact closing line
        text = _finish_partial(text)
    return _result(text, sources, outcome, warnings=check_numbers(text, sources), meta=meta)

_TAG_GROUP = re.compile(r"[【\[(]\s*(S\d+(?:\s*[,;]\s*S\d+)*)\s*[】\])]")

def normalize_tags(text):
    """Turn 【S3】, (S3), 【S1, S4】 etc. into [S3], [S1][S4]; existing [S#] tags are unchanged."""
    return _TAG_GROUP.sub(lambda m: "".join(f"[{t}]" for t in re.findall(r"S\d+", m.group(1))), text)

def print_result(res):
    print(res["answer"])
    print(f"\n[outcome: {res.get('outcome')}]")
    for w in res.get("warnings") or []:
        print("  WARNING:", w["issue"], w["numbers"], "|", w["text"][:120])
    if res["sources"]:
        print("\nSOURCES:")
        for s in res["sources"]:
            print(f"  {s['id']} | {s['psi']} | {s['doc_type']} | {s['file'][:70]} | "
                  f"{s['loc']} | {s['distance']:.3f}")

def _scrub(msg):
    """Never show an API key, even if a server echoes it back in an error body."""
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        k = os.environ.get(name, "")
        if len(k) >= 8:
            msg = msg.replace(k, "[hidden]")
    return msg

def _fail(e):
    print(f"ERROR: {type(e).__name__}: {_scrub(str(e))}", flush=True)

def main():
    global _progress
    _progress = lambda msg: print(msg, flush=True)
    if len(sys.argv) > 1:
        try:
            print_result(answer(" ".join(sys.argv[1:]), os.environ.get("MISSION", "")))
        except KeyboardInterrupt:
            print("Interrupted.", flush=True)
            sys.exit(130)
        except Exception as e:
            _fail(e)
            sys.exit(1)
        return
    mission = os.environ.get("MISSION", "")
    while True:
        line = input("> ").strip()
        if not line:
            break
        if line.lower().startswith("mission:"):
            mission = line[8:].strip()
            print("mission set.")
            continue
        try:
            print_result(answer(line, mission))
        except KeyboardInterrupt:
            print("Interrupted (the request was still waiting).", flush=True)
        except Exception as e:
            _fail(e)
        print()

if __name__ == "__main__":
    main()
