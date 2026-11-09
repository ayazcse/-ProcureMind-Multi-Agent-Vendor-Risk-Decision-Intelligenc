from app.agents.risk_agent import assess_risk


def test_no_pricing_raises_financial_risk():
    extraction = {"prices_found": [], "delivery_timelines": ["10 days"], "emails": ["a@b.com"],
                  "certifications": ["ISO 9001"], "warnings": []}
    matching = {"overall_match_score": 80.0, "results": []}
    compliance = {"results": []}
    result = assess_risk(extraction, matching, compliance)
    financial = next(c for c in result["categories"] if c["category"] == "financial")
    assert financial["score"] > 0


def test_missing_compliance_evidence_raises_compliance_risk():
    extraction = {"prices_found": ["USD 1000"], "delivery_timelines": ["10 days"], "emails": ["a@b.com"],
                  "certifications": [], "warnings": []}
    matching = {"overall_match_score": 80.0, "results": []}
    compliance = {"results": [{"status": "MISSING", "requirement_text": "x"}]}
    result = assess_risk(extraction, matching, compliance)
    comp_risk = next(c for c in result["categories"] if c["category"] == "compliance")
    assert comp_risk["score"] > 0


def test_clean_vendor_has_low_overall_risk():
    extraction = {"prices_found": ["USD 1000"], "delivery_timelines": ["10 days"], "emails": ["a@b.com"],
                  "certifications": ["ISO 9001"], "warnings": []}
    matching = {"overall_match_score": 95.0, "results": []}
    compliance = {"results": [{"status": "MET", "requirement_text": "x"}]}
    result = assess_risk(extraction, matching, compliance)
    assert result["overall_risk_level"] in ("LOW", "MEDIUM")


def test_risk_level_thresholds():
    from app.agents.risk_agent import _level
    assert _level(10) == "LOW"
    assert _level(30) == "MEDIUM"
    assert _level(60) == "HIGH"
    assert _level(90) == "CRITICAL"
