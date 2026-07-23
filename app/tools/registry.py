"""
app.tools.registry
===================
The tool allowlist.

This is intentionally the ONLY place that maps a tool name to a
callable. The Researcher agent may only ever invoke a tool that
appears in TOOL_REGISTRY; anything else — a name the model
hallucinates, a name from a prompt-injection attempt embedded in a
ticket, or a typo — is rejected here and logged, never executed.

Do not give nodes direct imports of app.tools.order / .product /
.search. Route everything through call_tool() so the allowlist check
can never accidentally be bypassed.
"""

from __future__ import annotations

import time
from typing import Any

from app.tools.order import ORDER_STATUS_SCHEMA, get_order_status
from app.tools.product import GET_PRODUCT_SCHEMA, get_product
from app.tools.search import SEARCH_PRODUCTS_SCHEMA, search_products

TOOL_REGISTRY: dict[str, Any] = {
    "get_order_status": get_order_status,
    "get_product": get_product,
    "search_products": search_products,
}

TOOL_SCHEMAS: list[dict] = [
    ORDER_STATUS_SCHEMA,
    GET_PRODUCT_SCHEMA,
    SEARCH_PRODUCTS_SCHEMA,
]


def call_tool(name: str, arguments: dict) -> dict:
    """Execute a tool call by name, enforcing the allowlist.

    Returns an audit-log-ready dict:
        {tool_name, arguments, result, status, latency_ms}

    `status` is one of "ok", "error", or "blocked". A blocked call
    never touches the underlying function — it fails closed.
    """
    started = time.monotonic()

    if name not in TOOL_REGISTRY:
        return {
            "tool_name": name,
            "arguments": arguments,
            "result": None,
            "status": "blocked",
            "latency_ms": (time.monotonic() - started) * 1000,
            "reason": f"'{name}' is not in the tool allowlist",
        }

    try:
        result = TOOL_REGISTRY[name](**arguments)
        status = "error" if isinstance(result, dict) and "error" in result else "ok"
        return {
            "tool_name": name,
            "arguments": arguments,
            "result": result,
            "status": status,
            "latency_ms": (time.monotonic() - started) * 1000,
        }
    except TypeError as exc:
        # Bad/missing arguments from the model — fail closed, don't crash the graph.
        return {
            "tool_name": name,
            "arguments": arguments,
            "result": None,
            "status": "error",
            "latency_ms": (time.monotonic() - started) * 1000,
            "reason": f"Invalid arguments: {exc}",
        }
