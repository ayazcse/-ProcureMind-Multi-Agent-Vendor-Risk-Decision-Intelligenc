"""
Top-level evaluation orchestration: runs the LangGraph vendor-eval workflow
for every vendor in a procurement request, then runs comparison + decision
agents, persisting every agent's output to agent_executions for full
auditability, plus the final VendorScore, Recommendation rows.
"""
from __future__ import annotations
import datetime as dt
import re
from sqlalchemy.orm import Session

from app.models import models
from app.agents.graph import run_vendor_evaluation
from app.agents import comparison_agent, decision_agent
from app.rag.vector_store import get_store
from app.core.llm_client import llm_status


def _log_execution(db: Session, request_id: str, vendor_id: str | None, agent_name: str,
                    status: str, output: dict, llm_enhanced: bool, started: dt.datetime,
                    error: str | None = None):
    finished = dt.datetime.now(dt.timezone.utc)
    row = models.AgentExecution(
        request_id=request_id,
        vendor_id=vendor_id,
        agent_name=agent_name,
        status=status,
        output_json=output,
        llm_enhanced=llm_enhanced,
        error_message=error,
        started_at=started,
        finished_at=finished,
        duration_ms=int((finished - started).total_seconds() * 1000),
    )
    db.add(row)
    return row


def _extract_price_number(extraction: dict) -> float | None:
    prices = extraction.get("prices_found") or []
    nums = []
    for p in prices:
        digits = re.sub(r"[^\d.]", "", p)
        try:
            nums.append(float(digits))
        except ValueError:
            continue
    return min(nums) if nums else None


def run_full_evaluation(db: Session, request_id: str) -> dict:
    request = db.query(models.ProcurementRequest).filter_by(id=request_id).first()
    if not request:
        raise ValueError("Procurement request not found")

    request.status = "EVALUATING"
    db.commit()

    requirements = [
        {"text": r.text, "category": r.category, "weight": r.weight}
        for r in request.requirements
    ]
    documents = db.query(models.Document).filter_by(request_id=request_id).all()

    # Build/refresh the vector store for this request from all vendor documents
    store = get_store(request_id)
    vendor_docs: dict[str, list[models.Document]] = {}
    for doc in documents:
        if not doc.vendor_id:
            continue
        vendor_docs.setdefault(doc.vendor_id, []).append(doc)
        if doc.raw_text_path:
            try:
                with open(doc.raw_text_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                text = ""
            if text and not any(r.source_document_id == doc.id for r in store.records):
                store.add_document(doc.id, doc.filename, [(1, text)])

    # Pre-pass: extract prices from every vendor to enable relative pricing scores
    all_prices: list[float] = []
    vendor_texts: dict[str, str] = {}
    for vendor_id, docs in vendor_docs.items():
        combined_text = ""
        for doc in docs:
            if doc.raw_text_path:
                try:
                    with open(doc.raw_text_path, "r", encoding="utf-8") as f:
                        combined_text += "\n" + f.read()
                except FileNotFoundError:
                    pass
        vendor_texts[vendor_id] = combined_text
        from app.agents.extraction_agent import run_extraction
        pre_extract = run_extraction(combined_text, docs[0].filename if docs else "")
        price = _extract_price_number(pre_extract)
        if price:
            all_prices.append(price)

    vendor_score_rows = []
    matching_by_vendor = {}
    compliance_by_vendor = {}

    for vendor_id, docs in vendor_docs.items():
        vendor = db.query(models.Vendor).filter_by(id=vendor_id).first()
        if not vendor:
            continue
        doc_ids = {d.id for d in docs}
        filename = docs[0].filename if docs else "unknown"
        started = dt.datetime.now(dt.timezone.utc)
        try:
            result = run_vendor_evaluation(
                vendor_id=vendor_id,
                vendor_name=vendor.name,
                document_text=vendor_texts.get(vendor_id, ""),
                document_filename=filename,
                requirements=requirements,
                vendor_store=store,
                vendor_document_ids=doc_ids,
                all_vendor_prices=all_prices,
                scoring_weights=request.scoring_weights,
            )
            status = "SUCCESS" if not result.get("errors") else "SUCCESS"
            error = "; ".join(result.get("errors", [])) or None
        except Exception as exc:  # noqa: BLE001
            db.add(models.AuditLog(entity_type="procurement_request", entity_id=request_id,
                                    action="evaluation_vendor_failed", details={"vendor_id": vendor_id, "error": str(exc)}))
            continue

        llm_on = llm_status()["enabled"]

        for agent_name, key in [
            ("DocumentExtractionAgent", "extraction_result"),
            ("RequirementMatchingAgent", "matching_result"),
            ("ComplianceAnalysisAgent", "compliance_result"),
            ("VendorRiskAnalysisAgent", "risk_result"),
        ]:
            _log_execution(db, request_id, vendor_id, agent_name, "SUCCESS",
                            result.get(key, {}), llm_on, started, error)

        extraction = result["extraction_result"]
        matching = result["matching_result"]
        compliance = result["compliance_result"]
        risk = result["risk_result"]
        score = result["score_result"]

        matching_by_vendor[vendor_id] = matching
        compliance_by_vendor[vendor_id] = compliance

        # Persist compliance checks & risk assessments as rows for audit querying
        for c in compliance.get("results", []):
            db.add(models.ComplianceCheck(
                vendor_id=vendor_id, request_id=request_id,
                requirement_text=c["requirement_text"], status=c["status"],
                evidence_snippet=c.get("evidence_snippet"), evidence_source=c.get("evidence_source"),
                confidence=c.get("confidence", 0.0), explanation=c.get("explanation"),
            ))
        for r in risk.get("categories", []):
            db.add(models.RiskAssessment(
                vendor_id=vendor_id, request_id=request_id, category=r["category"],
                risk_level=r["risk_level"], score=r["score"], evidence=r["evidence"],
                explanation=r["explanation"],
            ))

        score_row = models.VendorScore(
            vendor_id=vendor_id, request_id=request_id,
            requirement_match_score=score["requirement_match_score"],
            pricing_score=score["pricing_score"],
            delivery_score=score["delivery_score"],
            compliance_score=score["compliance_score"],
            risk_score=score["risk_score"],
            technical_score=score["technical_score"],
            weighted_total=score["weighted_total"],
            breakdown_json=score["breakdown_json"],
        )
        db.add(score_row)

        vendor_score_rows.append({
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "weighted_total": score["weighted_total"],
            "requirement_match_score": score["requirement_match_score"],
            "pricing_score": score["pricing_score"],
            "delivery_score": score["delivery_score"],
            "compliance_score": score["compliance_score"],
            "risk_score": score["risk_score"],
            "technical_score": score["technical_score"],
            "missing_data_flags": score["breakdown_json"].get("missing_data_flags", []),
        })

    db.commit()

    comparison = comparison_agent.compare_vendors(vendor_score_rows)
    _log_execution(db, request_id, None, "VendorComparisonAgent", "SUCCESS",
                    comparison, llm_status()["enabled"], dt.datetime.now(dt.timezone.utc))

    recommendation_data = decision_agent.generate_recommendation(
        comparison, matching_by_vendor, compliance_by_vendor, {}
    )
    _log_execution(db, request_id, None, "DecisionIntelligenceAgent", "SUCCESS",
                    recommendation_data, recommendation_data.get("llm_enhanced", False), dt.datetime.now(dt.timezone.utc))

    rec_row = models.Recommendation(
        request_id=request_id,
        ranked_vendor_ids=recommendation_data["ranked_vendor_ids"],
        summary=recommendation_data["summary"],
        evidence_refs=recommendation_data["evidence_refs"],
        limitations=recommendation_data["limitations"],
        llm_enhanced=recommendation_data.get("llm_enhanced", False),
    )
    db.add(rec_row)
    db.flush()

    approval_row = models.HumanApproval(recommendation_id=rec_row.id, status=models.ApprovalStatus.PENDING)
    db.add(approval_row)

    request.status = "DECIDED"
    db.add(models.AuditLog(entity_type="procurement_request", entity_id=request_id,
                            action="evaluation_completed",
                            details={"vendor_count": len(vendor_score_rows)}))
    db.commit()

    return {
        "comparison": comparison,
        "recommendation": recommendation_data,
        "recommendation_id": rec_row.id,
        "vendor_scores": vendor_score_rows,
    }
