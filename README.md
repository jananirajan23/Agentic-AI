# Reviewer-Lens

An AI-based agentic system that pre-reviews student capstone project reports
before faculty evaluation. A faculty member signs in, uploads a PDF report
through a web UI, and the backend parses it and runs three verification
agents; the frontend displays a composite score, flagged issues, and
improvement suggestions. AI findings never reach a student directly — a
faculty reviewer must check the findings on a dedicated approval screen and
explicitly approve the final report before it's downloadable.

**This tool supports faculty review — it does not replace it.**

## Architecture

```
Browser (React frontend)
    |  sign in / register
    v
FastAPI backend  --------------------------> SQLite (users, review jobs)
    |
    v
Document Parsing Agent  --------> extracts: problem statement, literature
    |                              section, module list, diagram image(s)
    |
    +----------------+----------------+
    v                v                v
Literature Survey   Architecture     Alignment
Agent                Structure Agent  Agent
(Semantic Scholar    (OCR + Groq      (Embeddings + Groq LLM:
 API + Groq LLM      vision model     cosine-similarity match between
 scoring)            read diagram)    diagram components & modules)
    |                    |
    +----------------+----------------+
                     v
            Report Aggregator Agent
            (composite score, flags,
             suggestions -> AI-draft .docx)
                     |
                     v
     FastAPI returns JSON results + draft report
                     |
                     v
     React frontend renders score dashboard + flags
                     |
                     v
     Faculty Review & Approval screen (human-in-the-loop):
     check/uncheck individual flags & suggestions, edit the
     research-gap summary, then approve
                     |
                     v
     Faculty-approved .docx generated -> downloadable,
     dashboard updated with approval status
```

The four backend agents are orchestrated with **LangGraph**, using a single
shared `ReviewState` TypedDict passed through the graph:

```
parse -> literature   \
      \-> architecture -> alignment -> aggregate -> END
literature ------------------------------^
```

`literature` and `architecture` run in parallel after `parse`. `alignment`
runs after `architecture` (it needs the diagram components). `aggregate`
waits for both `literature` and `alignment` — via a single
`add_edge(["literature", "alignment"], "aggregate")` **join**, not two
separate `add_edge` calls. (Two separate edges into the same node are each
an independent trigger in LangGraph, not a barrier — that bug shipped in an
earlier version of this graph and silently ran `aggregate`, and its Groq
suggestion-generation call, twice per review.)

> **Important LangGraph detail:** every node function returns only the keys
> it adds or changes (a partial dict), never the full state object.
> Returning the whole mutated state from two parallel branches causes a
> concurrent-write conflict on shared keys (e.g. `pdf_path`) and raises
> `InvalidUpdateError`. See [`agents/`](backend/agents/) — every `run()`
> function follows this rule.

## Backend setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # then edit .env and paste in your real key
uvicorn app:app --reload
```

`config.py` loads `backend/.env` automatically via `python-dotenv` if present
(a real environment variable always takes precedence over it). If you'd
rather not use a `.env` file, `export GROQ_API_KEY=your_key_here` (or
`$env:GROQ_API_KEY = "your_key_here"` in PowerShell) works the same way.

The API runs at `http://localhost:8000`. Without `GROQ_API_KEY` set, the app
still starts and processes uploads normally — the LLM-dependent parts of
each score come back reduced (with an explanatory flag) instead of
crashing, and `GET /api/health` reports `groq_configured: false` so the
frontend can show a setup banner. OCR (architecture diagram labels) and the
embeddings-based alignment check run **without** a Groq key — they use
RapidOCR and a local sentence-transformer model respectively, not Groq.

On first run, the backend creates `backend/data/reviewerlens.db` (SQLite —
faculty accounts + review jobs) automatically. Set `JWT_SECRET` in `.env`
before deploying anywhere reachable by more than one trusted person; the
default in `config.py` is dev-only.

### About the Groq model IDs

`GROQ_TEXT_MODEL` and `GROQ_VISION_MODEL` (in [`config.py`](backend/config.py))
are **not hardcoded from memory** — Groq deprecates and replaces models
fairly often (for example, `llama-3.3-70b-versatile` was deprecated in favor
of `openai/gpt-oss-120b`). The defaults shipped here were confirmed against
Groq's docs at build time:

- `GROQ_TEXT_MODEL` defaults to `openai/gpt-oss-120b` (production instruct model)
- `GROQ_VISION_MODEL` defaults to `qwen/qwen3.8-27b` (production multimodal model)

Before you deploy, re-confirm these are still current via
`GET https://api.groq.com/openai/v1/models` or
[console.groq.com/docs/models](https://console.groq.com/docs/models), and
override via the `GROQ_TEXT_MODEL` / `GROQ_VISION_MODEL` environment
variables if they've changed.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173` and proxies `/api/*` to the backend
at `http://localhost:8000` (see `frontend/vite.config.ts`). A first-time
user registers a faculty account from the login screen; every review is
scoped to the account that uploaded it. See
[`frontend/README.md`](frontend/README.md) for more detail.

## File map

| Path | Purpose |
|---|---|
| `backend/config.py` | Central config — API keys, JWT settings, model IDs, score weights, section headings, storage paths |
| `backend/database.py` / `backend/models_db.py` | SQLite persistence — `User` and `ReviewJob` (job status, scores, flags, approval state) |
| `backend/auth.py` / `backend/schemas.py` | Password hashing (salted PBKDF2), JWT issuing/verification, Pydantic request/response models |
| `backend/state.py` | Shared `ReviewState` TypedDict passed through the LangGraph pipeline |
| `backend/graph.py` | Builds and wires the LangGraph `StateGraph` |
| `backend/app.py` | FastAPI app — auth, `/api/review`, `/api/reviews` (dashboard), `/api/review/{id}` (detail), `/api/review/{id}/approve`, `/api/report/{id}`, `/api/health` |
| `backend/agents/document_parser.py` | Splits PDF text into sections, extracts diagram images |
| `backend/agents/literature_survey_agent.py` | Citation extraction, Semantic Scholar lookup, relevance/recency scoring, citation-resolution rate |
| `backend/agents/architecture_structure_agent.py` | OCR (`ocr_util.py`, RapidOCR) + Groq vision model reading, merged into one component list; heuristic scoring |
| `backend/agents/alignment_agent.py` | Embeddings (`embedding_util.py`, sentence-transformers) + Groq LLM comparison, blended into one score |
| `backend/agents/report_aggregator.py` | Composite score, suggestions, AI-draft `.docx`, and the faculty-approved final `.docx` |
| `backend/agents/metrics.py` | Precision@K / Recall@K / citation-resolution-rate — pure functions, exercised in tests and `tests/evaluate_retrieval.py` |
| `backend/tests/` | pytest suite: unit (parsing, citation regex, scoring, embeddings math, OCR/vision merge), auth, and end-to-end API integration tests |
| `frontend/src/auth/AuthContext.tsx` | Login/register/logout, JWT persisted in `localStorage` |
| `frontend/src/pages/` | `LoginPage`, `RegisterPage`, `DashboardPage` (review history), `ReviewWorkspacePage` (upload → processing → faculty approval → download) |
| `frontend/src/components/ReviewApprovalPanel.tsx` | The human-in-the-loop screen: check/uncheck flags & suggestions, edit the gap summary, approve |
| `frontend/src/components/` | `UploadPanel`, `ProcessingView`, `ScoreDashboard`, `FlagsList`, `SuggestionsList`, `DownloadButton` (authenticated blob download) |

## Extension points

1. **Section splitting** (`backend/agents/document_parser.py`) relies on
   heading-keyword matching against `config.SECTION_HEADINGS`. Different
   department report templates use different heading phrasing — tune the
   keyword lists per template rather than the parsing logic itself.
2. **Citation extraction** (`backend/agents/literature_survey_agent.py`)
   handles the common `[n] Author, "Title," Venue, Year` and `Author (Year)`
   reference formats via regex. Very irregular reference styles should lean
   on the `llm_extract_citations` fallback, which is triggered automatically
   whenever the regex pass finds fewer than 2 candidates.
3. **New verification agents**: add a node + edge in `graph.py`, add its
   output keys to `state.py`'s `ReviewState`, and surface its flags in
   `report_aggregator.py`'s `all_flags` — the shared-state design means
   nothing else needs to change to plug in, e.g., a future problem-statement
   or methodology-consistency agent.

## Testing

```bash
cd backend
pytest tests/ -q
```

58+ tests covering:

- **Unit** — section splitting, citation regex, Precision@K/Recall@K,
  OCR-label filtering/merge logic, embedding-based alignment math (via a
  mocked embedding model so the real ~90MB download isn't required to run
  the suite), password hashing, JWT round-trips.
- **Integration** — `TestClient`-driven register → login → upload → poll →
  approve → download, including ownership isolation (one faculty account
  can't see another's reviews).
- **End-to-end** — a synthetic PDF (`tests/make_dummy_report.py`) is POSTed
  through the full FastAPI app and LangGraph pipeline (OCR and the local
  embedding model run for real; Groq is forced off via `conftest.py` for
  determinism — see its docstring).

`tests/evaluate_retrieval.py` is a separate, manually-run script (real
Semantic Scholar network calls, not part of the automated suite) that
computes actual Precision@K/Recall@K against a small labelled fixture set —
see its docstring for why this is kept out of the deterministic pytest run.

## Validation performed

- Backend imports and the LangGraph graph compile cleanly with no
  `GROQ_API_KEY` set.
- Full pipeline run end-to-end against a real capstone-style PDF with a real
  Groq key: OCR + vision merge, Semantic Scholar resolution, and the
  embeddings + LLM alignment blend all produced sensible, non-zero scores
  and human-readable flags.
- Diagram extraction was verified on both code paths: embedded raster
  images, and the 150 DPI page-render fallback when a diagram is
  vector-drawn rather than embedded as a raster image.
- Full browser-driven walkthrough: register → login → upload → processing →
  faculty review/approval (toggling flags, editing the gap summary) →
  approved report → authenticated download → dashboard reflecting the
  approved status and score. Found and fixed two real bugs this way (see
  below) rather than just asserting the flow "should" work.

### Bugs found and fixed during this pass

1. **Double `aggregate` execution** (`backend/graph.py`): two separate
   `add_edge("literature"/"alignment", "aggregate")` calls each independently
   triggered the node instead of joining, so `aggregate` — and its Groq
   suggestion-generation call — ran once prematurely (before `alignment`
   even finished) and once for real. Fixed with LangGraph's list-based join
   syntax, `add_edge(["literature", "alignment"], "aggregate")`.
2. **Stale review-detail cache in the frontend**
   (`frontend/src/pages/ReviewWorkspacePage.tsx`): the detail query's
   `refetchInterval` stopped polling after its first successful fetch —
   which, taken mid-pipeline, was a near-empty snapshot — so the results
   screen kept showing every score as `0` even after the job finished.
   Fixed by keying the query on the job's status so a status transition
   (`processing` → `done` → `approved`) forces a fresh fetch.
