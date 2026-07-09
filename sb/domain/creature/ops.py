"""Creature K7 lanes (band 6) — the shipped creature_workflow.catch as one
leg (read xp → roll encounter+catch → on success: collection write + xp
award in the SAME txn; a fled creature writes NOTHING), plus the battle
RECORD lane (the interactive PvP battle engine is live-adapter successor
work; results land through this audited lane when it arms)."""

from __future__ import annotations

import random

from sb.domain.creature import catalog, store
from sb.domain.games import xp as game_xp
from sb.domain.xp.levels import level_progress
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

__all__ = ["creature_level_from_xp", "register_ops", "set_rng_for_tests"]

_rng: random.Random = random.Random()


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def creature_level_from_xp(creature_xp: int) -> int:
    """1-based creature level from GAME_CREATURE xp — the shared curve,
    open-ended (no MAX cap, shipped verbatim)."""
    level_index, _, _ = level_progress(max(0, creature_xp))
    return 1 + level_index


@workflow("creature.record_catch")
async def _record_catch(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    now = int(ctx.clock().timestamp())
    rows = await _game_xp_rows(uid, gid, conn)
    creature_xp = rows.get(game_xp.GAME_CREATURE, 0)
    level = creature_level_from_xp(creature_xp)
    encounter = catalog.roll_encounter(_rng)
    if encounter is None:
        raise ValidatorError("🐾 The wilds are quiet — the creature "
                             "catalog is empty.")
    creature = encounter.creature
    if not catalog.attempt_catch(creature, level, _rng):
        ctx.params["_balance_changes"] = []
        ctx.params["_gxp"] = None
        return LegOutcome(
            step=StepResult(uid, "catch", True), before={},
            after={"caught": False, "creature": creature.name,
                   "emoji": creature.emoji, "rarity": creature.rarity,
                   "creature_level": level,
                   "message": f"{creature.emoji} A wild "
                              f"**{creature.name}** ({creature.rarity}) "
                              "appeared… and fled!"})
    collection = await store.get_collection(uid, gid, conn=conn)
    is_new = creature.name not in collection
    await store.record_catch(conn, user_id=uid, guild_id=gid,
                             creature=creature.name, now=now)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_CREATURE,
        action="catch", now=now)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award
    new_note = " ✨ NEW dex entry!" if is_new else ""
    return LegOutcome(
        step=StepResult(uid, "catch", True), before={},
        after={"caught": True, "creature": creature.name,
               "emoji": creature.emoji, "rarity": creature.rarity,
               "is_new": is_new,
               "creature_level": creature_level_from_xp(
                   creature_xp + award.amount),
               "message": f"{creature.emoji} Caught a wild "
                          f"**{creature.name}** "
                          f"({creature.rarity})!{new_note}"})


async def _game_xp_rows(uid: int, gid: int, conn) -> dict[str, int]:
    from sb.domain.games.store import game_xp_rows

    return {str(r["game"]): int(r["xp"])
            for r in await game_xp_rows(uid, gid, conn=conn)}


@workflow("creature.record_battle")
async def _record_battle(conn, ctx: WorkflowContext) -> LegOutcome:
    """The battle-result lane: winner + loser rows + battle_win xp, one
    txn (the interactive battle engine feeds this when it arms)."""
    gid = int(ctx.guild_id or 0)
    now = int(ctx.clock().timestamp())
    winner = int(ctx.params["winner_id"])
    loser = int(ctx.params["loser_id"])
    await store.record_battle_result(conn, user_id=winner, guild_id=gid,
                                     won=True, now=now)
    await store.record_battle_result(conn, user_id=loser, guild_id=gid,
                                     won=False, now=now)
    award = await game_xp.award_in_txn(
        conn, user_id=winner, guild_id=gid, game=game_xp.GAME_CREATURE,
        action="battle_win", now=now)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award
    return LegOutcome(step=StepResult(winner, "battle", True), before={},
                      after={"winner": winner, "loser": loser})


@workflow("creature.erase_subject_collection")
async def _erase_collection(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_collection(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_collection", True),
                      before={}, after={"rows": rows})


@workflow("creature.erase_subject_battles")
async def _erase_battles(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_battles(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_battles", True),
                      before={}, after={"rows": rows})


_XP_EMITS = (
    EventEmitSpec("game_xp.awarded",
                  WorkflowRef("games.game_xp_awarded_payload"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec("game_xp.level_up",
                  WorkflowRef("games.game_xp_levelup_payload"),
                  DeliveryClass.BEST_EFFORT),
)


def _op(op_key: str, verb: str, leg_ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="creature", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=_XP_EMITS)


CATCH = _op("creature.catch", "creature_catch_attempted",
            "creature.record_catch")
BATTLE = _op("creature.record_battle_result", "creature_battle_recorded",
             "creature.record_battle")

_OPS = (CATCH, BATTLE)

_REF_TABLE = (
    ("creature.record_catch", _record_catch),
    ("creature.record_battle", _record_battle),
    ("creature.erase_subject_collection", _erase_collection),
    ("creature.erase_subject_battles", _erase_battles),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
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
