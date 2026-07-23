"""
frontend.streamlit_app
========================
DeskFleet AI Operations Console.

    streamlit run frontend/streamlit_app.py

Talks to the FastAPI backend over HTTP — set API_BASE_URL if it's not
running on localhost:8000.

NOTE: resolve_ticket() and fetch_tickets() below are the original API
contract functions, byte-for-byte unchanged from the previous version
of this file (same endpoints, same request/response handling). Every
other line in this file is presentation wiring only.
"""

from __future__ import annotations

import os

import requests
import streamlit as st
from components.analytics import render_analytics
from components.header import render_header
from components.history import render_history
from components.loading import run_with_progress
from components.metrics import render_metrics
from components.pipeline import render_pipeline_html
from components.result_card import render_result
from components.sidebar import render_sidebar
from components.styles import inject_css
from dotenv import load_dotenv

# Match the backend's local-development behavior while allowing deployed
# environment variables to win over values in .env.
load_dotenv(override=False)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
VERSION = "1.0.0"

st.set_page_config(page_title="DeskFleet", page_icon="🎫", layout="wide")

DECISION_COLORS = {
    "RESOLVED": "🟢",
    "ESCALATE": "🟠",
    "REFUSE": "🔴",
}


# ---------------------------------------------------------------------------
# Original API contract — DO NOT MODIFY.
# ---------------------------------------------------------------------------
def resolve_ticket(ticket: str, order_id: str | None) -> dict | None:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/resolve",
            json={"ticket": ticket, "order_id": order_id or None},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach the DeskFleet API: {exc}")
        return None


def fetch_tickets(limit: int = 20) -> list[dict]:
    try:
        resp = requests.get(f"{API_BASE_URL}/tickets", params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return []


@st.cache_data(ttl=5, show_spinner=False)
def _check_api_online(base_url: str) -> bool:
    """Lightweight liveness check used only to drive status indicators.
    Does not touch the /resolve or /tickets contract."""
    try:
        resp = requests.get(f"{base_url}/tickets", params={"limit": 1}, timeout=3)
        return resp.status_code < 500
    except requests.RequestException:
        return False


def _clear_ticket_form() -> None:
    st.session_state["ticket_text"] = ""
    st.session_state["order_id"] = ""


def _fill_example_ticket() -> None:
    st.session_state["ticket_text"] = "Where is my order ORD-5001? It hasn't arrived yet."
    st.session_state["order_id"] = "ORD-5001"


# ---------------------------------------------------------------------------
# Presentation layer
# ---------------------------------------------------------------------------
inject_css()


@st.fragment(run_every="1s")
def _live_header(page_title: str) -> None:
    # Re-checks the backend and redraws just this bar every second —
    # isolated as a fragment so it doesn't rerun the whole page (and
    # doesn't wipe out whatever you're typing in the ticket box).
    st.session_state["_api_online"] = _check_api_online(API_BASE_URL)
    render_header(page_title, st.session_state["_api_online"])


api_online = _check_api_online(API_BASE_URL)
page = render_sidebar(API_BASE_URL, api_online, VERSION)
_live_header(page)
api_online = st.session_state.get("_api_online", api_online)


@st.cache_data(ttl=2)
def load_tickets():
    return fetch_tickets(limit=50)


tickets = load_tickets()
resolve_clicked = False

if page == "🏠 Dashboard":
    st.markdown(
        """
        <div class="df-hero df-fade">
            <h1>DeskFleet AI</h1>
            <p>AI Multi-Agent Customer Support Platform</p>
            <p style="font-size:0.92rem;">Real-time orchestration of AI agents for customer support —
            Classifier → Researcher → Responder → Reviewer.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
    render_metrics(tickets, api_online)
    st.markdown("<div style='height:1.4rem;'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown(
            "<div class='df-section-title'>📜 Recent activity</div>", unsafe_allow_html=True
        )
        render_history(tickets, compact=True)
    with col_right:
        st.markdown(
            "<div class='df-section-title'>🧠 Agent pipeline</div>", unsafe_allow_html=True
        )
        st.markdown(
            render_pipeline_html(done=api_online),
            unsafe_allow_html=True,
        )
        st.caption(
            "Glows once the backend responds; head to **Resolve Ticket** to watch it step through live."
        )

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='df-section-title'>📡 Live status</div>", unsafe_allow_html=True
        )
        status_rows = [
            ("Backend", "Online" if api_online else "Offline", api_online),
            ("Database", "Connected" if api_online else "Unknown", api_online),
            ("Agents", "Running" if api_online else "Idle", api_online),
        ]
        for label, value, ok in status_rows:
            dot = "var(--success)" if ok else "var(--danger)"
            st.markdown(
                f"<div class='df-card' style='padding:0.6rem 0.9rem; margin-bottom:0.5rem; "
                f"display:flex; justify-content:space-between; align-items:center;'>"
                f"<span style='font-size:0.85rem; color:var(--text-secondary);'>{label}</span>"
                f"<span style='font-size:0.85rem; color:var(--text-primary);'>"
                f"<span class='df-dot' style='background:{dot};'></span>{value}</span></div>",
                unsafe_allow_html=True,
            )

elif page == "🎫 Resolve Ticket":
    col_input, col_right = st.columns([2, 1])

    with col_right:
        st.markdown(
            "<div class='df-section-title'>🧠 System monitor</div>", unsafe_allow_html=True
        )
        pipeline_ph = st.empty()
        pipeline_ph.markdown(
            render_pipeline_html(done="last_result" in st.session_state),
            unsafe_allow_html=True,
        )
        st.caption("Lights up node-by-node while a ticket is being resolved.")

    with col_input:
        st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
        st.markdown(
            "<div class='df-section-title'>🎫 Resolve customer ticket</div>",
            unsafe_allow_html=True,
        )

        ticket_text = st.text_area(
            "Ticket body",
            placeholder="e.g. Where is my order ORD-5001? It hasn't arrived yet.",
            height=160,
            key="ticket_text",
            label_visibility="collapsed",
        )
        st.markdown(
            f"<div style='text-align:right; font-size:0.75rem; color:var(--text-secondary);'>"
            f"{len(ticket_text)} characters</div>",
            unsafe_allow_html=True,
        )
        order_id_input = st.text_input(
            "Order ID (optional)", placeholder="ORD-5001", key="order_id"
        )

        b1, b2, b3 = st.columns([1.4, 1, 1])
        with b1:
            resolve_clicked = st.button(
                "⚡ Resolve ticket", type="primary", use_container_width=True
            )
        with b2:
            st.button("🧹 Clear", use_container_width=True, on_click=_clear_ticket_form)
        with b3:
            st.button("✨ Example", use_container_width=True, on_click=_fill_example_ticket)
        st.markdown("</div>", unsafe_allow_html=True)

    if resolve_clicked:
        if not ticket_text.strip():
            st.warning("Enter a ticket first.")
        else:
            st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
            result = run_with_progress(
                resolve_ticket,
                ticket_text,
                order_id_input,
                pipeline_placeholder=pipeline_ph,
            )

            if result:
                st.session_state["last_result"] = result
                # Force the next dashboard/history render to fetch the newly
                # persisted ticket instead of showing a stale cached list.
                st.cache_data.clear()
                st.rerun()

    if "last_result" in st.session_state:
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        render_result(st.session_state["last_result"])

elif page == "📜 Ticket History":
    st.markdown(
        "<div class='df-section-title'>📜 Ticket history</div>", unsafe_allow_html=True
    )
    render_history(tickets, compact=False)

elif page == "📊 Analytics":
    st.markdown("<div class='df-section-title'>📊 Analytics</div>", unsafe_allow_html=True)
    render_analytics(tickets)

elif page == "⚙ Settings":
    st.markdown('<div class="df-card df-fade">', unsafe_allow_html=True)
    st.markdown("<div class='df-section-title'>⚙ Settings</div>", unsafe_allow_html=True)
    st.text_input("Backend URL", value=API_BASE_URL, disabled=True)
    st.text_input("Version", value=VERSION, disabled=True)
    st.caption(
        "Set the API_BASE_URL environment variable to point this dashboard at a different backend."
    )
    st.markdown("</div>", unsafe_allow_html=True)
