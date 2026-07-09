"""Casino handlers (band 6) — the hub + the poker pending terminal.

The shipped casino v1 = multiplayer Texas Hold'em with one
auto-updating EPHEMERAL table message per player
(views/casino/poker_table.py) — that broadcast orchestration is
live-adapter work by construction (per-player ephemeral followups have
no headless shape). The PURE layers port now: the shared 52-card model
(`cards.py`) + the hand evaluator (`evaluate.py`), both verbatim — the
table engine docks onto them when the live adapter arms (D-0045
successor note). `!poker` is an honest pending terminal until then."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import Reply

__all__ = ["Reply", "ensure_handler_refs"]


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("casino.poker_pending")):
        return

    @handler("casino.poker_pending")
    async def poker_pending(req) -> Reply:
        """!poker / !holdem — declared, waiting on the live table."""
        return Reply(BLOCKED,
                     "♠ Multiplayer Hold'em tables (per-player "
                     "auto-updating hands) arm with the live adapter — "
                     "the deck + hand evaluator are already aboard. "
                     "Meanwhile: `!blackjack`, `!rps`, `!deathmatch`.")

    @handler("casino.hand_rank_view")
    async def hand_rank_view(req) -> Reply:
        """Hand rankings — the evaluator's own category order (a live
        read over the ported evaluate.py, weakest → strongest)."""
        from sb.domain.casino.evaluate import HandCategory

        names = {
            "HIGH_CARD": "High Card",
            "PAIR": "Pair",
            "TWO_PAIR": "Two Pair",
            "THREE_OF_A_KIND": "Three of a Kind",
            "STRAIGHT": "Straight",
            "FLUSH": "Flush",
            "FULL_HOUSE": "Full House",
            "FOUR_OF_A_KIND": "Four of a Kind",
            "STRAIGHT_FLUSH": "Straight Flush",
        }
        lines = ["♠ **Poker hand rankings** (weakest → strongest)"] + [
            f"{cat.value + 1}. {names.get(cat.name, cat.name.title())}"
            for cat in sorted(HandCategory)]
        return Reply(SUCCESS, "\n".join(lines))


_register()


def ensure_handler_refs() -> None:
    _register()
