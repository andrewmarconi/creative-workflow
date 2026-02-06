"""LangGraph state-graph definition for the adaptation pipeline.

Defines the five-node graph with conditional routing for evaluation
loops and revision retries.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from cw.lib.pipeline.nodes import (
    MAX_CONCEPT_RETRIES,
    MAX_CULTURAL_RETRIES,
    concept_eval_node,
    concept_node,
    cultural_eval_node,
    culture_node,
    writer_node,
)
from cw.lib.pipeline.schemas import PipelineState


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------

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

    - Passed  -> end (success)
    - Failed but retries remain -> writer (revision loop)
    - Exhausted retries -> fail (END)
    """
    if state.get("concept_feedback") is None:
        return "end"

    if state.get("concept_revision_count", 0) < MAX_CONCEPT_RETRIES:
        return "writer"

    return "fail"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_adaptation_graph():
    """Build and compile the LangGraph adaptation pipeline.

    Flow::

        concept -> culture -> writer -> cultural_eval
                                ^            |
                                |            v
                                +-- writer <-- (fail? retry)
                                             |
                                             v (pass)
                                        concept_eval
                                             |
                                +-- writer <-- (fail? retry)
                                             |
                                             v (pass)
                                            END
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("concept", concept_node)
    graph.add_node("culture", culture_node)
    graph.add_node("writer", writer_node)
    graph.add_node("cultural_eval", cultural_eval_node)
    graph.add_node("concept_eval", concept_eval_node)

    # Linear flow: start -> concept -> culture -> writer -> cultural_eval
    graph.set_entry_point("concept")
    graph.add_edge("concept", "culture")
    graph.add_edge("culture", "writer")
    graph.add_edge("writer", "cultural_eval")

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
            "end": END,
            "writer": "writer",
            "fail": END,
        },
    )

    return graph.compile()
