"""Secret-redaction helpers (K5/observability home — A-8 obligation carrier).

Ported verbatim from shipped `disbot/core/runtime/ai/redaction.py`
(superbot main 7f7628e1) and HOISTED out of the ai namespace: A-8 lands the
operator-alert sink spec at K5 carrying the `redact_text` obligation, so the
scrubber must exist below the AI band. The K10 gateway pipeline imports it
from HERE when it lands (redaction is a kernel obligation, not an AI detail).

Deterministic and conservative: reduces risk without network access or
external state. Scrubs Discord-token-like strings, API-key prefixes,
postgres:// DSNs, bearer tokens, Discord snowflakes, emails, and
secret-bearing URL query params.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = ["RedactionResult", "redact_payload", "redact_text"]

_TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "discord_token_like",
        re.compile(r"[A-Za-z0-9_-]{23,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}"),
    ),
    (
        "api_key_like",
        # Underscore (legacy ``sk_secret``) and hyphen (OpenAI-style
        # ``sk-proj-...``) prefixes, plus common GitHub / Slack prefixes.
        re.compile(r"\b(?:sk|pk|rk|xoxb|ghp)[_-][A-Za-z0-9_\-]{12,}\b"),
    ),
    (
        "database_url",
        re.compile(r"\b(?:postgres|postgresql)://[^\s]+", re.IGNORECASE),
    ),
    (
        "bearer_token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    ),
    # Discord snowflakes are 17-20 decimal digits. Placed last so genuine
    # secrets with a long numeric tail get the more specific label above.
    (
        "discord_id",
        re.compile(r"\b\d{17,20}\b"),
    ),
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_URL_QUERY_RE = re.compile(
    r"([?&](?:token|key|secret|password|signature)=)[^&\s]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RedactionResult:
    """Result of redacting one value."""

    value: Any
    replacements: dict[str, int]


def _count(replacements: dict[str, int], key: str) -> None:
    replacements[key] = replacements.get(key, 0) + 1


def redact_text(text: str) -> RedactionResult:
    """Redact sensitive-looking substrings from plain text."""
    replacements: dict[str, int] = {}
    value = text

    for label, pattern in _TOKEN_PATTERNS:

        def _replace_token(_: re.Match[str], *, redaction_label: str = label) -> str:
            _count(replacements, redaction_label)
            return f"[{redaction_label}:redacted]"

        value = pattern.sub(_replace_token, value)

    def _replace_email(_: re.Match[str]) -> str:
        _count(replacements, "email")
        return "[email:redacted]"

    value = _EMAIL_RE.sub(_replace_email, value)

    def _replace_query(match: re.Match[str]) -> str:
        _count(replacements, "url_secret_query")
        return f"{match.group(1)}[redacted]"

    value = _URL_QUERY_RE.sub(_replace_query, value)
    return RedactionResult(value=value, replacements=replacements)


def redact_payload(payload: Any) -> RedactionResult:
    """Recursively redact strings in common JSON-like payloads."""
    replacements: dict[str, int] = {}

    def merge(child: RedactionResult) -> Any:
        for key, count in child.replacements.items():
            replacements[key] = replacements.get(key, 0) + count
        return child.value

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return merge(redact_text(value))
        if isinstance(value, dict):
            return {str(k): walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, tuple):
            return tuple(walk(v) for v in value)
        return value

    return RedactionResult(value=walk(payload), replacements=replacements)
