"""
LangGraph multi-agent orchestration.

This is the real workflow graph coordinating Agents 1-6 for a SINGLE
vendor's evaluation within a procurement request (Agent 7 / human review
happens afterward, outside the graph, since it's a human-in-the-loop gate
rather than an autonomous step).

State flows: extract -> match -> comply -> risk -> score, each node reading
only what it needs from VendorEvalState and writing its own namespaced
output. Errors in any node are caught and recorded in `errors` without
crashing the whole run — downstream nodes degrade gracefully (e.g. risk
assessment still runs even if compliance found nothing).
"""
from __future__ import annotations
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from app.agents import extraction_agent, requirement_matching_agent, compliance_agent, risk_agent
from app.services import scoring_engine
from app.rag.vector_store import RequestVectorStore


class VendorEvalState(TypedDict, total=False):
    vendor_id: str
    vendor_name: str
    document_text: str
    document_filename: str
    requirements: list[dict]
    vendor_store: Any  # RequestVectorStore (excluded from serialization)
    vendor_document_ids: set
    all_vendor_prices: list
    scoring_weights: dict

    extraction_result: dict
    matching_result: dict
    compliance_result: dict
    risk_result: dict
    score_result: dict
    errors: list[str]


def node_extract(state: VendorEvalState) -> VendorEvalState:
    try:
        result = extraction_agent.run_extraction(
            state.get("document_text", ""), state.get("document_filename", "")
        )
    except Exception as exc:  # noqa: BLE001
        result = {"warnings": [f"Extraction agent failed: {exc}"], "llm_enhanced": False,
                  "emails": [], "prices_found": [], "delivery_timelines": [], "certifications": []}
        state.setdefault("errors", []).append(f"extraction: {exc}")
    state["extraction_result"] = result
    return state


def node_match(state: VendorEvalState) -> VendorEvalState:
    try:
        result = requirement_matching_agent.run_requirement_matching(
            state.get("requirements", []),
            state["vendor_store"],
            state.get("vendor_document_ids", set()),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"results": [], "overall_match_score": 0.0, "fulfilled_count": 0,
                  "partial_count": 0, "missing_count": 0}
        state.setdefault("errors", []).append(f"matching: {exc}")
    state["matching_result"] = result
    return state


def node_compliance(state: VendorEvalState) -> VendorEvalState:
    try:
        result = compliance_agent.run_compliance_analysis(
            state.get("requirements", []),
            state["vendor_store"],
            state.get("vendor_document_ids", set()),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"results": [], "compliance_score": 0.0, "met_count": 0,
                  "missing_count": 0, "unverified_count": 0}
        state.setdefault("errors", []).append(f"compliance: {exc}")
    state["compliance_result"] = result
    return state


def node_risk(state: VendorEvalState) -> VendorEvalState:
    try:
        result = risk_agent.assess_risk(
            state.get("extraction_result", {}),
            state.get("matching_result", {}),
            state.get("compliance_result", {}),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"categories": [], "overall_risk_score": 100.0, "overall_risk_level": "CRITICAL"}
        state.setdefault("errors", []).append(f"risk: {exc}")
    state["risk_result"] = result
    return state


def node_score(state: VendorEvalState) -> VendorEvalState:
    try:
        result = scoring_engine.compute_vendor_score(
            state.get("extraction_result", {}),
            state.get("matching_result", {}),
            state.get("compliance_result", {}),
            state.get("risk_result", {}),
            state.get("all_vendor_prices", []),
            state.get("scoring_weights"),
        )
    except Exception as exc:  # noqa: BLE001
        result = {"weighted_total": 0.0, "breakdown_json": {"error": str(exc)}}
        state.setdefault("errors", []).append(f"scoring: {exc}")
    state["score_result"] = result
    return state


def build_vendor_eval_graph():
    graph = StateGraph(VendorEvalState)
    graph.add_node("extract", node_extract)
    graph.add_node("match", node_match)
    graph.add_node("comply", node_compliance)
    graph.add_node("assess_risk", node_risk)
    graph.add_node("score", node_score)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "match")
    graph.add_edge("match", "comply")
    graph.add_edge("comply", "assess_risk")
    graph.add_edge("assess_risk", "score")
    graph.add_edge("score", END)

    return graph.compile()


_COMPILED_GRAPH = None


def get_vendor_eval_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_vendor_eval_graph()
    return _COMPILED_GRAPH


def run_vendor_evaluation(
    vendor_id: str,
    vendor_name: str,
    document_text: str,
    document_filename: str,
    requirements: list[dict],
    vendor_store: RequestVectorStore,
    vendor_document_ids: set,
    all_vendor_prices: list,
    scoring_weights: dict | None = None,
) -> VendorEvalState:
    graph = get_vendor_eval_graph()
    initial_state: VendorEvalState = {
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "document_text": document_text,
        "document_filename": document_filename,
        "requirements": requirements,
        "vendor_store": vendor_store,
        "vendor_document_ids": vendor_document_ids,
        "all_vendor_prices": all_vendor_prices,
        "scoring_weights": scoring_weights or {},
        "errors": [],
    }
    final_state = graph.invoke(initial_state)
    return final_state
