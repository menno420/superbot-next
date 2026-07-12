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

# The loot draws ride the MODULE-GLOBAL `random` stream, shipped verbatim
# (disbot/utils/mining/rewards.py drew from bare `random`; the capture
# harness seeded it per case, and sb/adapters/parity/runner.py reseeds the
# same stream at every case head — the #163→#167 reseed lane's RNG flavor,
# trap 20/35c). goldens/mining/sweep_fastmine (iron ×1), sweep_chop
# (wood ×3) and sweep_explore (got_lost) pin the seed-42 trajectory
# through these exact draw shapes. A private Random() here would fork the
# stream and diff every loot byte.
_rng: random.Random = random  # type: ignore[assignment]


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
                             "description": description, "depth": depth,
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


@workflow("mining.record_reset_inventory")
async def _record_reset_inventory(conn, ctx: WorkflowContext) -> LegOutcome:
    """The shipped admin `!reset_inventory @member` — a guild-scoped
    wipe of the target's mining pack (mining_cog.py: \"reset a user's
    inventory in THIS guild (PR M3 — guild-scoped)\"); distinct from the
    account-wide GDPR erasure leg below."""
    uid, gid, _ = _ids(ctx)
    subject = int(ctx.params["subject_user_id"])
    rows = await store.reset_player_inventory(conn, user_id=subject,
                                              guild_id=gid)
    return LegOutcome(step=StepResult(uid, "reset_inventory", True),
                      before={}, after={"rows": rows, "subject": subject})


# --- equipment / loadout write legs (the direct-lane oracle writes, re-homed
# onto the audited K7 one-leg one-txn seam; services/mining_workflow.py verbatim
# copy — NO golden drives these argful paths, so the guard bytes in service.py
# are the only parity surface) --------------------------------------------------

#: A small, generous cap on saved presets (utils/mining loadout constants,
#: verbatim).
MAX_LOADOUT_PRESETS = 10
#: Cap on a preset name's length (keeps embeds + selects tidy).
MAX_LOADOUT_NAME_LEN = 24


def _clean_loadout_name(name: str) -> str:
    """Normalise a user-supplied preset name (lowercase, collapse whitespace)."""
    return " ".join(name.strip().lower().split())[:MAX_LOADOUT_NAME_LEN]


@workflow("mining.record_equip")
async def _record_equip(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.mining import equipment

    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)  # already stripped + lowercased
    slot = equipment.slot_for(item)
    if slot is None:
        raise ValidatorError(f"**{item.title()}** can't be equipped.")
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    if inventory.get(item, 0) < 1:
        raise ValidatorError(f"You don't own a **{item.title()}** to equip.")
    await store.equip_item(conn, user_id=uid, guild_id=gid, slot=slot,
                           item_name=item)
    return LegOutcome(
        step=StepResult(uid, "equip", True), before={},
        after={"item": item, "slot": slot,
               "message": f"equipped **{item.title()}** in the "
                          f"**{slot}** slot."})


@workflow("mining.record_unequip")
async def _record_unequip(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.mining import equipment

    uid, gid, _ = _ids(ctx)
    slot = _item_from(ctx)  # the slot token, stripped + lowercased
    if slot not in equipment.SLOTS:
        raise ValidatorError(
            f"Unknown slot **{slot}**. Slots: "
            f"{', '.join(equipment.SLOTS)}.")
    await store.unequip_slot(conn, user_id=uid, guild_id=gid, slot=slot)
    return LegOutcome(
        step=StepResult(uid, "unequip", True), before={},
        after={"slot": slot, "message": f"cleared the **{slot}** slot."})


@workflow("mining.record_save_loadout")
async def _record_save_loadout(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, _ = _ids(ctx)
    name = _clean_loadout_name(str(ctx.params.get("loadout_name", "") or ""))
    if not name:
        raise ValidatorError(
            "Give the loadout a name, e.g. `!loadout save mining`.")
    equipped = await store.get_equipment(uid, gid, conn=conn)
    if not equipped:
        raise ValidatorError(
            "You have no gear equipped to save — equip something first.")
    existing = await store.list_loadouts(uid, gid, conn=conn)
    if name not in existing and len(existing) >= MAX_LOADOUT_PRESETS:
        raise ValidatorError(
            f"You already have {MAX_LOADOUT_PRESETS} loadouts — delete one "
            "first with `!loadout delete <name>`.")
    await store.save_loadout(conn, user_id=uid, guild_id=gid, name=name,
                             slots=equipped)
    n = len(equipped)
    return LegOutcome(
        step=StepResult(uid, "save_loadout", True), before={},
        after={"name": name,
               "message": f"saved your current gear as the **{name}** "
                          f"loadout ({n} slot{'s' if n != 1 else ''})."})


@workflow("mining.record_apply_loadout")
async def _record_apply_loadout(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.mining import equipment

    uid, gid, _ = _ids(ctx)
    name = _clean_loadout_name(str(ctx.params.get("loadout_name", "") or ""))
    preset = await store.get_loadout(uid, gid, name, conn=conn)
    if not preset:
        raise ValidatorError(
            f"No loadout named **{name}**. See your loadouts with "
            "`!loadout list`.")
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    to_equip = {slot: item for slot, item in preset.items()
                if inventory.get(item, 0) >= 1}
    missing = sorted({i for i in preset.values() if inventory.get(i, 0) < 1})
    if not to_equip:
        msg = f"You no longer own any gear from the **{name}** loadout"
        if missing:
            msg += (f" (missing: "
                    f"{', '.join(i.title() for i in missing)})")
        raise ValidatorError(msg + ".")
    current = await store.get_equipment(uid, gid, conn=conn)
    cleared = 0
    for slot in equipment.SLOTS:
        if slot in to_equip:
            await store.equip_item(conn, user_id=uid, guild_id=gid,
                                   slot=slot, item_name=to_equip[slot])
        elif slot in current:
            await store.unequip_slot(conn, user_id=uid, guild_id=gid,
                                     slot=slot)
            cleared += 1
    n = len(to_equip)
    parts = [f"equipped the **{name}** loadout "
             f"({n} slot{'s' if n != 1 else ''})"]
    if cleared:
        parts.append(
            f"cleared {cleared} other slot{'s' if cleared != 1 else ''}")
    if missing:
        parts.append(
            f"skipped {len(missing)} you no longer own "
            f"({', '.join(i.title() for i in missing)})")
    return LegOutcome(
        step=StepResult(uid, "apply_loadout", True), before={},
        after={"name": name, "message": " — ".join(parts) + "."})


@workflow("mining.record_delete_loadout")
async def _record_delete_loadout(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid, _ = _ids(ctx)
    name = _clean_loadout_name(str(ctx.params.get("loadout_name", "") or ""))
    removed = await store.delete_loadout(conn, user_id=uid, guild_id=gid,
                                         name=name)
    if removed == 0:
        raise ValidatorError(f"No loadout named **{name}** to delete.")
    return LegOutcome(
        step=StepResult(uid, "delete_loadout", True), before={},
        after={"name": name,
               "message": f"deleted the **{name}** loadout."})


# --- descent / world-seed write legs (slice 2 — the shipped direct-lane depth
# moves + owner re-seed, re-homed onto the audited K7 one-leg one-txn seam;
# services/mining_workflow.py descend/ascend/reseed_world verbatim. NO golden
# drives these WRITE paths — every imported sweep pins the bare guard/read byte
# (goldens/mining/sweep_descend refuses at the Surface, sweep_ascend at the
# Surface, sweep_mineworld reads the default seed) — so the guard/read bytes in
# service.py are the only parity surface, and the tables stay guard-only
# (depth.exemptions.mining) ---------------------------------------------------


@workflow("mining.record_descend")
async def _record_descend(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.mining import character, world

    uid, gid, now = _ids(ctx)
    depth = await store.get_depth(uid, gid, conn=conn)
    # Gear + allocated skill points: an unspent player reads {} ⇒ all-zero
    # stats (the additive safety property), so a fresh player can't descend.
    equipped = await store.get_equipment(uid, gid, conn=conn)
    alloc = await store.get_skills(uid, gid, conn=conn)
    stats = character.character_stats(equipped, alloc)
    new_depth = world.descend(depth, stats)
    if new_depth == depth:
        # Defensive: the handler gates the not-moved case out before the op
        # (it has no write and no audit row — the guard-byte parity path).
        raise ValidatorError(
            f"can't descend any deeper. {world.descend_hint(stats)}")
    await store.set_depth(conn, user_id=uid, guild_id=gid, depth=new_depth)
    if await store.record_depth(conn, user_id=uid, guild_id=gid,
                                depth=new_depth):
        ctx.params["_gxp"] = await game_xp.award_in_txn(
            conn, user_id=uid, guild_id=gid, game=game_xp.GAME_MINING,
            action="depth_record", now=now)
    ctx.params["_balance_changes"] = []
    return LegOutcome(
        step=StepResult(uid, "descend", True), before={},
        after={"depth": new_depth,
               "message": f"descended to {world.describe_position(new_depth)}."})


@workflow("mining.record_ascend")
async def _record_ascend(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.mining import world

    uid, gid, _ = _ids(ctx)
    depth = await store.get_depth(uid, gid, conn=conn)
    new_depth = world.ascend(depth)
    if new_depth == depth:
        raise ValidatorError("is already at the Surface.")
    await store.set_depth(conn, user_id=uid, guild_id=gid, depth=new_depth)
    return LegOutcome(
        step=StepResult(uid, "ascend", True), before={},
        after={"depth": new_depth,
               "message": f"climbed up to "
                          f"{world.describe_position(new_depth)}."})


@workflow("mining.record_reseed_world")
async def _record_reseed_world(conn, ctx: WorkflowContext) -> LegOutcome:
    """The owner `!mineworld <seed>` re-seed — a per-guild write
    (mining_world; guild-keyed, no member data). The manage_guild gate
    rides in the handler (ActorRef.is_guild_operator), the shipped
    ``member_has_perms_or_owner(manage_guild=True)`` port home."""
    uid, gid, _ = _ids(ctx)
    seed = int(ctx.params["seed"])
    await store.set_world_seed(conn, guild_id=gid, seed=seed)
    return LegOutcome(
        step=StepResult(uid, "reseed_world", True), before={},
        after={"seed": seed})


@workflow("mining.erase_subject_equipment")
async def _erase_equipment(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_equipment(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_equipment", True),
                      before={}, after={"rows": rows})


@workflow("mining.erase_subject_gear_wear")
async def _erase_gear_wear(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_gear_wear(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_gear_wear", True),
                      before={}, after={"rows": rows})


@workflow("mining.erase_subject_loadouts")
async def _erase_loadouts(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_loadouts(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_loadouts", True),
                      before={}, after={"rows": rows})


@workflow("mining.erase_subject_skills")
async def _erase_skills(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_skills(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_skills", True),
                      before={}, after={"rows": rows})


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
RESET_INVENTORY = _op("mining.reset_inventory", "mining_inventory_reset",
                      "mining.record_reset_inventory", ())
EQUIP = _op("mining.equip", "mining_equipped", "mining.record_equip", ())
UNEQUIP = _op("mining.unequip", "mining_unequipped",
              "mining.record_unequip", ())
SAVE_LOADOUT = _op("mining.save_loadout", "mining_loadout_saved",
                   "mining.record_save_loadout", ())
APPLY_LOADOUT = _op("mining.apply_loadout", "mining_loadout_applied",
                    "mining.record_apply_loadout", ())
DELETE_LOADOUT = _op("mining.delete_loadout", "mining_loadout_deleted",
                     "mining.record_delete_loadout", ())
DESCEND = _op("mining.descend", "mining_descended", "mining.record_descend",
              _XP_EMITS)
ASCEND = _op("mining.ascend", "mining_ascended", "mining.record_ascend", ())
RESEED_WORLD = _op("mining.reseed_world", "mining_world_reseeded",
                   "mining.record_reseed_world", ())

_OPS = (MINE, HARVEST, EXPLORE, SELL, SELL_ALL, BUY, RESET_INVENTORY,
        EQUIP, UNEQUIP, SAVE_LOADOUT, APPLY_LOADOUT, DELETE_LOADOUT,
        DESCEND, ASCEND, RESEED_WORLD)

_REF_TABLE = (
    ("mining.record_mine", _record_mine),
    ("mining.record_harvest", _record_harvest),
    ("mining.record_explore", _record_explore),
    ("mining.record_sell", _record_sell),
    ("mining.record_sell_all", _record_sell_all),
    ("mining.record_buy", _record_buy),
    ("mining.record_reset_inventory", _record_reset_inventory),
    ("mining.record_equip", _record_equip),
    ("mining.record_unequip", _record_unequip),
    ("mining.record_save_loadout", _record_save_loadout),
    ("mining.record_apply_loadout", _record_apply_loadout),
    ("mining.record_delete_loadout", _record_delete_loadout),
    ("mining.record_descend", _record_descend),
    ("mining.record_ascend", _record_ascend),
    ("mining.record_reseed_world", _record_reseed_world),
    ("mining.erase_subject_inventory", _erase_inventory),
    ("mining.erase_subject_state", _erase_state),
    ("mining.erase_subject_equipment", _erase_equipment),
    ("mining.erase_subject_gear_wear", _erase_gear_wear),
    ("mining.erase_subject_loadouts", _erase_loadouts),
    ("mining.erase_subject_skills", _erase_skills),
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
