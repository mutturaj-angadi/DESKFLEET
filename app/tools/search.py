"""
app.tools.search
================
Tool wrapper around the mock API's /products?query= endpoint.
"""

from __future__ import annotations

import time

import httpx

from app.config import settings

SEARCH_PRODUCTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": (
            "Search the product catalog by free-text query (title, category, or "
            "description keywords). Use this when a ticket describes a product "
            "without giving an exact product ID, e.g. 'the backpack I bought'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text search terms, e.g. 'wireless headphones'.",
                }
            },
            "required": ["query"],
        },
    },
}


def search_products(query: str) -> dict:
    """Call the mock product search API and return matching products.

    Always returns a dict shape ({'results': [...]} or {'error': ...})
    so downstream code doesn't need to special-case list vs dict.
    """
    started = time.monotonic()
    try:
        resp = httpx.get(
            f"{settings.mock_api_base_url}/products",
            params={"query": query},
            timeout=5.0,
        )
        latency_ms = (time.monotonic() - started) * 1000
        resp.raise_for_status()
        return {"results": resp.json(), "latency_ms": latency_ms}
    except httpx.HTTPError as exc:
        latency_ms = (time.monotonic() - started) * 1000
        return {"error": f"Product search failed: {exc}", "latency_ms": latency_ms}
