"""
Agent 6 — Decision Intelligence Agent.

Consolidates comparison output into a structured recommendation with
evidence references and explicitly stated limitations. This agent NEVER
finalizes a decision — its output always routes to Agent 7 (Human Review)
before anything is considered final.
"""
from __future__ import annotations
from typing import Any
from app.core.llm_client import generate_text


def generate_recommendation(
    comparison: dict[str, Any],
    matching_by_vendor: dict[str, dict],
    compliance_by_vendor: dict[str, dict],
    risk_by_vendor: dict[str, dict],
) -> dict[str, Any]:
    ranking = comparison.get("ranking", [])
    if not ranking:
        return {
            "ranked_vendor_ids": [],
            "summary": "No vendors were evaluated; no recommendation can be made.",
            "evidence_refs": [],
            "limitations": "No data available.",
            "llm_enhanced": False,
        }

    ranked_ids = [r["vendor_id"] for r in ranking]
    top = ranking[0]
    top_id = top["vendor_id"]

    evidence_refs = []
    m = matching_by_vendor.get(top_id, {})
    c = compliance_by_vendor.get(top_id, {})
    for res in m.get("results", [])[:3]:
        for ev in res.get("evidence", [])[:1]:
            evidence_refs.append({
                "type": "requirement_match",
                "requirement": res["requirement_text"],
                "source": f"{ev['source_filename']} (p.{ev['page_number']})",
            })
    for res in c.get("results", [])[:2]:
        if res.get("evidence_source"):
            evidence_refs.append({
                "type": "compliance",
                "requirement": res["requirement_text"],
                "source": res["evidence_source"],
            })

    limitations = _build_limitations(ranking, matching_by_vendor, compliance_by_vendor)
    summary, was_llm_enhanced = _build_summary(top, ranking, comparison.get("narrative", ""))

    return {
        "ranked_vendor_ids": ranked_ids,
        "summary": summary,
        "evidence_refs": evidence_refs,
        "limitations": limitations,
        "llm_enhanced": was_llm_enhanced,
    }


def _build_limitations(ranking, matching_by_vendor, compliance_by_vendor) -> str:
    flags = []
    for r in ranking:
        vid = r["vendor_id"]
        m = matching_by_vendor.get(vid, {})
        c = compliance_by_vendor.get(vid, {})
        if m.get("missing_count", 0) > 0:
            flags.append(f"{r['vendor_name']}: {m['missing_count']} requirement(s) unmatched.")
        if c.get("unverified_count", 0) > 0:
            flags.append(f"{r['vendor_name']}: {c['unverified_count']} compliance claim(s) unverified.")
    if not flags:
        return "No major data gaps detected. This recommendation still requires human approval before finalization."
    return (
        "Data limitations: " + " ".join(flags) +
        " This recommendation requires human approval before finalization and should not be treated as final."
    )


def _build_summary(top: dict, ranking: list[dict], fallback_narrative: str) -> tuple[str, bool]:
    base = (
        f"Based on weighted scoring across requirement match, pricing, delivery, compliance, "
        f"risk, and technical capability, {top['vendor_name']} is the recommended vendor "
        f"with a total score of {top['weighted_total']}/100. "
        "This is a decision-support recommendation only; final selection requires human approval."
    )
    llm_text = generate_text(
        prompt=(
            f"Top-ranked vendor: {top}\nFull ranking: {ranking}\nPrior comparison narrative: {fallback_narrative}\n\n"
            "Write a 3-4 sentence procurement recommendation. State the recommended vendor, "
            "the key evidence-based reasons, and explicitly note this requires human approval and "
            "is not a final decision. Do not invent facts beyond the ranking data given."
        ),
        system="You are a decision-support analyst. You never make final decisions and you never overstate certainty.",
        max_tokens=250,
    )
    if llm_text:
        return llm_text.strip(), True
    return base, False
