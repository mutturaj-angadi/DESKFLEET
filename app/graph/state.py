"""
app.graph.state
=================
The single typed state object every node reads from and writes a
partial update to. Nothing in this graph passes data around as loose
function arguments — if a node needs something, it's in `TicketState`.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class ToolCallRecord(TypedDict):
    tool_name: str
    arguments: dict
    result: dict | None
    status: Literal["ok", "error", "blocked"]
    latency_ms: float


class ConversationTurn(TypedDict):
    iteration: int
    draft: str
    feedback: str | None


class NodeMetric(TypedDict):
    node: str
    latency_ms: float
    tokens: int
    cost_usd: float


class TicketState(TypedDict, total=False):
    ticket_id: str
    ticket_body: str
    order_id: str | None

    category: Literal["order", "product", "refund", "other"] | None

    facts: list[dict]
    tool_calls: list[ToolCallRecord]

    draft: str | None
    conversation: list[ConversationTurn]

    decision: Literal["RESOLVED", "ESCALATE", "REFUSE"] | None
    escalation_reason: str | None

    iterations: int
    trace_id: str | None
    llm_unavailable_reason: str | None
    node_metrics: list[NodeMetric]


def new_state(ticket_id: str, ticket_body: str, order_id: str | None = None) -> TicketState:
    """Construct a fresh TicketState with all required defaults set,
    so every node can safely assume these keys exist.
    """
    return TicketState(
        ticket_id=ticket_id,
        ticket_body=ticket_body,
        order_id=order_id,
        category=None,
        facts=[],
        tool_calls=[],
        draft=None,
        conversation=[],
        decision=None,
        escalation_reason=None,
        iterations=0,
        trace_id=None,
        node_metrics=[],
    )
