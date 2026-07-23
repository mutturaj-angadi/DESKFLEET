"""
app.routers.schemas
=====================
Pydantic request/response models for the FastAPI surface.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResolveRequest(BaseModel):
    ticket: str
    order_id: str | None = None


class ToolCallOut(BaseModel):
    tool_name: str
    arguments: dict
    result: dict | None
    status: str
    latency_ms: float


class ResolveResponse(BaseModel):
    ticket_id: str
    decision: str
    reply: str | None
    escalation_reason: str | None
    category: str | None
    iterations: int
    tool_calls: list[ToolCallOut]
    trace_url: str | None


class TicketOut(BaseModel):
    id: str
    body: str
    order_id: str | None
    category: str | None
    decision: str | None
    reply: str | None
    escalation_reason: str | None
    iterations: int
    trace_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackRequest(BaseModel):
    ticket_id: str
    was_helpful: bool
    corrected_reply: str | None = None
    notes: str | None = None
