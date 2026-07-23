from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database.db import init_db
from app.main import app

init_db()
client = TestClient(app)


def _fake_final_state(**overrides):
    base = {
        "category": "order",
        "draft": "Your order ORD-5001 has shipped and is on the way.",
        "decision": "RESOLVED",
        "escalation_reason": None,
        "iterations": 0,
        "tool_calls": [
            {
                "tool_name": "get_order_status",
                "arguments": {"order_id": "ORD-5001"},
                "result": {"status": "shipped"},
                "status": "ok",
                "latency_ms": 12.3,
            }
        ],
        "conversation": [
            {"iteration": 0, "draft": "Your order has shipped.", "feedback": None}
        ],
    }
    base.update(overrides)
    return base


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_endpoint_returns_prometheus_text():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"deskfleet_tickets_processed_total" in resp.content


def test_resolve_ticket_happy_path():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state()
        resp = client.post("/resolve", json={"ticket": "Where is my order ORD-5001?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "RESOLVED"
    assert body["category"] == "order"
    assert len(body["tool_calls"]) == 1


def test_resolve_ticket_escalation_path():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state(
            decision="ESCALATE",
            escalation_reason="Exceeded max reviewer iterations",
            draft=None,
        )
        resp = client.post("/resolve", json={"ticket": "This is a complicated refund case"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "ESCALATE"
    assert body["escalation_reason"] is not None


def test_resolve_then_fetch_ticket_by_id():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state()
        resolve_resp = client.post("/resolve", json={"ticket": "Where is my order?"})
    ticket_id = resolve_resp.json()["ticket_id"]

    get_resp = client.get(f"/ticket/{ticket_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ticket_id


def test_resolve_persists_the_guardrailed_ticket_body():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state(
            ticket_body="redacted ticket body"
        )
        resolve_resp = client.post("/resolve", json={"ticket": "raw customer ticket"})

    ticket_id = resolve_resp.json()["ticket_id"]
    ticket = client.get(f"/ticket/{ticket_id}")
    assert ticket.status_code == 200
    assert ticket.json()["body"] == "redacted ticket body"


def test_trace_endpoint_reports_when_tracing_is_disabled():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state()
        resolve_resp = client.post("/resolve", json={"ticket": "ticket with trace"})

    trace_resp = client.get(f"/trace/{resolve_resp.json()['ticket_id']}")
    assert trace_resp.status_code == 200
    assert trace_resp.json()["trace_url"] is None


def test_get_nonexistent_ticket_returns_404():
    resp = client.get("/ticket/does-not-exist")
    assert resp.status_code == 404


def test_list_tickets():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state()
        client.post("/resolve", json={"ticket": "ticket A"})
    resp = client.get("/tickets")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_feedback_on_existing_ticket():
    with patch("app.routers.tickets.compiled_graph") as mocked_graph:
        mocked_graph.invoke.return_value = _fake_final_state()
        resolve_resp = client.post("/resolve", json={"ticket": "ticket needing feedback"})
    ticket_id = resolve_resp.json()["ticket_id"]

    fb_resp = client.post(
        "/feedback",
        json={"ticket_id": ticket_id, "was_helpful": True, "notes": "Good reply"},
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["status"] == "recorded"


def test_feedback_on_nonexistent_ticket_returns_404():
    resp = client.post("/feedback", json={"ticket_id": "does-not-exist", "was_helpful": False})
    assert resp.status_code == 404
