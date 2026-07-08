"""Short-term per-channel conversation memory (K10) — ported verbatim from
shipped ``disbot/services/ai_conversation_service.py`` @7f7628e1.

In-process only (no Redis-backed state; the shipped decision stands). Each
channel keeps a rolling buffer of :class:`ConversationTurn` rows so the NL
front-end can ground replies in the channel's prior context. The cache
always retains at least :data:`MIN_FLOOR_TURNS` per channel regardless of
the configured window. Bounded by a per-channel deque cap and a
channel-level LRU.
"""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field

__all__ = [
    "CacheStats",
    "ConversationTurn",
    "MIN_FLOOR_TURNS",
    "append",
    "channel_stats",
    "forget_channel",
    "forget_guild",
    "recent_turns",
    "reset_conversation_for_tests",
    "stats",
]

# Always-on minimum: even with the memory window "off" the bot retains the
# last N messages per channel so a basic conversational handle works.
MIN_FLOOR_TURNS: int = 3

_PER_CHANNEL_CAP: int = 200
_CHANNEL_LRU_CAP: int = 50


@dataclass(frozen=True)
class ConversationTurn:
    user_id: int
    role: str  # 'user' | 'assistant'
    text: str
    ts: float = field(default_factory=time.time)
    # Display name as the user appeared at message time; the instruction
    # assembler sanitizes it into the bracketed speaker label. None → the
    # assembler falls back to an opaque pseudonym.
    display_name: str | None = None


_BUFFERS: OrderedDict[tuple[int, int], deque[ConversationTurn]] = OrderedDict()


def _buffer_for(guild_id: int, channel_id: int) -> deque[ConversationTurn]:
    key = (guild_id, channel_id)
    if key in _BUFFERS:
        _BUFFERS.move_to_end(key)
        return _BUFFERS[key]
    if len(_BUFFERS) >= _CHANNEL_LRU_CAP:
        _BUFFERS.popitem(last=False)
    buf: deque[ConversationTurn] = deque(maxlen=_PER_CHANNEL_CAP)
    _BUFFERS[key] = buf
    return buf


def append(
    guild_id: int,
    channel_id: int,
    *,
    user_id: int,
    role: str,
    text: str,
    ts: float | None = None,
    display_name: str | None = None,
) -> None:
    """Append one turn. Empty / non-str text is dropped silently so the NL
    engine can call this unconditionally. ``display_name`` is preserved raw
    here; sanitization happens in the instruction assembler."""
    if not isinstance(text, str):
        return
    text = text.strip()
    if not text:
        return
    buf = _buffer_for(guild_id, channel_id)
    buf.append(
        ConversationTurn(
            user_id=user_id,
            role=role,
            text=text,
            ts=ts if ts is not None else time.time(),
            display_name=display_name,
        ),
    )


def recent_turns(
    guild_id: int,
    channel_id: int,
    *,
    window_minutes: int = 0,
    min_floor: int = MIN_FLOOR_TURNS,
    limit: int = _PER_CHANNEL_CAP,
) -> list[ConversationTurn]:
    """Recent turns with window + floor semantics: ``window_minutes == 0``
    → up to ``min_floor`` most recent; ``> 0`` → turns inside the window
    but never fewer than the floor; ``limit`` caps regardless."""
    key = (guild_id, channel_id)
    buf = _BUFFERS.get(key)
    if not buf:
        return []
    _BUFFERS.move_to_end(key)

    all_turns = list(buf)
    if window_minutes <= 0:
        out = all_turns[-min_floor:]
        return out[-limit:]

    cutoff = time.time() - (window_minutes * 60)
    windowed = [t for t in all_turns if t.ts >= cutoff]
    if len(windowed) < min_floor:
        windowed = all_turns[-min_floor:]
    return windowed[-limit:]


def forget_guild(guild_id: int) -> int:
    """Drop every buffer scoped to ``guild_id``; returns the count."""
    drop = [key for key in _BUFFERS if key[0] == guild_id]
    for key in drop:
        del _BUFFERS[key]
    return len(drop)


def forget_channel(guild_id: int, channel_id: int) -> int:
    key = (guild_id, channel_id)
    if key in _BUFFERS:
        del _BUFFERS[key]
        return 1
    return 0


@dataclass(frozen=True)
class CacheStats:
    """Body-free snapshot of cache occupancy for operator diagnostics."""

    channel_count: int
    total_turns: int
    per_channel_cap: int = _PER_CHANNEL_CAP
    channel_lru_cap: int = _CHANNEL_LRU_CAP


def stats() -> CacheStats:
    total = sum(len(buf) for buf in _BUFFERS.values())
    return CacheStats(channel_count=len(_BUFFERS), total_turns=total)


def channel_stats(guild_id: int) -> dict[int, int]:
    """Per-channel turn counts for a guild. No bodies."""
    return {
        channel_id: len(buf)
        for (gid, channel_id), buf in _BUFFERS.items()
        if gid == guild_id
    }


def reset_conversation_for_tests() -> None:
    _BUFFERS.clear()
