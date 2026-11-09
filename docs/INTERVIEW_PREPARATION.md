# Interview Preparation

Realistic questions you're likely to get on this project, with answers
grounded in what's actually built — not aspirational claims.

## "Why did you build this?"

To demonstrate practical, end-to-end AI engineering: multi-agent
orchestration with explicit state management (not just prompt-chaining),
a RAG pipeline with real retrieval-quality engineering (not a copy-pasted
ChromaDB tutorial), a transparent/explainable scoring system (a hard
constraint in procurement — you can't tell a vendor "the AI decided" ),
and a human-in-the-loop design that reflects how AI decision-support
actually gets deployed in regulated/high-stakes domains: it recommends,
humans decide.

## "Walk me through the multi-agent architecture."

Seven agents, five of them (extraction, matching, compliance, risk,
scoring) orchestrated per-vendor through a LangGraph `StateGraph` with
explicit nodes and typed state (`VendorEvalState`). Two more (comparison,
decision) run across all vendors' already-computed scores. A seventh
(human review) isn't an LLM agent at all — it's a workflow gate that
blocks finalization without a human decision. Walk through
`MULTI_AGENT_WORKFLOW.md`'s diagram if asked to draw it.

## "Why LangGraph instead of just calling functions in sequence?"

Three reasons I can defend: (1) explicit typed state passed between nodes
makes the data contract between agents visible and testable, rather than
implicit function arguments; (2) per-node error isolation — if the
compliance node throws, I catch it, log it into state, and the risk node
still runs with a safe default, instead of the whole pipeline crashing;
(3) it's the direction the industry is actually moving for multi-step
agentic systems, so it's a more honest demonstration of the skill than
hand-rolled sequential calls.

## "Why TF-IDF instead of a real vector database?"

Direct answer: deliberate trade-off for a zero-dependency, fully
reproducible demo — no API keys, no network calls, same query always
returns the same result. I know the limitation (no true semantic
similarity, and IDF actually discounts shared compliance vocabulary across
vendors) because I hit it directly during development — see
`RAG_PIPELINE_EXPLANATION.md` for the specific bug and the hybrid
keyword-boost fix. The retrieval interface is abstracted
(`RequestVectorStore`) specifically so swapping in ChromaDB + real
embeddings later doesn't touch any agent code.

## "How do you ensure the AI doesn't make things up (hallucination)?"

Every factual score comes from a deterministic rule, not an LLM guess —
regex extraction, TF-IDF+keyword retrieval, evidence-based risk rules. The
LLM, when configured, is only ever asked to phrase an explanation of an
already-computed result, with an explicit system prompt instruction not to
invent facts beyond the given evidence, and a deterministic fallback
string if the LLM call fails or isn't configured. The compliance agent
specifically distinguishes MET (verifiable evidence) from UNVERIFIED
(vendor claims compliance with no supporting marker) — it never upgrades
an unverified claim to a verified one.

## "Explain the SQL scoring methodology."

Weighted sum of six 0-100 component scores (requirement match, pricing,
delivery, compliance, inverted risk, technical), with configurable weights
normalized to sum to 1.0. Every `VendorScore` row stores a full
`breakdown_json` — raw components, weights used, and plain-language notes
— so any ranking is explainable by reading one field. See
`SCORING_METHODOLOGY.md` for the exact formula and known limitations
(technical_score is currently a proxy for requirement match — I'd call
that out proactively if asked to critique my own design).

## "What's your risk assessment methodology?"

Six categories, each scored from concrete evidence rules referencing the
outputs of the upstream agents — e.g., financial risk rises directly when
no pricing is disclosed; compliance risk rises directly from the count of
MISSING/UNVERIFIED compliance checks. No arbitrary numbers — every score
traces to a rule in `risk_agent.py` I can point to line by line.

## "How does human-in-the-loop work?"

Every evaluation run ends with a `Recommendation` row and a linked
`HumanApproval` row created in `PENDING` status — created automatically,
can't be skipped. The procurement request's status can only reach
`CLOSED` through an explicit `POST /review/{id}/decide` call that records
reviewer name, decision, comments, and timestamp as an immutable
`AuditLog` entry. The Decision Agent's summary text always states
explicitly that it's a recommendation requiring approval, never a final
decision — that's enforced in code (see
`test_decision_agent_never_finalizes_without_approval_language`).

## "What security considerations did you address?"

File upload extension allowlist + size limit; uploaded document text
treated strictly as inert data (never as instructions — explicit
prompt-injection consideration documented in
`RAG_PIPELINE_EXPLANATION.md`); no API keys committed to source
(`.env` gitignored); explicit CORS origin configuration.

## "What would you do differently / what are the limitations?"

I'd be specific and not defensive:
- TF-IDF retrieval is good enough for a demo corpus but wouldn't scale in
  retrieval quality to large, heterogeneous real-world document sets the
  way sentence-transformer embeddings would — that's the first upgrade
  I'd make with more time/budget.
- `technical_score` is currently a proxy for requirement match rather than
  an independently weighted technical-capability signal.
- I didn't get to run the LLM-augmented path against a live API key in
  this environment — I'd want to validate prompt quality and latency
  under real conditions before calling that production-ready.
- No load testing — I'd want to understand how the per-request TF-IDF
  index rebuild behaves under concurrent evaluation requests before
  calling this scalable.

## "How would you extend this?"

Sentence-transformer embeddings behind the same `RequestVectorStore`
interface; a requirement-level weighted average (the `Requirement.weight`
field exists but isn't yet folded into scoring); role-based access control
for the human review step (currently any caller can approve); webhook/
notification on new pending reviews; versioned recommendations so a
MODIFIED decision creates a new recommendation with a diff against the
original rather than just a status change.
