from __future__ import annotations
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import models
from app.schemas.schemas import HumanDecisionIn
from app.agents.human_review_agent import record_decision

router = APIRouter(prefix="/api/review", tags=["human_review"])


@router.get("/pending")
def list_pending(db: Session = Depends(get_db)):
    rows = db.query(models.HumanApproval).filter_by(status=models.ApprovalStatus.PENDING).all()
    out = []
    for r in rows:
        rec = r.recommendation
        req = rec.request if rec else None
        out.append({
            "approval_id": r.id, "recommendation_id": r.recommendation_id,
            "request_id": req.id if req else None, "request_title": req.title if req else None,
            "summary": rec.summary if rec else None, "created_at": r.created_at,
        })
    return out


@router.post("/{approval_id}/decide")
def decide(approval_id: str, payload: HumanDecisionIn, db: Session = Depends(get_db)):
    approval = db.query(models.HumanApproval).filter_by(id=approval_id).first()
    if not approval:
        raise HTTPException(404, "Approval record not found")

    try:
        decision = record_decision(payload.status, payload.reviewer_name, payload.comments)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    approval.status = models.ApprovalStatus(decision["status"])
    approval.reviewer_name = decision["reviewer_name"]
    approval.comments = decision["comments"]
    approval.decided_at = dt.datetime.now(dt.timezone.utc)

    rec = approval.recommendation
    if rec and rec.request:
        rec.request.status = "CLOSED" if decision["status"] == "APPROVED" else "EVALUATING"

    db.add(models.AuditLog(
        entity_type="human_approval", entity_id=approval.id, action=f"decision_{decision['status'].lower()}",
        actor=decision["reviewer_name"], details={"comments": decision["comments"]},
    ))
    db.commit()
    return {"status": "ok", "approval_id": approval.id, "decision": decision}


@router.get("/audit-log/{request_id}")
def get_audit_log(request_id: str, db: Session = Depends(get_db)):
    rows = db.query(models.AuditLog).filter(
        (models.AuditLog.entity_id == request_id)
    ).order_by(models.AuditLog.created_at).all()
    return [
        {"id": r.id, "entity_type": r.entity_type, "action": r.action,
         "actor": r.actor, "details": r.details, "created_at": r.created_at}
        for r in rows
    ]
