"""
Loads the synthetic 3-vendor demo scenario through the real API (in-process,
no server needed) so `python seed_demo_data.py` gives you a fully populated,
immediately explorable ProcureMind instance — same code path a real client
would hit, not a shortcut that writes directly to the DB.

Run:  python seed_demo_data.py
"""
from __future__ import annotations
import json
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import app

DEMO_DIR = Path(__file__).parent / "demo_data"


def main():
    client = TestClient(app)

    print("=" * 70)
    print("ProcureMind — Loading Synthetic Demo Scenario")
    print("=" * 70)

    req_config = json.loads((DEMO_DIR / "requirements" / "sample_procurement_request.json").read_text())
    req = client.post("/api/requests", json=req_config).json()
    print(f"\n[1/4] Created procurement request: {req['title']} (id={req['id']})")

    vendor_files = {
        "Apex Cloud Solutions": "vendor_apex_cloud.txt",
        "BrightPath IT Services": "vendor_brightpath_it.txt",
        "Summit Technologies": "vendor_summit_technologies.txt",
    }

    print("\n[2/4] Creating vendors and uploading synthetic proposal documents...")
    vendor_ids = {}
    for name, filename in vendor_files.items():
        vendor = client.post("/api/vendors", json={
            "name": name, "is_synthetic_demo": True
        }).json()
        vendor_ids[name] = vendor["id"]

        file_bytes = (DEMO_DIR / "vendors" / filename).read_bytes()
        upload = client.post(
            "/api/documents/upload",
            files={"file": (filename, file_bytes, "text/plain")},
            data={"vendor_id": vendor["id"], "request_id": req["id"],
                  "doc_type": "proposal", "is_synthetic_demo": "true"},
        )
        status = "OK" if upload.status_code == 200 else f"FAILED ({upload.status_code})"
        print(f"    - {name}: uploaded {filename} [{status}]")

    print("\n[3/4] Running the full multi-agent evaluation workflow...")
    result = client.post(f"/api/requests/{req['id']}/evaluate")
    if result.status_code != 200:
        print(f"    EVALUATION FAILED: {result.status_code} {result.text}")
        return
    data = result.json()
    print("    Evaluation complete.\n")

    print("    Vendor Ranking:")
    for r in data["comparison"]["ranking"]:
        print(f"      #{r['rank']}  {r['vendor_name']:<28}  {r['weighted_total']}/100")

    print(f"\n    Recommendation: {data['recommendation']['summary']}")
    print(f"\n    Limitations: {data['recommendation']['limitations']}")

    print("\n[4/4] Demo data loaded. Pending human review item created.")
    print(f"\nProcurement request ID for exploring the API: {req['id']}")
    print("Try:  GET /api/requests/{id}/comparison")
    print("      GET /api/requests/{id}/agent-executions")
    print("      GET /api/review/pending")
    print("      GET /api/reports/{id}/pdf")
    print("=" * 70)


if __name__ == "__main__":
    main()
