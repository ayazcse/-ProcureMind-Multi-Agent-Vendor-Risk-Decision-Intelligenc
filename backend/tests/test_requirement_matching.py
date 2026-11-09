from app.rag.vector_store import RequestVectorStore
from app.agents.requirement_matching_agent import run_requirement_matching


def _make_store():
    store = RequestVectorStore("test-matching-req")
    text = (
        "We provide 24/7 customer support via phone and email. "
        "Our cloud hosting infrastructure includes disaster recovery and data encryption. "
        "Delivery timeline is 10 business days for standard orders."
    )
    store.add_document("doc-A", "vendor_a.txt", [(1, text)])
    return store


def test_requirement_fulfilled_when_strong_evidence():
    store = _make_store()
    requirements = [{"text": "Vendor must provide 24/7 customer support", "category": "technical"}]
    result = run_requirement_matching(requirements, store, {"doc-A"})
    assert result["results"][0]["status"] in ("FULFILLED", "PARTIAL")
    assert result["results"][0]["match_score"] > 0


def test_requirement_missing_when_no_evidence():
    store = _make_store()
    requirements = [{"text": "Vendor must offer blockchain-based supply chain tracking", "category": "technical"}]
    result = run_requirement_matching(requirements, store, {"doc-A"})
    assert result["results"][0]["status"] == "MISSING"
    assert result["results"][0]["match_score"] == 0.0


def test_requirement_matching_restricted_to_vendor_documents():
    store = _make_store()
    # A document that exists in the store but does NOT belong to this vendor
    store.add_document("doc-B", "vendor_b.txt", [(1, "We provide 24/7 customer support globally.")])
    requirements = [{"text": "Vendor must provide 24/7 customer support", "category": "technical"}]
    # Query restricted to doc-A only should not pull doc-B's evidence
    result = run_requirement_matching(requirements, store, {"doc-A"})
    for ev in result["results"][0]["evidence"]:
        assert ev["source_document_id"] == "doc-A"


def test_overall_match_score_is_average():
    store = _make_store()
    requirements = [
        {"text": "Vendor must provide 24/7 customer support", "category": "technical"},
        {"text": "Vendor must offer blockchain tracking", "category": "technical"},
    ]
    result = run_requirement_matching(requirements, store, {"doc-A"})
    scores = [r["match_score"] for r in result["results"]]
    assert abs(result["overall_match_score"] - sum(scores) / len(scores)) < 0.1
