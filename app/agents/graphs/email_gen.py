from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.generate import generate_email_to_recruiter
from app.agents.nodes.retrieve_chunks import retrieve_job_description_chunks, retrieve_resume_chunks
from app.agents.nodes.scorer import score_output

logger = logging.getLogger(__name__)


def node_retrieve_context(state: dict[str, Any]) -> dict[str, Any]:
    job_id = state.get("job_id")
    user_id = state.get("user_id")
    jd_chunks = retrieve_job_description_chunks(job_id, n_results=3)
    resume_chunks = retrieve_resume_chunks(user_id, n_results=3)
    return {
        **state,
        "job_context": "\n".join(chunk.get("document", "") for chunk in jd_chunks),
        "resume_context": "\n".join(chunk.get("document", "") for chunk in resume_chunks),
    }


def node_generate_email(state: dict[str, Any]) -> dict[str, Any]:
    email = generate_email_to_recruiter(
        job_description=state.get("job_context", ""),
        resume_context=state.get("resume_context", ""),
    )
    return {**state, "generated_email": email}


def node_evaluate_email(state: dict[str, Any]) -> dict[str, Any]:
    score_result = score_output(
        output_type="email",
        output_content=state.get("generated_email", ""),
        context={"job_description": state.get("job_context", "")},
        score_threshold=7,
    )
    return {**state, "score_result": score_result}


def route_on_score(state: dict[str, Any]) -> str:
    recommendation = state.get("score_result", {}).get("recommendation", "").lower()
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    if recommendation == "approve":
        return "approve"
    if recommendation == "retry" and retry_count < max_retries:
        return "retry"
    return "done"


def build_email_generation_graph() -> StateGraph:
    builder = StateGraph(dict)
    builder.add_node("retrieve_context", node_retrieve_context)
    builder.add_node("generate", node_generate_email)
    builder.add_node("evaluate", node_evaluate_email)
    builder.add_edge(START, "retrieve_context")
    builder.add_edge("retrieve_context", "generate")
    builder.add_edge("generate", "evaluate")
    builder.add_conditional_edges(
        "evaluate",
        route_on_score,
        {"approve": END, "retry": "generate", "done": END},
    )
    graph = builder.compile()
    logger.info("Email generation graph compiled")
    return graph
