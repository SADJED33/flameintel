# NASA microgravity combustion chatbot

Answers questions **only** from a local index of 24 NASA microgravity combustion experiments (13,112 chunks),
with source citations. Tested with Python 3.12.

## Folder layout

```
challenge 8/
├─ chat.py, eval.py, ask.py        entry points (they find their data from their own folder, so they work
│                                  from any working directory)
├─ .env, .env.example, requirements.txt, README.md, .gitignore
├─ data/    kb_index/ (the index), experiments.json, llm_cache.jsonl, known_gaps.txt, coverage.csv
├─ eval/    eval_questions.jsonl, eval_history.csv, eval_last.csv, eval_partial_*.jsonl
├─ build/   scripts that rebuild the index (build_index.py, ...) and their intermediate files (runs.jsonl, ...)
├─ raw/     the full downloaded NASA data (only needed to rebuild the index)
└─ _archive/  old backups, logs, reports
```

## Setup

```
pip install -r requirements.txt
copy .env.example .env        # then edit .env and put your own API key in it
```

`.env` stays in the project root and uses the OpenAI-compatible API format. Required: `LLM_PROVIDER=openai`,
`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LLM_MODEL` (the example file shows a Groq setup; for Gemini use
`OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/` and a Gemini model name).
Never commit `.env`. Optional settings: `LLM_FALLBACK_MODELS` (comma list, tried on HTTP 429 or a stall),
`LLM_TIMEOUT` (seconds, default 30), `LLM_REASONING_EFFORT` (minimal|low|medium|high), `LLM_TEMPERATURE`,
`LLM_CACHE` (on|off), `N_CONTEXT` (sources sent to the model, default 8), `CHUNK_SHOW` (characters per
source, default 1500), `MAX_DISTANCE` (retrieval cut-off, default 0.40), `MISSION`.

The first run downloads the embedding model (BAAI/bge-small-en-v1.5) from Hugging Face.

## Run

```
python chat.py "What channels did the SAFFIRE smoke detector record?"
python chat.py                       # interactive; "mission: ..." sets a mission; an empty line quits
```

It works from any folder, for example `python "C:\path\to\challenge 8\chat.py" "..."`.
It prints the answer, `[outcome: ...]`, any warnings, and the numbered SOURCES (S1, S2, ...).

## Use it from Python

```python
from chat import answer
result = answer("What channels did the SAFFIRE smoke detector record?", mission="")
```

`answer(question, mission="")` returns a dict:

| field | meaning |
|---|---|
| `answer` | the text, with `[S#]` tags and **Observed** / **Context** labels |
| `sources` | list of `{id, text, psi, doc_type, file, loc, distance, routed}` that the model saw |
| `outcome` | `answered`, `partial` (some part not supported, ends with "Not in the data: ..." or "Results are not in the retrieved sources."), or `refused` |
| `refused` | `True` when `outcome == "refused"` |
| `warnings` | list of `{text, numbers, issue}`: a number not found in the cited chunks, or an unknown `[S#]` tag |
| `related` | for refusals: up to 3 `{psi, acronym, title}` of related experiments |
| `model`, `model_switched`, `cached` | which model answered, whether a fallback model was used, whether it came from `data/llm_cache.jsonl` |
| `usage` | `{prompt_tokens, completion_tokens, total_tokens}` (0 when cached or not sent to the LLM) |

Questions that are off-topic, or that try to change the rules, are refused without calling the LLM.

## Files a teammate needs

- `chat.py`, `data/kb_index/` (the index), `data/experiments.json`, `.env.example`, `requirements.txt`
- `data/experiments.json` maps each PSI id to its acronym and title (used for the `related` list). `chat.py` stops
  with a clear error if it is missing. It can be rebuilt with `python build/make_experiments_json.py` (needs `raw/`).
- For evaluation: `eval.py` and `eval/eval_questions.jsonl`
  (`python eval.py full --subset core20 --label NAME`; results go to `eval/`).
- Coverage notes: `data/known_gaps.txt`, `data/coverage.csv`.
- Not needed to run: `raw/`, `build/`, `_archive/`. `raw/` and `build/` are only for rebuilding the index.

## FlameIntel dashboard (web app)

A Next.js dashboard (`dashboard/`) on top of a FastAPI backend (`api/`) that imports `chat.py` directly. The LLM key stays in `.env`
on the server and is never sent to the browser.

**Run (Windows):** `powershell -ExecutionPolicy Bypass -File .\start.ps1`, then open http://localhost:3000.
Needs Python 3.12 and Node.js LTS (`winget install OpenJS.NodeJS.LTS`). The API takes about 30 s to load the index.

Manual run: `python -m uvicorn api.main:app --port 8000` and, in `dashboard/`, `npm install` then `npm run dev`.

Rebuild generated data (all in `api/data/`):
- `python api/build_investigations.py` builds `investigations.json` and `index_files.json` from `raw/`, `data/` and the index (no LLM needed).
- `python api/build_insights.py` runs 12 fixed questions through `answer()` and writes `insights.json` (needs the LLM key; cached).

API: `POST /api/chat`, `GET /api/investigations[/{psi}]`, `/api/rank`, `/api/overview`, `/api/compare`, `/api/datasets[/{id}/preview|export]`, `/api/insights`, `/api/report`, `/api/coverage`, `/api/health`.
Ranking weights live in one dict, `RANK_WEIGHTS` in `api/config.py`.

Pages: Overview, Explorer, Investigation details, Compare, AI Assistant, Data Explorer, Fire Safety Insights, Report, About the data.

### Real vs curated
- **Real**: all 24 investigation records (metadata.json), KPI counts, charts, dataset columns/types/missing counts/rows (pandas on the real files), units (only when in a header), extraction status, all assistant answers and citations, coverage numbers, insight claims (cited model output).
- **App-generated (labelled in the UI)**: topic tags (keyword rules), relevance score and "why relevant" text (heuristic, not an official NASA score), ML-readiness checklist.
- **Curated by us (labelled "Potential application" / "FlameIntel interpretation")**: per-theme application and interpretation sentences (`POTENTIAL_APPLICATIONS` in `api/config.py`, `APP_INTERP` in `api/build_insights.py`), the 12 insight questions, scenario topic weights, gravity notes.
- **Demo data**: none.
