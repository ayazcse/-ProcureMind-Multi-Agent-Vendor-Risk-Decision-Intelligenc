# Testing and Evaluation — Actual Results

This document reports only tests that were actually executed in this
build environment. No numbers below are invented. Full raw output is
reproducible by running `python -m pytest tests/ -v` from `backend/`.

## Test suite summary

```
46 passed, 0 failed, 3 warnings in 0.83s
Python 3.12.3, pytest 8.3.3
```

## Coverage by area (all PASSED)

| File | Tests | Covers |
|---|---|---|
| `test_file_parser.py` | 5 | TXT/CSV parsing, unsupported extension handling, empty-file handling |
| `test_extraction_agent.py` | 7 | Email/price/certification/capability/timeline extraction, empty-doc warnings, missing-pricing warnings |
| `test_requirement_matching.py` | 4 | Fulfilled vs missing classification, evidence restricted to the correct vendor's documents, overall-score averaging |
| `test_compliance_agent.py` | 4 | MET with certificate evidence, UNVERIFIED for unsupported claims, MISSING with no evidence, category filtering |
| `test_risk_agent.py` | 4 | Financial risk from missing pricing, compliance risk from missing evidence, low risk for clean vendor, risk-level thresholds |
| `test_scoring_engine.py` | 7 | Weight normalization, pricing/delivery scoring, reproducibility, formula transparency, custom weight respect |
| `test_comparison_and_decision.py` | 5 | Ranking by weighted total, strengths/weaknesses detection, human-approval language always present, empty-input handling |
| `test_api_integration.py` | 9 | Vendor CRUD, request creation, document upload rejection, evaluate-without-documents rejection, **full two-vendor end-to-end workflow** (upload → evaluate → agent executions logged → human review → approval → PDF/JSON reports → audit log), invalid approval status rejection, dashboard summary |
| `test_requirement_matching.py` + others | — | (see above) |

**Total: 46/46 passed.**

## What `test_full_workflow_two_vendors` actually verifies end-to-end

This is the most important test — it exercises the entire system exactly
as a real user would, through the real HTTP API (FastAPI `TestClient`, no
mocking):

1. Create two vendors, one procurement request with 2 requirements
2. Upload a strong proposal (certifications, 24/7 support) and a weak one
   (no certifications, business-hours only)
3. Run `POST /requests/{id}/evaluate` — the full LangGraph pipeline fires
   for both vendors
4. Assert the comparison ranks the stronger vendor first (not just that
   scores exist — that the *ordering is correct given the evidence*)
5. Assert all 6 expected agent names appear in the audit log
   (`agent_executions`)
6. Walk the human review workflow: list pending → approve → verify the
   recommendation reflects `APPROVED`
7. Download both PDF and JSON reports and verify they return valid
   content with correct content-types
8. Verify the audit log recorded `evaluation_completed`

## Manual verification (also actually run, not simulated)

- `python seed_demo_data.py` was run against the real API with the 3
  synthetic demo vendors (Apex Cloud Solutions, BrightPath IT Services,
  Summit Technologies) and a sample 8-requirement procurement request.
  Output ranking: Summit Technologies (75.84) > Apex Cloud Solutions
  (72.22) > BrightPath IT Services (51.12) — correctly reflecting that
  BrightPath's unverifiable compliance claims and weaker capability
  disclosure rank it last, and the two vendors with verifiable
  certificate-numbered compliance evidence rank highest.
- `npm run build` in `frontend/` completes successfully (TypeScript
  compiles with no errors, Vite production bundle generated).
- The FastAPI backend was started and manually exercised via `curl`
  against `/api/health` and `/api/vendors` to confirm the server starts
  cleanly outside the test harness.

## Bugs found and fixed during this build (shown, not hidden)

1. **Delivery timeline parsing** — the regex expected "N day(s)"
   immediately but actual extracted text was "N business days"; fixed to
   accept the business/calendar qualifier.
2. **`llm_enhanced` flag miscomputed** — the Decision Agent's
   `llm_enhanced` flag was comparing two unrelated text strings instead of
   checking whether the LLM call actually returned a result; fixed to
   track the LLM call's actual success/failure.
3. **Unhandled `ValueError` on invalid approval status** — POSTing an
   invalid status to `/review/{id}/decide` crashed with a 500 instead of a
   clean 422; added proper exception handling.
4. **TF-IDF chunk size too large** — initial 220-word sliding-window
   chunks diluted single facts among unrelated content, causing
   well-evidenced vendors to score as poorly-matched as vendors with no
   evidence at all. Fixed with sentence-aware chunking (see
   `RAG_PIPELINE_EXPLANATION.md`).
5. **Shared-vocabulary IDF discount** — once vendors shared compliance
   terminology, standard TF-IDF discounted exactly the terms needed for
   accurate compliance matching. Fixed with a hybrid lexical
   keyword-overlap boost.

## What was explicitly NOT tested (marked honestly per the brief)

- **NOT TESTED**: LLM-augmented agent paths against a live Anthropic or
  OpenAI API key. The deterministic fallback path (triggered when no key
  is configured) is what the test suite and seed script actually
  exercised. The LLM code path was reviewed but not live-verified in this
  environment, since no API key was provided.
- **NOT TESTED**: PostgreSQL as the database backend. The schema and
  `DATABASE_URL` switch are written to support it (and `psycopg2-binary`
  installs cleanly), but the actual test run used SQLite only.
- **NOT TESTED**: PDF/DOCX extraction against real-world scanned or
  complex-layout documents — `pypdf`/`python-docx` parsing was exercised
  against plain-text synthetic demo files, not real PDF/DOCX binaries, in
  this environment.
- **NOT TESTED**: Frontend automated tests (no Jest/Vitest/Playwright
  suite was written) — only `npm run build` (TypeScript + bundling) and
  manual exercise of the API client against a live backend during
  development.
- **NOT TESTED**: Docker Compose build/run (Dockerfiles and compose
  configuration are written but `docker compose up` was not executed in
  this sandboxed environment).
- **NOT TESTED**: Load/concurrency testing, multi-user access patterns.
