NODES = [
    "Classifier",
    "Researcher",
    "Responder",
    "Reviewer",
]


def render_pipeline_html(active_node=None, done=False):

    html = """
    <div style="
        display:flex;
        flex-direction:column;
        gap:12px;
    ">
    """

    for i, node in enumerate(NODES):

        active = done or node == active_node

        border = "#00d4ff" if active else "#3d4b66"
        bg = "#18253b" if active else "#111827"

        html += f"""
        <div style="
            padding:12px;
            border:2px solid {border};
            border-radius:12px;
            text-align:center;
            font-weight:700;
            background:{bg};
            color:white;
        ">
            {node}
        </div>
        """

        if i != len(NODES) - 1:

            html += """
            <div style="
                text-align:center;
                font-size:22px;
                color:#00d4ff;
            ">
                ↓
            </div>
            """

    html += "</div>"

    return html
