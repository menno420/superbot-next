"""Farm K7 lanes (band 6) — collect / buy_chicken / upgrade_coop, the
shipped farm_workflow semantics as one-leg one-txn ops (RS02/Q-0071 made
structural): settle → coin leg via the ledger-audited wager helpers →
farm-row write → game-XP award, all on the leg's conn; events emit after
commit via the games conditional builders. Buying a chicken settles at
the OLD flock size first (the shipped no-retroactive-rate subtlety)."""

from __future__ import annotations

from sb.domain.farm import core, store
from sb.domain.games import wager
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

__all__ = ["COLLECT_REASON", "register_ops"]

# shipped reason tags verbatim
COLLECT_REASON = "farm:collect"
BUY_CHICKEN_REASON = "farm:buy_chicken"
UPGRADE_COOP_REASON = "farm:upgrade_coop"


def _ids(ctx: WorkflowContext) -> tuple[int, int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0), int(ctx.clock().timestamp()))


def _stored(now: int, chickens: int, eggs: int, ts: int,
            coop: int) -> core.FarmState:
    """Zero timestamp = uninitialized: accrual starts NOW, never from 1970
    (the shipped free-full-coop closure)."""
    return core.FarmState(chickens, eggs, ts or now, coop)


@workflow("farm.record_collect")
async def _record_collect(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn,
                                                    for_update=True)
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    if settled.eggs <= 0:
        raise ValidatorError(
            "🥚 The coop is empty — your hens need time to lay. "
            "Check back soon!")
    payout = core.collect_value(settled.eggs)
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=payout,
        reason=COLLECT_REASON, actor_id=uid)
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens, eggs=0, now=now,
                         coop_level=settled.coop_level)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_FARM,
        action="collect_eggs", now=now)
    ctx.params["_balance_changes"] = [(uid, payout, balance,
                                       COLLECT_REASON)]
    ctx.params["_gxp"] = award
    return LegOutcome(step=StepResult(uid, "collect", True), before={},
                      after={"eggs_collected": settled.eggs,
                             "coins_earned": payout, "balance": balance,
                             "message": f"🥚 Collected **{settled.eggs}** "
                                        f"egg(s) for **{payout}** 🪙! "
                                        f"Balance: **{balance}** 🪙."})


@workflow("farm.record_buy_chicken")
async def _record_buy_chicken(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn,
                                                    for_update=True)
    if not core.can_buy_chicken(chickens):
        raise ValidatorError(
            f"🐔 Your flock is at the cap of **{core.MAX_CHICKENS}** hens "
            "— that's a lot of clucking!")
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    price = core.chicken_price(chickens)
    from sb.domain.economy.service import InsufficientFundsError

    try:
        balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=price,
            reason=BUY_CHICKEN_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"🐔 A new hen costs **{price}** 🪙 — you only have "
            f"**{held}** 🪙.") from None
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens + 1, eggs=settled.eggs,
                         now=now, coop_level=settled.coop_level)
    ctx.params["_balance_changes"] = [(uid, -price, balance,
                                       BUY_CHICKEN_REASON)]
    return LegOutcome(step=StepResult(uid, "buy_chicken", True), before={},
                      after={"price": price, "balance": balance,
                             "chickens": settled.chickens + 1,
                             "message": f"🐔 Bought a hen for **{price}** "
                                        f"🪙! Your flock is now "
                                        f"**{settled.chickens + 1}** "
                                        f"strong. Balance: "
                                        f"**{balance}** 🪙."})


@workflow("farm.record_upgrade_coop")
async def _record_upgrade_coop(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn,
                                                    for_update=True)
    if not core.can_upgrade_coop(coop):
        raise ValidatorError(
            f"🏠 Your coop is already maxed at level "
            f"**{core.MAX_COOP_LEVEL}** (holds "
            f"**{core.coop_capacity(coop)}** eggs).")
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    price = core.coop_upgrade_price(coop)
    from sb.domain.economy.service import InsufficientFundsError

    try:
        balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=price,
            reason=UPGRADE_COOP_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"🏠 The next coop upgrade costs **{price}** 🪙 — you only "
            f"have **{held}** 🪙.") from None
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens, eggs=settled.eggs,
                         now=now, coop_level=settled.coop_level + 1)
    ctx.params["_balance_changes"] = [(uid, -price, balance,
                                       UPGRADE_COOP_REASON)]
    return LegOutcome(step=StepResult(uid, "upgrade_coop", True),
                      before={},
                      after={"price": price, "balance": balance,
                             "coop_level": settled.coop_level + 1,
                             "message": f"🏠 Upgraded your coop to level "
                                        f"**{settled.coop_level + 1}** for "
                                        f"**{price}** 🪙! Balance: "
                                        f"**{balance}** 🪙."})


@workflow("farm.erase_subject_farm")
async def _erase_subject_farm(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_farm(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_farm", True),
                      before={}, after={"rows": rows})


_BALANCE_EMITS = (
    EventEmitSpec("economy.balance_changed",
                  WorkflowRef("games.balance_payload_0"),
                  DeliveryClass.BEST_EFFORT),
)
_XP_EMITS = (
    EventEmitSpec("game_xp.awarded",
                  WorkflowRef("games.game_xp_awarded_payload"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec("game_xp.level_up",
                  WorkflowRef("games.game_xp_levelup_payload"),
                  DeliveryClass.BEST_EFFORT),
)


def _op(op_key: str, verb: str, leg_ref: str,
        emits: tuple[EventEmitSpec, ...]) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="farm", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=emits)


COLLECT = _op("farm.collect", "farm_collected", "farm.record_collect",
              _BALANCE_EMITS + _XP_EMITS)
BUY_CHICKEN = _op("farm.buy_chicken", "farm_chicken_bought",
                  "farm.record_buy_chicken", _BALANCE_EMITS)
UPGRADE_COOP = _op("farm.upgrade_coop", "farm_coop_upgraded",
                   "farm.record_upgrade_coop", _BALANCE_EMITS)

_OPS = (COLLECT, BUY_CHICKEN, UPGRADE_COOP)

_REF_TABLE = (
    ("farm.record_collect", _record_collect),
    ("farm.record_buy_chicken", _record_buy_chicken),
    ("farm.record_upgrade_coop", _record_upgrade_coop),
    ("farm.erase_subject_farm", _erase_subject_farm),
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
