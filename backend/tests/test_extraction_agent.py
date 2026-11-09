from app.agents.extraction_agent import run_extraction


SAMPLE_DOC = """Acme Logistics Pvt Ltd
Contact: sales@acme.com
We offer 24/7 support and API integration with cloud hosting.
Pricing: USD 45,000 for annual contract.
Delivery timeline: 14 business days.
We are ISO 9001 certified, certificate number ISO-2024-8871, issued by BSI.
"""


def test_extraction_finds_email():
    result = run_extraction(SAMPLE_DOC, "acme.txt")
    assert "sales@acme.com" in result["emails"]


def test_extraction_finds_price():
    result = run_extraction(SAMPLE_DOC, "acme.txt")
    assert any("45,000" in p for p in result["prices_found"])


def test_extraction_finds_certification():
    result = run_extraction(SAMPLE_DOC, "acme.txt")
    assert "ISO 9001" in result["certifications"]


def test_extraction_finds_capability_keywords():
    result = run_extraction(SAMPLE_DOC, "acme.txt")
    assert "24/7 support" in result["capabilities"]
    assert "cloud hosting" in result["capabilities"]


def test_extraction_finds_delivery_timeline():
    result = run_extraction(SAMPLE_DOC, "acme.txt")
    assert any("14" in t for t in result["delivery_timelines"])


def test_extraction_empty_document_produces_warning():
    result = run_extraction("", "empty.txt")
    assert result["warnings"]
    assert result["emails"] == []


def test_extraction_missing_pricing_warns():
    result = run_extraction("We provide excellent service with no numbers here.", "x.txt")
    assert any("pricing" in w.lower() for w in result["warnings"])
