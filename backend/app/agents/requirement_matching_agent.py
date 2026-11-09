"""
Agent 2 — Requirement Matching Agent.

For each procurement requirement, matches it against the vendor's extracted
capabilities/text using TF-IDF cosine similarity (via the RAG store) plus
keyword overlap, producing a transparent 0-100 match score and a
FULFILLED / PARTIAL / MISSING classification with an explanation.
"""
from __future__ import annotations
from typing import Any

from app.rag.vector_store import RequestVectorStore
from app.core.llm_client import generate_text

FULFILLED_THRESHOLD = 55.0
PARTIAL_THRESHOLD = 25.0


def _classify(score: float) -> str:
    if score >= FULFILLED_THRESHOLD:
        return "FULFILLED"
    if score >= PARTIAL_THRESHOLD:
        return "PARTIAL"
    return "MISSING"


def match_requirement(
    requirement_text: str,
    vendor_store: RequestVectorStore,
    vendor_document_ids: set[str],
) -> dict[str, Any]:
    """
    Retrieve the top evidence chunks for this requirement text, restricted to
    this vendor's own documents, and score the match.
    """
    all_hits = vendor_store.query(requirement_text, top_k=10)
    vendor_hits = [h for h in all_hits if h["source_document_id"] in vendor_document_ids]
    top_hits = vendor_hits[:3]

    if not top_hits:
        score = 0.0
    else:
        # similarity is 0..1 from TF-IDF cosine; scale to 0..100 with a
        # slight boost for having multiple corroborating chunks
        best = top_hits[0]["similarity"]
        corroboration_bonus = min(len(top_hits) - 1, 2) * 3
        score = round(min(best * 100 + corroboration_bonus, 100), 1)

    status = _classify(score)
    explanation = _build_explanation(requirement_text, status, top_hits)

    return {
        "requirement_text": requirement_text,
        "match_score": score,
        "status": status,
        "evidence": top_hits,
        "explanation": explanation,
    }


def _build_explanation(requirement_text: str, status: str, hits: list[dict]) -> str:
    if status == "MISSING":
        return (
            f"No evidence found in vendor documents addressing: \"{requirement_text}\". "
            "This requirement should be treated as unmet unless manually verified."
        )
    sources = ", ".join(sorted({f"{h['source_filename']} (p.{h['page_number']})" for h in hits}))
    base = (
        f"Requirement matched with {'strong' if status == 'FULFILLED' else 'partial'} evidence "
        f"from: {sources}."
    )
    llm_text = generate_text(
        prompt=(
            f"Requirement: \"{requirement_text}\"\n"
            f"Match status: {status}\n"
            f"Evidence snippets: {[h['text'][:200] for h in hits]}\n\n"
            "In 1-2 sentences, explain plainly why this evidence does or doesn't "
            "satisfy the requirement. Do not invent facts beyond the snippets."
        ),
        system="You are a precise procurement analyst writing audit-ready explanations.",
        max_tokens=200,
    )
    return llm_text.strip() if llm_text else base


def run_requirement_matching(
    requirements: list[dict],
    vendor_store: RequestVectorStore,
    vendor_document_ids: set[str],
) -> dict[str, Any]:
    results = [match_requirement(r["text"], vendor_store, vendor_document_ids) for r in requirements]
    fulfilled = sum(1 for r in results if r["status"] == "FULFILLED")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    missing = sum(1 for r in results if r["status"] == "MISSING")
    total = len(results) or 1
    overall_score = round(sum(r["match_score"] for r in results) / total, 1)
    return {
        "results": results,
        "fulfilled_count": fulfilled,
        "partial_count": partial,
        "missing_count": missing,
        "overall_match_score": overall_score,
    }
