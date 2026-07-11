"""Mining K7 lanes (band 6) — the CORE loop (mine / chop / explore / sell
/ sellall / buy) as one-leg one-txn ops over the shipped math. The deep
systems (equipment+wear, energy, grid dig, vault, structures, skills,
forge/workshop, titles, loadouts, descend/ascend) are the D-0043 named
successor port — their commands are honest pending terminals."""

from __future__ import annotations

import random

from sb.domain.games import wager
from sb.domain.games import xp as game_xp
from sb.domain.mining import market, rewards, store
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

__all__ = ["SELL_REASON", "register_ops", "set_rng_for_tests"]

# shipped reason tags verbatim (utils/mining/market.py)
SELL_REASON = "mining:sell_ore"
BUY_REASON = "mining:buy_gear"

_rng: random.Random = random.Random()


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def _ids(ctx: WorkflowContext) -> tuple[int, int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0), int(ctx.clock().timestamp()))


def _item_from(ctx: WorkflowContext, *, skip: int = 0) -> str:
    item = ctx.params.get("item")
    values = tuple(ctx.params.get("values", ()) or ())
    if item is None and values:
        item = values[0]
    if item is None:
        argv = [str(t) for t in tuple(ctx.params.get("argv", ()) or ())]
        words = [t for t in argv if not t.isdigit()]
        if words[skip:]:
            item = " ".join(words[skip:])   # multi-word gear names
    if not item:
        raise ValidatorError("Name an item.")
    return str(item).strip().lower()


def _qty_from(ctx: WorkflowContext, default: int = 1) -> int:
    qty = ctx.params.get("qty")
    if qty is None:
        for tok in tuple(ctx.params.get("argv", ()) or ()):
            if str(tok).isdigit():
                qty = int(tok)
                break
    qty = int(qty or default)
    if qty <= 0:
        raise ValidatorError("Quantity must be positive.")
    return qty


@workflow("mining.record_mine")
async def _record_mine(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, now = _ids(ctx)
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    depth = await store.get_depth(uid, gid, conn=conn)
    found, amount = rewards.roll_mine_loot(
        has_pickaxe=inventory.get("pickaxe", 0) > 0, depth=depth,
        rng=_rng)
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=found, delta=amount)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_MINING,
        action="mine", now=now, depth=depth)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award
    return LegOutcome(step=StepResult(uid, "mine", True), before={},
                      after={"found": found, "amount": amount,
                             "depth": depth,
                             "message": f"⛏️ You mined **{amount}× "
                                        f"{found}**!"})


@workflow("mining.record_harvest")
async def _record_harvest(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, now = _ids(ctx)
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    amount = rewards.roll_harvest_amount(
        has_axe=inventory.get("axe", 0) > 0, rng=_rng)
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item="wood", delta=amount)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_MINING,
        action="harvest", now=now)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award
    return LegOutcome(step=StepResult(uid, "harvest", True), before={},
                      after={"amount": amount,
                             "message": f"🪓 You chopped **{amount}× "
                                        f"wood**!"})


@workflow("mining.record_explore")
async def _record_explore(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, now = _ids(ctx)
    depth = await store.get_depth(uid, gid, conn=conn)
    description, item, delta = rewards.roll_explore_outcome(_rng)
    if item is not None and delta:
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=item, delta=delta)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_MINING,
        action="explore", now=now, depth=depth)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award
    return LegOutcome(step=StepResult(uid, "explore", True), before={},
                      after={"item": item, "delta": delta,
                             "message": f"🧭 You {description}"})


async def _sell_rows(conn, ctx: WorkflowContext,
                     rows: list[tuple[str, int, int]]) -> dict:
    uid, gid, _ = _ids(ctx)
    total = 0
    sold: list[str] = []
    for name, qty, price in rows:
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=name, delta=-qty)
        total += qty * price
        sold.append(f"{qty}× {name}")
    if total <= 0:
        raise ValidatorError("Nothing sellable — mine some ore first!")
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=total, reason=SELL_REASON,
        actor_id=uid)
    ctx.params["_balance_changes"] = [(uid, total, balance, SELL_REASON)]
    return {"earned": total, "balance": balance, "sold": sold,
            "message": f"💰 Sold {', '.join(sold)} for **{total}** 🪙. "
                       f"Balance: **{balance}** 🪙."}


@workflow("mining.record_sell")
async def _record_sell(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    qty = _qty_from(ctx)
    price = market.sell_price(item)
    if price is None:
        raise ValidatorError(f"❌ `{item}` can't be sold.")
    held = (await store.get_mining_inventory(
        uid, gid, conn=conn, for_update=True)).get(item, 0)
    if held < qty:
        raise ValidatorError(f"❌ You only have **{held}× {item}**.")
    after = await _sell_rows(conn, ctx, [(item, qty, price)])
    return LegOutcome(step=StepResult(uid, "sell", True), before={},
                      after=after)


@workflow("mining.record_sell_all")
async def _record_sell_all(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, _ = _ids(ctx)
    inventory = await store.get_mining_inventory(uid, gid, conn=conn,
                                                 for_update=True)
    rows = market.sellable_inventory(inventory)
    if not rows:
        raise ValidatorError("Nothing sellable — mine some ore first!")
    after = await _sell_rows(conn, ctx, rows)
    return LegOutcome(step=StepResult(uid, "sell_all", True), before={},
                      after=after)


@workflow("mining.record_buy")
async def _record_buy(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    price = market.GEAR_SHOP.get(item)
    if price is None:
        raise ValidatorError(f"❌ `{item}` isn't in the gear shop.")
    from sb.domain.economy.service import InsufficientFundsError

    try:
        balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=price,
            reason=BUY_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"❌ `{item}` costs **{price}** 🪙 — you only have "
            f"**{held}** 🪙.") from None
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=item, delta=1)
    ctx.params["_balance_changes"] = [(uid, -price, balance, BUY_REASON)]
    return LegOutcome(step=StepResult(uid, "buy", True), before={},
                      after={"item": item, "price": price,
                             "balance": balance,
                             "message": f"🛒 Bought **{item}** for "
                                        f"**{price}** 🪙. Balance: "
                                        f"**{balance}** 🪙."})


@workflow("mining.erase_subject_inventory")
async def _erase_inventory(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_inventory(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_inventory", True),
                      before={}, after={"rows": rows})


@workflow("mining.erase_subject_state")
async def _erase_state(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_state(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_state", True),
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
        op_key=op_key, domain="mining", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=emits)


MINE = _op("mining.mine", "mining_dug", "mining.record_mine", _XP_EMITS)
HARVEST = _op("mining.harvest", "mining_harvested",
              "mining.record_harvest", _XP_EMITS)
EXPLORE = _op("mining.explore", "mining_explored",
              "mining.record_explore", _XP_EMITS)
SELL = _op("mining.sell", "mining_sold", "mining.record_sell",
           _BALANCE_EMITS)
SELL_ALL = _op("mining.sell_all", "mining_sold", "mining.record_sell_all",
               _BALANCE_EMITS)
BUY = _op("mining.buy", "mining_gear_bought", "mining.record_buy",
          _BALANCE_EMITS)

_OPS = (MINE, HARVEST, EXPLORE, SELL, SELL_ALL, BUY)

_REF_TABLE = (
    ("mining.record_mine", _record_mine),
    ("mining.record_harvest", _record_harvest),
    ("mining.record_explore", _record_explore),
    ("mining.record_sell", _record_sell),
    ("mining.record_sell_all", _record_sell_all),
    ("mining.record_buy", _record_buy),
    ("mining.erase_subject_inventory", _erase_inventory),
    ("mining.erase_subject_state", _erase_state),
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
