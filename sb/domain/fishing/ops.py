"""Fishing K7 lanes (band 6) — the CORE cast (the shipped legacy
``fish()`` path): level-gated inverse-size roll + commit (dex upsert +
pearl/coral materials + the fish as a tangible mining_inventory item +
game-XP award) in ONE leg txn.

DEVIATION (D-0043): casts run at the STARTER profile — starter rod
(rarity_pull 1.0), no bait, shore venue, neutral weather, base
double-catch chance — until the rod/bait/energy/minigame/structure
systems port (named successor work; their commands are honest pending
terminals). At the starter profile the roll is byte-identical to a fresh
shipped player's. Slice 1 made the VENUE STATE live (!sail persists
``fishing_venue``; the hub/cast renders read it) but the cast LEG still
rolls the shore pool — the venue→cast wiring (deepwater species pool,
coral drop, minigame difficulty) rides the rod/bait/minigame rung, where
the oracle's rolled knobs (rarity_pull, bite speed, escape) land
together."""

from __future__ import annotations

import random

from sb.domain.fishing import catalog, store
from sb.domain.games import xp as game_xp
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
    "BONUS_CATCH_CHANCE",
    "PEARL_ITEM",
    "register_ops",
    "roll_catch",
    "set_rng_for_tests",
]

# shipped constants verbatim (utils/fishing/rewards.py)
BONUS_CATCH_CHANCE = 0.10
PEARL_ITEM = "pearl"
PEARL_DROP_BASE_CHANCE = 0.02
PEARL_DROP_PER_SIZE_RANK = 0.004
PEARL_DROP_MAX_CHANCE = 0.15
CORAL_ITEM = "coral"
CORAL_DROP_CHANCE = 0.06

_rng: random.Random = random.Random()


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def roll_catch(fishing_level: int, rng: random.Random | None = None, *,
               rarity_pull: float = 1.0,
               venue: str = catalog.SHORE_VENUE) -> catalog.Catch | None:
    """Inverse-size weighted roll within the unlocked band (shipped
    verbatim; rarity_pull ≥ 1 flattens toward the big end)."""
    pool = catalog.unlocked_species(fishing_level, venue)
    if not pool:
        return None
    r = rng or random.Random()
    pull = max(1.0, rarity_pull)
    weights = [1.0 / (s.size_rank ** (1.0 / pull)) for s in pool]
    species = r.choices(pool, weights=weights, k=1)[0]
    return catalog.Catch(species=species,
                         weight=catalog.roll_weight(species, r))


def pearl_drop_chance(size_rank: int) -> float:
    rank = max(1, size_rank)
    chance = (PEARL_DROP_BASE_CHANCE
              + PEARL_DROP_PER_SIZE_RANK * (rank - 1))
    return min(chance, PEARL_DROP_MAX_CHANCE)


@workflow("fishing.record_cast")
async def _record_cast(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    now = int(ctx.clock().timestamp())
    from sb.domain.games.store import game_xp_rows

    xp_rows = {str(r["game"]): int(r["xp"])
               for r in await game_xp_rows(uid, gid, conn=conn)}
    level_before = catalog.fishing_level_from_xp(
        xp_rows.get(game_xp.GAME_FISHING, 0))
    catch = roll_catch(level_before, _rng)
    if catch is None:
        raise ValidatorError("🎣 The waters are quiet — the fish catalog "
                             "is empty.")
    # bonus → pearl (coral is deepwater-only; shore casts never roll it)
    bonus = _rng.random() < BONUS_CATCH_CHANCE
    pearl = _rng.random() < pearl_drop_chance(catch.species.size_rank)
    prior_best = await store.record_catch(
        conn, user_id=uid, guild_id=gid, species=catch.species.name,
        weight=catch.weight, now=now)
    from sb.domain.mining.store import update_mining_item

    if pearl:
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=PEARL_ITEM, delta=1)
    await update_mining_item(conn, user_id=uid, guild_id=gid,
                             item=catch.species.name,
                             delta=2 if bonus else 1)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_FISHING,
        action="fish", now=now)
    level_after = catalog.fishing_level_from_xp(
        xp_rows.get(game_xp.GAME_FISHING, 0) + award.amount)
    new_best = catch.weight > 0 and (prior_best is None
                                     or catch.weight > prior_best)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award
    parts = [f"{catch.species.emoji} Caught a **{catch.species.name}** "
             f"({catch.weight:.2f} kg)!"]
    if bonus:
        parts.append("🎣 Lucky double catch — 2 landed!")
    if pearl:
        parts.append("🦪 A pearl washed up with it!")
    if new_best:
        parts.append("🏆 New personal best!")
    if level_after > level_before:
        parts.append(f"⬆️ Fishing level {level_after} — bigger fish "
                     "unlocked!")
    return LegOutcome(
        step=StepResult(uid, "cast", True), before={},
        after={"species": catch.species.name, "weight": catch.weight,
               "bonus_catch": bonus, "pearl_found": pearl,
               "new_personal_best": new_best,
               "fishing_level": level_after,
               "message": "\n".join(parts)})


@workflow("fishing.erase_subject_catch_log")
async def _erase_catch_log(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_catch_log(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_catch_log", True),
                      before={}, after={"rows": rows})


@workflow("fishing.erase_subject_energy")
async def _erase_energy(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_energy(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_energy", True),
                      before={}, after={"rows": rows})


@workflow("fishing.erase_subject_venue")
async def _erase_venue(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_venue(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_venue", True),
                      before={}, after={"rows": rows})


_XP_EMITS = (
    EventEmitSpec("game_xp.awarded",
                  WorkflowRef("games.game_xp_awarded_payload"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec("game_xp.level_up",
                  WorkflowRef("games.game_xp_levelup_payload"),
                  DeliveryClass.BEST_EFFORT),
)

CAST = CompoundOpSpec(
    op_key="fishing.cast", domain="fishing", lane=WorkflowLane.DOMAIN,
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB, WorkflowRef("fishing.record_cast"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fish_caught", emits=_XP_EMITS)

_OPS = (CAST,)

_REF_TABLE = (
    ("fishing.record_cast", _record_cast),
    ("fishing.erase_subject_catch_log", _erase_catch_log),
    ("fishing.erase_subject_energy", _erase_energy),
    ("fishing.erase_subject_venue", _erase_venue),
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
