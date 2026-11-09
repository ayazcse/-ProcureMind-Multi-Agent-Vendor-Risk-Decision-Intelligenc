# API Documentation

Interactive Swagger docs are auto-generated at `http://localhost:8000/docs`
once the backend is running (FastAPI's built-in OpenAPI UI) — that's the
authoritative, always-up-to-date reference. This file is a human-readable
summary.

Base URL: `http://localhost:8000/api`

## Vendors

| Method | Path | Description |
|---|---|---|
| POST | `/vendors` | Create a vendor `{name, contact_email?, is_synthetic_demo?}` |
| GET | `/vendors` | List all vendors |
| GET | `/vendors/{id}` | Get one vendor |
| GET | `/vendors/{id}/documents` | List a vendor's uploaded documents + extracted data |

## Documents

| Method | Path | Description |
|---|---|---|
| POST | `/documents/upload` | Multipart upload: `file`, `vendor_id?`, `request_id?`, `doc_type?`, `is_synthetic_demo?`. Parses the file, runs the Extraction Agent immediately, returns extracted JSON + warnings. |
| GET | `/documents/{id}` | Get one document + its extraction |

Allowed file types: `.pdf .docx .txt .csv .md`. Max size configurable via
`MAX_UPLOAD_SIZE_MB` in `.env`.

## Procurement Requests

| Method | Path | Description |
|---|---|---|
| POST | `/requests` | Create a request with requirements `{title, description?, requirements: [{text, category, is_mandatory, weight}], scoring_weights?}` |
| GET | `/requests` | List all requests |
| GET | `/requests/{id}` | Full request detail: requirements + documents |
| POST | `/requests/{id}/evaluate` | **Runs the full multi-agent evaluation.** Requires ≥1 uploaded document. Returns comparison + recommendation. |
| GET | `/requests/{id}/agent-executions` | Full audit log of every agent run for this request (drives the AI Evaluation Workspace) |
| GET | `/requests/{id}/comparison` | Ranked vendor scores with full breakdown |
| GET | `/requests/{id}/recommendation` | Latest recommendation + its approval status |

## Human Review

| Method | Path | Description |
|---|---|---|
| GET | `/review/pending` | All recommendations awaiting human decision |
| POST | `/review/{approval_id}/decide` | `{status: "APPROVED"\|"REJECTED"\|"MODIFIED", reviewer_name?, comments?}` |
| GET | `/review/audit-log/{request_id}` | Full audit trail for a procurement request |

## Dashboard

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | Live counts: vendors evaluated, active requests, pending reviews, risk distribution, recent evaluations, vendor performance, LLM mode |

## Reports

| Method | Path | Description |
|---|---|---|
| GET | `/reports/{request_id}/json` | Downloadable JSON report: methodology, scoring breakdown, recommendation, limitations |
| GET | `/reports/{request_id}/pdf` | Downloadable PDF report (same content, formatted) |

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{status, llm: {provider, enabled, mode}}` |

## Example: full workflow via curl

```bash
# 1. Create a vendor
curl -X POST http://localhost:8000/api/vendors \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Logistics", "is_synthetic_demo": true}'

# 2. Create a procurement request
curl -X POST http://localhost:8000/api/requests \
  -H "Content-Type: application/json" \
  -d '{"title": "Office IT Equipment", "requirements": [
        {"text": "Vendor must provide 24/7 support", "category": "technical"}
      ]}'

# 3. Upload a vendor proposal (use the IDs from steps 1-2)
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@proposal.pdf" -F "vendor_id=<vendor_id>" -F "request_id=<request_id>"

# 4. Run the evaluation
curl -X POST http://localhost:8000/api/requests/<request_id>/evaluate

# 5. View the comparison
curl http://localhost:8000/api/requests/<request_id>/comparison
```
