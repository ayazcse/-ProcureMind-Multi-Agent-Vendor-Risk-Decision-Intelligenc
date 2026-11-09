from app.agents.comparison_agent import compare_vendors
from app.agents.decision_agent import generate_recommendation


def _row(vendor_id, name, total, **overrides):
    base = {
        "vendor_id": vendor_id, "vendor_name": name, "weighted_total": total,
        "requirement_match_score": 80, "pricing_score": 70, "delivery_score": 60,
        "compliance_score": 90, "risk_score": 85, "technical_score": 75,
        "missing_data_flags": [],
    }
    base.update(overrides)
    return base


def test_compare_vendors_ranks_by_weighted_total():
    rows = [_row("v1", "A", 50.0), _row("v2", "B", 90.0), _row("v3", "C", 70.0)]
    result = compare_vendors(rows)
    ranked_names = [r["vendor_name"] for r in result["ranking"]]
    assert ranked_names == ["B", "C", "A"]


def test_compare_vendors_empty_list():
    result = compare_vendors([])
    assert result["ranking"] == []


def test_compare_vendors_identifies_strengths_weaknesses():
    rows = [_row("v1", "A", 80.0, requirement_match_score=90, pricing_score=20)]
    result = compare_vendors(rows)
    sw = result["strengths_weaknesses"][0]
    assert "requirement_match_score" in sw["strengths"]
    assert "pricing_score" in sw["weaknesses"]


def test_decision_agent_never_finalizes_without_approval_language():
    comparison = {
        "ranking": [{"vendor_id": "v1", "vendor_name": "Acme", "rank": 1, "weighted_total": 85.0}],
        "narrative": "Acme leads.",
    }
    matching_by_vendor = {"v1": {"results": [], "missing_count": 0}}
    compliance_by_vendor = {"v1": {"results": [], "unverified_count": 0}}
    rec = generate_recommendation(comparison, matching_by_vendor, compliance_by_vendor, {})
    assert "human approval" in rec["summary"].lower() or "human approval" in rec["limitations"].lower()
    assert rec["ranked_vendor_ids"] == ["v1"]


def test_decision_agent_handles_empty_ranking():
    rec = generate_recommendation({"ranking": []}, {}, {}, {})
    assert rec["ranked_vendor_ids"] == []
    assert "No vendors" in rec["summary"]
