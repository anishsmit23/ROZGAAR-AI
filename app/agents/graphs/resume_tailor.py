"""
Resume Tailor LangGraph - Multi-node workflow with evaluator-retry loop.
Flow: retrieve job → retrieve resume → generate tailored → evaluate → conditional retry
"""

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END
from app.agents.nodes.retrieve_chunks import retrieve_job_description_chunks, retrieve_resume_chunks
from app.agents.nodes.generate import generate_tailored_resume
from app.agents.nodes.scorer import score_output

logger = logging.getLogger(__name__)


# Graph state schema
class ResumeTailorState:
    """State passed through resume tailor graph nodes."""
    
    def __init__(self):
        self.user_id: str = ""
        self.job_id: str = ""
        self.job_description: str = ""
        self.original_resume: str = ""
        self.retrieved_jd_chunks: list[dict] = []
        self.retrieved_resume_sections: list[dict] = []
        self.tailored_resume: str = ""
        self.score_result: dict[str, Any] = {}
        self.retry_count: int = 0
        self.max_retries: int = 3


def node_retrieve_job_description(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve job description chunks from ChromaDB."""
    try:
        job_id = state.get("job_id")
        chunks = retrieve_job_description_chunks(job_id, n_results=3)
        state["retrieved_jd_chunks"] = chunks
        logger.info(f"Retrieved {len(chunks)} job chunks for job_id={job_id}")
        return state
    except Exception as e:
        logger.error(f"Failed to retrieve job description: {e}")
        state["error"] = str(e)
        return state


def node_retrieve_resume_sections(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve resume chunks from ChromaDB."""
    try:
        user_id = state.get("user_id")
        chunks = retrieve_resume_chunks(user_id, n_results=5)
        state["retrieved_resume_sections"] = chunks
        logger.info(f"Retrieved {len(chunks)} resume chunks for user_id={user_id}")
        return state
    except Exception as e:
        logger.error(f"Failed to retrieve resume: {e}")
        state["error"] = str(e)
        return state


def node_generate_tailored_resume(state: dict[str, Any]) -> dict[str, Any]:
    """Generate a resume tailored to the job."""
    try:
        job_description = state.get("job_description", "")
        original_resume = state.get("original_resume", "")
        highlighted_sections = "\\n".join([c.get("document", "") for c in state.get("retrieved_resume_sections", [])[:3]])
        
        tailored = generate_tailored_resume(
            job_description=job_description,
            original_resume=original_resume,
            highlighted_sections=highlighted_sections,
        )
        
        state["tailored_resume"] = tailored
        logger.info(f"Generated tailored resume (length={len(tailored)} chars)")
        return state
    except Exception as e:
        logger.error(f"Failed to generate tailored resume: {e}")
        state["error"] = str(e)
        return state


def node_evaluate_resume(state: dict[str, Any]) -> dict[str, Any]:
    """Score the tailored resume against job description."""
    try:
        score_result = score_output(
            output_type="resume",
            output_content=state.get("tailored_resume", ""),
            context={"job_description": state.get("job_description", "")},
            score_threshold=7,
        )
        
        state["score_result"] = score_result
        state["overall_score"] = score_result.get("overall_score", 0)
        logger.info(f"Resume scored: {score_result.get('overall_score'):.1f}/10, recommendation: {score_result.get('recommendation')}")
        return state
    except Exception as e:
        logger.error(f"Failed to evaluate resume: {e}")
        state["error"] = str(e)
        return state


def route_on_score(state: dict[str, Any]) -> str:
    """Conditional routing: approve or retry."""
    recommendation = state.get("score_result", {}).get("recommendation", "").lower()
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if recommendation == "approve":
        logger.info("Resume approved, completing workflow")
        return "approve"
    elif retry_count < max_retries and recommendation == "retry":
        logger.info(f"Retrying resume generation (attempt {retry_count + 1}/{max_retries})")
        return "retry"
    else:
        logger.warning(f"Max retries reached or unknown recommendation: {recommendation}")
        return "done"


def build_resume_tailor_graph() -> StateGraph:
    """
    Build the resume tailor LangGraph workflow.
    
    Flow:
    1. Retrieve job description chunks from ChromaDB
    2. Retrieve user's resume chunks from ChromaDB
    3. Generate tailored resume (LLM)
    4. Evaluate tailored resume (LLM scorer)
    5. Conditional: if score >= 7 → approve, else → retry (max 3)
    
    Returns:
        Compiled LangGraph StateGraph
    """
    
    # Create graph
    builder = StateGraph(dict)
    
    # Add nodes
    builder.add_node("retrieve_job", node_retrieve_job_description)
    builder.add_node("retrieve_resume", node_retrieve_resume_sections)
    builder.add_node("generate", node_generate_tailored_resume)
    builder.add_node("evaluate", node_evaluate_resume)
    
    # Add edges with START
    builder.add_edge(START, "retrieve_job")
    builder.add_edge("retrieve_job", "retrieve_resume")
    builder.add_edge("retrieve_resume", "generate")
    builder.add_edge("generate", "evaluate")
    
    # Conditional edge from evaluate
    builder.add_conditional_edges(
        "evaluate",
        route_on_score,
        {
            "approve": END,
            "retry": "generate",  # Loop back to generate
            "done": END,
        },
    )
    
    # Compile graph
    graph = builder.compile()
    logger.info("Resume tailor graph compiled successfully")
    return graph
