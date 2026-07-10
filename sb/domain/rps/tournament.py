"""RPS tournament orchestration (band 6) — the shipped
``RPSTournamentCog`` registration/round state, headless.

Shipped semantics carried verbatim where the cog held them:

* orchestration state is IN-MEMORY per guild (``self.players`` /
  ``self.scores`` / ``self.matches`` / ``self.current_round`` on the cog —
  a restart forfeits the bracket; entry fees are refunded at boot through
  the audited lane, `ESCROW_RECOVERY_SUBSYSTEMS`);
* the registration window is 600 s with the ✅ emoji
  (``registration_timer`` / ``registration_emoji``), sign-up rides BOTH the
  Join button and the reaction (the shipped `_RpsRegistrationView` +
  ``on_reaction_add`` pair — the reaction path binds to the kernel
  reaction seam, sb/kernel/interaction/reactions.py);
* the DB side is exactly the shipped rows: the ACTIVE_TOURNAMENT runtime
  flag (guild_settings) and per-player entry rows written atomically with
  the fee debit (``rps.tournament_enter``, reason ``rps:entry_fee``).

DELIBERATE DEVIATIONS (ledgered in
docs/ideas/rps-tournament-remaining-surface-2026-07-10.md):

* matches run as BUTTON views in the tournament's home channel (the #124
  PvP seam) instead of private match channels + no-prefix message parsing
  — channel provisioning rides the resource-provision port (the counting
  D-0044 posture);
* the 10-minute close is LAZY (checked when `!rpsstart` runs) instead of a
  background sleep task; the 5-minute reminder loop is not carried
  (time-driven class).
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

from sb.domain.rps import rules

logger = logging.getLogger("sb.domain.rps.tournament")

__all__ = [
    "FREE_TOURNAMENT_REWARD",
    "Match",
    "REGISTRATION_EMOJI",
    "REGISTRATION_WINDOW_S",
    "TournamentState",
    "advance_round",
    "end_tournament",
    "get_state",
    "pair_round",
    "record_move",
    "register_player",
    "register_reaction_signup",
    "reset_tournaments_for_tests",
    "start_bracket",
    "state_or_none",
]

#: shipped cog constants, verbatim.
REGISTRATION_EMOJI = "✅"
REGISTRATION_WINDOW_S = 600           # "10 minutes in seconds"
FREE_TOURNAMENT_REWARD = 100          # the shipped payout call's free_reward


@dataclass
class Match:
    match_id: str
    p1: int
    p2: int
    best_of: int
    mode: str
    moves: dict[str, str] = field(default_factory=dict)   # this throw
    scores: dict[str, int] = field(default_factory=dict)  # throws won
    message_key: str | None = None
    done: bool = False
    winner: int | None = None

    @property
    def needed(self) -> int:
        return self.best_of // 2 + 1

    def loser(self) -> int | None:
        if self.winner is None:
            return None
        return self.p2 if self.winner == self.p1 else self.p1


@dataclass
class TournamentState:
    guild_id: int
    channel_id: int
    entry_fee: int = 0
    registration_active: bool = False
    registration_opened_mono: float = 0.0
    registration_message_id: int | None = None
    players: list[int] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)
    active: bool = False                       # bracket running
    game_mode: str = "classic"
    best_of: int = 3
    round_num: int = 0
    current_round: list[int] = field(default_factory=list)
    matches: dict[str, Match] = field(default_factory=dict)
    _match_seq: int = 0

    def registration_window_elapsed(self, *, now_mono: float | None = None) -> bool:
        now = time.monotonic() if now_mono is None else now_mono
        return (now - self.registration_opened_mono) >= REGISTRATION_WINDOW_S

    def open_matches(self) -> list[Match]:
        return [m for m in self.matches.values() if not m.done]


_TOURNAMENTS: dict[int, TournamentState] = {}


def state_or_none(guild_id: int) -> TournamentState | None:
    return _TOURNAMENTS.get(int(guild_id))


def get_state(guild_id: int) -> TournamentState:
    return _TOURNAMENTS.setdefault(int(guild_id),
                                   TournamentState(guild_id=int(guild_id),
                                                   channel_id=0))


def reset_tournaments_for_tests() -> None:
    _TOURNAMENTS.clear()


# --- sign-up (button + reaction, one body) -----------------------------------------


async def register_player(guild_id: int, user_id: int, *,
                          display_name: str | None = None,
                          actor: object | None = None) -> tuple[bool, str]:
    """The shipped ``try_register_player`` body, headless: closed/duplicate
    guards, the entry-fee balance gate, the audited fee debit + entry row
    (``rps.tournament_enter``), then the in-memory roster append.

    Returns ``(ok, detail)`` — detail is the user-facing failure copy on
    the button path; the reaction path stays silent on failure (shipped)."""
    state = _TOURNAMENTS.get(int(guild_id))
    if state is None or not state.registration_active:
        return False, "Registration is not active."
    uid = int(user_id)
    if uid in state.players:
        return False, "You're already registered."
    fee = int(state.entry_fee or 0)
    if fee > 0:
        from sb.domain.economy.store import get_coins

        bal = await get_coins(uid, int(guild_id))
        if bal < fee:
            # shipped _RpsRegistrationView copy, verbatim
            return False, f"❌ Need **{fee}** 🪙 to enter (you have {bal})."
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import WorkflowRef

    if actor is None:
        from sb.kernel.interaction.request import ActorRef

        actor = ActorRef(user_id=uid, is_guild_operator=False,
                         is_bot_owner=False, is_dm=False)
    import uuid

    ctx = WorkflowContext(actor=actor, guild_id=int(guild_id),
                          request_id=f"rps-tournament-join-{uuid.uuid4()}",
                          params={"fee": fee})
    result = await engine.run(WorkflowRef("rps.tournament_enter"), ctx)
    if result.outcome != SUCCESS:
        return False, result.user_message or "Couldn't register you."
    state.players.append(uid)
    if display_name:
        state.names[str(uid)] = str(display_name)
    return True, ""


async def _on_reaction(event: object) -> None:
    """The shipped ``on_reaction_add`` sign-up path on the kernel reaction
    seam: a ✅ on the live registration message registers the reactor
    (silent — the shipped listener never replied)."""
    if not getattr(event, "added", False):
        return
    if str(getattr(event, "emoji", "")) != REGISTRATION_EMOJI:
        return
    state = _TOURNAMENTS.get(int(getattr(event, "guild_id", 0) or 0))
    if state is None or not state.registration_active:
        return
    if state.registration_message_id is None:
        return
    if int(getattr(event, "message_id", 0) or 0) != state.registration_message_id:
        return
    member = getattr(event, "member", None)
    name = (getattr(member, "display_name", None)
            or getattr(member, "name", None))
    ok, _detail = await register_player(
        state.guild_id, int(getattr(event, "user_id", 0) or 0),
        display_name=str(name) if name else None)
    if ok:
        logger.info("rps tournament: reaction sign-up user=%s guild=%s "
                    "(%d registered)", getattr(event, "user_id", 0),
                    state.guild_id, len(state.players))


_consumer_registered = False


def register_reaction_signup() -> None:
    """Bind the sign-up consumer to the kernel reaction seam. Registered at
    MODULE IMPORT + ENSURE_REFS (declaring IS reserving); idempotent."""
    global _consumer_registered
    from sb.kernel.interaction.reactions import register_reaction_consumer

    register_reaction_consumer("rps.tournament_signup", _on_reaction)
    _consumer_registered = True


# --- bracket ------------------------------------------------------------------------


def pair_round(state: TournamentState) -> tuple[list[Match], list[int]]:
    """Pair the surviving players into this round's matches; an odd player
    count gives the last shuffled player a bye. Mutates state.matches."""
    field_players = list(state.current_round)
    byes: list[int] = []
    if len(field_players) % 2 == 1:
        byes.append(field_players.pop())
    new_matches: list[Match] = []
    for i in range(0, len(field_players), 2):
        state._match_seq += 1
        match = Match(match_id=f"r{state.round_num}m{state._match_seq}",
                      p1=field_players[i], p2=field_players[i + 1],
                      best_of=state.best_of, mode=state.game_mode)
        state.matches[match.match_id] = match
        new_matches.append(match)
    return new_matches, byes


def start_bracket(state: TournamentState, *, mode: str, best_of: int,
                  rng: random.Random | None = None) -> tuple[list[Match], list[int]]:
    """The shipped rps_start body after its guards: activate, seed the
    round from the registered players (shuffled), pair the first round."""
    state.active = True
    state.registration_active = False
    state.game_mode = mode
    state.best_of = int(best_of)
    state.round_num = 1
    state.current_round = list(state.players)
    (rng or random).shuffle(state.current_round)
    state.matches.clear()
    return pair_round(state)


def record_move(state: TournamentState, match_id: str, user_id: int,
                move: str) -> dict:
    """One button throw into an open match. Pure in-memory; returns a stage
    mapping the handler renders:

    ``{"stage": "not_yours" | "already_picked" | "waiting" |
       "throw_tie" | "throw_scored" | "match_done", ...}``
    """
    match = state.matches.get(match_id)
    if match is None or match.done:
        return {"stage": "expired"}
    uid = int(user_id)
    if uid not in (match.p1, match.p2):
        return {"stage": "not_yours"}
    if str(uid) in match.moves:
        return {"stage": "already_picked"}
    match.moves[str(uid)] = move
    if len(match.moves) < 2:
        return {"stage": "waiting", "match": match}
    m1 = match.moves[str(match.p1)]
    m2 = match.moves[str(match.p2)]
    outcome = rules.determine_winner(m1, m2, match.mode)
    thrown = dict(match.moves)
    match.moves.clear()
    if outcome == 0:
        return {"stage": "throw_tie", "match": match, "moves": thrown}
    throw_winner = match.p1 if outcome == 1 else match.p2
    key = str(throw_winner)
    match.scores[key] = match.scores.get(key, 0) + 1
    if match.scores[key] >= match.needed:
        match.done = True
        match.winner = throw_winner
        loser = match.loser()
        if loser in state.current_round:
            state.current_round.remove(loser)
        return {"stage": "match_done", "match": match, "moves": thrown,
                "winner": throw_winner, "loser": loser}
    return {"stage": "throw_scored", "match": match, "moves": thrown,
            "throw_winner": throw_winner}


def advance_round(state: TournamentState) -> dict:
    """Called after a match completes: nothing while matches stay open;
    the champion once one player survives; otherwise the next round's
    pairings. Returns ``{"stage": "waiting_matches" | "champion" |
    "next_round", ...}``."""
    if state.open_matches():
        return {"stage": "waiting_matches"}
    if len(state.current_round) <= 1:
        champion = state.current_round[0] if state.current_round else None
        state.active = False
        return {"stage": "champion", "winner": champion}
    state.round_num += 1
    matches, byes = pair_round(state)
    return {"stage": "next_round", "round": state.round_num,
            "matches": matches, "byes": byes}


def end_tournament(guild_id: int) -> None:
    """Drop the in-memory state (the shipped end-of-tournament reset)."""
    _TOURNAMENTS.pop(int(guild_id), None)


register_reaction_signup()
