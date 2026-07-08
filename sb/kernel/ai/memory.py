"""Chat-memory orchestration (K10) — sits between the pure conversation
buffer and the NL engine. Ported from shipped
``disbot/services/ai_memory_service.py`` with the two couplings cut:

* the per-guild settings read (``ai.memory_window_minutes`` /
  ``ai.memory_channel_scan``) arrives through
  :func:`install_memory_settings_reader` (the settings band installs the
  real K7-seam reader; default = ``(0, False)`` — floor-only memory);
* the Discord ``TextChannel.history()`` fallback scan arrives through
  :func:`install_history_scanner` (band 7 installs the discord-aware
  scanner in ``sb/adapters/``; default = no scan).

Privacy posture unchanged: scanned bodies are never persisted — they seed
the in-process buffer only.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from sb.kernel.ai import conversation

__all__ = [
    "ALLOWED_WINDOWS",
    "MAX_PROMPT_TURNS",
    "gather_recent_turns",
    "install_history_scanner",
    "install_memory_settings_reader",
    "read_memory_settings",
    "reset_memory_ports_for_tests",
]

logger = logging.getLogger("sb.kernel.ai.memory")

# Upper bound on turns handed to the prompt assembler regardless of window
# (busy channel + wide window would inflate cost / truncate the question).
MAX_PROMPT_TURNS: int = 40

# Validated window choices (mirrors the shipped SettingSpec); anything else
# is treated as disabled.
ALLOWED_WINDOWS: frozenset[int] = frozenset({0, 15, 30, 60, 120})

#: reader(guild_id) -> (window_minutes, channel_scan_enabled)
MemorySettingsReader = Callable[[int], Awaitable[tuple[int, bool]]]

#: scanner(guild_id, channel_id) -> number of turns it appended to the
#: buffer via conversation.append (the discord adapter owns the fetch).
HistoryScanner = Callable[[int, int], Awaitable[int]]

_settings_reader: MemorySettingsReader | None = None
_history_scanner: HistoryScanner | None = None


def install_memory_settings_reader(reader: MemorySettingsReader) -> None:
    global _settings_reader
    _settings_reader = reader


def install_history_scanner(scanner: HistoryScanner) -> None:
    global _history_scanner
    _history_scanner = scanner


def reset_memory_ports_for_tests() -> None:
    global _settings_reader, _history_scanner
    _settings_reader = None
    _history_scanner = None


async def read_memory_settings(guild_id: int) -> tuple[int, bool]:
    """``(window_minutes, channel_scan_enabled)`` with safe defaults
    ``(0, False)`` and the window clamped to :data:`ALLOWED_WINDOWS`."""
    if _settings_reader is None:
        return 0, False
    try:
        window, scan_enabled = await _settings_reader(guild_id)
    except Exception:  # noqa: BLE001 — settings faults never break a reply
        logger.debug("ai memory: settings reader failed", exc_info=True)
        return 0, False
    try:
        window = int(window)
    except (TypeError, ValueError):
        window = 0
    if window not in ALLOWED_WINDOWS:
        window = 0
    return window, bool(scan_enabled)


async def gather_recent_turns(
    *,
    guild_id: int,
    channel_id: int,
) -> list[conversation.ConversationTurn]:
    """The recent turns the NL engine should see, with the fallback scan.

    1. Read the per-guild settings (installed reader).
    2. Ask the buffer for turns within the window (floor always retained).
    3. If the buffer is short AND scan is enabled AND a scanner is
       installed: scan channel history (best-effort) and re-ask.
    """
    window, scan_enabled = await read_memory_settings(guild_id)
    turns = conversation.recent_turns(
        guild_id,
        channel_id,
        window_minutes=window,
        limit=MAX_PROMPT_TURNS,
    )
    if (
        scan_enabled
        and _history_scanner is not None
        and len(turns) < conversation.MIN_FLOOR_TURNS
    ):
        try:
            await _history_scanner(guild_id, channel_id)
        except Exception as exc:  # noqa: BLE001 — best-effort fallback
            logger.debug(
                "ai memory: channel scan failed for guild=%s channel=%s: %s",
                guild_id,
                channel_id,
                exc,
            )
        turns = conversation.recent_turns(
            guild_id,
            channel_id,
            window_minutes=window,
            limit=MAX_PROMPT_TURNS,
        )
    return turns
