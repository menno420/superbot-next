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
"""

from __future__ import annotations

from typing import Awaitable, Callable, Sequence

__all__ = [
    "HistoryReaderNotInstalled",
    "install_history_reader",
    "read_history",
    "reset_cleanup_ports_for_tests",
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


async def read_history(channel_id: int, *, limit: int) -> Sequence[object]:
    if _reader is None:
        raise HistoryReaderNotInstalled(
            "cleanup history reader not installed (composition root "
            "installs the discord adapter's reader)")
    return await _reader(channel_id, limit=limit)
