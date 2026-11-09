# Architecture Overview

## High-level design

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  React/Vite │─────▶│   FastAPI (REST)  │─────▶│  SQLAlchemy ORM      │
│  Frontend   │◀─────│   app/routers/*   │◀─────│  (SQLite/Postgres)   │
└─────────────┘      └─────────┬─────────┘      └─────────────────────┘
                                │
                      ┌─────────▼─────────┐
                      │ Evaluation Service │  orchestrates per-vendor runs,
                      │ (evaluation_service│  persists every agent output
                      │  .py)              │
                      └─────────┬─────────┘
                                │
                      ┌─────────▼─────────┐
                      │  LangGraph State   │  5-node graph: extract → match
                      │  Graph (graph.py)  │  → comply → risk → score
                      └─────────┬─────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
      ┌───────────────┐ ┌──────────────┐  ┌─────────────────┐
      │ RAG Vector     │ │ LLM Client   │  │ Scoring Engine   │
      │ Store (TF-IDF) │ │ Abstraction  │  │ (transparent,    │
      │ per-request    │ │ (optional)   │  │  configurable    │
      │ collections    │ │              │  │  weights)        │
      └───────────────┘ └──────────────┘  └─────────────────┘
```

## Why LLM-optional by design

The brief required "real functionality... no fake AI agents." A system
that silently fails or produces garbage the moment someone forgets to
paste in an API key is not real functionality for a portfolio demo. So
every agent follows one rule:

> **Compute the deterministic, rule-based result first. Only then,
> optionally, ask an LLM to add a natural-language explanation layered on
> top — never ask the LLM to produce the underlying fact or score.**

Concretely:
- Extraction facts (emails, prices, dates, certifications) come from
  regex/keyword matching — always, regardless of LLM availability.
- Requirement match scores come from TF-IDF + keyword-overlap retrieval
  against the vendor's own documents — never from an LLM guessing.
- Risk scores come from concrete evidence rules (see `risk_agent.py`) —
  never from an LLM asked to "rate the risk."
- The LLM, when configured, is only ever asked to **phrase an explanation
  of a result that was already computed**, and every such call has a
  deterministic fallback string if the LLM call fails, times out, or isn't
  configured. The `llm_enhanced` boolean on every agent execution record
  tells you, per call, whether the LLM path actually fired.

This means ProcureMind is demoable and defensible with **zero external
dependencies or API keys** — important both for a free-tier deployment and
for an interview where you don't want to depend on a live API call working
in front of the panel.

## The LLM abstraction layer (`app/core/llm_client.py`)

Single chokepoint for all LLM calls. `generate_text()` and
`generate_json()` check `settings.llm_enabled` (true only if a provider is
selected AND a real key — not the placeholder — is present), call the
configured provider (Anthropic or OpenAI), and return `None` on any
failure (missing key, network error, malformed response) rather than
raising. Every caller treats `None` as "fall back to deterministic
output." Switching providers, or turning the LLM on/off entirely, is a
single `.env` edit — see README.md.

## Data flow for one evaluation

1. Documents are uploaded per vendor per procurement request
   (`routers/documents.py`) → parsed (`services/file_parser.py`) → run
   through the extraction agent immediately for a quick preview.
2. `POST /api/requests/{id}/evaluate` triggers
   `services/evaluation_service.py`, which:
   - builds/refreshes the request's vector store from all vendor documents
   - pre-extracts prices from every vendor (needed for relative pricing
     scores)
   - runs the LangGraph vendor-eval graph once per vendor
   - persists every agent's output to `agent_executions` (full audit
     trail), plus `compliance_checks`, `risk_assessments`, `vendor_scores`
   - runs the Comparison Agent across all vendor scores
   - runs the Decision Intelligence Agent to produce a `Recommendation`
   - creates a `HumanApproval` row in `PENDING` status — the request
     cannot be marked `CLOSED` without a human decision on this row
3. The frontend's AI Evaluation Workspace reads `agent_executions` to show
   per-agent, per-vendor progress and raw output.
4. Human Review page reads `/api/review/pending`, and the reviewer's
   decision is the only thing that can change a request's status to
   `CLOSED`.

## Security considerations

- File upload is restricted by extension allowlist and a configurable max
  size (`MAX_UPLOAD_SIZE_MB`).
- Uploaded document text is never executed or interpreted as instructions
  — it's treated as inert data by every agent (see
  `RAG_PIPELINE_EXPLANATION.md` for the prompt-injection note).
- No API keys are ever committed to source; `.env` is gitignored,
  `.env.example` ships with placeholders only.
- CORS origins are explicitly configured, not wildcarded, in production
  config.
