from __future__ import annotations
from pathlib import Path
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models import models
from app.services.file_parser import parse_file

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
TEXT_DIR = DATA_DIR / "extracted_text"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEXT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "csv", "md"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    vendor_id: str | None = Form(None),
    request_id: str | None = Form(None),
    doc_type: str = Form("proposal"),
    is_synthetic_demo: bool = Form(False),
    db: Session = Depends(get_db),
):
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: .{ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(400, f"File exceeds max upload size of {settings.max_upload_size_mb}MB")

    doc = models.Document(
        vendor_id=vendor_id, request_id=request_id, filename=file.filename,
        doc_type=doc_type, is_synthetic_demo=is_synthetic_demo,
    )
    db.add(doc)
    db.flush()

    file_path = UPLOAD_DIR / f"{doc.id}_{file.filename}"
    file_path.write_bytes(contents)
    doc.file_path = str(file_path)

    parsed = parse_file(file.filename, contents)
    text_path = TEXT_DIR / f"{doc.id}.txt"
    text_path.write_text(parsed.full_text, encoding="utf-8")
    doc.raw_text_path = str(text_path)

    from app.agents.extraction_agent import run_extraction
    extraction = run_extraction(parsed.full_text, file.filename)
    extraction["warnings"] = list(set(extraction.get("warnings", []) + parsed.warnings))

    extracted_row = models.ExtractedData(
        document_id=doc.id, structured_json=extraction, extraction_warnings=extraction["warnings"],
    )
    db.add(extracted_row)
    db.add(models.AuditLog(entity_type="document", entity_id=doc.id, action="uploaded",
                            details={"filename": file.filename, "doc_type": doc_type}))
    db.commit()
    db.refresh(doc)

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "pages_extracted": len(parsed.pages),
        "warnings": parsed.warnings,
        "extraction": extraction,
    }


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id, "filename": doc.filename, "doc_type": doc.doc_type,
        "vendor_id": doc.vendor_id, "request_id": doc.request_id,
        "uploaded_at": doc.uploaded_at, "is_synthetic_demo": doc.is_synthetic_demo,
        "extracted": doc.extracted.structured_json if doc.extracted else None,
        "warnings": doc.extracted.extraction_warnings if doc.extracted else [],
    }
