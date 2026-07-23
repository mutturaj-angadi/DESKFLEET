"""
app.database.db
=================
SQLite engine/session setup plus small persistence helpers used by
the FastAPI routers and the graph's post-processing step. Keeping
the helpers here (rather than scattering raw session code through
routers.py) keeps every INSERT/SELECT in one auditable place.
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import (
    AgentLog,
    Base,
    ConversationHistory,
    Escalation,
    Feedback,
    Ticket,
    ToolCall,
)

engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_ticket_result(
    *,
    ticket_id: str,
    body: str,
    order_id: str | None,
    category: str | None,
    decision: str,
    reply: str | None,
    escalation_reason: str | None,
    iterations: int,
    trace_id: str | None,
    tool_calls: list[dict],
    conversation: list[dict],
) -> None:
    """Persist the full outcome of one graph run in a single transaction."""
    with get_session() as session:
        session.merge(
            Ticket(
                id=ticket_id,
                body=body,
                order_id=order_id,
                category=category,
                decision=decision,
                reply=reply,
                escalation_reason=escalation_reason,
                iterations=iterations,
                trace_id=trace_id,
            )
        )

        for call in tool_calls:
            session.add(
                ToolCall(
                    ticket_id=ticket_id,
                    tool_name=call.get("tool_name", "unknown"),
                    arguments=call.get("arguments"),
                    result=call.get("result"),
                    status=call.get("status", "error"),
                    latency_ms=call.get("latency_ms"),
                )
            )

        for turn in conversation:
            session.add(
                ConversationHistory(
                    ticket_id=ticket_id,
                    iteration=turn.get("iteration", 0),
                    draft=turn.get("draft", ""),
                    reviewer_feedback=turn.get("feedback"),
                )
            )

        if decision == "ESCALATE":
            session.add(
                Escalation(
                    ticket_id=ticket_id,
                    reason=escalation_reason or "No reason provided",
                )
            )


def log_node_latency(
    *, ticket_id: str, node: str, latency_ms: float, tokens: int = 0, cost_usd: float = 0.0
) -> None:
    with get_session() as session:
        session.add(
            AgentLog(
                ticket_id=ticket_id,
                node=node,
                latency_ms=latency_ms,
                tokens=tokens,
                cost_usd=cost_usd,
            )
        )


def save_feedback(
    *,
    ticket_id: str,
    was_helpful: bool,
    corrected_reply: str | None,
    notes: str | None,
) -> None:
    with get_session() as session:
        session.add(
            Feedback(
                ticket_id=ticket_id,
                was_helpful=int(was_helpful),
                corrected_reply=corrected_reply,
                notes=notes,
            )
        )


def get_ticket(ticket_id: str) -> Ticket | None:
    with get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        if ticket is not None:
            session.expunge(ticket)
        return ticket


def list_tickets(limit: int = 50) -> list[Ticket]:
    with get_session() as session:
        tickets = session.query(Ticket).order_by(Ticket.created_at.desc()).limit(limit).all()
        for t in tickets:
            session.expunge(t)
        return tickets
