"""
frontend.components.metrics
==============================
Metric cards summarizing recent ticket activity, derived entirely from
the /tickets response — no new backend fields required.
"""

import streamlit as st

ICONS = {
    "total": "🎫",
    "resolved": "✅",
    "escalated": "⚠️",
    "response_time": "⏱️",
    "api_health": "💚",
    "iterations": "🔁",
}


def _card(label: str, value: str, icon: str, color: str, trend: str | None = None) -> str:
    trend_html = (
        f"<div class='df-metric-trend' style='color:{color};'>{trend}</div>" if trend else ""
    )
    return f"""
        <div class="df-metric df-fade" style="--metric-color:{color};">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <div class="df-metric-label">{label}</div>
                    <div class="df-metric-value">{value}</div>
                </div>
                <div style="font-size:1.4rem;">{icon}</div>
            </div>
            {trend_html}
        </div>
    """


def render_metrics(tickets: list[dict], api_online: bool) -> None:
    total = len(tickets)
    resolved = sum(1 for t in tickets if t.get("decision") == "RESOLVED")
    escalated = sum(1 for t in tickets if t.get("decision") == "ESCALATE")

    all_latencies = []
    for t in tickets:
        for call in t.get("tool_calls", []) or []:
            if call.get("latency_ms") is not None:
                all_latencies.append(call["latency_ms"])
    avg_latency = (
        f"{(sum(all_latencies) / len(all_latencies)):.0f}ms" if all_latencies else "—"
    )

    total_iterations = sum(t.get("iterations", 0) or 0 for t in tickets)
    avg_iterations = f"{(total_iterations / total):.1f}" if total else "—"

    prev_total = st.session_state.get("_prev_total_tickets")
    trend = None
    if prev_total is not None and total != prev_total:
        diff = total - prev_total
        trend = f"↑ {diff} new" if diff > 0 else f"↓ {abs(diff)}"
    st.session_state["_prev_total_tickets"] = total

    cols = st.columns(6)
    cards = [
        ("Total Tickets", str(total), ICONS["total"], "var(--primary)", trend),
        ("Resolved", str(resolved), ICONS["resolved"], "var(--success)", None),
        ("Escalated", str(escalated), ICONS["escalated"], "var(--warning)", None),
        ("Avg Response", avg_latency, ICONS["response_time"], "var(--accent)", None),
        (
            "API Health",
            "Online" if api_online else "Offline",
            ICONS["api_health"],
            "var(--success)" if api_online else "var(--danger)",
            None,
        ),
        ("Avg Iterations", avg_iterations, ICONS["iterations"], "var(--primary-light)", None),
    ]
    for col, (label, value, icon, color, tr) in zip(cols, cards):
        with col:
            st.markdown(_card(label, value, icon, color, tr), unsafe_allow_html=True)
