from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import models
from app.schemas.schemas import ProcurementRequestCreate, ProcurementRequestOut
from app.services.scoring_engine import DEFAULT_WEIGHTS
from app.services.evaluation_service import run_full_evaluation

router = APIRouter(prefix="/api/requests", tags=["procurement_requests"])


@router.post("", response_model=ProcurementRequestOut)
def create_request(payload: ProcurementRequestCreate, db: Session = Depends(get_db)):
    req = models.ProcurementRequest(
        title=payload.title,
        description=payload.description,
        scoring_weights=payload.scoring_weights or DEFAULT_WEIGHTS,
    )
    db.add(req)
    db.flush()
    for r in payload.requirements:
        db.add(models.Requirement(request_id=req.id, text=r.text, category=r.category,
                                   is_mandatory=r.is_mandatory, weight=r.weight))
    db.add(models.AuditLog(entity_type="procurement_request", entity_id=req.id, action="created",
                            details={"title": req.title}))
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=list[ProcurementRequestOut])
def list_requests(db: Session = Depends(get_db)):
    return db.query(models.ProcurementRequest).order_by(models.ProcurementRequest.created_at.desc()).all()


@router.get("/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(models.ProcurementRequest).filter_by(id=request_id).first()
    if not req:
        raise HTTPException(404, "Procurement request not found")
    return {
        "id": req.id, "title": req.title, "description": req.description,
        "status": req.status, "scoring_weights": req.scoring_weights, "created_at": req.created_at,
        "requirements": [{"id": r.id, "text": r.text, "category": r.category,
                           "is_mandatory": r.is_mandatory, "weight": r.weight} for r in req.requirements],
        "documents": [{"id": d.id, "filename": d.filename, "vendor_id": d.vendor_id,
                        "doc_type": d.doc_type} for d in req.documents],
    }


@router.post("/{request_id}/evaluate")
def evaluate_request(request_id: str, db: Session = Depends(get_db)):
    req = db.query(models.ProcurementRequest).filter_by(id=request_id).first()
    if not req:
        raise HTTPException(404, "Procurement request not found")
    doc_count = db.query(models.Document).filter_by(request_id=request_id).count()
    if doc_count == 0:
        raise HTTPException(400, "No documents uploaded for this procurement request yet.")
    try:
        result = run_full_evaluation(db, request_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Evaluation failed: {exc}")
    return result


@router.get("/{request_id}/agent-executions")
def get_agent_executions(request_id: str, db: Session = Depends(get_db)):
    rows = db.query(models.AgentExecution).filter_by(request_id=request_id).order_by(
        models.AgentExecution.started_at
    ).all()
    return [
        {"id": r.id, "agent_name": r.agent_name, "vendor_id": r.vendor_id, "status": r.status,
         "llm_enhanced": r.llm_enhanced, "duration_ms": r.duration_ms,
         "error_message": r.error_message, "output_json": r.output_json,
         "started_at": r.started_at, "finished_at": r.finished_at}
        for r in rows
    ]


@router.get("/{request_id}/comparison")
def get_comparison(request_id: str, db: Session = Depends(get_db)):
    scores = db.query(models.VendorScore).filter_by(request_id=request_id).all()
    rows = []
    for s in scores:
        vendor = db.query(models.Vendor).filter_by(id=s.vendor_id).first()
        rows.append({
            "vendor_id": s.vendor_id, "vendor_name": vendor.name if vendor else "Unknown",
            "weighted_total": s.weighted_total, "requirement_match_score": s.requirement_match_score,
            "pricing_score": s.pricing_score, "delivery_score": s.delivery_score,
            "compliance_score": s.compliance_score, "risk_score": s.risk_score,
            "technical_score": s.technical_score, "breakdown_json": s.breakdown_json,
        })
    rows.sort(key=lambda r: r["weighted_total"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


@router.get("/{request_id}/recommendation")
def get_recommendation(request_id: str, db: Session = Depends(get_db)):
    rec = db.query(models.Recommendation).filter_by(request_id=request_id).order_by(
        models.Recommendation.created_at.desc()
    ).first()
    if not rec:
        raise HTTPException(404, "No recommendation generated yet. Run evaluation first.")
    approval = rec.approval
    return {
        "id": rec.id, "ranked_vendor_ids": rec.ranked_vendor_ids, "summary": rec.summary,
        "evidence_refs": rec.evidence_refs, "limitations": rec.limitations,
        "llm_enhanced": rec.llm_enhanced, "created_at": rec.created_at,
        "approval": {
            "status": approval.status.value if approval else "PENDING",
            "reviewer_name": approval.reviewer_name if approval else None,
            "comments": approval.comments if approval else None,
            "decided_at": approval.decided_at if approval else None,
        } if approval else None,
    }
