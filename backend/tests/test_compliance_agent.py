from app.rag.vector_store import RequestVectorStore
from app.agents.compliance_agent import run_compliance_analysis


def test_compliance_met_with_certificate_evidence():
    store = RequestVectorStore("test-compliance-met")
    text = "We are ISO 9001 certified, certificate number ISO-2024-8871, issued by BSI, valid until 2027."
    store.add_document("doc-A", "vendor_a.txt", [(1, text)])
    requirements = [{"text": "Vendor must be ISO 9001 certified", "category": "compliance"}]
    result = run_compliance_analysis(requirements, store, {"doc-A"})
    assert result["results"][0]["status"] == "MET"


def test_compliance_unverified_without_evidence_marker():
    store = RequestVectorStore("test-compliance-unverified")
    text = "We are fully compliant with all data protection regulations."
    store.add_document("doc-A", "vendor_a.txt", [(1, text)])
    requirements = [{"text": "Vendor must comply with GDPR data protection", "category": "compliance"}]
    result = run_compliance_analysis(requirements, store, {"doc-A"})
    assert result["results"][0]["status"] in ("UNVERIFIED", "PARTIAL")


def test_compliance_missing_when_no_evidence():
    store = RequestVectorStore("test-compliance-missing")
    store.add_document("doc-A", "vendor_a.txt", [(1, "We sell office furniture.")])
    requirements = [{"text": "Vendor must hold a valid SOC 2 certification", "category": "compliance"}]
    result = run_compliance_analysis(requirements, store, {"doc-A"})
    assert result["results"][0]["status"] == "MISSING"


def test_compliance_only_processes_compliance_category():
    store = RequestVectorStore("test-compliance-filter")
    store.add_document("doc-A", "vendor_a.txt", [(1, "some text")])
    requirements = [
        {"text": "Must be cheap", "category": "pricing"},
        {"text": "Must be ISO certified", "category": "compliance"},
    ]
    result = run_compliance_analysis(requirements, store, {"doc-A"})
    assert len(result["results"]) == 1
