"""
frontend.components.analytics
================================
Plotly charts summarizing DeskFleet activity: decision mix, category
breakdown, ticket volume over time, tool latency, and success rate.
Built entirely from the existing /tickets payload.
"""

from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

COLORWAY = ["#4F46E5", "#06B6D4", "#22C55E", "#F59E0B", "#EF4444", "#818CF8"]


def _empty_state(msg: str) -> None:
    st.markdown(
        f"<div class='df-card' style='text-align:center; color:var(--text-secondary); padding:2rem;'>{msg}</div>",
        unsafe_allow_html=True,
    )


def _themed_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#E2E8F0")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94A3B8", family="Inter"),
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        colorway=COLORWAY,
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.12)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)")
    return fig


def render_analytics(tickets: list[dict]) -> None:
    if not tickets:
        _empty_state("No ticket data yet — analytics will populate once tickets are resolved.")
        return

    df = pd.DataFrame(tickets)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
        decision_counts = Counter(df.get("decision", pd.Series(dtype=str)).fillna("—"))
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=list(decision_counts.keys()),
                    values=list(decision_counts.values()),
                    hole=0.55,
                    marker=dict(colors=COLORWAY),
                )
            ]
        )
        st.plotly_chart(_themed_layout(fig, "Resolved vs Escalated"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
        cat_counts = Counter(df.get("category", pd.Series(dtype=str)).fillna("Uncategorized"))
        fig = go.Figure(
            data=[
                go.Bar(
                    x=list(cat_counts.keys()),
                    y=list(cat_counts.values()),
                    marker_color=COLORWAY[0],
                )
            ]
        )
        st.plotly_chart(_themed_layout(fig, "Tickets by category"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
        if "created_at" in df.columns:
            try:
                df["_date"] = pd.to_datetime(df["created_at"]).dt.date
                by_day = df.groupby("_date").size().reset_index(name="count")
                fig = go.Figure(
                    data=[
                        go.Scatter(
                            x=by_day["_date"],
                            y=by_day["count"],
                            mode="lines+markers",
                            line=dict(color=COLORWAY[1], width=3),
                            fill="tozeroy",
                            fillcolor="rgba(6,182,212,0.12)",
                        )
                    ]
                )
                st.plotly_chart(
                    _themed_layout(fig, "Tickets over time"), use_container_width=True
                )
            except Exception:
                _empty_state("Timestamps unavailable for this chart.")
        else:
            _empty_state("Timestamps unavailable for this chart.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
        latencies = []
        for t in tickets:
            for c in t.get("tool_calls", []) or []:
                if c.get("latency_ms") is not None:
                    latencies.append(c["latency_ms"])
        if latencies:
            fig = go.Figure(
                data=[go.Histogram(x=latencies, marker_color=COLORWAY[2], nbinsx=12)]
            )
            st.plotly_chart(
                _themed_layout(fig, "Tool call latency distribution"), use_container_width=True
            )
        else:
            _empty_state("No tool-call latency data yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    total = len(tickets)
    resolved = sum(1 for t in tickets if t.get("decision") == "RESOLVED")
    success_rate = (resolved / total * 100) if total else 0
    st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=success_rate,
            number={"suffix": "%", "font": {"color": "#E2E8F0"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#94A3B8"},
                "bar": {"color": COLORWAY[0]},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
            },
        )
    )
    st.plotly_chart(_themed_layout(fig, "Resolution success rate"), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
