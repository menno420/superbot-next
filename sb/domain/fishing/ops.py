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
together. Slice 2 made the ROD STATE live the same way (!rod / !craftrod
persist ``fishing_rod``; the rod panels read it) — the rod→cast wiring
(rarity_pull on the roll) rides the same rung. Slice 3 made the BAIT
STATE live the same way (!bait / !craftbait / !craftpearl persist
``fishing_bait``; the bait panel reads it) — the bait→cast wiring
(loaded knobs on the roll + the per-cast charge spend) rides the same
rung."""

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
    "BAIT_PURCHASE_REASON",
    "BONUS_CATCH_CHANCE",
    "PEARL_ITEM",
    "ROD_PURCHASE_REASON",
    "register_ops",
    "roll_catch",
    "set_rng_for_tests",
]

#: the shipped economy-ledger reason for a rod purchase
#: (services/fishing_workflow.py ROD_PURCHASE_REASON, verbatim).
ROD_PURCHASE_REASON = "fishing:rod_purchase"

#: the shipped economy-ledger reason for a bait purchase
#: (services/fishing_workflow.py BAIT_PURCHASE_REASON, verbatim).
BAIT_PURCHASE_REASON = "fishing:bait_purchase"

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


@workflow("fishing.erase_subject_rod")
async def _erase_rod(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_rod(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_rod", True),
                      before={}, after={"rows": rows})


@workflow("fishing.erase_subject_bait")
async def _erase_bait(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_bait(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_bait", True),
                      before={}, after={"rows": rows})


# --- the rod ladder write legs (slice 2): the shipped services/
# fishing_workflow.py buy_rod / craft_rod verbatim, re-homed onto the audited
# one-leg one-txn seam. NO golden drives a funded buy or a stocked craft —
# the imported sweep drove only the bare fresh-player invocations
# (goldens/fishing/sweep_rod pins the tier-0 shop render, sweep_craftrod the
# "need 10 fish" guard — depth.exemptions.fishing guard-only-capture:
# fishing_rod), so the guard bytes in service.py are the only parity surface.
# Both settles are advisory-fenced (store.lock_rod_slot) against the
# read-then-settle money / double-craft race (check_money_race, #217) --------


@workflow("fishing.record_buy_rod")
async def _record_buy_rod(conn, ctx: WorkflowContext) -> LegOutcome:
    """The rod shop's ⬆️ Upgrade button — buy the next rod up the ladder
    (the shipped ``buy_rod``, mirroring ``mining_workflow.vault_upgrade``):
    debit the coin price and raise the owned tier in ONE txn (the debit is
    economy-audited; the balance event emits after commit). The handler
    gates the maxed / insufficient-funds cases out as pure reads before
    this leg runs (no write, no audit row — the oracle's rollback posture),
    so the raises here are defensive."""
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.fishing import rods as rods_mod
    from sb.domain.games import wager

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    # Fence concurrent buy/craft attempts for this player BEFORE the tier
    # read → the debit + tier bump serialize (no double-charge — #217).
    await store.lock_rod_slot(conn, user_id=uid, guild_id=gid)
    current_tier = await store.get_rod_tier(uid, gid, conn=conn)
    nxt = rods_mod.next_rod(current_tier)
    if nxt is None:
        top = rods_mod.rod_for_tier(current_tier)
        raise ValidatorError(
            f"You already wield the **{top.name}** {top.emoji} — the "
            "finest rod there is!")
    try:
        new_balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=nxt.price,
            reason=ROD_PURCHASE_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        balance = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"The **{nxt.name}** {nxt.emoji} costs **{nxt.price}** 🪙 — "
            f"you only have **{balance}** 🪙.") from None
    await store.set_rod_tier(uid, gid, nxt.tier, conn=conn)
    ctx.params["_balance_changes"] = [
        (uid, -nxt.price, new_balance, ROD_PURCHASE_REASON)]
    return LegOutcome(
        step=StepResult(uid, "buy_rod", True), before={},
        after={"tier": nxt.tier, "balance": new_balance,
               "message": f"You upgraded to the **{nxt.name}** "
                          f"{nxt.emoji} for **{nxt.price}** 🪙! "
                          f"Balance: **{new_balance}** 🪙."})


@workflow("fishing.record_craft_rod")
async def _record_craft_rod(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!craftrod` / the rod panels' craft buttons — craft the next rod up
    the ladder from small caught fish (the shipped ``craft_rod``): an
    inventory-only conversion (no coins) — debit the eligible fish
    (smallest-first) and raise the owned tier by one in ONE txn (the
    shipped Q-0071 order). Not money-bearing, but the fish spend is
    advisory-fenced against a concurrent double-craft (the quick_craft
    posture). The handler answers the maxed / not-enough-fish cases as
    pure reads before this leg runs — the only path any golden pins
    (goldens/fishing/sweep_craftrod)."""
    from sb.domain.fishing import crafting, rods as rods_mod
    from sb.domain.mining.store import get_mining_inventory, update_mining_item

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    await store.lock_rod_slot(conn, user_id=uid, guild_id=gid)
    current_tier = await store.get_rod_tier(uid, gid, conn=conn)
    nxt = rods_mod.next_rod(current_tier)
    if nxt is None:
        top = rods_mod.rod_for_tier(current_tier)
        raise ValidatorError(
            f"You already wield the **{top.name}** {top.emoji} — the "
            "finest rod there is!")
    recipe = rods_mod.rod_recipe(nxt.tier)
    if recipe is None:  # defensive — every non-starter tier has a recipe
        raise ValidatorError(
            f"The **{nxt.name}** {nxt.emoji} can't be crafted from fish "
            "— buy it with `!rod`.")
    inventory = await get_mining_inventory(uid, gid, conn=conn)
    spend = crafting.plan_fish_spend(inventory, recipe)
    if spend is None:
        raise ValidatorError(
            f"You need **{recipe.fish_count}** fish of size ≤ "
            f"**{recipe.max_size_rank}** to craft the **{nxt.name}** "
            f"{nxt.emoji} — catch more fish with `!fish` (or buy it "
            "with `!rod`).")
    for name, qty in spend.items():
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=name, delta=-qty)
    await store.set_rod_tier(uid, gid, nxt.tier, conn=conn)
    used = ", ".join(f"{qty}× {name}" for name, qty in spend.items())
    return LegOutcome(
        step=StepResult(uid, "craft_rod", True), before={},
        after={"tier": nxt.tier, "spend": dict(spend),
               "message": f"Crafted the **{nxt.name}** {nxt.emoji} from "
                          f"**{used}** — cast with `!fish` to feel the "
                          "difference!"})


# --- the bait shelf write legs (slice 3): the shipped services/
# fishing_workflow.py buy_bait / craft_bait / craft_pearl_bait / craft_charm
# verbatim, re-homed onto the audited one-leg one-txn seam. NO golden drives
# a funded buy or a stocked craft — the imported sweeps drove only the bare
# fresh-player invocations (goldens/fishing/sweep_bait + sweep_craftbait pin
# the bait-less shop render, sweep_craftpearl the no-pearls guard,
# sweep_craftcharm the recipe listing — depth.exemptions.fishing
# guard-only-capture: fishing_bait), so the guard bytes in service.py are the
# only parity surface. All settles are advisory-fenced (store.lock_bait_slot /
# store.lock_charm_slot) against the read-then-settle money / double-craft
# race (check_money_race, #217) ----------------------------------------------


@workflow("fishing.record_buy_bait")
async def _record_buy_bait(conn, ctx: WorkflowContext) -> LegOutcome:
    """The bait shop's buy select — buy one pack of the picked bait (the
    shipped ``buy_bait``, mirroring ``buy_rod``): debit the coin price
    and load/stack the bait in ONE txn (the debit is economy-audited;
    the balance event emits after commit). A player loads at most one
    bait at a time: buying the SAME bait again stacks its charges;
    buying a DIFFERENT bait replaces the loadout. The handler gates the
    unknown-bait / insufficient-funds cases out as pure reads before
    this leg runs (no write, no audit row — the oracle's rollback
    posture), so the raises here are defensive."""
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.fishing import bait as bait_mod
    from sb.domain.games import wager

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    bait = bait_mod.bait_by_key(str(ctx.params.get("bait_key", "")))
    if bait is None:  # defensive — the handler validated the key
        raise ValidatorError("That bait doesn't exist on the shelf.")
    # Fence concurrent buy/craft attempts for this player BEFORE the
    # loadout read → the debit + load serialize (no double-charge — #217).
    await store.lock_bait_slot(conn, user_id=uid, guild_id=gid)
    cur_key, cur_charges = await store.get_active_bait(uid, gid, conn=conn)
    stacking = cur_key == bait.key and cur_charges > 0
    new_charges = (cur_charges if stacking else 0) + bait.charges
    try:
        new_balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=bait.price,
            reason=BAIT_PURCHASE_REASON, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        balance = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"A pack of **{bait.name}** {bait.emoji} costs "
            f"**{bait.price}** 🪙 — you only have "
            f"**{balance}** 🪙.") from None
    await store.set_active_bait(uid, gid, bait.key, new_charges, conn=conn)
    ctx.params["_balance_changes"] = [
        (uid, -bait.price, new_balance, BAIT_PURCHASE_REASON)]
    verb = "Topped up" if stacking else "Loaded"
    return LegOutcome(
        step=StepResult(uid, "buy_bait", True), before={},
        after={"bait": bait.key, "charges": new_charges,
               "balance": new_balance,
               "message": f"{verb} **{bait.name}** {bait.emoji} "
                          f"({bait_mod.bait_effect_text(bait)}) — "
                          f"**{new_charges}** casts ready for "
                          f"**{bait.price}** 🪙. "
                          f"Balance: **{new_balance}** 🪙."})


@workflow("fishing.record_craft_bait")
async def _record_craft_bait(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!craftbait <bait>` / the bait shop's craft select — craft one
    pack from small caught fish (the shipped ``craft_bait``): an
    inventory-only conversion (no coins) — debit the eligible fish
    (smallest-first) and load/stack the bait in ONE txn (the shipped
    Q-0071 order). Not money-bearing, but the fish spend is
    advisory-fenced against a concurrent double-craft (the quick_craft
    posture). The handler answers the unknown-bait / not-enough-fish
    cases as pure reads before this leg runs."""
    from sb.domain.fishing import bait as bait_mod, crafting
    from sb.domain.mining.store import get_mining_inventory, update_mining_item

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    key = str(ctx.params.get("bait_key", ""))
    bait = bait_mod.bait_by_key(key)
    recipe = bait_mod.craft_recipe(key)
    if bait is None or recipe is None:  # defensive — handler-validated
        raise ValidatorError(
            "That bait can't be crafted from fish — buy it with `!bait`.")
    await store.lock_bait_slot(conn, user_id=uid, guild_id=gid)
    inventory = await get_mining_inventory(uid, gid, conn=conn)
    spend = crafting.plan_fish_spend(inventory, recipe)
    if spend is None:
        raise ValidatorError(
            f"You need **{recipe.fish_count}** fish of size ≤ "
            f"**{recipe.max_size_rank}** to craft **{bait.name}** "
            f"{bait.emoji} — catch more small fish with `!fish`.")
    cur_key, cur_charges = await store.get_active_bait(uid, gid, conn=conn)
    stacking = cur_key == bait.key and cur_charges > 0
    new_charges = (cur_charges if stacking else 0) + bait.charges
    for name, qty in spend.items():
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=name, delta=-qty)
    await store.set_active_bait(uid, gid, bait.key, new_charges, conn=conn)
    used = ", ".join(f"{qty}× {name}" for name, qty in spend.items())
    verb = "Topped up" if stacking else "Crafted"
    return LegOutcome(
        step=StepResult(uid, "craft_bait", True), before={},
        after={"bait": bait.key, "charges": new_charges,
               "spend": dict(spend),
               "message": f"{verb} **{bait.name}** {bait.emoji} "
                          f"({bait_mod.bait_effect_text(bait)}) from "
                          f"**{used}** — **{new_charges}** casts ready."})


@workflow("fishing.record_craft_pearl_bait")
async def _record_craft_pearl_bait(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!craftpearl` / the bait shop's pearl select — craft one pack of
    the premium bait from **pearls** (the shipped ``craft_pearl_bait``),
    the rare reel-drop's sole sink: an inventory-only conversion (no
    coins) — debit the pearls and load/stack the bait in ONE txn (the
    shipped Q-0071 order). Advisory-fenced like the other bait legs. The
    handler answers the unknown-bait / not-enough-pearls cases as pure
    reads before this leg runs — the only path any golden pins
    (goldens/fishing/sweep_craftpearl)."""
    from sb.domain.fishing import bait as bait_mod
    from sb.domain.mining.store import get_mining_inventory, update_mining_item

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    key = str(ctx.params.get("bait_key", ""))
    bait = bait_mod.bait_by_key(key)
    pearl_cost = bait_mod.pearl_recipe(key)
    if bait is None or pearl_cost is None:  # defensive — handler-validated
        raise ValidatorError(
            "That bait isn't crafted from pearls — buy it with `!bait`.")
    await store.lock_bait_slot(conn, user_id=uid, guild_id=gid)
    inventory = await get_mining_inventory(uid, gid, conn=conn)
    have = inventory.get(PEARL_ITEM, 0)
    if have < pearl_cost:
        raise ValidatorError(
            f"You need **{pearl_cost}** 🦪 pearls to craft "
            f"**{bait.name}** {bait.emoji} — you have **{have}**. "
            "Pearls drop rarely when you reel in a fish (bigger fish, "
            "better odds).")
    cur_key, cur_charges = await store.get_active_bait(uid, gid, conn=conn)
    stacking = cur_key == bait.key and cur_charges > 0
    new_charges = (cur_charges if stacking else 0) + bait.charges
    await update_mining_item(conn, user_id=uid, guild_id=gid,
                             item=PEARL_ITEM, delta=-pearl_cost)
    await store.set_active_bait(uid, gid, bait.key, new_charges, conn=conn)
    verb = "Topped up" if stacking else "Crafted"
    return LegOutcome(
        step=StepResult(uid, "craft_pearl_bait", True), before={},
        after={"bait": bait.key, "charges": new_charges,
               "message": f"{verb} **{bait.name}** {bait.emoji} "
                          f"({bait_mod.bait_effect_text(bait)}) from "
                          f"**{pearl_cost}** 🦪 pearls — "
                          f"**{new_charges}** casts ready."})


@workflow("fishing.record_craft_charm")
async def _record_craft_charm(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!craftcharm <charm>` — craft one CHARM-slot fishing charm from
    small caught fish (the shipped ``craft_charm``, mirroring
    ``craft_bait``): an inventory-only conversion (no coins) — debit the
    eligible fish (smallest-first) and grant one charm item into the
    shared mining inventory in ONE txn (the shipped Q-0071 order). The
    charm then equips through the normal mining gear panel (its name
    byte-matches the mining equipment catalog). Not money-bearing, but
    the fish spend is advisory-fenced against a concurrent double-craft
    (the quick_craft posture). The handler answers the unknown-charm /
    not-enough-fish cases as pure reads before this leg runs."""
    from sb.domain.fishing import crafting, gear as gear_mod
    from sb.domain.mining.store import get_mining_inventory, update_mining_item

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    recipe = gear_mod.charm_recipe(str(ctx.params.get("charm_name", "")))
    if recipe is None:  # defensive — the handler validated the name
        raise ValidatorError(
            "That charm can't be crafted from fish — buy it with "
            "`!gear`.")
    await store.lock_charm_slot(conn, user_id=uid, guild_id=gid)
    inventory = await get_mining_inventory(uid, gid, conn=conn)
    spend = crafting.plan_fish_spend(inventory, recipe)
    if spend is None:
        raise ValidatorError(
            f"You need **{recipe.fish_count}** fish of size ≤ "
            f"**{recipe.max_size_rank}** to craft a **{recipe.charm}** "
            "— catch more fish with `!fish`.")
    for name, qty in spend.items():
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=name, delta=-qty)
    await update_mining_item(conn, user_id=uid, guild_id=gid,
                             item=recipe.charm, delta=1)
    used = ", ".join(f"{qty}× {name}" for name, qty in spend.items())
    return LegOutcome(
        step=StepResult(uid, "craft_charm", True), before={},
        after={"charm": recipe.charm, "spend": dict(spend),
               "message": f"Crafted a **{recipe.charm}** from "
                          f"**{used}** — equip it from the gear panel "
                          "(`!gear`) to fish better."})


_XP_EMITS = (
    EventEmitSpec("game_xp.awarded",
                  WorkflowRef("games.game_xp_awarded_payload"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec("game_xp.level_up",
                  WorkflowRef("games.game_xp_levelup_payload"),
                  DeliveryClass.BEST_EFFORT),
)

_BALANCE_EMITS = (
    EventEmitSpec("economy.balance_changed",
                  WorkflowRef("games.balance_payload_0"),
                  DeliveryClass.BEST_EFFORT),
)

CAST = CompoundOpSpec(
    op_key="fishing.cast", domain="fishing", lane=WorkflowLane.DOMAIN,
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB, WorkflowRef("fishing.record_cast"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fish_caught", emits=_XP_EMITS)

BUY_ROD = CompoundOpSpec(
    op_key="fishing.buy_rod", domain="fishing", lane=WorkflowLane.DOMAIN,
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_buy_rod"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_rod_bought", emits=_BALANCE_EMITS)

CRAFT_ROD = CompoundOpSpec(
    op_key="fishing.craft_rod", domain="fishing", lane=WorkflowLane.DOMAIN,
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_craft_rod"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_rod_crafted", emits=())

BUY_BAIT = CompoundOpSpec(
    op_key="fishing.buy_bait", domain="fishing", lane=WorkflowLane.DOMAIN,
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_buy_bait"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_bait_bought", emits=_BALANCE_EMITS)

CRAFT_BAIT = CompoundOpSpec(
    op_key="fishing.craft_bait", domain="fishing", lane=WorkflowLane.DOMAIN,
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_craft_bait"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_bait_crafted", emits=())

CRAFT_PEARL_BAIT = CompoundOpSpec(
    op_key="fishing.craft_pearl_bait", domain="fishing",
    lane=WorkflowLane.DOMAIN, authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_craft_pearl_bait"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_pearl_bait_crafted", emits=())

CRAFT_CHARM = CompoundOpSpec(
    op_key="fishing.craft_charm", domain="fishing",
    lane=WorkflowLane.DOMAIN, authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_craft_charm"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_charm_crafted", emits=())

_OPS = (CAST, BUY_ROD, CRAFT_ROD, BUY_BAIT, CRAFT_BAIT, CRAFT_PEARL_BAIT,
        CRAFT_CHARM)

_REF_TABLE = (
    ("fishing.record_cast", _record_cast),
    ("fishing.record_buy_rod", _record_buy_rod),
    ("fishing.record_craft_rod", _record_craft_rod),
    ("fishing.record_buy_bait", _record_buy_bait),
    ("fishing.record_craft_bait", _record_craft_bait),
    ("fishing.record_craft_pearl_bait", _record_craft_pearl_bait),
    ("fishing.record_craft_charm", _record_craft_charm),
    ("fishing.erase_subject_catch_log", _erase_catch_log),
    ("fishing.erase_subject_energy", _erase_energy),
    ("fishing.erase_subject_venue", _erase_venue),
    ("fishing.erase_subject_rod", _erase_rod),
    ("fishing.erase_subject_bait", _erase_bait),
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
