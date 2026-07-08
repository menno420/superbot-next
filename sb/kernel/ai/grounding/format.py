"""Grounding-line formatting (K10) — hoisted verbatim from shipped
``disbot/utils/btd6/grounding_format.py`` @7f7628e1 (projmoon already
consumed it cross-domain — never BTD6 code).

Turns raw fact bodies into single, length-bounded strings suitable for
the instruction stack's untrusted-data envelope. Sync, format-only, no
I/O.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

__all__ = [
    "DEFAULT_CAP",
    "INFINITE_SENTINEL",
    "is_infinite",
    "relative_time",
    "render_grounding_line",
    "sanitise",
]

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

DEFAULT_CAP = 240


def sanitise(value: object, *, cap: int = DEFAULT_CAP) -> str:
    """Strip control chars, collapse whitespace, cap at ``cap`` chars.
    Non-strings return ''. ``cap`` is a hard bound; use
    :func:`render_grounding_line` when body + provenance share a budget."""
    if not isinstance(value, str):
        return ""
    cleaned = _CONTROL_CHARS.sub("", value)
    cleaned = " ".join(cleaned.split())
    if cap > 0 and len(cleaned) > cap:
        cleaned = cleaned[: cap - 1] + "…"
    return cleaned


def relative_time(fetched_at: datetime | None) -> str:
    """Render a ``fetched_at`` timestamp as ``Ns / Nm / Nh / Nd ago``.
    Naive datetimes read as UTC; future timestamps render 'just now'."""
    if not isinstance(fetched_at, datetime):
        return "unknown"
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - fetched_at
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def render_grounding_line(
    body: str,
    *,
    source_name: str,
    fetched_at: datetime | None,
    max_chars: int = DEFAULT_CAP,
) -> str:
    """Compose ``<body> (source: <name>, fetched <when>)`` — the body is
    truncated BEFORE the provenance suffix so source/fetched never cut."""
    safe_source = sanitise(source_name, cap=0) or "unknown source"
    rel = relative_time(fetched_at)
    suffix = f" (source: {safe_source}, fetched {rel})"
    body_budget = max(8, max_chars - len(suffix))
    safe_body = sanitise(body, cap=body_budget)
    if not safe_body:
        safe_body = "(no summary)"
    return f"{safe_body}{suffix}"


# Game datasets store 9,999,999 as an "infinite" sentinel for instant-kill
# collision layers. It must render as ∞, never the raw number — a literal
# "9,999,999 dmg" in grounding misleads the model into reporting it as a
# real stat. (Shipped BTD6 rule; the sentinel value is domain-shared.)
INFINITE_SENTINEL = 9_999_999


def is_infinite(value: object) -> bool:
    """True for the 9,999,999 'infinite' (instant-effect) sentinel value."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= INFINITE_SENTINEL
    )
