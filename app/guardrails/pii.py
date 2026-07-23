"""
app.guardrails.pii
====================
Regex-based PII redaction for emails, phone numbers, credit card
numbers, and US SSNs. Applied to the inbound ticket before logging
and to the outbound reply before it's returned to the caller — so
sensitive data never lands in a log line or a drafted email by
accident.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "CREDIT_CARD",
        re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    ),
    ("PHONE", re.compile(r"(?:\+?\d{1,2}[\s.-])?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")),
]


def redact_pii(text: str) -> str:
    """Replace any detected PII substrings with a `[REDACTED_<TYPE>]` tag.

    Order matters: credit cards and SSNs are checked before the looser
    phone pattern so a 16-digit card number isn't partially consumed
    as a phone number first.
    """
    redacted = text
    for label, pattern in _PATTERNS:
        redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
    return redacted
