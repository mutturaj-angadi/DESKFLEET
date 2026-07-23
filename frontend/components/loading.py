"""
frontend.components.loading
==============================
Animated loading sequence for DeskFleet.
"""

import threading
import time

import streamlit as st
from components.pipeline import render_pipeline_html

PIPELINE_STEPS = [
    ("Classifier", 0.20),
    ("Researcher", 0.45),
    ("Responder", 0.70),
    ("Reviewer", 0.90),
]


def run_with_progress(
    resolve_fn,
    ticket_text: str,
    order_id: str,
    pipeline_placeholder=None,
):
    """
    Runs resolve_fn(ticket_text, order_id) in a background thread while
    animating both the progress bar and the agent pipeline.
    """

    result_box = {}

    def worker():
        result_box["result"] = resolve_fn(ticket_text, order_id)

    thread = threading.Thread(target=worker)
    thread.start()

    status = st.empty()
    progress = st.progress(0)

    step = 0

    while thread.is_alive():

        node, pct = PIPELINE_STEPS[min(step, len(PIPELINE_STEPS) - 1)]

        if pipeline_placeholder:
            pipeline_placeholder.markdown(
                render_pipeline_html(active_node=node),
                unsafe_allow_html=True,
            )

        status.markdown(
            f"""
            <div style="
                color:var(--text-secondary);
                font-size:0.9rem;
                margin-top:0.4rem;">
                <span class="df-dot"
                style="background:var(--accent);
                animation:glow 1s infinite;"></span>

                Running <b>{node}</b> agent...
            </div>
            """,
            unsafe_allow_html=True,
        )

        progress.progress(pct)

        time.sleep(0.65)

        if step < len(PIPELINE_STEPS) - 1:
            step += 1

    thread.join()

    progress.progress(1.0)

    if pipeline_placeholder:
        pipeline_placeholder.markdown(
            render_pipeline_html(done=True),
            unsafe_allow_html=True,
        )

    status.markdown(
        """
        <div style="
        color:var(--success);
        font-weight:600;">
        ✅ Ticket processed successfully
        </div>
        """,
        unsafe_allow_html=True,
    )

    time.sleep(0.5)

    status.empty()
    progress.empty()

    return result_box.get("result")
