# Scoring Methodology

All scoring logic lives in `backend/app/services/scoring_engine.py`. No
score in ProcureMind is a hardcoded or LLM-guessed number — every
component traces to a stated rule.

## The formula

```
weighted_total = Σ (component_score_i × weight_i)   for i in:
  requirement_match, pricing, delivery, compliance, risk, technical
```

Weights are normalized to sum to 1.0 (`normalize_weights()`), configurable
per procurement request via `scoring_weights` on `ProcurementRequest`, and
default to:

| Component | Default Weight |
|---|---|
| requirement_match | 0.30 |
| pricing | 0.15 |
| delivery | 0.15 |
| compliance | 0.20 |
| risk (inverted) | 0.15 |
| technical | 0.05 |

## Component scores (all 0–100)

**requirement_match_score** — the Requirement Matching Agent's
`overall_match_score`: the average TF-IDF+keyword-boost match score across
all stated requirements for that vendor.

**pricing_score** — `compute_pricing_score()`: the vendor with the
lowest disclosed price among all vendors compared scores 100; others scale
down proportionally (`cheapest_overall / vendor_price × 100`). A vendor
disclosing no price scores 0 and is flagged in
`breakdown_json.missing_data_flags`.

**delivery_score** — `compute_delivery_score()`: the vendor's shortest
disclosed delivery timeline (in days) is normalized against a 90-day
ceiling: `max(0, 100 - (days/90)×100)`. No disclosed timeline scores 20
(a low default, not zero, because "unstated" isn't necessarily "longest
possible").

**compliance_score** — the Compliance Agent's `compliance_score`:
`(met_count / total_compliance_requirements) × 100`. Only requirements
tagged `category: "compliance"` count; UNVERIFIED and PARTIAL do not count
as MET (this is a deliberate choice — see
`RAG_PIPELINE_EXPLANATION.md`/`compliance_agent.py` for why UNVERIFIED
claims are never treated as compliant).

**risk_score** — `100 − overall_risk_score` (the Risk Agent's raw
risk, inverted so a higher score is always "better" like every other
component, keeping the weighted-sum formula consistent).

**technical_score** — currently a proxy equal to
`requirement_match_score` (documented explicitly as a simplification —
see "Known limitations" below).

## Transparency guarantees

Every `VendorScore` row stores a `breakdown_json` with:
- `weights_used` — the exact normalized weights applied
- `raw_components` — every component score before weighting
- `formula` — the formula string itself
- `notes` — human-readable notes on pricing/delivery/risk calculations
  (e.g. "Lowest disclosed price 128500.0 vs cheapest compared vendor
  97200.0")
- `missing_data_flags` — which components scored 0 due to absent data

This means any ranking can be fully explained by reading one JSON field —
no score is a black box.

## Reproducibility

`compute_vendor_score()` is a pure function: same inputs always produce
the same output (verified in
`test_compute_vendor_score_reproducible`). No randomness, no
LLM call in the scoring path itself (LLM calls only ever add explanatory
text in upstream agents, never alter a score).

## Known limitations (stated honestly)

- `technical_score` is currently a proxy for `requirement_match_score`
  rather than an independently assessed dimension — a genuinely separate
  technical-capability signal (e.g. weighting specific high-value
  technical requirements more heavily) would be a natural next
  improvement, noted in `INTERVIEW_PREPARATION.md` under "Future
  Improvements."
- Per-requirement `weight` (on the `Requirement` model) is captured but
  not currently folded into the component-level formula — only
  category-level weights (requirement_match, compliance, etc.) are
  applied. A requirement-level weighted average within each category
  would be a straightforward enhancement.
