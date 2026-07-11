"""Blackjack tournament orchestration (band 6) — the shipped
``BlackjackCog`` registration/rounds state, headless (the #130 rps
tournament shape on the same seams).

Shipped semantics carried verbatim where the cog held them
(cogs/blackjack_cog.py + utils/tournaments.py +
views/blackjack/tournament_views.py @7c6278e):

* orchestration state is IN-MEMORY per guild (``_tournaments`` /
  ``_TournPlayerState`` on the cog — a restart forfeits the bracket;
  paid entry rows are refunded at boot through the audited lane,
  ``ESCROW_RECOVERY_SUBSYSTEMS``);
* sign-up rides BOTH the Join button and the ✅ reaction (the shipped
  ``_TournRegistrationView`` + ``on_raw_reaction_add`` pair — the
  reaction path binds to the kernel reaction seam); the shared
  ``TournamentRegistration.try_join`` guards/copy are verbatim;
* entry fees debit at LAUNCH, not at join (the shipped
  ``_launch_tournament`` loop: per-player ``enter_tournament`` calls,
  a broke player is silently skipped — ``InsufficientFundsError:
  continue``);
* rounds are solo hands vs the dealer played for CHIPS (start 1000,
  flat 200 per round, floor 0 — ``TOURN_START_CHIPS`` /
  ``TOURN_BET_PER_ROUND`` / ``_finish_round``'s ``max(0, …)``), the
  wallet never moves until the champion payout.

DELIBERATE DEVIATIONS (ledgered in
docs/ideas/blackjack-remaining-surface-2026-07-10.md item 3):

* rounds run as per-entrant BUTTON views in the tournament's home
  channel (the solo-table seam) instead of private per-player channels
  ("BJ Tournament" category) — the rps home-channel precedent;
* the autostart timer (``duration_mins``) is not carried (time-driven
  class); `!bjstart` is the start path — the shipped command already
  started a pending tournament at any moment;
* a natural at deal is NOT auto-resolved — Stand reveals and settles it
  through the same table (the shipped tournament-round natural shape is
  unpinned by any golden).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from sb.domain.blackjack import engine as bj
from sb.domain.blackjack.ops import TOURN_BET_PER_ROUND, TOURN_START_CHIPS

logger = logging.getLogger("sb.domain.blackjack.tournament")

__all__ = [
    "DEFAULT_DURATION_MINS",
    "DEFAULT_ROUNDS",
    "FREE_TOURNAMENT_REWARD",
    "REGISTRATION_EMOJI",
    "TournPlayer",
    "TournamentState",
    "all_done",
    "deal_round",
    "end_tournament",
    "get_state",
    "hand_view",
    "ranking",
    "register_player",
    "register_reaction_signup",
    "reset_tournaments_for_tests",
    "round_move",
    "set_tournament_rng_for_tests",
    "state_or_none",
]

#: shipped constants, verbatim (blackjack_cog.py defaults + the shipped
#: payout call's free_reward — views/blackjack/tournament_views.py).
REGISTRATION_EMOJI = "✅"
DEFAULT_ROUNDS = 5
DEFAULT_DURATION_MINS = 5
FREE_TOURNAMENT_REWARD = 200

# None ⇒ the GLOBAL random stream (the parity posture — ops.py's rule).
_rng: random.Random | None = None


def set_tournament_rng_for_tests(rng: random.Random | None) -> None:
    global _rng
    _rng = rng


@dataclass
class TournPlayer:
    """The shipped ``_TournPlayerState``: chips/rounds bookkeeping plus
    the current round's live hand."""
    user_id: int
    rounds_left: int
    chips: int = TOURN_START_CHIPS
    done: bool = False
    round_no: int = 0
    hand: dict | None = None          # {"deck": [...], "player": [...], "dealer": [...]}
    message_key: str | None = None


@dataclass
class TournamentState:
    guild_id: int
    channel_id: int
    entry_fee: int = 0
    rounds: int = DEFAULT_ROUNDS
    duration_mins: int = DEFAULT_DURATION_MINS
    started: bool = False
    reg_message_id: int | None = None
    players: list[int] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)
    entrants: dict[str, TournPlayer] = field(default_factory=dict)
    results: dict[str, int] = field(default_factory=dict)
    settled: bool = False   # results render fired (in-memory check-and-set
                            # twin of the payout op's flag-row guard — two
                            # racing final stands render ONE results embed;
                            # the #133 review's cosmetic race)

    @property
    def pot(self) -> int:
        """The shipped ``TournamentRegistration.pot`` property."""
        return int(self.entry_fee) * len(self.players)


_TOURNAMENTS: dict[int, TournamentState] = {}


def state_or_none(guild_id: int) -> TournamentState | None:
    return _TOURNAMENTS.get(int(guild_id))


def get_state(guild_id: int) -> TournamentState:
    return _TOURNAMENTS.setdefault(int(guild_id),
                                   TournamentState(guild_id=int(guild_id),
                                                   channel_id=0))


def reset_tournaments_for_tests() -> None:
    _TOURNAMENTS.clear()


def end_tournament(guild_id: int) -> None:
    """Drop the in-memory state (the shipped ``_tournaments.pop``)."""
    _TOURNAMENTS.pop(int(guild_id), None)


# --- sign-up (button + reaction, one body) ------------------------------------------


async def register_player(guild_id: int, user_id: int, *,
                          display_name: str | None = None) -> tuple[bool, str]:
    """The shipped ``TournamentRegistration.try_join`` body, headless —
    guards and copy verbatim. NO fee debit here: the shipped flow
    collects fees at launch (P0-1 moved collection out of this shared
    helper into ``enter_tournament``, called by ``_launch_tournament``);
    the balance check is a read-only gate."""
    state = _TOURNAMENTS.get(int(guild_id))
    if state is None or state.started:
        return False, "The tournament has already started."
    uid = int(user_id)
    if uid in state.players:
        return False, "You're already registered!"
    fee = int(state.entry_fee or 0)
    if fee > 0:
        from sb.domain.economy.store import get_coins

        bal = await get_coins(uid, int(guild_id))
        if bal < fee:
            # shipped utils/tournaments.py copy, verbatim
            return False, f"❌ Need **{fee}** 🪙 to enter (you have {bal})."
    state.players.append(uid)
    if display_name:
        state.names[str(uid)] = str(display_name)
    # shipped utils/tournaments.py success copy, verbatim
    return True, f"✅ Registered! ({len(state.players)} player(s) so far)"


async def _on_reaction(event: object) -> None:
    """The shipped ``on_raw_reaction_add`` sign-up path on the kernel
    reaction seam: a ✅ on the live registration message registers the
    reactor (silent — the shipped listener never replied; the bot-reactor
    guard lives in the feed)."""
    if not getattr(event, "added", False):
        return
    if str(getattr(event, "emoji", "")) != REGISTRATION_EMOJI:
        return
    state = _TOURNAMENTS.get(int(getattr(event, "guild_id", 0) or 0))
    if state is None or state.started or state.reg_message_id is None:
        return
    if int(getattr(event, "message_id", 0) or 0) != state.reg_message_id:
        return
    member = getattr(event, "member", None)
    name = (getattr(member, "display_name", None)
            or getattr(member, "name", None))
    ok, _detail = await register_player(
        state.guild_id, int(getattr(event, "user_id", 0) or 0),
        display_name=str(name) if name else None)
    if ok:
        logger.info("blackjack tournament: reaction sign-up user=%s "
                    "guild=%s (%d registered)", getattr(event, "user_id", 0),
                    state.guild_id, len(state.players))


def register_reaction_signup() -> None:
    """Bind the sign-up consumer to the kernel reaction seam. Registered
    at MODULE IMPORT + ENSURE_REFS (declaring IS reserving); idempotent."""
    from sb.kernel.interaction.reactions import register_reaction_consumer

    register_reaction_consumer("blackjack.tournament_signup", _on_reaction)


# --- rounds (chips-space solo hands — the wallet never moves here) --------------------


def hand_view(entrant: TournPlayer, *, reveal: bool) -> dict:
    """Deck-free render view of the entrant's current hand + chip state."""
    hand = entrant.hand or {"player": [], "dealer": []}
    return {
        "uid": entrant.user_id,
        "player": [str(c) for c in hand["player"]],
        "player_value": bj.hand_value(hand["player"]),
        "dealer": (list(hand["dealer"]) if reveal
                   else [hand["dealer"][0], "?"]),
        "dealer_value": (bj.hand_value(hand["dealer"]) if reveal else None),
        "chips": entrant.chips,
        "rounds_left": entrant.rounds_left,
        "round_no": entrant.round_no,
        "rounds": None,
    }


def deal_round(state: TournamentState, user_id: int) -> dict:
    """Deal the entrant's next round (the shipped ``_start_tourn_round``
    fresh-hand deal). Returns the render view."""
    entrant = state.entrants[str(int(user_id))]
    deck = bj.new_deck(_rng)
    entrant.hand = {"deck": deck, "player": [deck.pop(), deck.pop()],
                    "dealer": [deck.pop(), deck.pop()]}
    entrant.round_no += 1
    return hand_view(entrant, reveal=False)


def _resolve_round(hand: dict) -> tuple[str, int]:
    """The shipped settle table in CHIPS space: effective bet is the flat
    ``TOURN_BET_PER_ROUND`` (never free — chips floor at 0 instead)."""
    bet = TOURN_BET_PER_ROUND
    pv = bj.hand_value(hand["player"])
    dv = bj.hand_value(hand["dealer"])
    if bj.is_blackjack(hand["player"]):
        return "🎉 Blackjack!", int(bet * 1.5)
    if dv > 21:
        return "🎉 Dealer busts — you win!", bet
    if pv > dv:
        return "🎉 You win!", bet
    if pv == dv:
        return "🤝 Push — tie.", 0
    return "😞 Dealer wins.", -bet


def _finish_round(state: TournamentState, entrant: TournPlayer,
                  result: str, delta: int) -> dict:
    """The shipped ``_finish_round`` bookkeeping: chip floor, round
    decrement, done ⇒ results row. Returns the terminal-stage payload."""
    entrant.chips = max(0, entrant.chips + delta)
    entrant.rounds_left -= 1
    payload = {**hand_view(entrant, reveal=True), "result": result,
               "delta": delta, "terminal": True}
    if entrant.rounds_left <= 0:
        entrant.done = True
        state.results[str(entrant.user_id)] = entrant.chips
        payload["player_done"] = True
    entrant.hand = None
    return payload


def round_move(state: TournamentState, user_id: int, action: str) -> dict:
    """One Hit/Stand click on the entrant's live tournament hand. Pure
    in-memory; returns a stage mapping the handler renders:

    ``{"stage": "expired" | "not_yours" | "hand" | "round_done", ...}``
    (``round_done`` payloads carry ``player_done`` when the entrant just
    finished their last round)."""
    entrant = state.entrants.get(str(int(user_id)))
    if entrant is None:
        return {"stage": "not_yours"}
    if entrant.done or entrant.hand is None:
        return {"stage": "expired"}
    hand = entrant.hand
    if action == "hit":
        hand["player"].append(hand["deck"].pop())
        if bj.hand_value(hand["player"]) > 21:
            return {"stage": "round_done",
                    **_finish_round(state, entrant, "💥 Bust — you lose!",
                                    -TOURN_BET_PER_ROUND)}
        return {"stage": "hand", **hand_view(entrant, reveal=False),
                "terminal": False}
    if action == "stand":
        bj.dealer_play(hand["deck"], hand["dealer"])
        result, delta = _resolve_round(hand)
        return {"stage": "round_done",
                **_finish_round(state, entrant, result, delta)}
    return {"stage": "expired"}


def all_done(state: TournamentState) -> bool:
    """The shipped ``_check_tourn_done`` completion guard."""
    return len(state.results) >= len(state.entrants) and bool(state.entrants)


def ranking(state: TournamentState) -> list[tuple[int, int]]:
    """The shipped results ranking: (user_id, chips) sorted by chips desc."""
    return sorted(((int(uid), int(chips))
                   for uid, chips in state.results.items()),
                  key=lambda pair: pair[1], reverse=True)


register_reaction_signup()
