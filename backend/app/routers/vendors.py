from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import models
from app.schemas.schemas import VendorCreate, VendorOut

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.post("", response_model=VendorOut)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    vendor = models.Vendor(**payload.model_dump())
    db.add(vendor)
    db.add(models.AuditLog(entity_type="vendor", entity_id=vendor.id, action="created",
                            details={"name": vendor.name}))
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    return db.query(models.Vendor).order_by(models.Vendor.created_at.desc()).all()


@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    vendor = db.query(models.Vendor).filter_by(id=vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    return vendor


@router.get("/{vendor_id}/documents")
def get_vendor_documents(vendor_id: str, db: Session = Depends(get_db)):
    docs = db.query(models.Document).filter_by(vendor_id=vendor_id).all()
    return [
        {"id": d.id, "filename": d.filename, "doc_type": d.doc_type,
         "uploaded_at": d.uploaded_at, "is_synthetic_demo": d.is_synthetic_demo,
         "extracted": (d.extracted.structured_json if d.extracted else None)}
        for d in docs
    ]
