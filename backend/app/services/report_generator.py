"""
Generates downloadable JSON and PDF reports for a completed evaluation.
Reports include methodology, source references, scoring breakdown, and
explicit limitations — never just a bare ranking.
"""
from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy.orm import Session

from app.models import models

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _gather_report_data(db: Session, request_id: str) -> dict:
    req = db.query(models.ProcurementRequest).filter_by(id=request_id).first()
    if not req:
        raise ValueError("Procurement request not found")
    scores = db.query(models.VendorScore).filter_by(request_id=request_id).all()
    scores_sorted = sorted(scores, key=lambda s: s.weighted_total, reverse=True)
    rec = db.query(models.Recommendation).filter_by(request_id=request_id).order_by(
        models.Recommendation.created_at.desc()
    ).first()

    vendor_rows = []
    for s in scores_sorted:
        vendor = db.query(models.Vendor).filter_by(id=s.vendor_id).first()
        compliance = db.query(models.ComplianceCheck).filter_by(
            vendor_id=s.vendor_id, request_id=request_id
        ).all()
        risks = db.query(models.RiskAssessment).filter_by(
            vendor_id=s.vendor_id, request_id=request_id
        ).all()
        vendor_rows.append({
            "vendor_name": vendor.name if vendor else "Unknown",
            "weighted_total": s.weighted_total,
            "breakdown": s.breakdown_json,
            "compliance_checks": [
                {"requirement": c.requirement_text, "status": c.status, "source": c.evidence_source}
                for c in compliance
            ],
            "risk_assessments": [
                {"category": r.category, "level": r.risk_level.value if hasattr(r.risk_level, "value") else r.risk_level,
                 "score": r.score, "explanation": r.explanation}
                for r in risks
            ],
        })

    return {
        "request_title": req.title,
        "request_description": req.description,
        "generated_at": str(req.created_at),
        "methodology": (
            "Vendors are evaluated by a multi-agent pipeline (extraction, requirement "
            "matching, compliance analysis, risk analysis) orchestrated via LangGraph. "
            "Scores are computed with transparent, configurable weighted formulas "
            "(see scoring_weights and per-vendor breakdown)."
        ),
        "scoring_weights": req.scoring_weights,
        "vendors": vendor_rows,
        "recommendation": {
            "summary": rec.summary if rec else None,
            "ranked_vendor_ids": rec.ranked_vendor_ids if rec else [],
            "evidence_refs": rec.evidence_refs if rec else [],
            "limitations": rec.limitations if rec else None,
        } if rec else None,
    }


def generate_json_report(db: Session, request_id: str) -> Path:
    data = _gather_report_data(db, request_id)
    path = REPORTS_DIR / f"{request_id}.json"
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path


def generate_pdf_report(db: Session, request_id: str) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    data = _gather_report_data(db, request_id)
    path = REPORTS_DIR / f"{request_id}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"ProcureMind Evaluation Report", styles["Title"]))
    story.append(Paragraph(data["request_title"], styles["Heading2"]))
    if data["request_description"]:
        story.append(Paragraph(data["request_description"], styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Methodology", styles["Heading3"]))
    story.append(Paragraph(data["methodology"], styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Vendor Ranking", styles["Heading3"]))
    table_data = [["Rank", "Vendor", "Weighted Score"]]
    for i, v in enumerate(data["vendors"], start=1):
        table_data.append([str(i), v["vendor_name"], str(v["weighted_total"])])
    t = Table(table_data, colWidths=[40 * mm, 80 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    if data["recommendation"]:
        story.append(Paragraph("Recommendation", styles["Heading3"]))
        story.append(Paragraph(data["recommendation"]["summary"] or "", styles["Normal"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Limitations", styles["Heading4"]))
        story.append(Paragraph(data["recommendation"]["limitations"] or "", styles["Normal"]))
        story.append(Spacer(1, 10))

    for v in data["vendors"]:
        story.append(Paragraph(f"Risk Findings — {v['vendor_name']}", styles["Heading4"]))
        for r in v["risk_assessments"]:
            story.append(Paragraph(f"• {r['category'].title()}: {r['level']} ({r['score']}/100) — {r['explanation']}",
                                    styles["Normal"]))
        story.append(Spacer(1, 8))

    doc.build(story)
    return path
