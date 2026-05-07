from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.normalize_jd import normalize_job_description
from app.agents.nodes.search_web import search_jobs_web

logger = logging.getLogger(__name__)


def node_search_web(state: dict[str, Any]) -> dict[str, Any]:
    query = state.get("query", "")
    location = state.get("location")
    results = search_jobs_web(query, location=location, max_results=state.get("limit", 10))
    return {**state, "raw_results": results}


def node_normalize_results(state: dict[str, Any]) -> dict[str, Any]:
    normalized = []
    for result in state.get("raw_results", []):
        description = result.get("description") or result.get("title", "")
        normalized_job = normalize_job_description(description)
        normalized_job.update({"source_url": result.get("link")})
        normalized.append(normalized_job)
    return {**state, "normalized_results": normalized}


def build_job_search_graph() -> StateGraph:
    builder = StateGraph(dict)
    builder.add_node("search_web", node_search_web)
    builder.add_node("normalize", node_normalize_results)
    builder.add_edge(START, "search_web")
    builder.add_edge("search_web", "normalize")
    builder.add_edge("normalize", END)
    graph = builder.compile()
    logger.info("Job search graph compiled")
    return graph
