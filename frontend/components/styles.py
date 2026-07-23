"""
frontend.components.styles
============================
Design tokens + CSS injection for the DeskFleet dashboard.

Palette, animations, and component classes used across every page.
Nothing here touches API behavior — presentation only.
"""

import streamlit as st

COLORS = {
    "primary": "#4F46E5",
    "accent": "#06B6D4",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "bg": "#0F172A",
    "card": "#1E293B",
}


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {{
            --primary: {COLORS['primary']};
            --primary-light: #6366F1;
            --accent: {COLORS['accent']};
            --success: {COLORS['success']};
            --warning: {COLORS['warning']};
            --danger: {COLORS['danger']};
            --bg: {COLORS['bg']};
            --card: {COLORS['card']};
            --card-border: rgba(148, 163, 184, 0.12);
            --text-primary: #E2E8F0;
            --text-secondary: #94A3B8;
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* Hide default Streamlit chrome */
        #MainMenu, footer, header {{visibility: hidden;}}
        div[data-testid="stToolbar"] {{visibility: hidden;}}
        div[data-testid="stDecoration"] {{display: none;}}

        .stApp {{
            background: radial-gradient(circle at 15% 0%, rgba(79,70,229,0.18), transparent 45%),
                        radial-gradient(circle at 85% 10%, rgba(6,182,212,0.14), transparent 40%),
                        var(--bg);
        }}

        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #131B2E 0%, #0F172A 100%);
            border-right: 1px solid var(--card-border);
        }}

        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(148,163,184,0.25); border-radius: 8px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(148,163,184,0.4); }}

        div[data-testid="stButton"] > button {{
            border-radius: 10px;
            border: 1px solid var(--card-border);
            background: var(--card);
            color: var(--text-primary);
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        div[data-testid="stButton"] > button:hover {{
            border-color: var(--primary-light);
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(79,70,229,0.25);
        }}
        div[data-testid="stButton"] > button[kind="primary"] {{
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border: none;
            box-shadow: 0 4px 16px rgba(79,70,229,0.35);
        }}
        div[data-testid="stButton"] > button[kind="primary"]:hover {{
            box-shadow: 0 8px 28px rgba(79,70,229,0.5);
        }}

        textarea, input {{ border-radius: 10px !important; }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes glow {{
            0%, 100% {{ box-shadow: 0 0 6px rgba(79,70,229,0.4); }}
            50% {{ box-shadow: 0 0 22px rgba(79,70,229,0.8); }}
        }}
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-10px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        .df-fade {{ animation: fadeIn 0.45s ease both; }}
        .df-slide {{ animation: slideIn 0.35s ease both; }}

        .df-card {{
            background: rgba(30, 41, 59, 0.65);
            backdrop-filter: blur(14px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.25rem 1.4rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .df-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 32px rgba(0,0,0,0.35);
        }}

        .df-metric {{
            background: rgba(30, 41, 59, 0.65);
            backdrop-filter: blur(14px);
            border: 1px solid var(--card-border);
            border-left: 3px solid var(--metric-color, var(--primary));
            border-radius: 14px;
            padding: 1rem 1.2rem;
            transition: transform 0.2s ease;
        }}
        .df-metric:hover {{ transform: translateY(-3px); }}
        .df-metric-label {{
            font-size: 0.78rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
        }}
        .df-metric-value {{
            font-size: 1.9rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-top: 0.15rem;
        }}
        .df-metric-trend {{ font-size: 0.78rem; font-weight: 600; margin-top: 0.2rem; }}

        .df-hero {{
            background: linear-gradient(120deg, rgba(79,70,229,0.35), rgba(6,182,212,0.22));
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 2.2rem 2.4rem;
            position: relative;
            overflow: hidden;
        }}
        .df-hero::before {{
            content: "";
            position: absolute;
            top: -60%; right: -10%;
            width: 420px; height: 420px;
            background: radial-gradient(circle, rgba(6,182,212,0.35), transparent 70%);
            animation: glow 4s ease-in-out infinite;
        }}
        .df-hero h1 {{
            font-size: 2.3rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(90deg, #E2E8F0, #A5B4FC);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .df-hero p {{ color: var(--text-secondary); margin-top: 0.5rem; font-size: 1.02rem; }}

        .df-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 0.02em;
        }}
        .df-badge-success {{ background: rgba(34,197,94,0.15); color: var(--success); border: 1px solid rgba(34,197,94,0.35); }}
        .df-badge-warning {{ background: rgba(245,158,11,0.15); color: var(--warning); border: 1px solid rgba(245,158,11,0.35); }}
        .df-badge-danger {{ background: rgba(239,68,68,0.15); color: var(--danger); border: 1px solid rgba(239,68,68,0.35); }}
        .df-badge-neutral {{ background: rgba(148,163,184,0.15); color: var(--text-secondary); border: 1px solid rgba(148,163,184,0.3); }}

        .df-bubble {{
            background: rgba(15,23,42,0.55);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            border-top-left-radius: 4px;
            padding: 1rem 1.2rem;
            color: var(--text-primary);
            line-height: 1.55;
            font-size: 0.96rem;
        }}

        .df-tool-card {{
            background: rgba(30,41,59,0.55);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 0.7rem 1rem;
            margin-bottom: 0.5rem;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}
        .df-tool-card:hover {{ transform: translateX(3px); border-color: var(--primary-light); }}
        .df-tool-bar-track {{
            width: 100%;
            height: 6px;
            border-radius: 4px;
            background: rgba(148,163,184,0.15);
            margin-top: 0.4rem;
            overflow: hidden;
        }}
        .df-tool-bar-fill {{
            height: 100%;
            border-radius: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
        }}

        .df-node {{
            background: rgba(30,41,59,0.6);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 0.65rem 0.9rem;
            text-align: center;
            font-weight: 600;
            color: var(--text-secondary);
            transition: all 0.3s ease;
        }}
        .df-node-active {{
            border-color: var(--accent);
            color: var(--text-primary);
            animation: glow 1.6s ease-in-out infinite;
        }}
        .df-node-arrow {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin: 0.1rem 0;
        }}

        .df-dot {{
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }}

        .df-section-title {{
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.6rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
