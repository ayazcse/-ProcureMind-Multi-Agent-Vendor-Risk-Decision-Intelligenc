from app.services.scoring_engine import (
    compute_vendor_score, normalize_weights, compute_pricing_score, compute_delivery_score, DEFAULT_WEIGHTS
)


def test_normalize_weights_sums_to_one():
    w = normalize_weights({"a": 2, "b": 2, "c": 4})
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_normalize_weights_falls_back_on_zero_total():
    w = normalize_weights({"a": 0, "b": 0})
    assert w == DEFAULT_WEIGHTS


def test_pricing_score_cheapest_gets_100():
    score, note = compute_pricing_score({"prices_found": ["USD 1000"]}, [1000.0, 2000.0])
    assert score == 100.0


def test_pricing_score_no_price_disclosed_scores_zero():
    score, note = compute_pricing_score({"prices_found": []}, [1000.0])
    assert score == 0.0
    assert "No" in note


def test_delivery_score_shorter_is_better():
    fast, _ = compute_delivery_score({"delivery_timelines": ["5 days"]})
    slow, _ = compute_delivery_score({"delivery_timelines": ["80 days"]})
    assert fast > slow


def test_compute_vendor_score_reproducible():
    extraction = {"prices_found": ["USD 1000"], "delivery_timelines": ["10 days"]}
    matching = {"overall_match_score": 80.0}
    compliance = {"compliance_score": 90.0}
    risk = {"overall_risk_score": 10.0}
    result1 = compute_vendor_score(extraction, matching, compliance, risk, [1000.0, 1500.0])
    result2 = compute_vendor_score(extraction, matching, compliance, risk, [1000.0, 1500.0])
    assert result1["weighted_total"] == result2["weighted_total"]


def test_compute_vendor_score_breakdown_has_formula():
    extraction = {"prices_found": ["USD 1000"], "delivery_timelines": ["10 days"]}
    matching = {"overall_match_score": 80.0}
    compliance = {"compliance_score": 90.0}
    risk = {"overall_risk_score": 10.0}
    result = compute_vendor_score(extraction, matching, compliance, risk, [1000.0])
    assert "formula" in result["breakdown_json"]
    assert "weights_used" in result["breakdown_json"]


def test_compute_vendor_score_respects_custom_weights():
    extraction = {"prices_found": [], "delivery_timelines": []}
    matching = {"overall_match_score": 100.0}
    compliance = {"compliance_score": 0.0}
    risk = {"overall_risk_score": 0.0}
    # Weight everything on requirement_match only
    custom_weights = {"requirement_match": 1.0, "pricing": 0, "delivery": 0,
                       "compliance": 0, "risk": 0, "technical": 0}
    result = compute_vendor_score(extraction, matching, compliance, risk, [], custom_weights)
    assert result["weighted_total"] == 100.0
