"""
Agent 5 — Vendor Comparison Agent.

Builds a side-by-side comparison from already-computed VendorScore rows.
Pure aggregation/explanation layer — does not recompute scores itself,
keeping a single source of truth (scoring_engine) for all numbers.
"""
from __future__ import annotations
from typing import Any
from app.core.llm_client import generate_text


def compare_vendors(vendor_score_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    vendor_score_rows: list of dicts like
      {"vendor_id", "vendor_name", "weighted_total", "requirement_match_score",
       "pricing_score", "delivery_score", "compliance_score", "risk_score",
       "technical_score", "missing_data_flags": [...]}
    """
    if not vendor_score_rows:
        return {"ranking": [], "table": [], "narrative": "No vendors to compare."}

    ranked = sorted(vendor_score_rows, key=lambda r: r["weighted_total"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i

    strengths_weaknesses = []
    dims = ["requirement_match_score", "pricing_score", "delivery_score",
            "compliance_score", "risk_score", "technical_score"]
    for r in ranked:
        strengths = [d for d in dims if r[d] >= 70]
        weaknesses = [d for d in dims if r[d] < 40]
        strengths_weaknesses.append({
            "vendor_id": r["vendor_id"],
            "vendor_name": r["vendor_name"],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_data_flags": r.get("missing_data_flags", []),
        })

    narrative = _build_narrative(ranked)

    return {
        "ranking": [{"vendor_id": r["vendor_id"], "vendor_name": r["vendor_name"],
                      "rank": r["rank"], "weighted_total": r["weighted_total"]} for r in ranked],
        "table": ranked,
        "strengths_weaknesses": strengths_weaknesses,
        "narrative": narrative,
    }


def _build_narrative(ranked: list[dict[str, Any]]) -> str:
    if len(ranked) == 1:
        base = f"{ranked[0]['vendor_name']} is the only vendor evaluated, scoring {ranked[0]['weighted_total']}/100."
    else:
        top = ranked[0]
        second = ranked[1]
        gap = round(top["weighted_total"] - second["weighted_total"], 1)
        base = (
            f"{top['vendor_name']} ranks first with a weighted score of {top['weighted_total']}/100, "
            f"{gap} points ahead of {second['vendor_name']} ({second['weighted_total']}/100)."
        )
    llm_text = generate_text(
        prompt=f"Vendor ranking data: {ranked}\n\nWrite a 2-3 sentence executive summary of this comparison, "
               "grounded strictly in the numbers given. Mention the top vendor and any notable gap or weakness.",
        system="You are a procurement analyst writing a concise, evidence-based comparison summary.",
        max_tokens=200,
    )
    return llm_text.strip() if llm_text else base
