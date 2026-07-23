"""
app.graph.edges
=================
Conditional routing functions. LangGraph calls these with the current
state and expects back the name of the next node (or END). Keeping
routing decisions here, separate from nodes.py, makes the two
branch points in the graph easy to find and unit-test in isolation.
"""

from __future__ import annotations

from langgraph.graph import END

from app.graph.state import TicketState


def route_after_input_guardrail(state: TicketState) -> str:
    """If the injection guardrail already set a REFUSE decision,
    short-circuit straight to END. Otherwise proceed to the Classifier.
    """
    if state.get("decision") == "REFUSE":
        return END
    return "classifier"


def route_after_classifier(state: TicketState) -> str:
    """Use deterministic support handling when the LLM provider is unavailable."""
    if state.get("llm_unavailable_reason"):
        return "fallback"
    return "researcher"


def route_after_reviewer(state: TicketState) -> str:
    """The Reviewer node sets `decision` directly when it approves or
    escalates. When neither is set, it means the reviewer asked for a
    retry and iterations were incremented — loop back to Responder.
    """
    decision = state.get("decision")
    if decision in ("RESOLVED", "ESCALATE"):
        return "output_guardrail"
    return "responder"
