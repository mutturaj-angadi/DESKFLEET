"""
app.metrics.cost
==================
Rough token/cost accounting using tiktoken. This is an estimate (it
counts prompt text we control, not the model's actual reported
usage), good enough for the Grafana cost panel and for keeping an
eye on spend during development.
"""

from __future__ import annotations

import tiktoken

from app.config import settings

# Approximate blended per-1K-token price for gpt-4o-mini class models.
# Update this if you swap models.
PRICE_PER_1K_TOKENS_USD = 0.00060

_encoding = None


def _get_encoding():
    global _encoding
    if _encoding is None:
        try:
            _encoding = tiktoken.encoding_for_model(settings.openai_model)
        except Exception:
            try:
                _encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # tiktoken lazily downloads its encoding tables. Keep request
                # handling fully offline-capable when that cache is absent.
                _encoding = False
    return _encoding


def count_tokens(text: str) -> int:
    if not text:
        return 0
    if _get_encoding() is False:
        # Conservative approximation for the observability dashboard only.
        return max(1, round(len(text.split()) * 1.3))
    return len(_get_encoding().encode(text))


def estimate_cost_usd(token_count: int) -> float:
    return round((token_count / 1000) * PRICE_PER_1K_TOKENS_USD, 6)
