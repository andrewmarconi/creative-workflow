"""LangGraph state-graph definition for the adaptation pipeline.

Defines the seven-node graph with conditional routing for evaluation
loops and revision retries.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from cw.lib.pipeline.nodes import (
    MAX_BRAND_RETRIES,
    MAX_CONCEPT_RETRIES,
    MAX_CULTURAL_RETRIES,
    MAX_FORMAT_RETRIES,
    brand_eval_node,
    concept_eval_node,
    concept_node,
    cultural_eval_node,
    culture_node,
    format_eval_node,
    writer_node,
)
from cw.lib.pipeline.schemas import PipelineState


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------

def route_after_format_eval(state: PipelineState) -> str:
    """Route after format/language compliance evaluation.

    - Passed  -> cultural_eval
    - Failed but retries remain -> writer (revision loop)
    - Exhausted retries -> fail (END)
    """
    if state.get("format_feedback") is None:
        return "cultural_eval"

    if state.get("format_revision_count", 0) < MAX_FORMAT_RETRIES:
        return "writer"

    return "fail"


def route_after_cultural_eval(state: PipelineState) -> str:
    """Route after cultural evaluation.

    - Passed  -> concept_eval
    - Failed but retries remain -> writer (revision loop)
    - Exhausted retries -> fail (END)
    """
    if state.get("cultural_feedback") is None:
        return "concept_eval"

    if state.get("cultural_revision_count", 0) < MAX_CULTURAL_RETRIES:
        return "writer"

    return "fail"


def route_after_concept_eval(state: PipelineState) -> str:
    """Route after concept fidelity evaluation.

    - Passed  -> brand_eval
    - Failed but retries remain -> writer (revision loop)
    - Exhausted retries -> fail (END)
    """
    if state.get("concept_feedback") is None:
        return "brand_eval"

    if state.get("concept_revision_count", 0) < MAX_CONCEPT_RETRIES:
        return "writer"

    return "fail"


def route_after_brand_eval(state: PipelineState) -> str:
    """Route after brand consistency evaluation.

    - Passed  -> end (success)
    - Failed but retries remain -> writer (revision loop)
    - Exhausted retries -> fail (END)
    """
    if state.get("brand_feedback") is None:
        return "end"

    if state.get("brand_revision_count", 0) < MAX_BRAND_RETRIES:
        return "writer"

    return "fail"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_adaptation_graph():
    """Build and compile the LangGraph adaptation pipeline.

    Flow::

        concept -> culture -> writer -> format_eval
                                ^            |
                                |            v (pass)
                                |       cultural_eval
                                |            |
                                |            v (pass)
                                |       concept_eval
                                |            |
                                |            v (pass)
                                |       brand_eval
                                |            |
                                +--(fail? retry at any eval)
                                             |
                                             v (pass)
                                            END
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("concept", concept_node)
    graph.add_node("culture", culture_node)
    graph.add_node("writer", writer_node)
    graph.add_node("format_eval", format_eval_node)
    graph.add_node("cultural_eval", cultural_eval_node)
    graph.add_node("concept_eval", concept_eval_node)
    graph.add_node("brand_eval", brand_eval_node)

    # Linear flow: start -> concept -> culture -> writer -> format_eval
    graph.set_entry_point("concept")
    graph.add_edge("concept", "culture")
    graph.add_edge("culture", "writer")
    graph.add_edge("writer", "format_eval")

    # Format eval -> conditional
    graph.add_conditional_edges(
        "format_eval",
        route_after_format_eval,
        {
            "cultural_eval": "cultural_eval",
            "writer": "writer",
            "fail": END,
        },
    )

    # Cultural eval -> conditional
    graph.add_conditional_edges(
        "cultural_eval",
        route_after_cultural_eval,
        {
            "concept_eval": "concept_eval",
            "writer": "writer",
            "fail": END,
        },
    )

    # Concept eval -> conditional
    graph.add_conditional_edges(
        "concept_eval",
        route_after_concept_eval,
        {
            "brand_eval": "brand_eval",
            "writer": "writer",
            "fail": END,
        },
    )

    # Brand eval -> conditional
    graph.add_conditional_edges(
        "brand_eval",
        route_after_brand_eval,
        {
            "end": END,
            "writer": "writer",
            "fail": END,
        },
    )

    return graph.compile()
