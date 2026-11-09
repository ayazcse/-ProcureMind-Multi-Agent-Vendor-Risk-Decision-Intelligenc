from __future__ import annotations
import datetime as dt
from pydantic import BaseModel, Field


class VendorCreate(BaseModel):
    name: str
    contact_email: str | None = None
    is_synthetic_demo: bool = False


class VendorOut(BaseModel):
    id: str
    name: str
    contact_email: str | None = None
    is_synthetic_demo: bool
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class RequirementIn(BaseModel):
    text: str
    category: str = "general"
    is_mandatory: bool = True
    weight: float = 1.0


class ProcurementRequestCreate(BaseModel):
    title: str
    description: str | None = None
    requirements: list[RequirementIn] = Field(default_factory=list)
    scoring_weights: dict[str, float] | None = None


class ProcurementRequestOut(BaseModel):
    id: str
    title: str
    description: str | None
    status: str
    scoring_weights: dict
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class HumanDecisionIn(BaseModel):
    status: str  # APPROVED, REJECTED, MODIFIED
    reviewer_name: str | None = None
    comments: str | None = None
