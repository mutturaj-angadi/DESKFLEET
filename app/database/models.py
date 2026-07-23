"""
app.database.models
=====================
SQLAlchemy ORM models for DeskFleet's five tables. LangSmith holds
the rich, per-node trace; these tables hold the durable business
record — enough to answer "what happened to ticket X" without
needing to open a trace viewer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=_uuid)
    body = Column(Text, nullable=False)
    order_id = Column(String, nullable=True)
    category = Column(String, nullable=True)
    decision = Column(String, nullable=True)  # RESOLVED | ESCALATE | REFUSE
    reply = Column(Text, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    iterations = Column(Integer, default=0)
    trace_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True, default=_uuid)
    ticket_id = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(String, nullable=False)  # ok | error | blocked
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=_uuid)
    ticket_id = Column(String, nullable=False)
    node = Column(String, nullable=False)  # classifier | researcher | responder | reviewer
    latency_ms = Column(Float, nullable=True)
    tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(String, primary_key=True, default=_uuid)
    ticket_id = Column(String, nullable=False)
    iteration = Column(Integer, nullable=False)
    draft = Column(Text, nullable=False)
    reviewer_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, default=_uuid)
    ticket_id = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=_uuid)
    ticket_id = Column(String, nullable=False)
    was_helpful = Column(Integer, nullable=False)  # 0/1
    corrected_reply = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
