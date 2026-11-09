"""
End-to-end API integration tests covering: vendor CRUD, document upload,
procurement request creation, full evaluation workflow, agent workflow
transitions, database operations, human approval workflow, and report
generation.
"""


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_list_vendor(client):
    r = client.post("/api/vendors", json={"name": "Test Vendor Co", "contact_email": "x@y.com"})
    assert r.status_code == 200
    vendor_id = r.json()["id"]

    r2 = client.get("/api/vendors")
    assert r2.status_code == 200
    assert any(v["id"] == vendor_id for v in r2.json())


def test_get_vendor_not_found(client):
    r = client.get("/api/vendors/does-not-exist")
    assert r.status_code == 404


def test_create_procurement_request_with_requirements(client):
    payload = {
        "title": "Test Procurement",
        "description": "desc",
        "requirements": [
            {"text": "Must support API integration", "category": "technical"},
            {"text": "Must be ISO 27001 certified", "category": "compliance"},
        ],
    }
    r = client.post("/api/requests", json=payload)
    assert r.status_code == 200
    req_id = r.json()["id"]

    detail = client.get(f"/api/requests/{req_id}").json()
    assert len(detail["requirements"]) == 2
    assert detail["status"] == "OPEN"


def test_document_upload_unsupported_extension_rejected(client):
    r = client.post("/api/documents/upload", files={"file": ("bad.exe", b"binary", "application/octet-stream")})
    assert r.status_code == 400


def test_evaluate_without_documents_fails(client):
    req = client.post("/api/requests", json={"title": "Empty Req", "requirements": []}).json()
    r = client.post(f"/api/requests/{req['id']}/evaluate")
    assert r.status_code == 400


def test_full_workflow_two_vendors(client):
    v1 = client.post("/api/vendors", json={"name": "Vendor One", "is_synthetic_demo": True}).json()
    v2 = client.post("/api/vendors", json={"name": "Vendor Two", "is_synthetic_demo": True}).json()

    req = client.post("/api/requests", json={
        "title": "Full Workflow Test",
        "requirements": [
            {"text": "Vendor must provide 24/7 support", "category": "technical"},
            {"text": "Vendor must be ISO 9001 certified", "category": "compliance"},
        ],
    }).json()

    doc1 = b"We offer 24/7 support. ISO 9001 certified, certificate number ABC-123, issued by TUV. Price USD 5000. Delivery 7 days."
    doc2 = b"Business hours support only. No certifications listed. Price USD 4000."

    u1 = client.post("/api/documents/upload", files={"file": ("v1.txt", doc1, "text/plain")},
                      data={"vendor_id": v1["id"], "request_id": req["id"]})
    u2 = client.post("/api/documents/upload", files={"file": ("v2.txt", doc2, "text/plain")},
                      data={"vendor_id": v2["id"], "request_id": req["id"]})
    assert u1.status_code == 200
    assert u2.status_code == 200

    ev = client.post(f"/api/requests/{req['id']}/evaluate")
    assert ev.status_code == 200
    data = ev.json()
    assert len(data["comparison"]["ranking"]) == 2
    # Vendor One has stronger compliance + support evidence, should rank higher
    assert data["comparison"]["ranking"][0]["vendor_id"] == v1["id"]

    # Agent executions were logged for both vendors + comparison + decision
    executions = client.get(f"/api/requests/{req['id']}/agent-executions").json()
    agent_names = {e["agent_name"] for e in executions}
    assert "DocumentExtractionAgent" in agent_names
    assert "RequirementMatchingAgent" in agent_names
    assert "ComplianceAnalysisAgent" in agent_names
    assert "VendorRiskAnalysisAgent" in agent_names
    assert "VendorComparisonAgent" in agent_names
    assert "DecisionIntelligenceAgent" in agent_names

    # Human review workflow
    pending = client.get("/api/review/pending").json()
    assert any(p["request_id"] == req["id"] for p in pending)
    approval_id = next(p["approval_id"] for p in pending if p["request_id"] == req["id"])

    decide = client.post(f"/api/review/{approval_id}/decide",
                          json={"status": "APPROVED", "reviewer_name": "Tester"})
    assert decide.status_code == 200

    # Recommendation reflects approval
    rec = client.get(f"/api/requests/{req['id']}/recommendation").json()
    assert rec["approval"]["status"] == "APPROVED"

    # Reports generate successfully
    rjson = client.get(f"/api/reports/{req['id']}/json")
    assert rjson.status_code == 200
    rpdf = client.get(f"/api/reports/{req['id']}/pdf")
    assert rpdf.status_code == 200
    assert rpdf.headers["content-type"] == "application/pdf"

    # Audit log recorded key actions
    audit = client.get(f"/api/review/audit-log/{req['id']}").json()
    actions = {a["action"] for a in audit}
    assert "evaluation_completed" in actions


def test_invalid_approval_status_rejected(client):
    v1 = client.post("/api/vendors", json={"name": "V", "is_synthetic_demo": True}).json()
    req = client.post("/api/requests", json={"title": "R", "requirements": [{"text": "x", "category": "technical"}]}).json()
    client.post("/api/documents/upload", files={"file": ("a.txt", b"some text here", "text/plain")},
                data={"vendor_id": v1["id"], "request_id": req["id"]})
    client.post(f"/api/requests/{req['id']}/evaluate")
    pending = client.get("/api/review/pending").json()
    approval_id = next(p["approval_id"] for p in pending if p["request_id"] == req["id"])
    r = client.post(f"/api/review/{approval_id}/decide", json={"status": "NOT_A_REAL_STATUS"})
    assert r.status_code in (400, 422, 500)


def test_dashboard_summary_reflects_data(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_vendors_evaluated" in data
    assert "llm_status" in data
