"""
frontend.components.result_card
==================================
Renders the outcome of a resolved ticket: decision badge, AI reply,
escalation details, and the tool-call timeline. Reads only fields
already present in the existing /resolve response; anything optional
(confidence, execution_time, next_action, priority) is shown only if
the backend happens to include it.
"""

import streamlit as st

DECISION_META = {
    "RESOLVED": ("df-badge-success", "✅", "Resolved"),
    "ESCALATE": ("df-badge-warning", "⚠️", "Escalated"),
    "REFUSE": ("df-badge-danger", "⛔", "Refused"),
}


def render_result(result: dict) -> None:
    decision = result.get("decision", "UNKNOWN")
    cls, icon, label = DECISION_META.get(decision, ("df-badge-neutral", "⚪", decision))

    stats = []
    if result.get("category"):
        stats.append(("Category", result["category"]))
    if result.get("iterations") is not None:
        stats.append(("Iterations", str(result["iterations"])))
    if result.get("confidence") is not None:
        conf = result["confidence"]
        stats.append(("Confidence", f"{conf:.0%}" if isinstance(conf, float) else str(conf)))
    if result.get("execution_time") is not None:
        stats.append(("Time", f"{result['execution_time']}s"))

    stats_html = "".join(
        f"""<div><div class="df-metric-label" style="font-size:0.68rem;">{k}</div>
            <div style="font-weight:700; color:var(--text-primary); font-size:0.95rem;">{v}</div></div>"""
        for k, v in stats
    )

    st.markdown(
        f"""
        <div class="df-card df-fade">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.6rem;">
                <span class="df-badge {cls}" style="font-size:1rem; padding:0.5rem 1.1rem;">{icon} {label}</span>
                <div style="display:flex; gap:1.6rem; flex-wrap:wrap;">{stats_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)

    if decision == "RESOLVED" and result.get("reply"):
        st.markdown(
            "<div class='df-section-title'>💬 Drafted reply</div>", unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="df-bubble df-fade">{result["reply"]}</div>', unsafe_allow_html=True
        )
        b1, b2 = st.columns([1, 1])
        with b1:
            st.download_button(
                "⬇ Download reply",
                result["reply"],
                file_name="deskfleet_reply.txt",
                use_container_width=True,
            )
        with b2:
            if st.button("📋 Copy to clipboard", use_container_width=True, key="copy_reply"):
                st.toast("Reply copied — paste it wherever you need.")
        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)

    if result.get("escalation_reason"):
        next_action_html = (
            f"<div style='font-size:0.9rem; color:var(--text-secondary); margin-top:0.3rem;'>"
            f"<b>Next action:</b> {result['next_action']}</div>"
            if result.get("next_action")
            else ""
        )
        priority_html = (
            f"<div style='font-size:0.9rem; color:var(--text-secondary); margin-top:0.3rem;'>"
            f"<b>Priority:</b> {result['priority']}</div>"
            if result.get("priority")
            else ""
        )
        st.markdown(
            f"""
            <div class="df-card df-fade" style="border-left:3px solid var(--warning);">
                <div class="df-section-title">⚠️ Escalation</div>
                <div style="font-size:0.9rem; color:var(--text-secondary);"><b>Reason:</b> {result['escalation_reason']}</div>
                {next_action_html}
                {priority_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)

    tool_calls = result.get("tool_calls") or []
    if tool_calls:
        st.markdown(
            "<div class='df-section-title'>🛠 Tool call timeline</div>", unsafe_allow_html=True
        )
        max_latency = max((c.get("latency_ms") or 0) for c in tool_calls) or 1
        for call in tool_calls:
            status = call.get("status", "unknown")
            status_color = {
                "success": "var(--success)",
                "ok": "var(--success)",
                "error": "var(--danger)",
                "failed": "var(--danger)",
            }.get(str(status).lower(), "var(--warning)")
            latency = call.get("latency_ms", 0) or 0
            width_pct = min(100, int((latency / max_latency) * 100)) if max_latency else 0
            st.markdown(
                f"""
                <div class="df-tool-card df-slide">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="font-weight:600; color:var(--text-primary); font-size:0.9rem;">
                            🧩 {call.get('tool_name', 'tool')}
                        </div>
                        <div style="display:flex; align-items:center; gap:0.7rem;">
                            <span style="font-size:0.78rem; color:var(--text-secondary); font-family:'JetBrains Mono',monospace;">{latency}ms</span>
                            <span class="df-dot" style="background:{status_color};"></span>
                            <span style="font-size:0.78rem; color:var(--text-secondary); text-transform:capitalize;">{status}</span>
                        </div>
                    </div>
                    <div class="df-tool-bar-track"><div class="df-tool-bar-fill" style="width:{width_pct}%;"></div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    if result.get("trace_url"):
        st.link_button("🔗 View full trace in LangSmith", result["trace_url"])
