"""
app.metrics.prometheus
========================
All Prometheus metric objects live here, imported wherever they need
to be incremented/observed. Kept separate from routers.py so metric
names/labels are defined in exactly one place.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

tickets_processed_total = Counter(
    "deskfleet_tickets_processed_total", "Total tickets processed"
)
tickets_resolved_total = Counter(
    "deskfleet_tickets_resolved_total", "Tickets resolved automatically"
)
tickets_escalated_total = Counter(
    "deskfleet_tickets_escalated_total", "Tickets escalated to a human"
)
tickets_refused_total = Counter(
    "deskfleet_tickets_refused_total", "Tickets refused (e.g. injection blocked)"
)

ticket_latency_seconds = Histogram(
    "deskfleet_ticket_latency_seconds", "End-to-end latency per ticket resolution"
)
node_latency_seconds = Histogram(
    "deskfleet_agent_node_latency_seconds",
    "Latency for each DeskFleet graph node",
    ["node"],
)

tool_calls_total = Counter(
    "deskfleet_tool_calls_total",
    "Tool calls made by the Researcher agent",
    ["tool_name", "status"],
)

tokens_used_total = Counter("deskfleet_tokens_used_total", "Cumulative LLM tokens consumed")
cost_usd_total = Counter("deskfleet_cost_usd_total", "Cumulative estimated LLM cost in USD")


def record_decision(decision: str) -> None:
    tickets_processed_total.inc()
    if decision == "RESOLVED":
        tickets_resolved_total.inc()
    elif decision == "ESCALATE":
        tickets_escalated_total.inc()
    elif decision == "REFUSE":
        tickets_refused_total.inc()


def record_tool_calls(tool_calls: list[dict]) -> None:
    for call in tool_calls:
        tool_calls_total.labels(
            tool_name=call.get("tool_name", "unknown"), status=call.get("status", "error")
        ).inc()


def record_node_usage(*, node: str, latency_ms: float, tokens: int, cost_usd: float) -> None:
    """Record the node-level observability data required by the agent brief."""
    node_latency_seconds.labels(node=node).observe(latency_ms / 1000)
    if tokens:
        tokens_used_total.inc(tokens)
    if cost_usd:
        cost_usd_total.inc(cost_usd)


def metrics_response() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST
