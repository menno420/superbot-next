"""Fishing K7 lanes (band 6) — the CORE cast (the shipped legacy
``fish()`` path): level-gated inverse-size roll + commit (dex upsert +
pearl/coral materials + the fish as a tangible mining_inventory item +
game-XP award) in ONE leg txn.

DEVIATION (D-0043) — updated by the cast-leg depth wiring: the cast
now runs the FULL oracle knob compound. ``cast_open``
(service.py) is the shipped ``begin_cast``
(services/fishing_workflow.py:384-518 @cdb26804): one structures read
drives the Boathouse regen interval + the Tide Pool/Dock/Fishery
knobs; rod/venue/weather/bait/gear are read live and compounded —
``effective_pull = rod × bait × weather × gear × tide_pool`` — the
catch is ROLLED AT CAST TIME (the oracle ``roll_cast`` timing), energy
is spent only post-roll, and one bait charge is spent per cast
(clear-at-0). The rolled cast waits in the in-memory pending-cast
registry (service.py — the oracle ``active_casts``/view-state,
ADR-002-accepted) until Reel commits it through this module's
``_record_cast`` = the shipped ``commit_catch``
(fishing_workflow.py:174-278): draws bonus → pearl → coral (pinned
order), writes record_catch → pearl → coral → fish (×2 on bonus) → xp
in ONE leg txn, and answers the oracle ``_finish_caught`` result copy
(views/fishing/cast_view.py:398-456). Every knob defaults exactly
neutral (no row ⇒ ×1.0 / +0.0), so a fresh player's cast is
byte-identical to the pre-wiring goldens.

TIMING RUNG (D-0043) — COMPLETE but for the continuation (slice 1
click-gated resolution + slice 2 live edits & full enforcement,
service.py): the cast ROLLS its timing at cast time (bite delay on the
compounded ``effective_bite_speed`` at the venue band + the fake-out,
both on this module's private cast RNG STRICTLY AFTER the catch roll)
and the Reel click RESOLVES against it — premature spook / one
``premature_grace`` forgive, LATE-window too-slow (slice 2 —
``minigame.reel_is_in_time`` on SYSTEM_CLOCK), and the trophy
reel-fight (per-tap ``roll_escape`` under venue ``base_escape`` × rod
``escape_resist``, each round its own ``FIGHT_INTER_ROUND_DELAY`` +
window). So EVERY timing knob now GATES outcomes. The live panel cues
— fake-out nibble, 🐟 BITE! arm, unprompted got-away, fight-round
prompts — ride the D-0090 kernel one-shot timers +
``push_session_refresh`` seam (wall-clock, process-local per ADR-002;
headless/parity they no-op via EDIT_UNAVAILABLE, and enforcement never
depends on them). STILL PARKED: the ``_FishingDoneView`` Cast-again
continuation (the RESULT_CARD reply stands in — the games-finalization
review's ranked gap 3, a named successor).

RNG POSTURE: the module ``_rng`` stays PRIVATE and unseeded in prod
(the oracle's fresh-``random.Random()`` posture) — NEVER bind it to
the global ``random`` module: the passive chat-XP award draws from the
GLOBAL stream (sb/domain/xp/service.py) and goldens/fishing/sweep_fish
pins ``xp: 25`` — a cast roll on that stream would shift the pinned
byte. The parity runner arms it per case
(``set_rng_for_tests(random.Random(case.seed))``) so cast-write
goldens replay deterministically."""

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
    "CORAL_ITEM",
    "PEARL_ITEM",
    "ROD_PURCHASE_REASON",
    "cast_rng",
    "coral_drop_chance",
    "register_ops",
    "roll_bonus_catch",
    "roll_catch",
    "roll_coral_drop",
    "roll_pearl_drop",
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

#: The module's private cast RNG — unseeded in prod (the oracle's
#: fresh-``random.Random()`` posture, rewards.py takes ``rng or
#: random.Random()``). PRIVATE on purpose — see the module docstring's
#: RNG POSTURE note (never the mining global-bind shape).
_rng: random.Random = random.Random()


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def cast_rng() -> random.Random:
    """The armed cast RNG (for the cast-time roll in ``cast_open`` — the
    same stream the commit draws land on, so a runner-armed seed pins
    the whole species → weight → bonus → pearl → coral trajectory)."""
    return _rng


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


def roll_bonus_catch(rng: random.Random | None = None, *,
                     chance: float | None = None) -> bool:
    """Roll the lucky-double-catch bonus (shipped verbatim —
    utils/fishing/rewards.py ``roll_bonus_catch``). *chance* defaults to
    :data:`BONUS_CATCH_CHANCE`; a built Fishery raises it (``begin_cast``
    fixes it onto the pending cast) and it is clamped to ``[0, 1]``."""
    effective = BONUS_CATCH_CHANCE if chance is None else chance
    effective = min(1.0, max(0.0, effective))
    r = rng or random.Random()
    return r.random() < effective


def roll_pearl_drop(size_rank: int,
                    rng: random.Random | None = None) -> bool:
    """Roll a pearl drop for a landed fish of *size_rank* (shipped
    verbatim — utils/fishing/rewards.py ``roll_pearl_drop``)."""
    r = rng or random.Random()
    return r.random() < pearl_drop_chance(size_rank)


def coral_drop_chance(venue: str) -> float:
    """The coral-drop probability for a landed catch made in *venue*
    (shipped verbatim — utils/fishing/rewards.py ``coral_drop_chance``):
    :data:`CORAL_DROP_CHANCE` in deepwater, ``0.0`` everywhere else —
    coral is a reef find, exclusive to the boat venue."""
    from sb.domain.fishing import venue as venue_mod

    return (CORAL_DROP_CHANCE
            if venue_mod.normalize(venue) == venue_mod.DEEPWATER else 0.0)


def roll_coral_drop(venue: str, rng: random.Random | None = None) -> bool:
    """Roll a coral drop for a landed catch made in *venue* (shipped
    verbatim — utils/fishing/rewards.py ``roll_coral_drop``). Always
    ``False`` outside deepwater — and, load-bearing for the pinned draw
    order: a zero-chance venue returns WITHOUT consuming a draw, exactly
    as shipped, so a shore commit's RNG trajectory is untouched."""
    chance = coral_drop_chance(venue)
    if chance <= 0.0:
        return False
    r = rng or random.Random()
    return r.random() < chance


@workflow("fishing.record_cast")
async def _record_cast(conn, ctx: WorkflowContext) -> LegOutcome:
    """The Reel commit — the shipped ``commit_catch``
    (services/fishing_workflow.py:174-278 @cdb26804) on the audited
    one-leg one-txn seam: draws **bonus → pearl → coral** in the pinned
    order (fishing_workflow.py:207-224 — "the rolls are drawn
    (bonus → pearl → coral) before the transaction so the write set is
    deterministic under an injected rng"), then writes
    record_catch → pearl grant → coral grant → fish grant (2 on a lucky
    double) → xp award, all on this leg's conn. The result message is
    the shipped ``_finish_caught`` copy
    (views/fishing/cast_view.py:398-456) verbatim.

    The pending cast rolled at cast time (``cast_open`` = the shipped
    ``begin_cast`` timing) arrives in ``ctx.params`` — species / weight /
    venue / double_catch_chance / level_before. A Reel with NO pending
    cast (a direct op invocation) keeps the roll-at-commit STARTER
    fallback = the shipped legacy ``fish()`` seam
    (fishing_workflow.py:281-289: ``roll_cast`` defaults — starter rod,
    shore, base double-catch chance)."""
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    now = int(ctx.clock().timestamp())

    species = catalog.species_by_name(str(ctx.params.get("species", "")))
    if species is not None:
        # the pending cast, rolled at cast time (begin_cast → roll_cast).
        weight = float(ctx.params.get("weight", 0.0))
        venue = str(ctx.params.get("venue", catalog.SHORE_VENUE))
        double_catch_chance = float(
            ctx.params.get("double_catch_chance", BONUS_CATCH_CHANCE))
        level_before = int(ctx.params.get("level_before", 1))
        catch = catalog.Catch(species=species, weight=weight)
    else:
        # legacy fallback — the shipped ``fish()`` seam: roll now at the
        # starter profile (rod pull 1.0, shore pool, base double chance).
        from sb.domain.games.store import game_xp_rows

        xp_rows = {str(r["game"]): int(r["xp"])
                   for r in await game_xp_rows(uid, gid, conn=conn)}
        level_before = catalog.fishing_level_from_xp(
            xp_rows.get(game_xp.GAME_FISHING, 0))
        venue = catalog.SHORE_VENUE
        double_catch_chance = BONUS_CATCH_CHANCE
        catch = roll_catch(level_before, _rng)
        if catch is None:
            raise ValidatorError("🎣 The waters are quiet — the fish "
                                 "catalog is empty.")

    # the pinned draw order: bonus → pearl → coral (commit_catch
    # L207-210; a shore venue's coral roll consumes NO draw — see
    # roll_coral_drop).
    bonus = roll_bonus_catch(_rng, chance=double_catch_chance)
    grant = 2 if bonus else 1
    pearl = roll_pearl_drop(catch.species.size_rank, _rng)
    coral = roll_coral_drop(venue, _rng)
    prior_best = await store.record_catch(
        conn, user_id=uid, guild_id=gid, species=catch.species.name,
        weight=catch.weight, now=now)
    from sb.domain.mining.store import update_mining_item

    # The rare-material drops (pearl, coral) are granted before the fish
    # so the fish grant stays the last inventory write (the shipped
    # stable seam, commit_catch L221-224).
    if pearl:
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=PEARL_ITEM, delta=1)
    if coral:
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=CORAL_ITEM, delta=1)
    await update_mining_item(conn, user_id=uid, guild_id=gid,
                             item=catch.species.name, delta=grant)
    award = await game_xp.award_in_txn(
        conn, user_id=uid, guild_id=gid, game=game_xp.GAME_FISHING,
        action="fish", now=now)
    # level_after from the award's post-write game total (the shipped
    # ``fishing_level_from_xp(award.game_total)``, commit_catch L264).
    level_after = catalog.fishing_level_from_xp(award.new_game_xp)
    unlocked_bigger = level_after > level_before
    # the shipped GameXpAward.note, rendered only on a shared-level
    # boundary (game_xp_service.py: "🎉 Game level up — …").
    xp_note = (f"🎉 Game level up — you reached "
               f"**Level {award.new_level}**!"
               if award.leveled_up else None)
    new_best = catch.weight > 0 and (prior_best is None
                                     or catch.weight > prior_best)
    ctx.params["_balance_changes"] = []
    ctx.params["_gxp"] = award

    # --- the result copy: views/fishing/cast_view.py _finish_caught
    # (L398-456) verbatim — title + description lines, byte-for-byte.
    from sb.domain.fishing import minigame
    from sb.domain.fishing import venue as venue_mod

    # at level_AFTER, deliberately: the shipped result card judges the
    # trophy title at ``result.fishing_level`` — the POST-award level
    # (cast_view.py:413; FishResult.fishing_level = level_after,
    # commit_catch L262-266). The level_BEFORE check at cast_view.py:333
    # is a different branch — the BITE-phase reel-fight decision, which
    # rides the parked timing rung. Codex #373 flagged the level-up
    # suppression; it is the oracle's own shipped result-title semantics.
    trophy = minigame.is_trophy(catch.species, level_after)
    pool_size = len(catalog.species_for_venue(catch.species.venue))
    profile = venue_mod.profile_for(venue)
    title = "🏆 Trophy landed!" if trophy else "🎣 Caught it!"
    desc = (
        f"You reeled in {catch.species.emoji} a "
        f"**{catch.species.name.title()}**!  "
        f"(size #{catch.species.size_rank} of {pool_size} "
        f"{profile.name.lower()})"
    )
    if catch.weight > 0:
        desc += f"\n⚖️ It weighs **{catch.weight:g} kg**."
        if new_best:
            desc += " 🏅 **New personal best!**"
    if bonus:
        desc += (
            f"\n🍀 **Lucky double catch!** A second {catch.species.emoji} "
            f"**{catch.species.name.title()}** for the craft bin."
        )
    if pearl:
        desc += (
            "\n🦪 **A pearl!** A rare crafting material — save them up to "
            "craft the premium **Royal Feast** bait (`!craftpearl`)."
        )
    if coral:
        desc += (
            "\n🪸 **A piece of coral!** A rare deepwater find — carve it "
            "into cosmetic curios for your collection (`!curios`)."
        )
    if unlocked_bigger:
        cap = catalog.max_size_rank_for_level(level_after,
                                              catch.species.venue)
        desc += (
            f"\n\n🌟 **Fishing level {level_after}!** "
            f"You can now catch fish up to size #{cap}."
        )
    if xp_note:
        desc += f"\n{xp_note}"
    return LegOutcome(
        step=StepResult(uid, "cast", True), before={},
        after={"species": catch.species.name, "weight": catch.weight,
               "venue": venue, "bonus_catch": bonus, "pearl_found": pearl,
               "coral_found": coral, "new_personal_best": new_best,
               "fishing_level": level_after,
               "message": f"{title}\n{desc}"})


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
    (goldens/fishing/sweep_craftrod). Ledgered posture (cross-craft
    fish spend): the fish-spending crafts are fenced PER KIND (rod /
    bait / charm each key their own advisory lock), so a raced craftrod
    × craftbait/craftcharm pair can both plan over one fish stack and
    the floor-0 ``update_mining_item`` debit masks the loser — two
    grants from one stack, matching-or-narrower than the oracle (which
    fenced nothing; same-kind races ARE serialized here). Materials,
    never coins, so ``check_money_race`` does not cover it; if a coin
    leg ever joins a cross-kind spend, the fix is one SHARED key (the
    ``lock_coral_slot`` precedent)."""
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
    cases as pure reads before this leg runs. Cross-craft fish-spend
    posture ledgered at ``_record_craft_rod`` (per-kind locks — a raced
    OTHER-kind craft over the same stack is not serialized)."""
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
    not-enough-fish cases as pure reads before this leg runs.
    Cross-craft fish-spend posture ledgered at ``_record_craft_rod``
    (per-kind locks — a raced OTHER-kind craft over the same stack is
    not serialized)."""
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


# --- the coral sinks + structure builds (slice 4, FINAL): the shipped
# services/fishing_workflow.py craft_curio and services/mining_workflow.py
# build_structure verbatim, re-homed onto the audited one-leg one-txn seam.
# NO golden drives a stocked carve or a funded build — the imported sweeps
# drove only the bare fresh-player invocations (goldens/fishing/sweep_curios
# pins the 0-coral shelf read, sweep_craftcurio the not-carvable guard, and
# the four structure sweeps pin the not-built panel renders — all pure
# reads), so the guard bytes in service.py are the only parity surface. The
# curio carve and the build share ONE coral fence (store.lock_coral_slot)
# so a racing carve × Build over the same floor-at-zero coral row
# serializes (PR #350 codex finding); the build is money-bearing and
# additionally fenced first (mining.store.lock_structure_build_slot,
# stable order) per #217. mining_structures is
# written ONLY through sb.domain.mining.store.set_structure_level (the
# sole-writer seam; the fishing/ops lazy-import precedent, L124) -------------


@workflow("fishing.record_craft_curio")
async def _record_craft_curio(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!craftcurio <curio>` — carve one cosmetic curio from **coral**
    (the shipped ``craft_curio``, coral's analogue of
    ``craft_pearl_bait`` with a cosmetic TREASURE target): an
    inventory-only conversion (no coins, never sellable) — debit the
    coral and grant the curio item in ONE txn (the shipped Q-0071
    order). Carving a curio you already own simply adds another copy
    (harmless; the collection tally counts distinct curios). Not
    money-bearing, but the coral spend is advisory-fenced against a
    concurrent double-spend — the SHARED coral fence
    (store.lock_coral_slot) the structure-build leg also takes, so a
    racing carve × Build over one coral stack serializes (the
    floor-at-zero inventory decrement would otherwise let both spenders
    pass their pre-spend guards — PR #350 codex finding). The handler
    answers the not-carvable / not-enough-coral cases as pure reads
    before this leg runs."""
    from sb.domain.fishing import curios as curios_mod
    from sb.domain.mining.store import get_mining_inventory, update_mining_item

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    curio = curios_mod.curio_by_key(str(ctx.params.get("curio_key", "")))
    if curio is None:  # defensive — the handler validated the key
        raise ValidatorError(
            "That isn't a carvable curio — see `!curios` for the "
            "collection.")
    await store.lock_coral_slot(conn, user_id=uid, guild_id=gid)
    inventory = await get_mining_inventory(uid, gid, conn=conn)
    have = inventory.get(CORAL_ITEM, 0)
    if have < curio.coral_cost:
        raise ValidatorError(
            f"You need **{curio.coral_cost}** 🪸 coral to carve "
            f"**{curio.name}** {curio.emoji} — you have **{have}**. "
            "Coral drops rarely when you reel in a fish out in "
            "**deepwater** (`!sail` to the boat first).")
    await update_mining_item(conn, user_id=uid, guild_id=gid,
                             item=CORAL_ITEM, delta=-curio.coral_cost)
    await update_mining_item(conn, user_id=uid, guild_id=gid,
                             item=curio.item, delta=1)
    owned, total = curios_mod.collection_progress(
        {**inventory, curio.item: inventory.get(curio.item, 0) + 1})
    return LegOutcome(
        step=StepResult(uid, "craft_curio", True), before={},
        after={"curio": curio.key, "owned": owned, "total": total,
               "message": f"Carved **{curio.name}** {curio.emoji} from "
                          f"**{curio.coral_cost}** 🪸 coral — a cosmetic "
                          "collectible for your shelf. Collection: "
                          f"**{owned}/{total}** curios."})


def _build_success_suffix(structure: str, new_level: int) -> str:
    """The structure-specific reward line appended to a successful build
    (the shipped ``mining_workflow._build_success_suffix``, the four
    fishing branches verbatim — the forge/home branches ride the mining
    build lane's own deferred port; this op only ever builds the fishing
    structures)."""
    from sb.domain.mining import structures

    if structure == structures.TIDE_POOL:
        mult = structures.tide_pool_pull_mult(new_level)
        pct = round((mult - 1.0) * 100)
        return f" Your casts now pull **+{pct}%** toward rarer fish."
    if structure == structures.DOCK:
        mult = structures.dock_bite_speed_mult(new_level)
        pct = round((1.0 - mult) * 100)
        return f" Fish now bite **{pct}%** faster."
    if structure == structures.BOATHOUSE:
        mult = structures.boathouse_regen_mult(new_level)
        pct = round((1.0 - mult) * 100)
        return f" Your fishing energy now refills **{pct}%** faster."
    if structure == structures.FISHERY:
        pct = round(structures.fishery_bonus_chance(new_level) * 100)
        return f" Your reels now have **+{pct}%** chance of a double catch."
    return ""


@workflow("fishing.record_build_structure")
async def _record_build_structure(conn, ctx: WorkflowContext) -> LegOutcome:
    """The structure panels' Build buttons — build/upgrade one coral
    structure one level (the shipped ``mining_workflow.build_structure``,
    the §7.5 coin + material sink): debit the coins, consume the build
    materials, and raise the structure level by one in ONE txn (the
    vault_upgrade precedent extended with a material leg — every part
    commits together or not at all; the debit is economy-audited with
    the shipped ``mining:{structure}_build`` reason; the balance event
    emits after commit). #217 posture: the (guild, user) build slot is
    advisory-fenced BEFORE the level/inventory reads so two racing
    builds serialize, and the SHARED coral fence (store.lock_coral_slot,
    taken second — a stable order, the carve leg holds only that one
    key) serializes a build racing a `!craftcurio` over the same
    floor-at-zero coral row (PR #350 codex finding). The handler gates
    the maxed / short-on-materials / insufficient-funds cases out as
    pure reads before this leg runs (no write, no audit row — the
    oracle's rollback posture), so the raises here are defensive."""
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.games import wager
    from sb.domain.mining import market, structures, workshop
    from sb.domain.mining.store import (
        get_mining_inventory,
        get_structures,
        lock_structure_build_slot,
        update_mining_item,
    )

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    structure = str(ctx.params.get("structure", "")).strip().lower()
    if not structures.is_structure(structure):
        raise ValidatorError(
            f"**{structure or '(blank)'}** isn't a buildable structure.")
    display = structures.display_name(structure)
    await lock_structure_build_slot(conn, user_id=uid, guild_id=gid)
    # the shared coral-spend fence, AFTER the build fence (stable order;
    # the curio leg holds only the coral key — no deadlock cycle): a
    # racing carve now blocks until this txn commits and re-reads the
    # decremented coral instead of double-granting off the pre-spend
    # count (the GREATEST(0, …) floor — PR #350 codex finding).
    await store.lock_coral_slot(conn, user_id=uid, guild_id=gid)
    built = await get_structures(uid, gid, conn=conn)
    level = built.get(structure, 0)
    cost = structures.build_cost(structure, level)
    if cost is None:
        name = structures.level_name(structure, level)
        raise ValidatorError(
            f"Your {display} is already at its maximum level "
            f"(**{name}**).")
    # Material check first, for a clean message (the shipped craft
    # precedent) — the coin debit below handles the affordability failure.
    inventory = await get_mining_inventory(uid, gid, conn=conn)
    if any(inventory.get(mat, 0) < qty
           for mat, qty in cost.materials.items()):
        raise ValidatorError(
            f"Building the {display} needs "
            f"{workshop.describe_materials(cost.materials)} "
            f"plus {cost.coins} 🪙 — you're short on materials.")
    reason = market.structure_build_reason(structure)
    try:
        new_balance = await wager.debit_in_txn(
            conn, guild_id=gid, user_id=uid, amount=cost.coins,
            reason=reason, actor_id=uid)
    except InsufficientFundsError:
        from sb.domain.economy.store import get_coins

        balance = await get_coins(uid, gid, conn=conn)
        raise ValidatorError(
            f"Building the {display} costs **{cost.coins}** 🪙 — you "
            f"only have **{balance}** 🪙.") from None
    for mat, qty in cost.materials.items():
        await update_mining_item(conn, user_id=uid, guild_id=gid,
                                 item=mat, delta=-qty)
    from sb.domain.mining.store import set_structure_level

    await set_structure_level(conn, user_id=uid, guild_id=gid,
                              structure=structure, level=level + 1)
    ctx.params["_balance_changes"] = [
        (uid, -cost.coins, new_balance, reason)]
    new_name = structures.level_name(structure, level + 1)
    suffix = _build_success_suffix(structure, level + 1)
    return LegOutcome(
        step=StepResult(uid, "build_structure", True), before={},
        after={"structure": structure, "level": level + 1,
               "balance": new_balance,
               "message": f"{display} built to **{new_name}** for "
                          f"{workshop.describe_materials(cost.materials)} "
                          f"+ {cost.coins} 🪙.{suffix} "
                          f"Balance: **{new_balance}** 🪙."})


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

CRAFT_CURIO = CompoundOpSpec(
    op_key="fishing.craft_curio", domain="fishing",
    lane=WorkflowLane.DOMAIN, authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_craft_curio"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_curio_carved", emits=())

BUILD_STRUCTURE = CompoundOpSpec(
    op_key="fishing.build_structure", domain="fishing",
    lane=WorkflowLane.DOMAIN, authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("fishing.record_build_structure"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="fishing_structure_built", emits=_BALANCE_EMITS)

_OPS = (CAST, BUY_ROD, CRAFT_ROD, BUY_BAIT, CRAFT_BAIT, CRAFT_PEARL_BAIT,
        CRAFT_CHARM, CRAFT_CURIO, BUILD_STRUCTURE)

_REF_TABLE = (
    ("fishing.record_cast", _record_cast),
    ("fishing.record_buy_rod", _record_buy_rod),
    ("fishing.record_craft_rod", _record_craft_rod),
    ("fishing.record_buy_bait", _record_buy_bait),
    ("fishing.record_craft_bait", _record_craft_bait),
    ("fishing.record_craft_pearl_bait", _record_craft_pearl_bait),
    ("fishing.record_craft_charm", _record_craft_charm),
    ("fishing.record_craft_curio", _record_craft_curio),
    ("fishing.record_build_structure", _record_build_structure),
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
