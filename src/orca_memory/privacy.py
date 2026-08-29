"""Deterministic secret containment for conversation and memory text."""

from __future__ import annotations

import re


REDACTION_POLICY = "orca-secret-containment/0.1"
_REDACTED = "[REDACTED]"
_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|password|secret)"
        r"(\s*[:=]\s*)([^\s,;]+)"
    ),
)


def redact_secrets(text: str) -> str:
    """Replace obvious credential values while preserving surrounding context."""

    redacted = text
    for index, pattern in enumerate(_PATTERNS):
        if index == 3:
            redacted = pattern.sub(
                lambda match: f"{match.group(1)}{match.group(2)}{_REDACTED}",
                redacted,
            )
        else:
            redacted = pattern.sub(_REDACTED, redacted)
    return redacted


def contains_secret(text: str) -> bool:
    """Return whether text still contains an obvious credential-like value."""

    return any(pattern.search(text) is not None for pattern in _PATTERNS)
