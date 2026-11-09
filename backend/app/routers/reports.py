from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.report_generator import generate_json_report, generate_pdf_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{request_id}/json")
def get_json_report(request_id: str, db: Session = Depends(get_db)):
    try:
        path = generate_json_report(db, request_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return FileResponse(path, media_type="application/json", filename=f"procuremind_report_{request_id}.json")


@router.get("/{request_id}/pdf")
def get_pdf_report(request_id: str, db: Session = Depends(get_db)):
    try:
        path = generate_pdf_report(db, request_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return FileResponse(path, media_type="application/pdf", filename=f"procuremind_report_{request_id}.pdf")
