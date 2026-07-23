"""
app.graph.workflow
====================
Assembles the full graph:

    START -> input_guardrail -> [REFUSE? -> END]
                              -> classifier -> researcher -> responder -> reviewer
                                                                  ^            |
                                                                  |  retry     | approve/escalate
                                                                  +------------+
                                                                               v
                                                                     output_guardrail -> END

`input_guardrail` and `output_guardrail` are graph nodes (not bare
functions called from the router) so that PII redaction and injection
scoring show up as their own steps in the LangSmith trace, same as
every LLM/tool node.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.edges import (
    route_after_classifier,
    route_after_input_guardrail,
    route_after_reviewer,
)
from app.graph.nodes import (
    classifier_node,
    fallback_node,
    researcher_node,
    responder_node,
    reviewer_node,
)
from app.graph.state import TicketState
from app.guardrails.injection import injection_score, is_injection
from app.guardrails.pii import redact_pii


def input_guardrail_node(state: TicketState) -> dict:
    body = state["ticket_body"]
    score = injection_score(body)
    if is_injection(body):
        return {
            "decision": "REFUSE",
            "escalation_reason": f"Ticket blocked by input guardrail (injection score {score:.2f})",
            "ticket_body": redact_pii(body),
        }
    return {"ticket_body": redact_pii(body)}


def output_guardrail_node(state: TicketState) -> dict:
    draft = state.get("draft")
    if draft:
        return {"draft": redact_pii(draft)}
    return {}


def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("classifier", classifier_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("responder", responder_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("output_guardrail", output_guardrail_node)

    graph.set_entry_point("input_guardrail")

    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {"classifier": "classifier", END: END},
    )
    graph.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {"researcher": "researcher", "fallback": "fallback"},
    )
    graph.add_edge("fallback", "output_guardrail")
    graph.add_edge("researcher", "responder")
    graph.add_edge("responder", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {"responder": "responder", "output_guardrail": "output_guardrail"},
    )
    graph.add_edge("output_guardrail", END)

    return graph.compile()


# Compiled once at import time; reused across requests.
compiled_graph = build_graph()
