from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models import models
from app.core.llm_client import llm_status

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_vendors = db.query(func.count(models.Vendor.id)).scalar()
    active_requests = db.query(func.count(models.ProcurementRequest.id)).filter(
        models.ProcurementRequest.status.in_(["OPEN", "EVALUATING"])
    ).scalar()
    pending_reviews = db.query(func.count(models.HumanApproval.id)).filter(
        models.HumanApproval.status == models.ApprovalStatus.PENDING
    ).scalar()

    risk_counts = dict(
        db.query(models.RiskAssessment.risk_level, func.count(models.RiskAssessment.id))
        .group_by(models.RiskAssessment.risk_level).all()
    )
    risk_distribution = {level.value if hasattr(level, "value") else level: count
                          for level, count in risk_counts.items()}

    recent_scores = (
        db.query(models.VendorScore).order_by(models.VendorScore.computed_at.desc()).limit(8).all()
    )
    recent_evaluations = []
    for s in recent_scores:
        vendor = db.query(models.Vendor).filter_by(id=s.vendor_id).first()
        req = db.query(models.ProcurementRequest).filter_by(id=s.request_id).first()
        recent_evaluations.append({
            "vendor_name": vendor.name if vendor else "Unknown",
            "request_title": req.title if req else "Unknown",
            "weighted_total": s.weighted_total,
            "computed_at": s.computed_at,
        })

    vendor_perf = (
        db.query(models.Vendor.name, func.avg(models.VendorScore.weighted_total), func.count(models.VendorScore.id))
        .join(models.VendorScore, models.VendorScore.vendor_id == models.Vendor.id)
        .group_by(models.Vendor.id).all()
    )
    vendor_performance = [
        {"vendor_name": name, "avg_score": round(avg, 1) if avg else 0.0, "evaluations": cnt}
        for name, avg, cnt in vendor_perf
    ]

    return {
        "total_vendors_evaluated": total_vendors,
        "active_procurement_requests": active_requests,
        "pending_human_reviews": pending_reviews,
        "risk_distribution": risk_distribution,
        "recent_evaluations": recent_evaluations,
        "vendor_performance_summary": vendor_performance,
        "llm_status": llm_status(),
    }
