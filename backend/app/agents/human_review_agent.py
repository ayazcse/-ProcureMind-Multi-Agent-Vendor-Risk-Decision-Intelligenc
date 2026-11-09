"""
Agent 7 — Human Review Agent.

Not an LLM agent — a deliberate workflow gate. Presents the Decision
Agent's recommendation for human approval/rejection/modification and
records an immutable audit trail entry for every decision. No procurement
request can be marked DECIDED without a row in human_approvals.
"""
from __future__ import annotations
import datetime as dt
from typing import Any


def build_review_payload(recommendation: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommendation_summary": recommendation["summary"],
        "ranked_vendor_ids": recommendation["ranked_vendor_ids"],
        "evidence_refs": recommendation["evidence_refs"],
        "limitations": recommendation["limitations"],
        "comparison_table": comparison.get("table", []),
        "requires_action": True,
        "possible_actions": ["APPROVED", "REJECTED", "MODIFIED"],
    }


def record_decision(status: str, reviewer_name: str | None, comments: str | None) -> dict[str, Any]:
    if status not in ("APPROVED", "REJECTED", "MODIFIED"):
        raise ValueError(f"Invalid approval status: {status}")
    return {
        "status": status,
        "reviewer_name": reviewer_name or "unspecified",
        "comments": comments,
        "decided_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
