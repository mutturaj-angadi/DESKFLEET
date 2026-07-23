"""
app.tools.order
================
Tool wrapper around the mock API's /orders/{id} endpoint.

Exposes both the callable itself and its JSON schema, so the same
definition can be registered with the tool-calling agent AND checked
against the allowlist in app.tools.registry.
"""

from __future__ import annotations

import time

import httpx

from app.config import settings

ORDER_STATUS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": (
            "Look up the current status, ETA, and tracking number for a customer "
            "order by its order ID. Use this whenever a ticket references an order "
            "number or asks 'where is my order'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID, e.g. 'ORD-5001'.",
                }
            },
            "required": ["order_id"],
        },
    },
}


def get_order_status(order_id: str) -> dict:
    """Call the mock order API and return the order record.

    Returns a dict with either the order fields or an 'error' key —
    never raises, so the agent loop can inspect and react to failures
    instead of crashing.
    """
    started = time.monotonic()
    try:
        resp = httpx.get(f"{settings.mock_api_base_url}/orders/{order_id}", timeout=5.0)
        latency_ms = (time.monotonic() - started) * 1000
        if resp.status_code == 404:
            return {"error": f"Order '{order_id}' not found", "latency_ms": latency_ms}
        resp.raise_for_status()
        data = resp.json()
        data["latency_ms"] = latency_ms
        return data
    except httpx.HTTPError as exc:
        latency_ms = (time.monotonic() - started) * 1000
        return {"error": f"Order lookup failed: {exc}", "latency_ms": latency_ms}
