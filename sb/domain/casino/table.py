"""The poker table lobby model (band 6 / parity flip) — the SHIPPED
per-channel table registry (disbot/views/casino/poker_table.py, the
lobby layer): one open table per channel, process-memory keyed by
channel_id exactly like the shipped module-level ``_tables`` dict.

Ported here: the shipped table constants (verbatim), the lobby seating
state (host + seat order + host-crown legend), and the open/close
lifecycle the ``!poker`` golden pins the OPEN of
(``parity/goldens/casino/sweep_poker.json``). The GAME layer — dealing,
betting rounds, and the per-player **auto-updating ephemeral hand**
messages — is live-adapter work by construction (per-player ephemeral
followups have no headless shape; D-0045 successor note): ``start``
past the lobby guards stays an honest blocked terminal in
sb/domain/casino/service.py until the live adapter arms. The pure deck
(cards.py) + evaluator (evaluate.py) it will deal from are aboard.

Play-chips only — no economy leg anywhere in the shipped table
(START_STACK is table stake, never a wallet read/write), which is why
the goldens carry no economy rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "BIG_BLIND",
    "MAX_SEATS",
    "MIN_PLAYERS",
    "PokerLobby",
    "SMALL_BLIND",
    "START_STACK",
    "close_table",
    "get_table",
    "launch_table",
    "reset_tables_for_tests",
]

# disbot/views/casino/poker_table.py constants, verbatim (the golden pins
# the interpolated bytes: "Buy-in: **1000** play-chips · Blinds 5/10 ·
# up to 8 seats.").
MAX_SEATS = 8
MIN_PLAYERS = 2
START_STACK = 1000
SMALL_BLIND = 5
BIG_BLIND = 10
LOBBY_TIMEOUT = 600


@dataclass
class PokerLobby:
    """One channel's open table — the shipped ``PokerTable`` lobby state
    (seating order + host), display names resolved at seat time (the
    shipped views held ``discord.abc.User`` objects; headless we hold
    the resolved name — the guild-directory read happens at the seam)."""

    channel_id: int
    host_id: int
    # seat order: (user_id, display_name); the host is seat 0 (the
    # shipped ``self.seated = [host]``).
    seats: list[tuple[int, str]] = field(default_factory=list)
    started: bool = False
    ended: bool = False

    def is_seated(self, user_id: int) -> bool:
        return any(uid == user_id for uid, _ in self.seats)

    def host_name(self) -> str:
        for uid, name in self.seats:
            if uid == self.host_id:
                return name
        return "Player"                     # the shipped _display_name fallback

    def seat_lines(self) -> str:
        """The shipped seated-list legend: 👑 host, • everyone else."""
        return "\n".join(
            f"{'👑 ' if uid == self.host_id else '• '}{name}"
            for uid, name in self.seats) or "—"


# the shipped module-level registry (one open table per channel).
_tables: dict[int, PokerLobby] = {}


def get_table(channel_id: int) -> PokerLobby | None:
    return _tables.get(int(channel_id))


def launch_table(channel_id: int, host_id: int,
                 host_name: str) -> PokerLobby | None:
    """The shipped ``launch_table`` lobby half: refuse while a live table
    holds the channel, else seat the host at a fresh table."""
    existing = _tables.get(int(channel_id))
    if existing is not None and not existing.ended:
        return None
    lobby = PokerLobby(channel_id=int(channel_id), host_id=int(host_id))
    lobby.seats.append((int(host_id), host_name))
    _tables[int(channel_id)] = lobby
    return lobby


def close_table(channel_id: int) -> None:
    lobby = _tables.get(int(channel_id))
    if lobby is not None:
        lobby.ended = True
        _tables.pop(int(channel_id), None)


def reset_tables_for_tests() -> None:
    _tables.clear()
