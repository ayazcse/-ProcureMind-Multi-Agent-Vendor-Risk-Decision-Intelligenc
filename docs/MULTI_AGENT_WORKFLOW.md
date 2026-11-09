# Multi-Agent Workflow (LangGraph)

## Why LangGraph

LangGraph gives us explicit state management across agent steps: a typed
state object (`VendorEvalState`) flows through named nodes, each node
reads only the state keys it needs and writes its own, and errors in one
node are caught and recorded without crashing the whole run — downstream
nodes degrade gracefully instead of the entire evaluation failing. This is
a meaningfully different thing from "seven prompts calling the same
function" — each agent is a distinct module with its own file, its own
tests, and its own deterministic core.

## The graph (`app/agents/graph.py`)

```
extract ──▶ match ──▶ comply ──▶ assess_risk ──▶ score ──▶ END
```

One graph execution evaluates **one vendor** against the procurement
request's requirements. The evaluation service (`evaluation_service.py`)
calls this graph once per vendor, then runs the Comparison and Decision
agents across all vendors' results afterward (those two operate on
already-computed scores, not per-vendor, so they live outside the graph).

### Node: `extract` → Agent 1, Document Extraction Agent
Regex/keyword extraction of emails, prices, dates, delivery timelines,
certifications, and capability keywords from the vendor's document text.
Optionally layers an LLM summary/risk-flag pass on top (additive only).

### Node: `match` → Agent 2, Requirement Matching Agent
For each requirement, retrieves the top evidence chunks from the vendor's
own documents (via the RAG store, restricted to that vendor's document
IDs) and classifies FULFILLED / PARTIAL / MISSING based on a hybrid
TF-IDF + keyword-overlap score. See `RAG_PIPELINE_EXPLANATION.md`.

### Node: `comply` → Agent 3, Compliance Analysis Agent
Runs only on requirements tagged `category: "compliance"`. Distinguishes
MET (evidence includes a verifiable marker like a certificate number) from
UNVERIFIED (vendor claims compliance with no supporting evidence) from
MISSING (no evidence at all) — see the regex patterns in
`compliance_agent.py` for exactly how that distinction is made.

### Node: `assess_risk` → Agent 4, Vendor Risk Analysis Agent
Computes 6 risk categories (financial, delivery, compliance, technical,
contractual, documentation), each from concrete evidence rules that
reference the outputs of the prior three nodes — e.g. "no pricing
disclosed" directly raises financial risk; "N compliance requirements
missing evidence" directly raises compliance risk. No arbitrary numbers.

### Node: `score` → SQL Scoring Engine
Not an LLM agent — the transparent, configurable-weight scoring
calculation described in `SCORING_METHODOLOGY.md`. Lives in
`services/scoring_engine.py` and is called from the graph node
`node_score`.

## After the graph: Agents 5, 6, 7

### Agent 5 — Vendor Comparison Agent (`comparison_agent.py`)
Takes the list of all vendors' `VendorScore` rows for the request, ranks
them by `weighted_total`, and identifies per-vendor strengths (dimensions
scoring ≥70) and weaknesses (dimensions scoring <40). Pure aggregation —
never recomputes a score, so there's a single source of truth.

### Agent 6 — Decision Intelligence Agent (`decision_agent.py`)
Consolidates the comparison into a `Recommendation`: ranked vendor IDs, a
summary, evidence references (pulled from the top vendor's actual matching
and compliance results), and an explicit `limitations` string listing data
gaps. **Never marks anything final** — every summary string includes "this
is a decision-support recommendation only."

### Agent 7 — Human Review Agent (`human_review_agent.py`)
Not an LLM call — a workflow gate. Creates a `HumanApproval` row in
`PENDING` status alongside every `Recommendation`. The procurement
request's `status` can only become `CLOSED` through
`POST /api/review/{approval_id}/decide`, which records reviewer name,
decision, comments, and timestamp, and writes an immutable `AuditLog` row.

## Error handling in the graph

Each node wraps its agent call in try/except; on failure it logs the error
into `state["errors"]` and substitutes a safe default (e.g. risk assessment
defaults to CRITICAL/100 if it crashes, rather than silently reporting
LOW risk) so a single agent failure can't accidentally make a risky vendor
look safe. The evaluation service surfaces these errors in the persisted
`agent_executions.error_message` field, visible in the AI Evaluation
Workspace.
