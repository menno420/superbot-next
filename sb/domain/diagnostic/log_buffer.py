"""In-memory ring buffer of recent bot log records — the shipped
``cogs/diagnostic/_log_buffer.py`` ported onto v1's logger tree, for
the Diagnostics-hub 🔍 Recent Errors card.

Oracle history, kept because it names the trap: the shipped
``build_query_logs_embed`` originally read a ``logs`` DB table that
NOTHING ever wrote to, so the panel always answered "No logs found" —
even right after a crash. The shipped fix (and this port) keeps the
last ``_MAXLEN`` records of the bot's own loggers in memory — cheap,
no DB/file I/O, no cross-process pollution. The oracle attached to the
``bot`` logger tree; v1's application loggers all live under ``sb``
(``sb.kernel.*`` / ``sb.domain.*`` / ``sb.adapters.*``), so the
handler attaches there. Installed once (idempotent) from the
composition root (sb/app/main.py — the ``install_ws_latency_reader``
boot family); an uninstalled buffer truthfully renders the shipped
empty copy ("No logs found matching the criteria.")."""

from __future__ import annotations

import logging
import time
from collections import deque

__all__ = ["install", "recent"]

_MAXLEN = 500
_buffer: deque[dict[str, str]] = deque(maxlen=_MAXLEN)


class _RingBufferHandler(logging.Handler):
    """Append each emitted record to the bounded in-memory buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _buffer.append({
                "timestamp": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "message": record.getMessage(),
            })
        except Exception:  # pragma: no cover — a log handler must never raise
            self.handleError(record)


_installed = False


def install() -> None:
    """Attach the ring-buffer handler to the ``sb`` logger tree
    (idempotent — the oracle's ``install()`` contract verbatim)."""
    global _installed
    if _installed:
        return
    handler = _RingBufferHandler()
    handler.setLevel(logging.INFO)
    logging.getLogger("sb").addHandler(handler)
    _installed = True


def recent(level: str | None = None, limit: int = 10) -> list[dict[str, str]]:
    """Up to ``limit`` most-recent buffered records, newest first,
    optionally filtered to a single level name (e.g. ``"ERROR"``)."""
    items = list(_buffer)
    if level:
        wanted = level.upper()
        items = [r for r in items if r["level"] == wanted]
    items.reverse()
    return items[: max(1, limit)]


def _reset_for_tests() -> None:
    _buffer.clear()
