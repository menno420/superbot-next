"""Deathmatch K7 lanes (band 6) — the shipped duel flow: challenge →
Accept/Decline on the challenge card → alternating Attack/Defend g1
session components → the finishing move records the W/L pair atomically
and deletes the row. No wager — the shipped deathmatch moves no money.

* PvP stats write ONLY for player-vs-player duels; bot duels stay off
  the leaderboard (the shipped PR-6 anti-farming rule).
* Both Attack and Defend END the turn (the shipped ``_resolve`` swap).
* Turn timeout (DEATHMATCH_TURN_TIMEOUT setting) is declared; the
  live-adapter duel view enforces it (the shipped on_timeout
  win-by-default) — stale duel rows fall to games:session_gc meanwhile.
* Equipment tilt rides the deferred equipment/wear system (D-0043) —
  fighters duel at the shipped bare baseline.

D-0042-REVIEW NOTE (the parity flip, 2026-07-12): the pre-accept
challenge is PROCESS MEMORY, never a checkpoint row. The shipped
``_ChallengeView`` (cogs/deathmatch_cog.py, ``timeout=30.0``) kept the
pending challenge entirely in the view object — ``active_duels`` gains
its entry in ``btn_accept`` — so ``!deathmatch @user`` wrote NO row,
and goldens/deathmatch/sweep_dm_challenge pins that rowless db_delta.
The D-0042 g1 recipe's pending-challenge checkpoint (the earlier shape
here) was a substrate deviation that could not survive the flip (the
moderation-#163 rule: a design deviation on a golden-exercised surface
reshapes to shipped semantics). Challenger/target now ride the
session-view binding's args (sb/kernel/panels/engine._mint_ephemeral —
the in-memory ``_ChallengeView`` analog, same restart/timeout loss
posture as shipped) and the duel row is BORN AT ACCEPT (the shipped
``btn_accept`` construction site) — settle-once row-consumption from
accept onward (D-0045) is unchanged.

Checkpoint rows (game_state, SESSION):
* pvp duel — (guild, challenger, channel, "deathmatch") (DuelState blob),
  minted at accept.
* bot duel — (guild, player, 0, "deathmatch_bot").
"""

from __future__ import annotations

from sb.domain.deathmatch import core
from sb.domain.deathmatch import store as dm_store
from sb.domain.games import session as games_session
from sb.domain.games import store as games_store
from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.refs import WorkflowRef, is_registered, workflow

__all__ = [
    "BOT_SUBSYSTEM",
    "PVP_SUBSYSTEM",
    "ensure_ops_refs",
    "register_ops",
]

PVP_SUBSYSTEM = "deathmatch"
BOT_SUBSYSTEM = "deathmatch_bot"
STATE_VERSION = 1
BOT_ID = 0  # the bot fighter's pseudo-id inside a bot-duel blob


def _ids(ctx: WorkflowContext) -> tuple[int, int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0), int(ctx.clock().timestamp()))


def _components(session_id: str, *actions: str) -> list[str]:
    return [games_session.mint_custom_id("deathmatch", session_id, a)
            for a in actions]


def _duel_lines(duel: core.DuelState) -> str:
    return (f"<@{duel.player1}> — {max(duel.player1_hp, 0)}/"
            f"{duel.player1_max_hp} HP\n"
            f"<@{duel.player2}> — {max(duel.player2_hp, 0)}/"
            f"{duel.player2_max_hp} HP")


async def _refuse_if_fighting(conn, gid: int, *fighters: int) -> None:
    """The shipped either-already-in-a-duel check over the ACTIVE duel
    rows (shipped ``active_duels`` held only accepted duels — a pending
    challenge was invisible to the guard; the accept op re-checks)."""
    for row in await games_store.list_active(PVP_SUBSYSTEM, guild_id=gid,
                                             conn=conn):
        state = row["state"]
        in_duel = {int(state.get("p1", 0)), int(state.get("p2", 0))}
        if in_duel & set(fighters):
            raise ValidatorError(
                "Either you or the opponent is already in a duel.")


@workflow("deathmatch.record_challenge")
async def _record_challenge(conn, ctx: WorkflowContext) -> LegOutcome:
    """!deathmatch @user — validate + guard ONLY; NO row (the module
    docstring's D-0042-review note: the shipped ``_ChallengeView`` kept
    the pre-accept challenge in memory, and sweep_dm_challenge pins the
    rowless db_delta). Accept/Decline ride the challenge card's
    session-view binding, which carries challenger/target in its args."""
    uid, gid, _now = _ids(ctx)
    target = int(ctx.params.get("target_id") or 0)
    if not target:
        raise ValidatorError(
            "Couldn't find the user. Please mention a valid member.")
    if target == uid:
        raise ValidatorError("You cannot challenge yourself!")
    await _refuse_if_fighting(conn, gid, uid, target)
    return LegOutcome(
        step=StepResult(uid, "challenge", True), before={},
        after={"challenger": uid, "target": target,
               "message": f"⚔️ <@{uid}> has challenged <@{target}> to a "
                          f"duel!\n\nPress **Accept** or **Decline** "
                          f"below."})


@workflow("deathmatch.record_accept")
async def _record_accept(conn, ctx: WorkflowContext) -> LegOutcome:
    """Only the challenged player may accept (shipped invoker lock);
    the duel row is BORN here (the shipped ``btn_accept`` construction
    site) — challenger/target arrive from the session binding's args."""
    uid, gid, now = _ids(ctx)
    challenger = int(ctx.params.get("challenger") or 0)
    target = int(ctx.params.get("target") or 0)
    cid = int(ctx.params.get("channel_id") or 0)
    if not challenger or not target:
        raise ValidatorError("This challenge has expired.")
    if uid != target:
        raise ValidatorError("This challenge isn't for you.")
    # accept-time re-check (replaces the retired pending-row consumption):
    # a fighter who entered another duel since the card was posted is
    # refused, and a double-accept lands on the guard via the row the
    # first click created.
    await _refuse_if_fighting(conn, gid, challenger, target)
    duel = core.DuelState(player1=challenger, player2=uid)
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=challenger, channel_id=cid,
        subsystem=PVP_SUBSYSTEM, state=duel.to_state(),
        version=STATE_VERSION, now=now)
    sid = games_session.mint_session_id(gid, challenger, cid)
    return LegOutcome(
        step=StepResult(uid, "accept", True), before={},
        after={"session_id": sid,
               "components": _components(sid, "attack", "defend"),
               "message": f"⚔️ **Deathmatch!**\n\n{_duel_lines(duel)}\n\n"
                          f"It's <@{duel.turn}>'s turn — **Attack** or "
                          f"**Defend**."})


@workflow("deathmatch.record_decline")
async def _record_decline(conn, ctx: WorkflowContext) -> LegOutcome:
    """Decline consumes nothing durable — the pending challenge lives in
    the session binding, and the card's expire tears the binding down
    (the shipped ``btn_decline`` + ``view.stop()``)."""
    uid, _gid, _now = _ids(ctx)
    target = int(ctx.params.get("target") or 0)
    if not target:
        raise ValidatorError("This challenge has expired.")
    if uid != target:
        raise ValidatorError("This challenge isn't for you.")
    return LegOutcome(
        step=StepResult(uid, "decline", True), before={},
        after={"message": f"<@{uid}> declined the duel.",
               "terminal": True})


async def _load_duel(conn, gid: int, sid: str, subsystem: str):
    parsed = games_session.parse_session_id(sid)
    if parsed is None:
        raise ValidatorError("This duel has ended.")
    _, owner, cid = parsed
    state = await games_store.fetch_checkpoint(
        gid, owner, cid, subsystem, conn=conn)
    if state is None:
        raise ValidatorError("This duel has ended.")
    return owner, cid, core.DuelState.from_state(state)


def _apply_move(duel: core.DuelState, actor_id: int,
                action: str) -> str:
    """One move (shipped btn_attack/btn_defend + _resolve turn swap)."""
    opponent = duel.opponent_of(actor_id)
    if action == "attack":
        damage, critical = duel.attack(actor_id, opponent)
        text = f"**<@{actor_id}>** attacks for **{damage} damage**!"
        if critical:
            text += " ⚡ **Critical Hit!**"
    else:
        duel.defend(actor_id)
        text = f"🛡️ **<@{actor_id}>** takes a defensive stance!"
    duel.turn = opponent
    return text


@workflow("deathmatch.record_move")
async def _record_move(conn, ctx: WorkflowContext) -> LegOutcome:
    """One PvP move; the finishing blow settles stats + deletes the row
    in the SAME txn (the shipped settle-once claim = row consumption)."""
    uid, gid, now = _ids(ctx)
    sid = str(ctx.params.get("session_id") or "")
    action = str(ctx.params.get("session_action")
                 or ctx.params.get("action") or "")
    if action not in ("attack", "defend"):
        raise ValidatorError("Pick **Attack** or **Defend**.")
    owner, cid, duel = await _load_duel(conn, gid, sid, PVP_SUBSYSTEM)
    if uid not in (duel.player1, duel.player2):
        raise ValidatorError("This duel isn't yours.")
    if uid != duel.turn:
        raise ValidatorError("It's not your turn!")
    text = _apply_move(duel, uid, action)
    winner = loser = None
    if duel.player1_hp <= 0:
        winner, loser = duel.player2, duel.player1
    elif duel.player2_hp <= 0:
        winner, loser = duel.player1, duel.player2
    if winner:
        duel.is_over = True
        await dm_store.record_result(conn, winner_id=winner,
                                     loser_id=loser, guild_id=gid)
        await games_store.delete_checkpoint(
            conn, guild_id=gid, user_id=owner, channel_id=cid,
            subsystem=PVP_SUBSYSTEM)
        return LegOutcome(
            step=StepResult(uid, "move", True), before={},
            after={"terminal": True,
                   "message": f"{text}\n\n{_duel_lines(duel)}\n\n"
                              f"🏆 <@{winner}> wins!"})
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=owner, channel_id=cid,
        subsystem=PVP_SUBSYSTEM, state=duel.to_state(),
        version=STATE_VERSION, now=now)
    return LegOutcome(
        step=StepResult(uid, "move", True), before={},
        after={"session_id": sid,
               "components": _components(sid, "attack", "defend"),
               "message": f"{text}\n\n{_duel_lines(duel)}\n\n"
                          f"It's <@{duel.turn}>'s turn."})


@workflow("deathmatch.record_bot_start")
async def _record_bot_start(conn, ctx: WorkflowContext) -> LegOutcome:
    """Fight Bot — an immediate duel vs the bot (results stay off the
    leaderboard, shipped PR-6 rule). One bot duel per (guild, user)."""
    uid, gid, now = _ids(ctx)
    existing = await games_store.fetch_checkpoint(
        gid, uid, 0, BOT_SUBSYSTEM, conn=conn)
    if existing is not None:
        raise ValidatorError(
            "You're already fighting the bot — finish that duel first!")
    duel = core.DuelState(player1=uid, player2=BOT_ID)
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=uid, channel_id=0,
        subsystem=BOT_SUBSYSTEM, state=duel.to_state(),
        version=STATE_VERSION, now=now)
    sid = games_session.mint_session_id(gid, uid, 0)
    return LegOutcome(
        step=StepResult(uid, "bot_start", True), before={},
        after={"session_id": sid,
               "components": _components(sid, "bot_attack", "bot_defend"),
               "message": f"🤖 **Bot duel!**\n\n{_duel_lines(duel)}\n\n"
                          f"Your move — **Attack** or **Defend**."})


@workflow("deathmatch.record_bot_move")
async def _record_bot_move(conn, ctx: WorkflowContext) -> LegOutcome:
    """Player move + the bot's reply move in ONE leg (shipped
    _BotDuelView semantics; pick_bot_action v1 AI)."""
    uid, gid, now = _ids(ctx)
    sid = str(ctx.params.get("session_id") or "")
    action = str(ctx.params.get("session_action")
                 or ctx.params.get("action") or "").removeprefix("bot_")
    if action not in ("attack", "defend"):
        raise ValidatorError("Pick **Attack** or **Defend**.")
    owner, _cid, duel = await _load_duel(conn, gid, sid, BOT_SUBSYSTEM)
    if uid != owner:
        raise ValidatorError("This duel isn't yours.")
    lines = [_apply_move(duel, uid, action)]
    if duel.hp_of(BOT_ID) <= 0:
        await games_store.delete_checkpoint(
            conn, guild_id=gid, user_id=owner, channel_id=0,
            subsystem=BOT_SUBSYSTEM)
        return LegOutcome(
            step=StepResult(uid, "bot_move", True), before={},
            after={"terminal": True,
                   "message": "\n".join(lines) + f"\n\n{_duel_lines(duel)}"
                              f"\n\n🏆 <@{uid}> wins! (Bot duels stay "
                              f"off the leaderboard.)"})
    bot_action = core.pick_bot_action(duel.hp_of(BOT_ID))
    if bot_action == "attack":
        damage, critical = duel.attack(BOT_ID, uid)
        line = f"🤖 The bot attacks for **{damage} damage**!"
        if critical:
            line += " ⚡ **Critical Hit!**"
        lines.append(line)
    else:
        duel.defend(BOT_ID)
        lines.append("🤖 The bot takes a defensive stance!")
    duel.turn = uid
    if duel.hp_of(uid) <= 0:
        await games_store.delete_checkpoint(
            conn, guild_id=gid, user_id=owner, channel_id=0,
            subsystem=BOT_SUBSYSTEM)
        return LegOutcome(
            step=StepResult(uid, "bot_move", True), before={},
            after={"terminal": True,
                   "message": "\n".join(lines) + f"\n\n{_duel_lines(duel)}"
                              f"\n\n🤖 The bot wins! (Bot duels stay off "
                              f"the leaderboard.)"})
    await games_store.upsert_checkpoint(
        conn, guild_id=gid, user_id=owner, channel_id=0,
        subsystem=BOT_SUBSYSTEM, state=duel.to_state(),
        version=STATE_VERSION, now=now)
    return LegOutcome(
        step=StepResult(uid, "bot_move", True), before={},
        after={"session_id": sid,
               "components": _components(sid, "bot_attack", "bot_defend"),
               "message": "\n".join(lines) + f"\n\n{_duel_lines(duel)}\n\n"
                          f"Your move."})


@workflow("deathmatch.erase_subject_stats")
async def _erase_subject_stats(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(ctx.params.get("subject_user_id")
              or getattr(ctx.actor, "user_id", 0) or 0)
    deleted = await dm_store.erase_subject_stats(conn, user_id=uid)
    return LegOutcome(step=StepResult(uid, "erase", True), before={},
                      after={"rows_deleted": deleted,
                             "disposition": "deleted"})


def _op(op_key: str, verb: str, leg_ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="deathmatch", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb)


CHALLENGE = _op("deathmatch.challenge", "dm_challenge",
                "deathmatch.record_challenge")
ACCEPT = _op("deathmatch.accept", "dm_accepted",
             "deathmatch.record_accept")
DECLINE = _op("deathmatch.decline", "dm_declined",
              "deathmatch.record_decline")
MOVE = _op("deathmatch.move", "dm_move", "deathmatch.record_move")
BOT_START = _op("deathmatch.bot_start", "dm_bot_started",
                "deathmatch.record_bot_start")
BOT_MOVE = _op("deathmatch.bot_move", "dm_bot_move",
               "deathmatch.record_bot_move")

_OPS = (CHALLENGE, ACCEPT, DECLINE, MOVE, BOT_START, BOT_MOVE)

_REF_TABLE = (
    ("deathmatch.record_challenge", _record_challenge),
    ("deathmatch.record_accept", _record_accept),
    ("deathmatch.record_decline", _record_decline),
    ("deathmatch.record_move", _record_move),
    ("deathmatch.record_bot_start", _record_bot_start),
    ("deathmatch.record_bot_move", _record_bot_move),
    ("deathmatch.erase_subject_stats", _erase_subject_stats),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import workflow as _workflow

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
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
