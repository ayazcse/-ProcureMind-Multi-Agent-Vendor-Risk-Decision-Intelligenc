"""
Agent 4 — Vendor Risk Analysis Agent.

Computes risk scores (0-100, higher = riskier) per category from the
outputs of the extraction, requirement-matching, and compliance agents.
Every score traces to a concrete evidence rule — no arbitrary numbers.
"""
from __future__ import annotations
from typing import Any

from app.core.llm_client import generate_text

RISK_CATEGORIES = [
    "financial", "delivery", "compliance", "technical", "contractual", "documentation"
]


def _level(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def assess_risk(
    extraction: dict[str, Any],
    matching: dict[str, Any],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    evidence_log: dict[str, list[str]] = {c: [] for c in RISK_CATEGORIES}
    scores: dict[str, float] = {c: 0.0 for c in RISK_CATEGORIES}

    # Financial risk: no pricing disclosed is a real red flag
    if not extraction.get("prices_found"):
        scores["financial"] += 40
        evidence_log["financial"].append("No pricing information was found in vendor documents.")
    if extraction.get("llm_risk_flags"):
        for flag in extraction["llm_risk_flags"]:
            if any(w in flag.lower() for w in ["price", "cost", "payment", "financ"]):
                scores["financial"] += 15
                evidence_log["financial"].append(f"Flagged: {flag}")

    # Delivery risk: no timelines disclosed
    if not extraction.get("delivery_timelines"):
        scores["delivery"] += 35
        evidence_log["delivery"].append("No delivery timeline was found in vendor documents.")
    missing_delivery_reqs = [
        r for r in matching.get("results", [])
        if r["status"] == "MISSING" and "deliver" in r["requirement_text"].lower()
    ]
    if missing_delivery_reqs:
        scores["delivery"] += 20 * len(missing_delivery_reqs)
        evidence_log["delivery"].append(f"{len(missing_delivery_reqs)} delivery-related requirement(s) unmet.")

    # Compliance risk: from compliance agent directly
    comp_results = compliance.get("results", [])
    missing_comp = [r for r in comp_results if r["status"] == "MISSING"]
    unverified_comp = [r for r in comp_results if r["status"] == "UNVERIFIED"]
    scores["compliance"] += len(missing_comp) * 25 + len(unverified_comp) * 15
    if missing_comp:
        evidence_log["compliance"].append(f"{len(missing_comp)} compliance requirement(s) have no evidence.")
    if unverified_comp:
        evidence_log["compliance"].append(f"{len(unverified_comp)} compliance claim(s) are unverified.")

    # Technical risk: overall requirement match score, inverted
    overall_match = matching.get("overall_match_score", 0.0)
    scores["technical"] = round(max(0.0, 100 - overall_match) * 0.6, 1)
    if overall_match < 50:
        evidence_log["technical"].append(f"Overall requirement match score is low ({overall_match}/100).")

    # Contractual risk: missing emails / contact = weak accountability signal
    if not extraction.get("emails"):
        scores["contractual"] += 20
        evidence_log["contractual"].append("No vendor contact email found — weak accountability trail.")
    if not extraction.get("certifications"):
        scores["contractual"] += 10
        evidence_log["contractual"].append("No certifications referenced in proposal documents.")

    # Documentation risk: extraction warnings are a direct signal
    warn_count = len(extraction.get("warnings", []))
    scores["documentation"] = min(warn_count * 15, 100)
    if warn_count:
        evidence_log["documentation"].append(f"{warn_count} extraction warning(s) raised during document parsing.")

    results = []
    for cat in RISK_CATEGORIES:
        score = round(min(scores[cat], 100), 1)
        level = _level(score)
        evidence = evidence_log[cat] or ["No significant risk indicators detected for this category."]
        explanation = _explain(cat, level, evidence)
        results.append({
            "category": cat,
            "risk_level": level,
            "score": score,
            "evidence": evidence,
            "explanation": explanation,
        })

    overall_risk_score = round(sum(r["score"] for r in results) / len(results), 1)
    return {
        "categories": results,
        "overall_risk_score": overall_risk_score,
        "overall_risk_level": _level(overall_risk_score),
    }


def _explain(category: str, level: str, evidence: list[str]) -> str:
    base = f"{category.capitalize()} risk assessed as {level} based on: " + "; ".join(evidence)
    llm_text = generate_text(
        prompt=(
            f"Risk category: {category}\nLevel: {level}\nEvidence: {evidence}\n\n"
            "Write 1-2 sentences explaining this risk level to a procurement manager, "
            "grounded only in the evidence given."
        ),
        system="You are a vendor risk analyst. Be concrete and evidence-based.",
        max_tokens=150,
    )
    return llm_text.strip() if llm_text else base
