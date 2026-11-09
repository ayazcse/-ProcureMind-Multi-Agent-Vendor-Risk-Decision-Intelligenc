"""
Agent 3 — Compliance Analysis Agent.

Checks vendor evidence against compliance-flagged requirements only
(category == "compliance"). Distinguishes:
  MET        - explicit certification/keyword evidence found with good similarity
  PARTIAL    - related evidence found but not a clean certification match
  MISSING    - no evidence at all
  UNVERIFIED - evidence mentions the topic but makes an unsupported claim
               (e.g. "we are fully compliant" with no certificate/date/number)

Never claims legal compliance. Always distinguishes verified vs unverified.
"""
from __future__ import annotations
import re
from typing import Any

from app.rag.vector_store import RequestVectorStore
from app.core.llm_client import generate_text

UNSUPPORTED_CLAIM_RE = re.compile(
    r"\b(fully compliant|100% compliant|guaranteed compliant|always compliant)\b", re.IGNORECASE
)
EVIDENCE_MARKER_RE = re.compile(
    r"\b(certificate|certified|certification number|audit|valid until|issued|accredited)\b",
    re.IGNORECASE,
)


def check_compliance_requirement(
    requirement_text: str,
    vendor_store: RequestVectorStore,
    vendor_document_ids: set[str],
) -> dict[str, Any]:
    hits = [h for h in vendor_store.query(requirement_text, top_k=5)
            if h["source_document_id"] in vendor_document_ids]

    if not hits:
        return {
            "requirement_text": requirement_text,
            "status": "MISSING",
            "confidence": 0.0,
            "evidence_snippet": None,
            "evidence_source": None,
            "explanation": "No vendor-provided evidence addresses this compliance requirement.",
        }

    top = hits[0]
    text = top["text"]
    has_unsupported_claim = bool(UNSUPPORTED_CLAIM_RE.search(text))
    has_evidence_marker = bool(EVIDENCE_MARKER_RE.search(text))

    if has_unsupported_claim and not has_evidence_marker:
        status = "UNVERIFIED"
        confidence = round(top["similarity"] * 0.5, 2)
        explanation = (
            "Vendor text claims compliance but provides no certificate number, "
            "issuing body, or audit evidence to verify the claim."
        )
    elif has_evidence_marker and top["similarity"] >= 0.3:
        status = "MET"
        confidence = round(min(top["similarity"] + 0.2, 1.0), 2)
        explanation = "Evidence includes a verifiable compliance marker (certificate/audit reference)."
    elif top["similarity"] >= 0.15:
        status = "PARTIAL"
        confidence = round(top["similarity"], 2)
        explanation = "Related evidence found but does not clearly confirm full compliance."
    else:
        status = "MISSING"
        confidence = 0.0
        explanation = "Retrieved evidence is too weak to support this requirement."

    llm_text = generate_text(
        prompt=(
            f"Compliance requirement: \"{requirement_text}\"\n"
            f"Vendor evidence snippet: \"{text[:400]}\"\n"
            f"Rule-based status: {status}\n\n"
            "In 1-2 sentences, state plainly whether this evidence verifies compliance, "
            "is unverified, or is missing. Never claim legal certainty. "
            "If the status is UNVERIFIED, explicitly say the claim is unverified."
        ),
        system="You are a compliance analyst who never overstates certainty.",
        max_tokens=180,
    )

    return {
        "requirement_text": requirement_text,
        "status": status,
        "confidence": confidence,
        "evidence_snippet": text[:300],
        "evidence_source": f"{top['source_filename']} (p.{top['page_number']})",
        "explanation": llm_text.strip() if llm_text else explanation,
    }


def run_compliance_analysis(
    requirements: list[dict],
    vendor_store: RequestVectorStore,
    vendor_document_ids: set[str],
) -> dict[str, Any]:
    compliance_reqs = [r for r in requirements if r.get("category") == "compliance"]
    results = [
        check_compliance_requirement(r["text"], vendor_store, vendor_document_ids)
        for r in compliance_reqs
    ]
    met = sum(1 for r in results if r["status"] == "MET")
    missing = sum(1 for r in results if r["status"] == "MISSING")
    unverified = sum(1 for r in results if r["status"] == "UNVERIFIED")
    total = len(results) or 1
    compliance_score = round((met / total) * 100, 1)
    return {
        "results": results,
        "met_count": met,
        "missing_count": missing,
        "unverified_count": unverified,
        "compliance_score": compliance_score,
    }
