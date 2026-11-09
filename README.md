# ProcureMind — Multi-Agent Vendor Risk & Decision Intelligence System

ProcureMind is a decision-support platform that analyzes vendor proposals
against procurement requirements using a genuine multi-agent pipeline
(LangGraph-orchestrated), a local RAG retrieval layer, a transparent SQL
scoring engine, and a mandatory human-approval gate. It never finalizes a
procurement decision on its own.

**Built by:** Ayaz Alam, as a portfolio project for Data Analyst / AI
Engineering interviews.

## What's actually here

This is a working application, not a mockup. Every button calls a real
backend route; every score traces to a stated formula; every "AI reasoning"
step runs a deterministic rule-based pass first and optionally layers an
LLM explanation on top if you add an API key (see below). 46 automated
tests pass against the real code (see `TESTING_AND_EVALUATION.md`).

## Quick start (Windows, zero setup)

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The backend defaults to SQLite (zero
database setup) and runs in fully deterministic mode (no LLM key needed —
see `ARCHITECTURE.md` for what that means).

Full step-by-step Windows instructions: `SETUP_GUIDE_WINDOWS.md`.

## Loading the demo scenario

```powershell
cd backend
python seed_demo_data.py
```

This creates 3 synthetic vendors, a procurement request with 8
requirements, runs the full agent pipeline, and prints the ranking —
all through the real API, no shortcuts.

## Adding an LLM key later

ProcureMind runs fully functional with **zero API key** — extraction,
matching, compliance, and risk scoring are all deterministic and rule-based
by default. To get richer LLM-generated explanations and recommendations,
just add a key to `backend/.env`:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Restart the backend — no code changes needed. See `ARCHITECTURE.md` for
exactly which agent outputs change.

## Project structure

```
ProcureMind/
├── backend/            FastAPI + LangGraph + SQLAlchemy + RAG
│   ├── app/
│   │   ├── agents/      7 agents + LangGraph orchestration
│   │   ├── core/        config, database, LLM abstraction
│   │   ├── models/      SQLAlchemy models (12 tables)
│   │   ├── rag/         TF-IDF vector store + hybrid retrieval
│   │   ├── routers/     FastAPI endpoints
│   │   ├── schemas/     Pydantic schemas
│   │   └── services/    scoring engine, file parser, reports
│   ├── tests/           46 automated tests
│   ├── demo_data/       3 synthetic vendors + sample procurement request
│   └── seed_demo_data.py
├── frontend/            React + TypeScript + Vite dashboard
└── docs/                this documentation set
```

## Documentation index

- `SETUP_GUIDE_WINDOWS.md` — exact PowerShell setup commands
- `DEPLOYMENT_GUIDE.md` — Docker + free-tier hosting options
- `ARCHITECTURE.md` — system design, LLM-optional design
- `MULTI_AGENT_WORKFLOW.md` — LangGraph workflow details
- `RAG_PIPELINE_EXPLANATION.md` — retrieval design + known limitations
- `DATABASE_SCHEMA.md` — all 12 tables
- `SCORING_METHODOLOGY.md` — the exact scoring formula
- `API_DOCUMENTATION.md` — all endpoints
- `TESTING_AND_EVALUATION.md` — actual test results
- `INTERVIEW_PREPARATION.md` — how to explain and defend this project

## Known limitations (stated honestly, not buried)

- RAG uses TF-IDF + a lexical keyword-overlap boost, not a hosted vector
  DB or sentence-transformer embeddings — a deliberate zero-dependency
  choice, documented with its trade-offs in `RAG_PIPELINE_EXPLANATION.md`.
- SQLite is the default database; PostgreSQL is fully supported via
  `DATABASE_URL` and a Compose override, but wasn't run against a live
  Postgres server in this environment (see `DEPLOYMENT_GUIDE.md`).
- LLM-augmented agent explanations were not exercised end-to-end against a
  live Anthropic/OpenAI API key in this build — the fallback path (no key)
  is what was actually tested. The code path for a real key is written and
  reviewed but not live-verified; try it with your own key and report back.
- The frontend was build-verified (`npm run build` succeeds) and
  manually exercised against the live API during development; it was not
  run through an automated frontend test suite.
