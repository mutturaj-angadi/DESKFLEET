"""
frontend.components.sidebar
=============================
Navigation, project info, and live agent/API status.
"""

import streamlit as st

PAGES = [
    "🏠 Dashboard",
    "🎫 Resolve Ticket",
    "📜 Ticket History",
    "📊 Analytics",
    "⚙ Settings",
]


def render_sidebar(api_base_url: str, api_online: bool, version: str = "1.0.0") -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:0.6rem; padding:0.4rem 0 1.2rem 0;">
                <div style="width:40px;height:40px;border-radius:11px;
                     background:linear-gradient(135deg, var(--primary), var(--accent));
                     display:flex;align-items:center;justify-content:center;font-size:1.3rem;">🎫</div>
                <div>
                    <div style="font-weight:800; color:var(--text-primary); font-size:1.05rem;">DeskFleet AI</div>
                    <div style="font-size:0.72rem; color:var(--text-secondary);">Multi-Agent Support</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio("Navigate", PAGES, label_visibility="collapsed")

        st.markdown(
            "<hr style='border-color:var(--card-border); margin:1rem 0;'>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class='df-section-title'>🧭 About</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.5;">
            Orchestrates a Classifier → Researcher → Responder → Reviewer
            agent pipeline to resolve customer support tickets end-to-end.
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='df-section-title'>🟢 Agent Status</div>", unsafe_allow_html=True
        )
        for name in ["Classifier", "Researcher", "Responder", "Reviewer"]:
            st.markdown(
                f"<div style='font-size:0.82rem; color:var(--text-secondary); margin-bottom:0.25rem;'>"
                f"<span class='df-dot' style='background:var(--success);'></span>{name} — ready</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='df-section-title'>🔌 API Status</div>", unsafe_allow_html=True
        )
        dot_color = "var(--success)" if api_online else "var(--danger)"
        status_word = "Connected" if api_online else "Unreachable"
        st.markdown(
            f"<div style='font-size:0.82rem; color:var(--text-secondary);'>"
            f"<span class='df-dot' style='background:{dot_color};'></span>{status_word}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:0.75rem; color:var(--text-secondary); margin-top:0.3rem; "
            f'font-family:"JetBrains Mono",monospace; word-break:break-all;\'>{api_base_url}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.75rem; color:var(--text-secondary);'>Version {version}</div>",
            unsafe_allow_html=True,
        )

    return page
