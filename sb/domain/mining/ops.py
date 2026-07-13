"""Mining K7 lanes (band 6) — the CORE loop (mine / chop / explore / sell
/ sellall / buy) as one-leg one-txn ops over the shipped math, plus the
ported deep-system write lanes (equip/loadout, descend/ascend, vault,
repair/quickcraft, the energy-lane cook/use consumables, and the slice-3
fastmine dig energy spend). The still unported deep systems (wear ticks,
grid dig) ride their named successor slices."""

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

__all__ = ["COOKED_FISH", "SELL_REASON", "is_fish", "register_ops",
           "set_rng_for_tests"]

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


def _rest_from(ctx: WorkflowContext) -> str:
    """The oracle's consume-rest argument (``*, item: str``) — the FULL arg
    tail verbatim, digits included, unlike :func:`_item_from`'s sell/buy
    trailing-qty split (``!use 5 torch`` must refuse on the literal
    ``5 torch``, the shipped cog contract)."""
    item = ctx.params.get("item")
    if item is None:
        values = tuple(ctx.params.get("values", ()) or ())
        if values:
            item = values[0]
    if item is None:
        argv = [str(t) for t in tuple(ctx.params.get("argv", ()) or ())]
        if argv:
            item = " ".join(argv)
    if not item:
        raise ValidatorError("Name an item.")
    return str(item).strip().lower()


@workflow("mining.record_mine")
async def _record_mine(conn, ctx: WorkflowContext) -> LegOutcome:
    """One quick swing (`!fastmine`) — loot roll + grant + game XP, and
    (energy-lane slice 3, Option A) the dig energy spend: settle →
    ``can_dig`` gate → spend ``DIG_COST`` → ``set_energy``, the oracle
    ``dig()`` energy bracket grafted onto the fastmine leg
    (services/mining_workflow.py ``dig`` @ 87bbe1d — the shipped ``mine()``
    predates the energy brake; Option A is the owner's chosen successor
    shape). The route pre-checks the same gate as a PURE READ so the
    refusal bytes stay oracle-plain (the slice-2 ValidatorError-envelope
    trap); this in-txn re-check is the race fence — a raced dig refuses
    (wrapped) rather than digging below zero. The energy upsert keeps the
    slice-1 lockless plain posture (game pacing, never money)."""
    from sb.domain.mining import energy

    uid, gid, now = _ids(ctx)
    e_state = energy.EnergyState(*await store.get_energy(uid, gid, conn=conn))
    if not energy.can_dig(e_state, now):
        wait = energy.seconds_until(e_state, now, energy.DIG_COST)
        raise ValidatorError(
            "⚡ You're out of energy — rest a moment "
            f"(~{wait}s until your next dig) or eat a **ration** / "
            "**energy drink** (`!use ration`).")
    spent = energy.spend(e_state, now)
    await store.set_energy(uid, gid, spent.current, spent.updated_at,
                           conn=conn)
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


# --- vault write legs (slice 3): the shipped services/mining_workflow.py
# vault_deposit / vault_withdraw / vault_deposit_all_resources / vault_upgrade
# verbatim, re-homed onto the audited one-leg one-txn seam. NO golden drives an
# argful stash/unstash/stash-all or a FUNDED upgrade — the guard bytes in
# service.py (the stash/unstash usage prompts + the insufficient-funds refusal,
# a pure read) are the only parity surface, so mining_vault stays guard-only
# (depth.exemptions.mining) ----------------------------------------------------


@workflow("mining.record_stash")
async def _record_stash(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!stash <item> [n]` — move *qty* of *item* from the active pack into the
    safe vault. Both legs (inventory debit + vault credit) commit in ONE txn so
    a mid-move failure can never duplicate or lose the items."""
    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    qty = _qty_from(ctx)
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    have = inventory.get(item, 0)
    if have < qty:
        owned = f"only **{have}× {item}**" if have else f"no **{item}**"
        raise ValidatorError(f"You have {owned} to deposit.")
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=item, delta=-qty)
    await store.update_vault_item(conn, user_id=uid, guild_id=gid,
                                  item=item, delta=qty)
    return LegOutcome(
        step=StepResult(uid, "stash", True), before={},
        after={"item": item, "qty": qty,
               "message": f"Deposited **{qty}× {item}** into your vault — "
                          "safe and out of your pack."})


@workflow("mining.record_unstash")
async def _record_unstash(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!unstash <item> [n]` — move *qty* of *item* from the safe vault back
    into the active pack (the symmetric inverse of the deposit)."""
    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    qty = _qty_from(ctx)
    vault = await store.get_vault(uid, gid, conn=conn)
    have = vault.get(item, 0)
    if have < qty:
        owned = f"only **{have}× {item}**" if have else f"no **{item}**"
        raise ValidatorError(f"Your vault holds {owned}.")
    await store.update_vault_item(conn, user_id=uid, guild_id=gid,
                                  item=item, delta=-qty)
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=item, delta=qty)
    return LegOutcome(
        step=StepResult(uid, "unstash", True), before={},
        after={"item": item, "qty": qty,
               "message": f"Withdrew **{qty}× {item}** from your vault back "
                          "into your pack."})


@workflow("mining.record_stash_all")
async def _record_stash_all(conn, ctx: WorkflowContext) -> LegOutcome:
    """The 📦 Stash All Ore convenience — tuck every raw resource into the vault
    in ONE txn (gear/tools/treasure stay in the pack; only sellable resources
    move). Shipped ``vault_deposit_all_resources`` verbatim."""
    uid, gid, _ = _ids(ctx)
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    resources = market.sellable_inventory(inventory)
    if not resources:
        raise ValidatorError(
            "You have no raw resources to stash — go mine some!")
    for name, qty, _price in resources:
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=name, delta=-qty)
        await store.update_vault_item(conn, user_id=uid, guild_id=gid,
                                      item=name, delta=qty)
    moved = ", ".join(f"{qty}× {name}" for name, qty, _price in resources)
    return LegOutcome(
        step=StepResult(uid, "stash_all", True), before={},
        after={"message": f"Stashed {moved} into your vault."})


@workflow("mining.record_vault_upgrade")
async def _record_vault_upgrade(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!vaultupgrade` — buy one vault-capacity tier (the §7.5 coin sink):
    debit the rising upgrade cost and raise ``vault_level`` by one in ONE txn
    (the buy precedent — the coin debit is economy-audited, the balance event
    emits after commit). The handler gates the maxed / insufficient-funds cases
    out as pure reads before this leg runs (no write, no audit row — the
    guard-byte parity path), so the raises here are defensive."""
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.mining import capacity

    uid, gid, _ = _ids(ctx)
    # Fence concurrent upgrades for this player BEFORE the level read → the
    # debit + level bump serialize (no double-charge / lost tier — #217).
    await store.lock_vault_upgrade_slot(conn, user_id=uid, guild_id=gid)
    level = await store.get_vault_level(uid, gid, conn=conn)
    cost = capacity.vault_upgrade_cost(level)
    if cost is None:
        cap = capacity.vault_capacity(level)
        raise ValidatorError(
            f"Your vault is already at its maximum capacity "
            f"(**{cap}** item types).")
    try:
        balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=cost,
            reason=market.VAULT_UPGRADE_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"A vault upgrade costs **{cost}** 🪙 — you only have "
            f"**{held}** 🪙.") from None
    await store.set_vault_level(conn, user_id=uid, guild_id=gid,
                               level=level + 1)
    new_cap = capacity.vault_capacity(level + 1)
    ctx.params["_balance_changes"] = [
        (uid, -cost, balance, market.VAULT_UPGRADE_REASON)]
    return LegOutcome(
        step=StepResult(uid, "vault_upgrade", True), before={},
        after={"cost": cost, "balance": balance,
               "message": f"Vault upgraded to capacity **{new_cap}** item "
                          f"types for **{cost}** 🪙. Balance: "
                          f"**{balance}** 🪙."})


# --- workshop / crafting write legs (slice 4): the shipped services/
# mining_workflow.py repair / quick_craft verbatim, re-homed onto the audited
# one-leg one-txn seam. NO golden drives a funded repair or a real quick-craft —
# every imported sweep pins the bare guard/read byte (sweep_repair pins the usage
# prompt, sweep_quickcraft pins the fresh-player "nothing broken" read off the
# NULL last_broken_item), so the guard/read bytes in service.py are the only
# parity surface. Both settles are advisory-fenced (lock_workshop_slot) against
# the read-then-settle money/material race (check_money_race) --------------------


@workflow("mining.record_repair")
async def _record_repair(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!repair <item>` — repair *item* to full durability for coins: debit the
    proportional cost and clear the wear row in ONE txn (the shipped RS02 order —
    both legs commit or roll back together). Money-bearing (wager.debit_in_txn),
    so the wear read that sizes the cost is advisory-fenced first."""
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.mining import equipment, workshop

    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    if equipment.max_durability(item) is None:
        raise ValidatorError(f"**{item}** doesn't wear out.")
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    if inventory.get(item, 0) < 1:
        raise ValidatorError(f"You don't own a **{item}** to repair.")
    # Fence concurrent repairs of this player's gear BEFORE the wear read →
    # the debit + wear clear serialize (no double-charge — #217).
    await store.lock_workshop_slot(conn, user_id=uid, guild_id=gid)
    wear = await store.get_gear_wear(uid, gid, conn=conn)
    if item not in wear:
        raise ValidatorError(f"Your **{item}** is already at full durability.")
    cost = workshop.repair_cost(item, wear[item])
    if cost is None:
        raise ValidatorError(f"**{item}** can't be repaired here.")
    try:
        balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=cost,
            reason=workshop.REPAIR_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        held = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"Repairing **{item}** costs **{cost}** 🪙 — you only have "
            f"**{held}** 🪙.") from None
    await store.clear_gear_wear(conn, user_id=uid, guild_id=gid, item_name=item)
    ctx.params["_balance_changes"] = [
        (uid, -cost, balance, workshop.REPAIR_REASON)]
    return LegOutcome(
        step=StepResult(uid, "repair", True), before={},
        after={"item": item, "cost": cost, "balance": balance,
               "message": f"Repaired **{item}** to full durability for "
                          f"**{cost}** 🪙. Balance: **{balance}** 🪙."})


@workflow("mining.record_quick_craft")
async def _record_quick_craft(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!quickcraft` — re-craft the last gear item that broke and auto-equip it
    if its slot is free. Craft deltas + equip + marker clear commit in ONE txn
    (the shipped RS02 order). Not money-bearing (materials, not coins), but the
    material spend is advisory-fenced against a concurrent double-quick-craft.

    The handler answers the fresh-player "nothing broken" read (NULL
    last_broken_item) as a pure read before this leg runs — the only path any
    golden pins (goldens/mining/sweep_quickcraft.json) — so this leg only ever
    runs behind a genuinely broken item."""
    from sb.domain.mining import equipment, recipes, structures

    uid, gid, _ = _ids(ctx)
    await store.lock_workshop_slot(conn, user_id=uid, guild_id=gid)
    last = await store.get_last_broken(uid, gid, conn=conn)
    if not last:
        raise ValidatorError(
            "Nothing has broken recently — craft or repair gear below.")
    recipe = recipes.load_recipes().get(last)
    if not recipe:
        raise ValidatorError(f"No recipe for **{last}**.")
    required = structures.forge_level_required(last)
    if required > 0:
        built = await store.get_structures(uid, gid, conn=conn)
        if built.get(structures.FORGE, 0) < required:
            needed = structures.forge_level_name(required)
            tier = equipment.gear_tier(last)
            raise ValidatorError(
                f"Crafting **{last}** needs a **{needed}** 🔥 — build the "
                f"Forge with `!forge` to unlock {tier}-tier gear.")
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    for mat, qty in recipe.items():
        if inventory.get(mat, 0) < qty:
            from sb.domain.mining import workshop

            raise ValidatorError(
                f"You don't have enough **{mat}** to craft **{last}** "
                f"(needs {workshop.describe_materials(recipe)}).")
    for mat, qty in recipe.items():
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=mat, delta=-qty)
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=last, delta=1)
    message = f"Crafted **{last}**!"
    slot = equipment.slot_for(last)
    if slot is not None:
        equipped = await store.get_equipment(uid, gid, conn=conn)
        if slot not in equipped:
            await store.equip_item(conn, user_id=uid, guild_id=gid, slot=slot,
                                   item_name=last)
            message = f"Crafted **{last}** and equipped it in the **{slot}** " \
                      "slot!"
    await store.set_last_broken(conn, user_id=uid, guild_id=gid, item=None)
    return LegOutcome(
        step=StepResult(uid, "quick_craft", True), before={},
        after={"item": last, "message": message})


#: The food produced by cooking a fish (eaten via ``!use`` for energy) —
#: services/mining_workflow.py ``COOKED_FISH`` verbatim (@ 87bbe1d).
COOKED_FISH = "cooked fish"


def is_fish(name: str) -> bool:
    """True if *name* is a caught fish species — the oracle's
    ``items.is_fish`` (every ``fish``-tagged catalog row is exactly a
    fishing species: ``utils/mining/items.py`` builds them from
    ``utils/fishing/fish.SPECIES``); the port's species home is
    ``sb.domain.fishing.catalog.SPECIES`` (the ``market._fish_values``
    seam). Function-level import: the same lazy mining→fishing edge
    market.py already carries."""
    from sb.domain.fishing.catalog import SPECIES

    return name in {s.name for s in SPECIES}


@workflow("mining.record_use_item")
async def _record_use_item(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!use <item>` — consume one item from the pack
    (services/mining_workflow.py ``use_item`` verbatim @ 87bbe1d). Food /
    boosters (``energy.RESTORE_VALUES``: ration / energy drink / cooked
    fish) restore mining energy: the item debit and the settled energy
    raise commit in ONE txn (the oracle's Q-0071 posture); a full bar
    refuses BEFORE any write (ValidatorError aborts the txn — no row, no
    audit, the oracle's no-txn ok=False twin). Torch / dynamite / any
    other item is the flavour-only debit. NOT money-bearing — no coins
    move; the energy upsert keeps the slice-1 lockless plain posture
    (game pacing, never money — the fishing-energy precedent; a raced
    double-use can at worst double-settle a regen tick, never mint or
    strand coins)."""
    from sb.domain.mining import energy

    uid, gid, now = _ids(ctx)
    item = _rest_from(ctx)
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    if inventory.get(item, 0) < 1:
        raise ValidatorError(f"You don't have **{item}** to use.")
    restore = energy.restore_value(item)
    if restore is not None:
        e_state = energy.EnergyState(
            *await store.get_energy(uid, gid, conn=conn))
        if energy.settle(e_state, now).current >= energy.MAX_ENERGY:
            raise ValidatorError(
                "Your energy is already full — save it for later.")
        restored = energy.restore(e_state, now, restore)
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=item, delta=-1)
        await store.set_energy(uid, gid, restored.current,
                               restored.updated_at, conn=conn)
        return LegOutcome(
            step=StepResult(uid, "use_item", True), before={},
            after={"item": item,
                   "message": f"You consume **{item}** and recover energy "
                              f"({energy.bar(restored.current)})."})
    if item == "torch":
        message = "You light a torch and peer into the darkness..."
    elif item == "dynamite":
        message = "You ignite dynamite and blow a new path in the mine!"
    else:
        message = f"You used **{item}**, but nothing special happened."
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=item, delta=-1)
    return LegOutcome(step=StepResult(uid, "use_item", True), before={},
                      after={"item": item, "message": message})


@workflow("mining.record_cook")
async def _record_cook(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!cook [amount] <fish>` — cook caught fish into ``cooked fish`` food
    at a built 🔥 Campfire (services/mining_workflow.py ``cook`` verbatim @
    87bbe1d; the leading-amount split is the cog's ``parts[0].isdigit()``
    parse, so ``!cook 3 minnow`` cooks three and ``!cook minnow 3`` refuses
    on the literal ``minnow 3`` — NOT the sell/buy trailing-qty grammar).
    Gates (campfire / not-a-fish / short stack) are pure reads that abort
    the txn row-less; the raw-fish debit + cooked-fish grant commit in ONE
    txn (Q-0071). NOT money-bearing — raw fish sell for coins through the
    market; cooking trades a fish for a meal."""
    from sb.domain.mining import energy, structures

    uid, gid, _ = _ids(ctx)
    rest = _rest_from(ctx)
    qty = 1
    parts = rest.split()
    if len(parts) > 1 and parts[0].isdigit():
        qty = max(1, int(parts[0]))
        rest = " ".join(parts[1:])
    fish = rest
    built = await store.get_structures(uid, gid, conn=conn)
    if not structures.cooking_unlocked(built.get(structures.CAMPFIRE, 0)):
        raise ValidatorError(
            "You need a 🔥 **Campfire** to cook — build one with "
            "`!build campfire`.")
    if not is_fish(fish):
        raise ValidatorError(
            f"**{fish}** isn't a fish you can cook — catch fish with "
            "`!fish`.")
    inventory = await store.get_mining_inventory(uid, gid, conn=conn)
    have = inventory.get(fish, 0)
    if have < qty:
        raise ValidatorError(
            f"You only have **{have}× {fish}** to cook (wanted {qty}).")
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=fish, delta=-qty)
    await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                   item=COOKED_FISH, delta=qty)
    gain = energy.RESTORE_VALUES.get(COOKED_FISH, 0)
    return LegOutcome(
        step=StepResult(uid, "cook", True), before={},
        after={"fish": fish, "qty": qty,
               "message": f"🔥 You cook **{qty}× {fish}** into "
                          f"**{qty}× cooked fish** (+{gain} ⚡ each when "
                          f"eaten — `!use cooked fish`)."})


@workflow("mining.erase_subject_structures")
async def _erase_structures(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_structures(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_structures", True),
                      before={}, after={"rows": rows})


@workflow("mining.erase_subject_vault")
async def _erase_vault(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_vault(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_vault", True),
                      before={}, after={"rows": rows})


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
STASH = _op("mining.stash", "mining_stashed", "mining.record_stash", ())
UNSTASH = _op("mining.unstash", "mining_unstashed", "mining.record_unstash",
              ())
STASH_ALL = _op("mining.stash_all", "mining_stashed_all",
                "mining.record_stash_all", ())
VAULT_UPGRADE = _op("mining.vault_upgrade", "mining_vault_upgraded",
                    "mining.record_vault_upgrade", _BALANCE_EMITS)
REPAIR = _op("mining.repair", "mining_repaired", "mining.record_repair",
             _BALANCE_EMITS)
QUICK_CRAFT = _op("mining.quick_craft", "mining_quick_crafted",
                  "mining.record_quick_craft", ())
USE_ITEM = _op("mining.use", "mining_item_used",
               "mining.record_use_item", ())
COOK = _op("mining.cook", "mining_cooked", "mining.record_cook", ())

_OPS = (MINE, HARVEST, EXPLORE, SELL, SELL_ALL, BUY, RESET_INVENTORY,
        EQUIP, UNEQUIP, SAVE_LOADOUT, APPLY_LOADOUT, DELETE_LOADOUT,
        DESCEND, ASCEND, RESEED_WORLD,
        STASH, UNSTASH, STASH_ALL, VAULT_UPGRADE,
        REPAIR, QUICK_CRAFT, USE_ITEM, COOK)

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
    ("mining.record_stash", _record_stash),
    ("mining.record_unstash", _record_unstash),
    ("mining.record_stash_all", _record_stash_all),
    ("mining.record_vault_upgrade", _record_vault_upgrade),
    ("mining.record_repair", _record_repair),
    ("mining.record_quick_craft", _record_quick_craft),
    ("mining.record_use_item", _record_use_item),
    ("mining.record_cook", _record_cook),
    ("mining.erase_subject_structures", _erase_structures),
    ("mining.erase_subject_vault", _erase_vault),
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
