"""
Agent 1 — Document Extraction Agent.

Deterministic core: regex/heuristic extraction of pricing, dates, emails,
certifications, and capability keywords from raw document text — this
always runs and always produces a result, with zero API cost.

LLM augmentation (optional): if an LLM is configured, we additionally ask
it to structure ambiguous fields (e.g. distinguishing "delivery timeline"
prose from contract boilerplate) and merge its output IN ADDITION TO the
regex pass, never replacing it. Extraction warnings are preserved either way.
"""
from __future__ import annotations
import re
from typing import Any

from app.core.llm_client import generate_json

PRICE_RE = re.compile(r"(?:USD|INR|\$|₹|Rs\.?)\s?[\d,]+(?:\.\d{1,2})?", re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
DATE_RE = re.compile(
    r"\b(\d{1,2}[-/ ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/ ]\d{2,4}|"
    r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b",
    re.IGNORECASE,
)
TIMELINE_RE = re.compile(
    r"(\d+)\s*(business\s*day|calendar\s*day|day|week|month)s?\b", re.IGNORECASE
)
CERT_KEYWORDS = [
    "ISO 9001", "ISO 27001", "ISO 14001", "SOC 2", "SOC2", "GDPR", "HIPAA",
    "PCI DSS", "PCI-DSS", "CMMI", "MSME", "GST registered", "GSTIN",
]
CAPABILITY_KEYWORDS = [
    "24/7 support", "on-site support", "cloud hosting", "on-premise",
    "API integration", "SLA", "dedicated account manager", "multi-currency",
    "scalability", "disaster recovery", "data encryption", "training included",
    "warranty", "maintenance", "customization",
]


def _extract_keywords(text: str, keywords: list[str]) -> list[str]:
    found = []
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            found.append(kw)
    return found


def run_extraction(document_text: str, filename: str) -> dict[str, Any]:
    warnings: list[str] = []
    if not document_text or not document_text.strip():
        warnings.append("Document contained no extractable text.")
        return {
            "vendor_name_guess": None,
            "emails": [],
            "prices_found": [],
            "dates_found": [],
            "delivery_timelines": [],
            "certifications": [],
            "capabilities": [],
            "warnings": warnings,
            "llm_enhanced": False,
        }

    emails = sorted(set(EMAIL_RE.findall(document_text)))
    prices = sorted(set(PRICE_RE.findall(document_text)))
    dates = sorted(set(DATE_RE.findall(document_text)))
    timelines = [f"{n} {unit}{'s' if int(n) != 1 else ''}" for n, unit in TIMELINE_RE.findall(document_text)]
    certifications = _extract_keywords(document_text, CERT_KEYWORDS)
    capabilities = _extract_keywords(document_text, CAPABILITY_KEYWORDS)

    # crude vendor-name guess: first non-empty line that isn't a price/date/email
    vendor_name_guess = None
    for line in document_text.splitlines():
        line = line.strip()
        if len(line) > 2 and len(line) < 80 and not PRICE_RE.search(line) and not EMAIL_RE.search(line):
            vendor_name_guess = line
            break

    if not emails:
        warnings.append("No contact email found in document.")
    if not prices:
        warnings.append("No pricing information detected — may require manual review.")
    if not certifications:
        warnings.append("No recognized certification keywords found.")

    result: dict[str, Any] = {
        "vendor_name_guess": vendor_name_guess,
        "emails": emails,
        "prices_found": prices,
        "dates_found": dates,
        "delivery_timelines": timelines,
        "certifications": certifications,
        "capabilities": capabilities,
        "warnings": warnings,
        "llm_enhanced": False,
    }

    # Optional LLM augmentation — additive only, never overwrites regex facts.
    llm_out = generate_json(
        prompt=(
            "Extract structured procurement data from this vendor document. "
            "Return JSON with keys: vendor_name (string or null), "
            "summary (one sentence), additional_capabilities (list of strings "
            "not already obvious from keyword matching), risk_flags (list of "
            "short strings describing anything concerning in the text).\n\n"
            f"DOCUMENT:\n{document_text[:6000]}"
        ),
        system="You are a precise procurement document analyst. Never invent facts not present in the text.",
    )
    if llm_out:
        result["llm_enhanced"] = True
        result["llm_summary"] = llm_out.get("summary")
        result["llm_additional_capabilities"] = llm_out.get("additional_capabilities", [])
        result["llm_risk_flags"] = llm_out.get("risk_flags", [])
        if llm_out.get("vendor_name") and not vendor_name_guess:
            result["vendor_name_guess"] = llm_out["vendor_name"]

    return result
