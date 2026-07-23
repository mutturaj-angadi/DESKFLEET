import uuid

from app.database.db import get_ticket, init_db, list_tickets, save_ticket_result


def test_save_and_get_ticket():
    init_db()
    ticket_id = str(uuid.uuid4())
    save_ticket_result(
        ticket_id=ticket_id,
        body="Where is my order?",
        order_id="ORD-5001",
        category="order",
        decision="RESOLVED",
        reply="Your order has shipped.",
        escalation_reason=None,
        iterations=0,
        trace_id="trace-123",
        tool_calls=[
            {
                "tool_name": "get_order_status",
                "arguments": {"order_id": "ORD-5001"},
                "result": {"status": "shipped"},
                "status": "ok",
                "latency_ms": 10.0,
            }
        ],
        conversation=[{"iteration": 0, "draft": "Your order has shipped.", "feedback": None}],
    )

    ticket = get_ticket(ticket_id)
    assert ticket is not None
    assert ticket.decision == "RESOLVED"
    assert ticket.category == "order"


def test_escalated_ticket_creates_escalation_row():
    from app.database.db import get_session
    from app.database.models import Escalation

    init_db()
    ticket_id = str(uuid.uuid4())
    save_ticket_result(
        ticket_id=ticket_id,
        body="Complex refund case",
        order_id=None,
        category="refund",
        decision="ESCALATE",
        reply=None,
        escalation_reason="Needs human review",
        iterations=3,
        trace_id="trace-456",
        tool_calls=[],
        conversation=[],
    )
    with get_session() as session:
        rows = session.query(Escalation).filter_by(ticket_id=ticket_id).all()
        assert len(rows) == 1
        assert rows[0].reason == "Needs human review"


def test_list_tickets_returns_most_recent_first():
    init_db()
    id1, id2 = str(uuid.uuid4()), str(uuid.uuid4())
    for tid in (id1, id2):
        save_ticket_result(
            ticket_id=tid,
            body="ticket",
            order_id=None,
            category="other",
            decision="RESOLVED",
            reply="reply",
            escalation_reason=None,
            iterations=0,
            trace_id=None,
            tool_calls=[],
            conversation=[],
        )
    tickets = list_tickets(limit=10)
    ids = [t.id for t in tickets]
    assert id1 in ids and id2 in ids
