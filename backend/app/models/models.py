"""
SQLAlchemy models — the relational core of ProcureMind.

Tables: vendors, procurement_requests, requirements, documents,
extracted_data, compliance_checks, risk_assessments, vendor_scores,
agent_executions, recommendations, human_approvals, audit_logs.
"""
from __future__ import annotations
import datetime as dt
import enum
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"


class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    contact_email = Column(String)
    is_synthetic_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    documents = relationship("Document", back_populates="vendor")
    scores = relationship("VendorScore", back_populates="vendor")
    compliance_checks = relationship("ComplianceCheck", back_populates="vendor")
    risk_assessments = relationship("RiskAssessment", back_populates="vendor")


class ProcurementRequest(Base):
    __tablename__ = "procurement_requests"
    id = Column(String, primary_key=True, default=uid)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="OPEN")  # OPEN, EVALUATING, DECIDED, CLOSED
    # weights as JSON: {"requirement_match":0.3,"pricing":0.2,...}
    scoring_weights = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)

    requirements = relationship("Requirement", back_populates="request", cascade="all,delete")
    documents = relationship("Document", back_populates="request")
    agent_executions = relationship("AgentExecution", back_populates="request")
    recommendations = relationship("Recommendation", back_populates="request")


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(String, primary_key=True, default=uid)
    request_id = Column(String, ForeignKey("procurement_requests.id"))
    text = Column(Text, nullable=False)
    category = Column(String, default="general")  # technical, compliance, pricing, delivery
    is_mandatory = Column(Boolean, default=True)
    weight = Column(Float, default=1.0)

    request = relationship("ProcurementRequest", back_populates="requirements")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=uid)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    request_id = Column(String, ForeignKey("procurement_requests.id"), nullable=True)
    filename = Column(String, nullable=False)
    doc_type = Column(String)  # proposal, compliance, policy, spec
    file_path = Column(String)
    raw_text_path = Column(String)
    uploaded_at = Column(DateTime, default=now)
    is_synthetic_demo = Column(Boolean, default=False)

    vendor = relationship("Vendor", back_populates="documents")
    request = relationship("ProcurementRequest", back_populates="documents")
    extracted = relationship("ExtractedData", back_populates="document", uselist=False)


class ExtractedData(Base):
    __tablename__ = "extracted_data"
    id = Column(String, primary_key=True, default=uid)
    document_id = Column(String, ForeignKey("documents.id"))
    structured_json = Column(JSON)  # vendor details, pricing, timelines, certs, capabilities
    extraction_warnings = Column(JSON, default=list)
    extracted_at = Column(DateTime, default=now)

    document = relationship("Document", back_populates="extracted")


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"
    id = Column(String, primary_key=True, default=uid)
    vendor_id = Column(String, ForeignKey("vendors.id"))
    request_id = Column(String, ForeignKey("procurement_requests.id"))
    requirement_text = Column(Text)
    status = Column(String)  # MET, PARTIAL, MISSING, UNVERIFIED
    evidence_snippet = Column(Text)
    evidence_source = Column(String)
    confidence = Column(Float, default=0.0)
    explanation = Column(Text)
    created_at = Column(DateTime, default=now)

    vendor = relationship("Vendor", back_populates="compliance_checks")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id = Column(String, primary_key=True, default=uid)
    vendor_id = Column(String, ForeignKey("vendors.id"))
    request_id = Column(String, ForeignKey("procurement_requests.id"))
    category = Column(String)  # financial, delivery, compliance, technical, contractual, documentation
    risk_level = Column(Enum(RiskLevel))
    score = Column(Float)  # 0-100, higher = riskier
    evidence = Column(JSON, default=list)
    explanation = Column(Text)
    created_at = Column(DateTime, default=now)

    vendor = relationship("Vendor", back_populates="risk_assessments")


class VendorScore(Base):
    __tablename__ = "vendor_scores"
    id = Column(String, primary_key=True, default=uid)
    vendor_id = Column(String, ForeignKey("vendors.id"))
    request_id = Column(String, ForeignKey("procurement_requests.id"))
    requirement_match_score = Column(Float, default=0.0)
    pricing_score = Column(Float, default=0.0)
    delivery_score = Column(Float, default=0.0)
    compliance_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)         # inverted risk (lower raw risk -> higher score)
    technical_score = Column(Float, default=0.0)
    weighted_total = Column(Float, default=0.0)
    breakdown_json = Column(JSON, default=dict)      # full transparent formula trace
    computed_at = Column(DateTime, default=now)

    vendor = relationship("Vendor", back_populates="scores")


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id = Column(String, primary_key=True, default=uid)
    request_id = Column(String, ForeignKey("procurement_requests.id"))
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    agent_name = Column(String)
    status = Column(String, default="PENDING")  # PENDING, RUNNING, SUCCESS, FAILED
    input_summary = Column(JSON, default=dict)
    output_json = Column(JSON, default=dict)
    llm_enhanced = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=now)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    request = relationship("ProcurementRequest", back_populates="agent_executions")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(String, primary_key=True, default=uid)
    request_id = Column(String, ForeignKey("procurement_requests.id"))
    ranked_vendor_ids = Column(JSON, default=list)  # ordered list
    summary = Column(Text)
    evidence_refs = Column(JSON, default=list)
    limitations = Column(Text)
    llm_enhanced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    request = relationship("ProcurementRequest", back_populates="recommendations")
    approval = relationship("HumanApproval", back_populates="recommendation", uselist=False)


class HumanApproval(Base):
    __tablename__ = "human_approvals"
    id = Column(String, primary_key=True, default=uid)
    recommendation_id = Column(String, ForeignKey("recommendations.id"))
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    reviewer_name = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)

    recommendation = relationship("Recommendation", back_populates="approval")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=uid)
    entity_type = Column(String)
    entity_id = Column(String)
    action = Column(String)
    actor = Column(String, default="system")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)
