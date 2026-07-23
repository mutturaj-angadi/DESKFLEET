"""
app.routers.tickets
=====================
All ticket-facing HTTP endpoints. Business logic (running the graph,
persisting results, recording metrics) lives here; the graph itself
knows nothing about HTTP or SQLite.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.database.db import (
    get_ticket,
    list_tickets,
    log_node_latency,
    save_feedback,
    save_ticket_result,
)
from app.graph.state import new_state
from app.graph.workflow import compiled_graph
from app.metrics.prometheus import (
    record_decision,
    record_node_usage,
    record_tool_calls,
    ticket_latency_seconds,
)
from app.routers.schemas import (
    FeedbackRequest,
    ResolveRequest,
    ResolveResponse,
    TicketOut,
    ToolCallOut,
)

router = APIRouter()


def _trace_url(trace_id: str | None) -> str | None:
    if not (
        trace_id
        and settings.langchain_tracing_v2
        and settings.langchain_api_key
        and settings.langchain_project
    ):
        return None
    return f"https://smith.langchain.com/o/-/projects/p/{settings.langchain_project}?traceId={trace_id}"


@router.post("/resolve", response_model=ResolveResponse)
def resolve_ticket(payload: ResolveRequest) -> ResolveResponse:
    ticket_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    state = new_state(ticket_id, payload.ticket, payload.order_id)
    state["trace_id"] = trace_id

    started = time.monotonic()
    try:
        with ticket_latency_seconds.time():
            final_state = compiled_graph.invoke(
                state,
                config={
                    # A stable root run id makes the optional LangSmith URL
                    # point to the actual graph invocation.
                    "run_id": uuid.UUID(trace_id),
                    "run_name": f"deskfleet-ticket-{ticket_id}",
                    "configurable": {"thread_id": ticket_id},
                    "tags": ["deskfleet"],
                    "metadata": {"ticket_id": ticket_id},
                },
            )
    except Exception:
        # A provider outage or invalid key must not turn a customer ticket into
        # a 500 response. Persist a reviewable escalation instead.
        final_state = {
            "category": None,
            "draft": None,
            "decision": "ESCALATE",
            "escalation_reason": (
                "Automatic resolution is temporarily unavailable. "
                "A support agent will review this ticket."
            ),
            "iterations": 0,
            "tool_calls": [],
            "conversation": [],
        }
    latency_ms = (time.monotonic() - started) * 1000

    decision = final_state.get("decision") or "ESCALATE"
    tool_calls = final_state.get("tool_calls", [])

    save_ticket_result(
        ticket_id=ticket_id,
        # The input guardrail has already redacted the graph state. Store that
        # safe representation rather than the raw customer submission.
        body=final_state.get("ticket_body", payload.ticket),
        order_id=payload.order_id,
        category=final_state.get("category"),
        decision=decision,
        reply=final_state.get("draft"),
        escalation_reason=final_state.get("escalation_reason"),
        iterations=final_state.get("iterations", 0),
        trace_id=trace_id,
        tool_calls=tool_calls,
        conversation=final_state.get("conversation", []),
    )

    record_decision(decision)
    record_tool_calls(tool_calls)
    for metric in final_state.get("node_metrics", []):
        log_node_latency(ticket_id=ticket_id, **metric)
        record_node_usage(**metric)

    return ResolveResponse(
        ticket_id=ticket_id,
        decision=decision,
        reply=final_state.get("draft"),
        escalation_reason=final_state.get("escalation_reason"),
        category=final_state.get("category"),
        iterations=final_state.get("iterations", 0),
        tool_calls=[ToolCallOut(**tc) for tc in tool_calls],
        trace_url=_trace_url(trace_id),
    )


@router.get("/ticket/{ticket_id}", response_model=TicketOut)
def get_ticket_by_id(ticket_id: str) -> TicketOut:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    return TicketOut.model_validate(ticket)


@router.get("/tickets", response_model=list[TicketOut])
def get_tickets(limit: int = 50) -> list[TicketOut]:
    return [TicketOut.model_validate(t) for t in list_tickets(limit=limit)]


@router.post("/feedback")
def submit_feedback(payload: FeedbackRequest) -> dict:
    ticket = get_ticket(payload.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{payload.ticket_id}' not found")
    save_feedback(
        ticket_id=payload.ticket_id,
        was_helpful=payload.was_helpful,
        corrected_reply=payload.corrected_reply,
        notes=payload.notes,
    )
    return {"status": "recorded"}


@router.get("/trace/{ticket_id}")
def get_trace(ticket_id: str) -> dict:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    url = _trace_url(ticket.trace_id)
    if url is None:
        return {
            "ticket_id": ticket_id,
            "trace_id": ticket.trace_id,
            "trace_url": None,
            "status": "LangSmith tracing is not enabled for this ticket.",
        }
    return {"ticket_id": ticket_id, "trace_id": ticket.trace_id, "trace_url": url}
