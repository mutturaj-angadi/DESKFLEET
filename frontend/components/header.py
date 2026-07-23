"""
DeskFleet Header
"""

from datetime import datetime

import streamlit as st


def render_header(page_title: str, api_online: bool):

    now = datetime.now().strftime("%d %b %Y • %H:%M:%S")

    status_color = "var(--success)" if api_online else "var(--danger)"

    status_text = "Online" if api_online else "Offline"

    col1, col2, col3 = st.columns([2, 3, 2])

    with col1:

        st.markdown(
            f"""
            <div class="df-card df-fade"
            style="padding:0.8rem;">

            <div style="
            font-size:1.1rem;
            font-weight:700;
            color:var(--text-primary);">

            🎫 DeskFleet AI

            </div>

            <div style="
            color:var(--text-secondary);
            font-size:0.8rem;">

            {page_title}

            </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:

        search = st.text_input(
            "",
            placeholder="🔍 Search tickets, traces, tools...",
            key="global_search",
            label_visibility="collapsed",
        )

        st.session_state["search_query"] = search

    with col3:

        st.markdown(
            f"""
            <div class="df-card"
            style="
            padding:0.8rem;
            text-align:right;">

            <div style="
            color:var(--text-secondary);
            font-size:0.8rem;">

            {now}

            </div>

            <div style="
            margin-top:4px;
            color:{status_color};
            font-weight:600;">

            ● API {status_text}

            </div>

            </div>
            """,
            unsafe_allow_html=True,
        )
