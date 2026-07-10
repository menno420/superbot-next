"""RPS K7 lanes (band 6, subsystem key rps_tournament) — quick-play solo
vs bot, PvP escrow matches (classic mode), and the tournament money legs.

Shipped semantics verbatim (views/rps/* + game_wager_workflow call sites
@7f7628e1): solo win pays the bet (or _FREE_WIN=30 on free play), loss
debits with the overdraft-tolerant floor; PvP stakes escrow at accept
(rps_pvp_escrow rows, reason rps:pvp_escrow), settle to the winner
(rps:pvp_win) or refund on tie (rps:pvp_refund) with row-consumption
settle-once. Tournament rounds/channels are live-adapter orchestration;
the entry/payout money lanes are real.
"""

from __future__ import annotations

import random

from sb.domain.games import session as games_session
from sb.domain.games import store as games_store
from sb.domain.games import wager
from sb.domain.rps import rules
from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, workflow

__all__ = [
    "FREE_WIN",
    "PVP_ESCROW_SUBSYSTEM",
    "PVP_PENDING_SUBSYSTEM",
    "TOURNAMENT_SUBSYSTEM",
    "register_ops",
    "set_rng_for_tests",
]

# shipped constants / subsystem keys verbatim (views/rps/_helpers.py)
FREE_WIN = 30
PVP_PENDING_SUBSYSTEM = "rps_pvp_pending"
PVP_PENDING_VERSION = 1
PVP_ESCROW_SUBSYSTEM = "rps_pvp_escrow"
PVP_ESCROW_VERSION = 1
TOURNAMENT_SUBSYSTEM = "rps_tournament_entry"
TOURNAMENT_VERSION = 1

QUICKPLAY_MODE = "classic"

_rng: random.Random = random.Random()


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def _actor_id(ctx: WorkflowContext) -> int:
    return int(getattr(ctx.actor, "user_id", 0) or 0)


def _now(ctx: WorkflowContext) -> int:
    return int(ctx.clock().timestamp())


def _bet_from(ctx: WorkflowContext) -> int:
    bet = ctx.params.get("bet")
    if bet is None:
        for token in tuple(ctx.params.get("argv", ()) or ()):
            if str(token).lstrip("-").isdigit():
                bet = int(token)
                break
    bet = int(bet or 0)
    if bet < 0:
        raise ValidatorError("Bet must be 0 or a positive number.")
    return bet


def _move_from(ctx: WorkflowContext) -> str:
    values = tuple(ctx.params.get("values", ()) or ())
    raw = str(ctx.params.get("session_action") or ctx.params.get("move")
              or (values[0] if values else "")).removeprefix("move_")
    move = rules.normalize_move(raw, QUICKPLAY_MODE)
    if move is None:
        raise ValidatorError(
            f"Valid moves: {', '.join(rules.GAME_MODES[QUICKPLAY_MODE])}.")
    return move


_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}


# --- quick-play solo (one leg: pick, resolve, settle) ---------------------------------


@workflow("rps.record_solo_play")
async def _record_solo_play(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    move = _move_from(ctx)
    bet = _bet_from(ctx)
    bot_move = _rng.choice(rules.GAME_MODES[QUICKPLAY_MODE])
    outcome = rules.determine_winner(move, bot_move, QUICKPLAY_MODE)
    changes: list[tuple[int, int, int, str]] = []
    if outcome == 1:
        payout = bet if bet else FREE_WIN
        balance = await wager.credit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=payout,
            reason="rps:solo_win", actor_id=uid)
        changes.append((uid, payout, balance, "rps:solo_win"))
        text = f"🎉 You win! +{payout} 🪙"
    elif outcome == 2 and bet:
        actual, balance = await wager.debit_floor_in_txn(
            conn, guild_id=gid, user_id=uid, amount=bet,
            reason="rps:solo_loss", actor_id=uid)
        if actual:
            changes.append((uid, actual, balance, "rps:solo_loss"))
        text = f"😞 You lose! -{bet} 🪙"
    elif outcome == 2:
        text = "😞 You lose!"
    else:
        text = "🤝 Tie!"
    # stats row (slice 4): the shipped _bot_matches.update_player_stats
    # site — quick play vs the bot IS the shipped bot match. Display
    # name captured at game time when the feed provides it; mention
    # fallback headless.
    from sb.domain.rps import stats as rps_stats

    await rps_stats.record_result(
        conn, user_id=uid, guild_id=gid,
        name=str(ctx.params.get("_display_name") or f"<@{uid}>"),
        result={1: "win", 2: "loss"}.get(outcome, "tie"))
    ctx.params["_balance_changes"] = changes
    after = {"move": move, "bot_move": bot_move, "result": text,
             "emoji": _EMOJI.get(move, ""),
             "bot_emoji": _EMOJI.get(bot_move, ""), "terminal": True}
    return LegOutcome(step=StepResult(uid, "solo_play", True), before={},
                      after=after,
                      # the success copy line — quick-play picker clicks
                      # dispatch this op directly (no handler composes a
                      # Reply), so the leg speaks its own result.
                      user_message=(f"{after['emoji']} vs "
                                    f"{after['bot_emoji']} (bot)\n{text}"))


# --- PvP (challenge → accept escrow → simultaneous throws → settle) --------------------


@workflow("rps.record_pvp_challenge")
async def _record_pvp_challenge(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    cid = int(ctx.params.get("channel_id") or 0)
    target = int(ctx.params["target_id"])
    bet = _bet_from(ctx)
    if target == uid:
        raise ValidatorError("You can't challenge yourself.")
    existing = await games_store.fetch_checkpoint(
        gid, uid, cid, PVP_PENDING_SUBSYSTEM, conn=conn)
    if existing is not None:
        raise ValidatorError("You already have a pending RPS challenge "
                             "in this channel.")
    if bet > 0:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        if bet > held:
            raise ValidatorError(f"❌ You only have **{held}** 🪙.")
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=uid, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM,
        state={"peer": target, "bet": bet, "moves": {}},
        version=PVP_PENDING_VERSION, now=_now(ctx))
    ctx.params["_balance_changes"] = []
    sid = games_session.mint_session_id(gid, uid, cid)
    after = {"challenger": uid, "target": target, "bet": bet,
             "session_id": sid,
             "components": [games_session.mint_custom_id(
                 "rps_tournament", sid, a) for a in ("accept", "decline")]}
    return LegOutcome(step=StepResult(uid, "pvp_challenge", True),
                      before={}, after=after)


async def _load_pending(conn, gid: int, sid: str):
    parsed = games_session.parse_session_id(sid)
    if parsed is None or parsed[0] != gid:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    _, challenger, cid = parsed
    state = await games_store.fetch_checkpoint(
        gid, challenger, cid, PVP_PENDING_SUBSYSTEM, conn=conn)
    if state is None:
        raise ValidatorError(games_session.EXPIRED_MESSAGE)
    return challenger, cid, state


@workflow("rps.record_pvp_accept")
async def _record_pvp_accept(conn, ctx: WorkflowContext) -> LegOutcome:
    """Opponent accepts: escrow both stakes (D1) and open the match —
    moves stay on the SAME pending row (state.accepted=True)."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    sid = str(ctx.params.get("session_id") or "")
    challenger, cid, state = await _load_pending(conn, gid, sid)
    if uid != int(state.get("peer", 0)):
        raise ValidatorError("This challenge isn't for you.")
    if state.get("accepted"):
        raise ValidatorError("Already accepted — pick your move!")
    bet = int(state.get("bet", 0))
    escrow = await wager.escrow_pvp_in_txn(
        conn, guild_id=gid, channel_id=cid,
        subsystem=PVP_ESCROW_SUBSYSTEM, version=PVP_ESCROW_VERSION,
        p1_id=challenger, p2_id=uid, stake=bet, reason="rps:pvp_escrow",
        now=_now(ctx))
    state["accepted"] = True
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=challenger, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM, state=state,
        version=PVP_PENDING_VERSION, now=_now(ctx))
    ctx.params["_balance_changes"] = [
        (u, d, b, "rps:pvp_escrow") for (u, d, b) in escrow.balance_changes]
    moves = [games_session.mint_custom_id("rps_tournament", sid,
                                          f"move_{m}")
             for m in rules.GAME_MODES[QUICKPLAY_MODE]]
    return LegOutcome(step=StepResult(uid, "pvp_accept", True), before={},
                      after={"bet": bet, "session_id": sid,
                             "components": moves, "terminal": False})


@workflow("rps.record_pvp_decline")
async def _record_pvp_decline(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    sid = str(ctx.params.get("session_id") or "")
    challenger, cid, state = await _load_pending(conn, gid, sid)
    if uid != int(state.get("peer", 0)):
        raise ValidatorError("This challenge isn't for you.")
    if state.get("accepted"):
        raise ValidatorError("The match already started — play it out.")
    await games_store.delete_checkpoint(
        conn, guild_id=gid, user_id=challenger, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM)
    ctx.params["_balance_changes"] = []
    return LegOutcome(step=StepResult(uid, "pvp_decline", True), before={},
                      after={"declined": True, "terminal": True})


@workflow("rps.record_pvp_move")
async def _record_pvp_move(conn, ctx: WorkflowContext) -> LegOutcome:
    """A player's throw. Moves are hidden until both are in (shipped);
    the second throw settles pot/refund in the SAME txn."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    sid = str(ctx.params.get("session_id") or "")
    challenger, cid, state = await _load_pending(conn, gid, sid)
    p1, p2 = challenger, int(state.get("peer", 0))
    if uid not in (p1, p2):
        # shipped views/rps/pvp_play.py interaction_check copy
        raise ValidatorError("You're not part of this match.")
    if not state.get("accepted"):
        raise ValidatorError("The challenge hasn't been accepted yet.")
    move = _move_from(ctx)
    moves: dict = state.setdefault("moves", {})
    if str(uid) in moves:
        raise ValidatorError("You already picked!")   # shipped copy
    moves[str(uid)] = move
    if len(moves) < 2:
        await games_store.upsert_checkpoint(
            conn, guild_id=gid, user_id=p1, channel_id=cid,
            subsystem=PVP_PENDING_SUBSYSTEM, state=state,
            version=PVP_PENDING_VERSION, now=_now(ctx))
        ctx.params["_balance_changes"] = []
        return LegOutcome(step=StepResult(uid, "pvp_move", True),
                          before={},
                          after={"waiting": True, "terminal": False})
    m1, m2 = moves[str(p1)], moves[str(p2)]
    outcome = rules.determine_winner(m1, m2, QUICKPLAY_MODE)
    bet = int(state.get("bet", 0))
    changes: list[tuple[int, int, int, str]] = []
    if outcome == 0:
        winner = None
        # the shipped result line (views/rps/pvp_play.py) — the escrow IS
        # refunded below; net coins exchanged: zero.
        text = "🤝 Tie! No coins exchanged."
        if bet > 0:
            refund = await wager.refund_pvp_in_txn(
                conn, guild_id=gid, channel_id=cid,
                subsystem=PVP_ESCROW_SUBSYSTEM, p1_id=p1, p2_id=p2,
                reason="rps:pvp_refund")
            changes = [(u, d, b, "rps:pvp_refund")
                       for (u, d, b) in refund.balance_changes]
    else:
        winner = p1 if outcome == 1 else p2
        text = f"🎉 <@{winner}> wins!"      # shipped pvp_play.py copy
        if bet > 0:
            settle = await wager.settle_pvp_in_txn(
                conn, guild_id=gid, channel_id=cid,
                subsystem=PVP_ESCROW_SUBSYSTEM, p1_id=p1, p2_id=p2,
                winner_id=winner, reason="rps:pvp_win")
            changes = [(u, d, b, "rps:pvp_win")
                       for (u, d, b) in settle.balance_changes]
    await games_store.delete_checkpoint(
        conn, guild_id=gid, user_id=p1, channel_id=cid,
        subsystem=PVP_PENDING_SUBSYSTEM)
    ctx.params["_balance_changes"] = changes
    return LegOutcome(step=StepResult(uid, "pvp_move", True), before={},
                      after={"result": text, "winner": winner,
                             "challenger": p1, "peer": p2,
                             "moves": {str(p1): m1, str(p2): m2},
                             "terminal": True})


# --- tournament money legs ---------------------------------------------------------------


@workflow("rps.record_tournament_open")
async def _record_tournament_open(conn, ctx: WorkflowContext) -> LegOutcome:
    """Registration opens: write the shipped ACTIVE_TOURNAMENT runtime flag
    (guild_settings {key: active_tournament, value: rps} — the
    tournament_state_service.set_active row the rpsregister golden pins).
    The registration window itself is in-memory orchestration state
    (sb/domain/rps/tournament.py), exactly the shipped cog's posture."""
    from sb.domain.games import tournament_flag

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    await tournament_flag.set_active(conn, guild_id=gid, game="rps")
    ctx.params["_balance_changes"] = []
    return LegOutcome(step=StepResult(uid, "tournament_open", True),
                      before={}, after={"flag": "rps"})


@workflow("rps.record_tournament_abort")
async def _record_tournament_abort(conn, ctx: WorkflowContext) -> LegOutcome:
    """Registration closed with too few players (the shipped
    ``if len(self.players) < 2: tournament_state_service.clear_active``):
    clear the runtime flag and refund every entry row atomically."""
    from sb.domain.games import tournament_flag

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    await tournament_flag.clear_active(conn, guild_id=gid)
    rows = await games_store.lock_rows_for_settlement(
        conn, guild_id=gid, subsystem=TOURNAMENT_SUBSYSTEM)
    changes: list[tuple[int, int, int, str]] = []
    for row in rows:
        stake = int((row.get("state") or {}).get("bet", 0) or 0)
        entrant = int(row["user_id"])
        await games_store.delete_checkpoint_by_id(conn, row_id=row["id"])
        if stake > 0:
            balance = await wager.credit_in_txn(
                conn, guild_id=gid, user_id=entrant, amount=stake,
                reason="rps:entry_refund", actor_id=entrant)
            changes.append((entrant, stake, balance, "rps:entry_refund"))
    ctx.params["_balance_changes"] = changes
    return LegOutcome(step=StepResult(uid, "tournament_abort", True),
                      before={}, after={"refunded": len(changes)})


@workflow("rps.record_tournament_enter")
async def _record_tournament_enter(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    fee = int(ctx.params.get("fee", 0) or 0)
    balance = await wager.enter_tournament_in_txn(
        conn, guild_id=gid, user_id=uid, channel_id=0,
        subsystem=TOURNAMENT_SUBSYSTEM, version=TOURNAMENT_VERSION,
        fee=fee, reason="rps:entry_fee", now=_now(ctx))
    ctx.params["_balance_changes"] = (
        [(uid, -fee, balance, "rps:entry_fee")] if fee > 0 else [])
    return LegOutcome(step=StepResult(uid, "tournament_enter", True),
                      before={}, after={"fee": fee, "balance": balance})


@workflow("rps.record_tournament_result")
async def _record_tournament_result(conn, ctx: WorkflowContext) -> LegOutcome:
    """One completed tournament match: the shipped update_player_stats
    site (winner +1 win, loser +1 loss) — money never moves here (the pot
    was collected at entry; the champion leg pays it)."""
    from sb.domain.rps import stats as rps_stats

    gid = int(ctx.guild_id or 0)
    winner = int(ctx.params["winner_id"])
    loser = int(ctx.params["loser_id"])
    names = dict(ctx.params.get("names") or {})
    await rps_stats.record_result(
        conn, user_id=winner, guild_id=gid,
        name=str(names.get(str(winner)) or f"<@{winner}>"), result="win")
    await rps_stats.record_result(
        conn, user_id=loser, guild_id=gid,
        name=str(names.get(str(loser)) or f"<@{loser}>"), result="loss")
    ctx.params["_balance_changes"] = []
    return LegOutcome(step=StepResult(winner, "tournament_result", True),
                      before={}, after={"winner": winner, "loser": loser})


@workflow("rps.record_tournament_payout")
async def _record_tournament_payout(conn, ctx: WorkflowContext) -> LegOutcome:
    """The champion settle — shipped call site verbatim
    (reason ``rps:tournament_win``, ``free_reward=100`` consolation on free
    tournaments under ``rps:tournament_free_reward``) + the shipped
    end-of-tournament ``clear_active`` in the SAME txn."""
    from sb.domain.games import tournament_flag

    gid = int(ctx.guild_id or 0)
    winner = ctx.params.get("winner_id")
    winner = int(winner) if winner is not None else None
    settle = await wager.payout_tournament_in_txn(
        conn, guild_id=gid, subsystem=TOURNAMENT_SUBSYSTEM,
        winner_id=winner, reason="rps:tournament_win",
        free_reward=int(ctx.params.get("free_reward", 0) or 0),
        free_reason="rps:tournament_free_reward")
    await tournament_flag.clear_active(conn, guild_id=gid)
    # paid-entry tournaments settle the pot (rps:tournament_win); free ones
    # pay the fixed consolation (rps:tournament_free_reward) — the handler
    # passes the tournament's entry fee so the emitted reason matches the
    # ledger row the wager layer wrote.
    reason = ("rps:tournament_win"
              if int(ctx.params.get("entry_fee", 0) or 0) > 0
              else "rps:tournament_free_reward")
    ctx.params["_balance_changes"] = [
        (u, d, b, reason) for (u, d, b) in settle.balance_changes]
    return LegOutcome(step=StepResult(winner or 0, "tournament_payout",
                                      settle.paid),
                      before={}, after={"paid": settle.paid,
                                        "amount": settle.amount})


# --- op table ----------------------------------------------------------------------------

_BALANCE_EMITS = (
    EventEmitSpec("economy.balance_changed",
                  WorkflowRef("games.balance_payload_0"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec("economy.balance_changed",
                  WorkflowRef("games.balance_payload_1"),
                  DeliveryClass.BEST_EFFORT),
)


def _op(op_key: str, verb: str, leg_ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="rps_tournament", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=_BALANCE_EMITS)


SOLO_PLAY = _op("rps.solo_play", "rps_played", "rps.record_solo_play")
PVP_CHALLENGE = _op("rps.pvp_challenge", "rps_challenge",
                    "rps.record_pvp_challenge")
PVP_ACCEPT = _op("rps.pvp_accept", "rps_pvp_escrowed",
                 "rps.record_pvp_accept")
PVP_DECLINE = _op("rps.pvp_decline", "rps_pvp_declined",
                  "rps.record_pvp_decline")
PVP_MOVE = _op("rps.pvp_move", "rps_pvp_move", "rps.record_pvp_move")
TOURN_OPEN = _op("rps.tournament_open", "tournament_opened",
                 "rps.record_tournament_open")
TOURN_ABORT = _op("rps.tournament_abort", "tournament_aborted",
                  "rps.record_tournament_abort")
TOURN_ENTER = _op("rps.tournament_enter", "tournament_entered",
                  "rps.record_tournament_enter")
TOURN_RESULT = _op("rps.tournament_result", "tournament_match_recorded",
                   "rps.record_tournament_result")
TOURN_PAYOUT = _op("rps.tournament_payout", "tournament_paid",
                   "rps.record_tournament_payout")

_OPS = (SOLO_PLAY, PVP_CHALLENGE, PVP_ACCEPT, PVP_DECLINE, PVP_MOVE,
        TOURN_OPEN, TOURN_ABORT, TOURN_ENTER, TOURN_RESULT, TOURN_PAYOUT)

@workflow("rps.erase_subject_stats")
async def _erase_subject_stats(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.rps import stats as rps_stats

    uid = int(ctx.params.get("subject_user_id")
              or getattr(ctx.actor, "user_id", 0) or 0)
    deleted = await rps_stats.erase_subject_stats(conn, user_id=uid)
    return LegOutcome(step=StepResult(uid, "erase", True), before={},
                      after={"rows_deleted": deleted,
                             "disposition": "deleted"})


_REF_TABLE = (
    ("rps.record_solo_play", _record_solo_play),
    ("rps.erase_subject_stats", _erase_subject_stats),
    ("rps.record_pvp_challenge", _record_pvp_challenge),
    ("rps.record_pvp_accept", _record_pvp_accept),
    ("rps.record_pvp_decline", _record_pvp_decline),
    ("rps.record_pvp_move", _record_pvp_move),
    ("rps.record_tournament_open", _record_tournament_open),
    ("rps.record_tournament_abort", _record_tournament_abort),
    ("rps.record_tournament_enter", _record_tournament_enter),
    ("rps.record_tournament_result", _record_tournament_result),
    ("rps.record_tournament_payout", _record_tournament_payout),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import is_registered, workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered, workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
