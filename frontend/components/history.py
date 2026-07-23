"""
frontend.components.history
==============================
Searchable, filterable, sortable list of recent tickets.
"""

import streamlit as st

DECISION_BADGE = {
    "RESOLVED": ("df-badge-success", "✅"),
    "ESCALATE": ("df-badge-warning", "⚠️"),
    "REFUSE": ("df-badge-danger", "⛔"),
}


def render_history(tickets: list[dict], compact: bool = False) -> None:
    if not tickets:
        st.markdown(
            "<div class='df-card' style='text-align:center; color:var(--text-secondary);'>"
            "No tickets resolved yet — resolve one to see it here.</div>",
            unsafe_allow_html=True,
        )
        return

    if not compact:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            query = st.text_input(
                "Search",
                placeholder="Search ticket body or category…",
                label_visibility="collapsed",
            )
        with c2:
            decision_options = ["All decisions"] + sorted(
                {t.get("decision", "—") for t in tickets if t.get("decision")}
            )
            decision_filter = st.selectbox(
                "Filter", decision_options, label_visibility="collapsed"
            )
        with c3:
            sort_order = st.selectbox(
                "Sort", ["Newest first", "Oldest first"], label_visibility="collapsed"
            )
    else:
        query, decision_filter, sort_order = "", "All decisions", "Newest first"

    filtered = tickets
    if query:
        q = query.lower()
        filtered = [
            t
            for t in filtered
            if q in (t.get("body", "") or "").lower()
            or q in (t.get("category", "") or "").lower()
        ]
    if decision_filter != "All decisions":
        filtered = [t for t in filtered if t.get("decision") == decision_filter]
    if sort_order == "Oldest first":
        filtered = list(reversed(filtered))

    display_list = filtered[:30] if compact else filtered
    for t in display_list:
        cls, icon = DECISION_BADGE.get(t.get("decision"), ("df-badge-neutral", "⚪"))
        body = t.get("body") or ""
        preview = body[:90]
        st.markdown(
            f"""
            <div class="df-card df-fade" style="margin-bottom:0.6rem; padding:0.9rem 1.1rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.4rem;">
                    <div>
                        <span class="df-badge {cls}">{icon} {t.get('decision', '—')}</span>
                        <span class="df-badge df-badge-neutral" style="margin-left:0.4rem;">{t.get('category') or '—'}</span>
                    </div>
                    <span style="font-size:0.75rem; color:var(--text-secondary); font-family:'JetBrains Mono',monospace;">
                        {t.get('created_at', '')}
                    </span>
                </div>
                <div style="margin-top:0.5rem; font-size:0.86rem; color:var(--text-secondary);">{preview}{"…" if len(body) > 90 else ""}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"View details · {t.get('id', '')[:8]}"):
            st.write(body)
            if t.get("reply"):
                st.caption(f"Reply: {t['reply']}")
            if t.get("escalation_reason"):
                st.caption(f"Escalation: {t['escalation_reason']}")
