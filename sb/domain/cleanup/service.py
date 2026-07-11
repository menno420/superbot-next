"""Cleanup domain read ports — the channel-history reader.

The ``!cleanuphistory`` scan reads recent channel messages before
planning matches (the shipped ``ctx.channel.history(limit=...)`` read
that discord.py's HTTP layer performed as ``logs_from`` — the goldens'
wire verb, parity/harness/fake_http.py). The kernel stays discord-free:
the composition root installs the real reader (the discord adapter
slice); the parity harness installs the capture twin
(sb/adapters/parity/transport.py ``ParityHistoryReader``). An
uninstalled port raises — callers degrade to the declared + honest
refusal, never a silent empty scan (the moderation-actions posture).

Also home of the per-guild prohibited-word cache, the shipped cog's own
design (disbot/cogs/cleanup_cog.py ``self._word_cache`` + ``_load_guild``:
load-on-miss from the DB, refreshed after a word mutation). ``!word`` /
``!word list`` render THIS cache, not a fresh DB read — the capture
pinned exactly that distinction (goldens/cleanup/sweep_word_list.json
renders "`test`" over a truncated DB: the capture's per-case truncate
could not reach the cog attribute, so the alphabetically-earlier
``!word add test`` write survived in process memory). Golden-rendered
process-local state is MODE-DEPENDENT under live accumulation (the
server_logging counters precedent, PR #167), so the parity runner seeds
the CAPTURE trajectory per observing case
(sb/adapters/parity/runner.py ``CAPTURE_WORLD_WORD_CACHE``) and clears
the cache for every other case.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

__all__ = [
    "HistoryReaderNotInstalled",
    "get_words_cached",
    "install_history_reader",
    "invalidate_word_cache",
    "read_history",
    "reset_cleanup_ports_for_tests",
    "seed_word_cache_for_replay",
]

#: (channel_id, limit=) -> the fetched messages, newest-first (opaque
#: message ducks; the scan reads only ``.content``).
HistoryReader = Callable[..., Awaitable[Sequence[object]]]


class HistoryReaderNotInstalled(RuntimeError):
    """No history reader installed (the discord/capture adapter owns it)."""


_reader: HistoryReader | None = None


def install_history_reader(reader: HistoryReader) -> None:
    global _reader
    _reader = reader


def reset_cleanup_ports_for_tests() -> None:
    global _reader
    _reader = None
    _word_cache.clear()


async def read_history(channel_id: int, *, limit: int) -> Sequence[object]:
    if _reader is None:
        raise HistoryReaderNotInstalled(
            "cleanup history reader not installed (composition root "
            "installs the discord adapter's reader)")
    return await _reader(channel_id, limit=limit)


# --- the per-guild prohibited-word cache (the shipped `_word_cache`) ----------------

#: guild_id → the cached word list (the shipped cog's per-guild cache,
#: cleanup_cog.py `self._word_cache`; module docstring for the parity
#: seeding contract).
_word_cache: dict[int, list[str]] = {}


async def get_words_cached(guild_id: int) -> list[str]:
    """Load-on-miss word read — the shipped ``_load_guild`` shape: a
    cache hit renders WITHOUT touching the DB (the golden-pinned
    staleness), a miss loads the store row set once."""
    if guild_id not in _word_cache:
        from sb.domain.cleanup import store

        _word_cache[guild_id] = list(await store.get_words(guild_id))
    return list(_word_cache[guild_id])


def invalidate_word_cache(guild_id: int) -> None:
    """Drop a guild's cached words (the shipped post-mutation refresh,
    load-on-miss flavor) — called AFTER the word op's txn settles, never
    inside a leg (no mutations before commit points)."""
    _word_cache.pop(guild_id, None)


def seed_word_cache_for_replay(guild_id: int,
                               words: Sequence[str] | None) -> None:
    """Set the process-local word cache to a reconstructed CAPTURE state
    (parity runner only — runner.CAPTURE_WORLD_WORD_CACHE). ``None``
    clears (the trajectory for every non-observing case): the cache is
    golden-rendered process state, so it must be runner-seeded, never
    accumulated across replayed cases (mode-dependence otherwise —
    gate filters, report replays everything, isolation replays one)."""
    _word_cache.clear()
    if words is not None:
        _word_cache[guild_id] = [str(w) for w in words]
