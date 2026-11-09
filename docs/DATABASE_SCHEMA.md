# Database Schema

SQLAlchemy models in `backend/app/models/models.py`. Default: SQLite
(`procuremind.db`), fully portable to PostgreSQL via `DATABASE_URL`.

## Tables

### `vendors`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| name | string | |
| contact_email | string | nullable |
| is_synthetic_demo | boolean | flags demo data |
| created_at | datetime | |

### `procurement_requests`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| title | string | |
| description | text | nullable |
| status | string | OPEN → EVALUATING → DECIDED → CLOSED |
| scoring_weights | JSON | configurable weights, see SCORING_METHODOLOGY.md |
| created_at | datetime | |

### `requirements`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| request_id | FK → procurement_requests | |
| text | text | |
| category | string | technical / compliance / pricing / delivery / general |
| is_mandatory | boolean | |
| weight | float | per-requirement weight (informational; scoring uses category-level weights) |

### `documents`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| vendor_id | FK → vendors | nullable |
| request_id | FK → procurement_requests | nullable |
| filename | string | |
| doc_type | string | proposal / compliance / policy / spec |
| file_path | string | original file on disk |
| raw_text_path | string | extracted plain text on disk |
| uploaded_at | datetime | |
| is_synthetic_demo | boolean | |

### `extracted_data`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| document_id | FK → documents | |
| structured_json | JSON | Extraction Agent output |
| extraction_warnings | JSON (list) | |
| extracted_at | datetime | |

### `compliance_checks`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| vendor_id | FK → vendors | |
| request_id | FK → procurement_requests | |
| requirement_text | text | |
| status | string | MET / PARTIAL / MISSING / UNVERIFIED |
| evidence_snippet | text | |
| evidence_source | string | filename + page |
| confidence | float | 0–1 |
| explanation | text | |
| created_at | datetime | |

### `risk_assessments`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| vendor_id | FK → vendors | |
| request_id | FK → procurement_requests | |
| category | string | financial / delivery / compliance / technical / contractual / documentation |
| risk_level | enum | LOW / MEDIUM / HIGH / CRITICAL |
| score | float | 0–100, higher = riskier |
| evidence | JSON (list) | |
| explanation | text | |
| created_at | datetime | |

### `vendor_scores`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| vendor_id | FK → vendors | |
| request_id | FK → procurement_requests | |
| requirement_match_score | float | |
| pricing_score | float | |
| delivery_score | float | |
| compliance_score | float | |
| risk_score | float | inverted risk (100 − raw) |
| technical_score | float | |
| weighted_total | float | final ranking score |
| breakdown_json | JSON | full formula trace, weights used, notes |
| computed_at | datetime | |

### `agent_executions`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| request_id | FK → procurement_requests | |
| vendor_id | FK → vendors | nullable (null for request-level agents) |
| agent_name | string | e.g. "DocumentExtractionAgent" |
| status | string | PENDING / RUNNING / SUCCESS / FAILED |
| input_summary | JSON | |
| output_json | JSON | full agent output — drives the AI Evaluation Workspace |
| llm_enhanced | boolean | whether an LLM call actually fired for this execution |
| error_message | text | nullable |
| started_at / finished_at | datetime | |
| duration_ms | integer | |

### `recommendations`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| request_id | FK → procurement_requests | |
| ranked_vendor_ids | JSON (list) | |
| summary | text | |
| evidence_refs | JSON (list) | |
| limitations | text | explicit data-gap disclosure |
| llm_enhanced | boolean | |
| created_at | datetime | |

### `human_approvals`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| recommendation_id | FK → recommendations | |
| status | enum | PENDING / APPROVED / REJECTED / MODIFIED |
| reviewer_name | string | nullable |
| comments | text | nullable |
| decided_at | datetime | nullable |
| created_at | datetime | |

### `audit_logs`
| Column | Type | Notes |
|---|---|---|
| id | string (UUID) | PK |
| entity_type | string | e.g. "procurement_request", "human_approval" |
| entity_id | string | |
| action | string | e.g. "created", "evaluation_completed", "decision_approved" |
| actor | string | default "system" |
| details | JSON | |
| created_at | datetime | |

## Relationships summary

```
ProcurementRequest 1──* Requirement
ProcurementRequest 1──* Document
ProcurementRequest 1──* AgentExecution
ProcurementRequest 1──* Recommendation
Vendor 1──* Document
Vendor 1──* VendorScore
Vendor 1──* ComplianceCheck
Vendor 1──* RiskAssessment
Document 1──1 ExtractedData
Recommendation 1──1 HumanApproval
```
