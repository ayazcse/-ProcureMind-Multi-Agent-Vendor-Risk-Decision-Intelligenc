"""
SQL Scoring and Decision Engine.

Transparent, reproducible, configurable-weight scoring — no hardcoded
rankings. Every sub-score comes directly from an upstream agent's output;
this module only normalizes and applies weights, and records the full
formula trace in `breakdown_json` so every ranking is explainable.
"""
from __future__ import annotations
from typing import Any

DEFAULT_WEIGHTS = {
    "requirement_match": 0.30,
    "pricing": 0.15,
    "delivery": 0.15,
    "compliance": 0.20,
    "risk": 0.15,     # inverted risk, i.e. (100 - risk) contributes positively
    "technical": 0.05,
}


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return DEFAULT_WEIGHTS
    return {k: round(v / total, 4) for k, v in weights.items()}


def compute_pricing_score(extraction: dict[str, Any], all_vendor_prices: list[float]) -> tuple[float, str]:
    """
    Pricing competitiveness: cheapest disclosed price among compared vendors
    scores 100, scaling down linearly for higher prices. No price disclosed
    scores 0 and is flagged.
    """
    prices = extraction.get("prices_found") or []
    if not prices or not all_vendor_prices:
        return 0.0, "No comparable pricing data available."
    import re
    def to_number(p: str) -> float | None:
        digits = re.sub(r"[^\d.]", "", p)
        try:
            return float(digits)
        except ValueError:
            return None
    nums = [n for n in (to_number(p) for p in prices) if n is not None]
    if not nums:
        return 0.0, "Pricing text found but not numerically parseable."
    vendor_min = min(nums)
    cheapest_overall = min(all_vendor_prices) if all_vendor_prices else vendor_min
    if vendor_min <= 0:
        return 0.0, "Invalid price value."
    score = round(min((cheapest_overall / vendor_min) * 100, 100), 1)
    return score, f"Lowest disclosed price {vendor_min} vs cheapest compared vendor {cheapest_overall}."


def compute_delivery_score(extraction: dict[str, Any]) -> tuple[float, str]:
    timelines = extraction.get("delivery_timelines") or []
    if not timelines:
        return 20.0, "No delivery timeline disclosed — scored low by default."
    # Prefer the shortest stated timeline, normalized against a 90-day ceiling
    import re
    days = []
    for t in timelines:
        m = re.match(r"(\d+)\s*(?:business\s*|calendar\s*)?(day|week|month)", t)
        if not m:
            continue
        n, unit = int(m.group(1)), m.group(2)
        mult = {"day": 1, "week": 7, "month": 30}[unit]
        days.append(n * mult)
    if not days:
        return 20.0, "Timeline text found but not parseable into days."
    shortest = min(days)
    score = round(max(0, 100 - (shortest / 90) * 100), 1)
    return score, f"Shortest disclosed delivery timeline: {shortest} day(s)."


def compute_vendor_score(
    extraction: dict[str, Any],
    matching: dict[str, Any],
    compliance: dict[str, Any],
    risk: dict[str, Any],
    all_vendor_prices: list[float],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = normalize_weights(weights or DEFAULT_WEIGHTS)

    requirement_match_score = matching.get("overall_match_score", 0.0)
    compliance_score = compliance.get("compliance_score", 0.0)
    risk_score_raw = risk.get("overall_risk_score", 0.0)
    risk_score_inverted = round(100 - risk_score_raw, 1)
    technical_score = requirement_match_score  # proxy: technical capability ~ requirement fulfillment depth

    pricing_score, pricing_note = compute_pricing_score(extraction, all_vendor_prices)
    delivery_score, delivery_note = compute_delivery_score(extraction)

    components = {
        "requirement_match": requirement_match_score,
        "pricing": pricing_score,
        "delivery": delivery_score,
        "compliance": compliance_score,
        "risk": risk_score_inverted,
        "technical": technical_score,
    }

    weighted_total = round(sum(components[k] * w.get(k, 0) for k in components), 2)

    breakdown = {
        "weights_used": w,
        "raw_components": components,
        "formula": "weighted_total = Σ(component_score_i × weight_i)",
        "notes": {
            "pricing": pricing_note,
            "delivery": delivery_note,
            "risk": f"Inverted from raw risk score {risk_score_raw} (100 - raw).",
        },
        "missing_data_flags": [
            k for k in components if components[k] == 0.0
        ],
    }

    return {
        "requirement_match_score": requirement_match_score,
        "pricing_score": pricing_score,
        "delivery_score": delivery_score,
        "compliance_score": compliance_score,
        "risk_score": risk_score_inverted,
        "technical_score": technical_score,
        "weighted_total": weighted_total,
        "breakdown_json": breakdown,
    }
