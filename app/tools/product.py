"""
app.tools.product
==================
Tool wrapper around the mock API's /products/{id} endpoint.
"""

from __future__ import annotations

import time

import httpx

from app.config import settings

GET_PRODUCT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_product",
        "description": (
            "Look up full details (price, stock status, description) for a single "
            "product by its product ID. Use this when a ticket asks about a "
            "specific product's features, price, or availability."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID, e.g. 'P-1001'.",
                }
            },
            "required": ["product_id"],
        },
    },
}


def get_product(product_id: str) -> dict:
    """Call the mock product API and return the product record.

    Never raises — returns {'error': ...} on failure so the agent can
    reason about a missing product instead of the process crashing.
    """
    started = time.monotonic()
    try:
        resp = httpx.get(f"{settings.mock_api_base_url}/products/{product_id}", timeout=5.0)
        latency_ms = (time.monotonic() - started) * 1000
        if resp.status_code == 404:
            return {"error": f"Product '{product_id}' not found", "latency_ms": latency_ms}
        resp.raise_for_status()
        data = resp.json()
        data["latency_ms"] = latency_ms
        return data
    except httpx.HTTPError as exc:
        latency_ms = (time.monotonic() - started) * 1000
        return {"error": f"Product lookup failed: {exc}", "latency_ms": latency_ms}
