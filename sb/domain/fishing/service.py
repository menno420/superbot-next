"""Fishing handlers (band 6) — the shipped cast-open lane (energy gate →
spend → the waiting-for-a-bite panel), the Reel commit route,
dex/leaderboard/trophy reads, the slice-1 weather/venue surfaces
(``!forecast`` / ``!sail``), the slice-2 rod-ladder surfaces (``!rod``
/ ``!rodrecipes`` / ``!craftrod``), the slice-3 bait-shelf surfaces
(``!bait`` / ``!craftbait`` / ``!craftpearl`` / ``!craftcharm``) + the
slice-4 coral sinks (``!curios`` / ``!craftcurio``) and structure Build
routes (the ``!tidepool`` / ``!dock`` / ``!boathouse`` / ``!fishery``
panel opens route straight to their PanelSpecs) — ALL 20 shipped
fishing commands are live; the PENDING roster is empty.
``goldens/fishing/sweep_fish.json`` pins the cast-open bytes (the spent
``fishing_energy`` row + the panel), sweep_forecast the Rain forecast
embed, sweep_sail the deepwater toggle + its ``fishing_venue`` row,
sweep_rod / sweep_rodrecipes the fresh tier-0 rod panels,
sweep_craftrod the not-enough-fish guard, sweep_bait / sweep_craftbait
the fresh bait-less bait shop, sweep_craftpearl the no-pearls guard,
sweep_craftcharm the charm-recipe listing, sweep_curios the 0-coral
curio shelf card, sweep_craftcurio the not-carvable guard, and
sweep_tidepool / sweep_dock / sweep_boathouse / sweep_fishery the
not-built structure panels; the dex embed lives on ``fishing.log``
(sb/domain/fishing/panels.py)."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


def _fmt_wait(seconds: int) -> str:
    """Human "ready in" — ``45s`` / ``2m 05s`` (the shipped
    services/fishing_workflow.py helper)."""
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def _embed(title: str, description: str):
    """The shipped ``discord.Embed(title=…, color=_FISHING_COLOR)`` frame
    (_FISHING_COLOR = INFO blue 3447003 — the goldens pin the byte)."""
    from sb.kernel.panels.render import RenderedEmbed

    return RenderedEmbed(title=title, description=description,
                         style_token="blue")


async def _card(req, embed) -> Reply:
    """Present one read card as the shipped public embed reply
    (``ctx.send(embed=…)`` — the mining.card open_panel lane)."""
    import dataclasses

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("fishing.card"), dataclasses.replace(
        req, args={**dict(req.args), "_card": embed}))
    return Reply(SUCCESS, None)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("fishing.fish_route")):
        return

    @handler("fishing.cast_open")
    async def cast_open(req) -> Reply:
        """!fish / the hub Cast button — the shipped ``begin_cast`` lane
        (services/fishing_workflow.py: settle → out of energy? → spend)
        ahead of the waiting-for-a-bite panel. The energy spend is the
        shipped direct game-state write (autocommit, non-money — the
        mining-energy posture); the golden pins the spent row."""
        import dataclasses

        from sb.domain.fishing import energy as energy_mod
        from sb.domain.fishing import store
        from sb.domain.fishing.panels import CAST_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.kernel.workflow.context import SYSTEM_CLOCK
        from sb.spec.refs import PanelRef

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        now = int(SYSTEM_CLOCK().timestamp())
        cur, ts = await store.get_fishing_energy(uid, gid)
        state = energy_mod.EnergyState(cur, ts)
        settled = energy_mod.settle(state, now)
        if not energy_mod.can_cast(settled):
            wait = energy_mod.regen_seconds_for(state, now,
                                                energy_mod.CAST_COST)
            return Reply(BLOCKED,
                         "🎣 You're out of energy — let the line rest. "
                         f"Ready to cast again in **{_fmt_wait(wait)}**.")
        spent = energy_mod.spend(state, now)
        await store.set_fishing_energy(uid, gid, spent.current,
                                       spent.updated_at)
        await open_panel(
            PanelRef(CAST_PANEL_ID),
            dataclasses.replace(
                req, args={**dict(req.args),
                           "cast_energy": spent.current}))
        return Reply(SUCCESS, None)

    @handler("fishing.fish_route")
    async def fish_route(req) -> Reply:
        """The cast panel's Reel button — commits the catch through the
        audited ``fishing.cast`` K7 op (dex upsert + materials + game XP
        in one leg txn). The shipped live-timing layer (bite delay /
        fake-out / escape) rides the D-0043 successor port — see the
        panels module under-port ledger."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef("fishing.cast"),
                                  _ctx_from_req(req, {}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "The line came back "
                                                "empty.")
        after = (result.after or {}).get("cast", {})
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.forecast_view")
    async def forecast_view(req) -> Reply:
        """!forecast — the shipped date-seeded forecast embed
        (fishing_cog.py ``forecast``: _FISHING_COLOR blue; title
        ``{emoji} Today's fishing forecast: {name}``, description
        ``{blurb}\\n\\n**Effect on every cast:** {effect}``, footer
        ``Same for everyone today · 🎣 !fish to cast`` —
        goldens/fishing/sweep_forecast pins the capture-day Rain bytes;
        the replay seam is CAPTURE_WORLD_WEATHER, trap 36a)."""
        from sb.domain.fishing import weather as weather_mod
        from sb.kernel.panels.render import RenderedEmbed

        w = weather_mod.current_weather()
        embed = RenderedEmbed(
            title=f"{w.emoji} Today's fishing forecast: {w.name}",
            description=(f"{w.blurb}\n\n**Effect on every cast:** "
                         f"{weather_mod.effect_text(w)}"),
            footer="Same for everyone today · 🎣 !fish to cast",
            style_token="blue")
        return await _card(req, embed)

    @handler("fishing.sail_route")
    async def sail_route(req) -> Reply:
        """!sail / the hub ⛵ Set sail / Dock button — the shipped venue
        toggle (fishing_cog.py ``sail`` → services/fishing_workflow.py
        ``toggle_venue``/``set_venue``): flip shore ↔ deepwater and
        persist it. The write is the shipped direct game-state upsert
        (autocommit, non-money, no audit — the energy-spend posture);
        goldens/fishing/sweep_sail pins the deepwater message + the
        minted ``fishing_venue`` row."""
        from sb.domain.fishing import store, venue as venue_mod

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        current = await store.get_fishing_venue(uid, gid)
        profile = venue_mod.profile_for(venue_mod.toggle(current))
        await store.set_fishing_venue(uid, gid, profile.key)
        if profile.key == venue_mod.DEEPWATER:
            message = (
                f"{profile.emoji} **You set sail for deepwater.** Rare "
                "boat-only fish lurk here — they bite slower and fight "
                "harder to break free, so a rod with good escape-resist "
                "pays off. Cast with `!fish`.")
        else:
            message = (
                f"{profile.emoji} **You docked back on the shore.** "
                "Relaxed casting for the everyday catch. Cast with "
                "`!fish`.")
        return Reply(SUCCESS, message)

    async def _op_after(req, op_key: str, params: dict | None = None):
        """Run a one-leg fishing op; (outcome-reply, after) — reply is
        None on SUCCESS so the caller composes the shipped copy from
        `after` (the mining service `_op_after` shape)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, dict(params or {})))
        if result.outcome != SUCCESS:
            return (Reply(result.outcome,
                          result.user_message or "Couldn't do that."), {})
        return (None, next(iter((result.after or {}).values()), {}))

    def _rest_arg(req) -> str:
        """The invocation's rest-string argument — a select pick
        (``values``) wins over the typed tail (``argv``), mirroring the
        shipped keyword-rest ``*, bait: str = ""`` cog signature and the
        select callbacks' direct-key calls."""
        values = tuple(req.args.get("values", ()) or ())
        if values:
            return str(values[0])
        return " ".join(str(t) for t in
                        tuple(req.args.get("argv", ()) or ()))

    @handler("fishing.rod_shop")
    async def rod_shop(req) -> Reply:
        """!rod — open the rod shop panel (fishing_cog.py ``rod``:
        build_rod_embed + RodShopView). A pure read — the open renders
        the live tier/balance and writes nothing;
        goldens/fishing/sweep_rod pins the fresh tier-0 bytes."""
        import dataclasses

        from sb.domain.fishing.panels import ROD_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(ROD_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.rodrecipes_view")
    async def rodrecipes_view(req) -> Reply:
        """!rodrecipes — open the rod recipe browser (fishing_cog.py
        ``rodrecipes``: build_recipe_panel). A pure read;
        goldens/fishing/sweep_rodrecipes pins the fresh tier-0 bytes."""
        import dataclasses

        from sb.domain.fishing.panels import ROD_RECIPES_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(ROD_RECIPES_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.craftrod_route")
    async def craftrod_route(req) -> Reply:
        """!craftrod / the rod panels' craft buttons — craft the next rod
        up the ladder from caught fish (fishing_cog.py ``craftrod`` →
        services/fishing_workflow.py ``craft_rod``). The maxed /
        not-enough-fish refusals are computed as PURE READS (tier +
        inventory + the smallest-first spend plan) so the failed attempt
        writes no row, exactly as the oracle's txn never opens —
        goldens/fishing/sweep_craftrod pins the fresh-player
        \"need **10** fish of size ≤ **6**\" guard byte. Only a stocked
        craft runs the audited fish-debit + tier-raise op
        (depth.exemptions.fishing guard-only-capture: fishing_rod)."""
        from sb.domain.fishing import crafting, rods as rods_mod, store
        from sb.domain.mining.store import get_mining_inventory

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        tier = await store.get_rod_tier(uid, gid)
        nxt = rods_mod.next_rod(tier)
        if nxt is None:
            top = rods_mod.rod_for_tier(tier)
            return Reply(BLOCKED,
                         f"You already wield the **{top.name}** "
                         f"{top.emoji} — the finest rod there is!")
        recipe = rods_mod.rod_recipe(nxt.tier)
        if recipe is None:  # defensive — every non-starter tier has one
            return Reply(BLOCKED,
                         f"The **{nxt.name}** {nxt.emoji} can't be "
                         "crafted from fish — buy it with `!rod`.")
        inventory = await get_mining_inventory(uid, gid)
        if crafting.plan_fish_spend(inventory, recipe) is None:
            return Reply(BLOCKED,
                         f"You need **{recipe.fish_count}** fish of size "
                         f"≤ **{recipe.max_size_rank}** to craft the "
                         f"**{nxt.name}** {nxt.emoji} — catch more fish "
                         "with `!fish` (or buy it with `!rod`).")
        blocked, after = await _op_after(req, "fishing.craft_rod")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.rod_upgrade_route")
    async def rod_upgrade_route(req) -> Reply:
        """The rod shop's ⬆️ Upgrade rod button — buy the next rod up the
        ladder (views/fishing/rod_shop.py ``upgrade_btn`` →
        services/fishing_workflow.py ``buy_rod``). The maxed /
        insufficient-funds refusals are computed as PURE READS (tier +
        balance) so the failed attempt writes no coin ledger / audit
        row, exactly as the oracle's txn rolls back. Only a funded
        upgrade runs the audited debit-and-bump op (#217 advisory-fenced
        locking read; economy.balance_changed emits after commit). No
        golden drives the click — copy oracle-source-verbatim."""
        from sb.domain.economy.store import get_coins
        from sb.domain.fishing import rods as rods_mod, store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        tier = await store.get_rod_tier(uid, gid)
        nxt = rods_mod.next_rod(tier)
        if nxt is None:
            top = rods_mod.rod_for_tier(tier)
            return Reply(BLOCKED,
                         f"You already wield the **{top.name}** "
                         f"{top.emoji} — the finest rod there is!")
        balance = await get_coins(uid, gid)
        if balance < nxt.price:
            return Reply(BLOCKED,
                         f"The **{nxt.name}** {nxt.emoji} costs "
                         f"**{nxt.price}** 🪙 — you only have "
                         f"**{balance}** 🪙.")
        blocked, after = await _op_after(req, "fishing.buy_rod")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    async def _open_bait_shop(req) -> Reply:
        """Open the bait shop panel (the ``!bait`` open and the shipped
        no-arg ``!craftbait`` fallthrough — ``await self.bait(ctx)``)."""
        import dataclasses

        from sb.domain.fishing.panels import BAIT_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(BAIT_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.bait_shop")
    async def bait_shop(req) -> Reply:
        """!bait — open the bait shop panel (fishing_cog.py ``bait``:
        build_bait_embed + BaitShopView). A pure read — the open renders
        the live loadout/pearls/balance and writes nothing;
        goldens/fishing/sweep_bait pins the fresh bait-less bytes."""
        return await _open_bait_shop(req)

    @handler("fishing.craftbait_route")
    async def craftbait_route(req) -> Reply:
        """!craftbait [bait] / the bait shop's craft select — craft one
        pack from small caught fish (fishing_cog.py ``craftbait`` →
        services/fishing_workflow.py ``craft_bait``). No argument opens
        the bait panel (the shipped ``await self.bait(ctx)`` — the
        byte-identical open goldens/fishing/sweep_craftbait pins); an
        unknown / non-craftable bait and the not-enough-fish case are
        computed as PURE READS so the failed attempt writes no row,
        exactly as the oracle's txn never opens. Only a stocked craft
        runs the audited fish-debit + load op
        (depth.exemptions.fishing guard-only-capture: fishing_bait)."""
        from sb.domain.fishing import bait as bait_mod, crafting
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        if not text:
            return await _open_bait_shop(req)
        key = bait_mod.craftable_key_for(text)
        if key is None:
            craftable = ", ".join(
                bait_mod.bait_by_key(k).name
                for k in bait_mod.CRAFTABLE_KEYS)
            return Reply(BLOCKED,
                         f"You can't craft **{text}** from fish. "
                         f"Craftable: {craftable}.")
        bait = bait_mod.bait_by_key(key)
        recipe = bait_mod.craft_recipe(key)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        if crafting.plan_fish_spend(inventory, recipe) is None:
            return Reply(BLOCKED,
                         f"You need **{recipe.fish_count}** fish of size "
                         f"≤ **{recipe.max_size_rank}** to craft "
                         f"**{bait.name}** {bait.emoji} — catch more "
                         "small fish with `!fish`.")
        blocked, after = await _op_after(req, "fishing.craft_bait",
                                         {"bait_key": key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.craftpearl_route")
    async def craftpearl_route(req) -> Reply:
        """!craftpearl [bait] / the bait shop's pearl select — craft the
        premium bait from pearls (fishing_cog.py ``craftpearl`` →
        services/fishing_workflow.py ``craft_pearl_bait``). No argument
        auto-selects the single pearl recipe (the shipped
        len(PEARL_CRAFTABLE_KEYS) == 1 branch); the unknown-bait and
        not-enough-pearls refusals are computed as PURE READS so the
        failed attempt writes no row — goldens/fishing/sweep_craftpearl
        pins the fresh-player \"need **4** 🦪 pearls\" guard byte. Only
        a stocked craft runs the audited pearl-debit + load op."""
        from sb.domain.fishing import bait as bait_mod
        from sb.domain.fishing.ops import PEARL_ITEM
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        key = bait_mod.pearl_craftable_key_for(text)
        if not text and len(bait_mod.PEARL_CRAFTABLE_KEYS) == 1:
            key = bait_mod.PEARL_CRAFTABLE_KEYS[0]
        if key is None:
            craftable = ", ".join(
                bait_mod.bait_by_key(k).name
                for k in bait_mod.PEARL_CRAFTABLE_KEYS)
            return Reply(BLOCKED,
                         f"You can't craft **{text}** from pearls. "
                         f"Pearl-craftable: {craftable}.")
        bait = bait_mod.bait_by_key(key)
        pearl_cost = bait_mod.pearl_recipe(key)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        have = inventory.get(PEARL_ITEM, 0)
        if have < pearl_cost:
            return Reply(BLOCKED,
                         f"You need **{pearl_cost}** 🦪 pearls to craft "
                         f"**{bait.name}** {bait.emoji} — you have "
                         f"**{have}**. Pearls drop rarely when you reel "
                         "in a fish (bigger fish, better odds).")
        blocked, after = await _op_after(req, "fishing.craft_pearl_bait",
                                         {"bait_key": key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.craftcharm_route")
    async def craftcharm_route(req) -> Reply:
        """!craftcharm [charm] — craft a CHARM-slot fishing charm from
        caught fish (fishing_cog.py ``craftcharm`` →
        services/fishing_workflow.py ``craft_charm``). No argument / an
        unknown charm lists the craftable recipes (the shipped listing —
        goldens/fishing/sweep_craftcharm pins the no-arg bytes); the
        not-enough-fish refusal is a PURE READ. Only a stocked craft
        runs the audited fish-debit + charm-grant op (the charm name
        byte-matches the mining gear catalog, so it equips via
        `!gear`)."""
        from sb.domain.fishing import crafting, gear as gear_mod
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        name = gear_mod.craftable_charm_for(text)
        if not text or name is None:
            lines = [
                f"🎣 **{r.charm.title()}** — "
                f"{gear_mod.charm_recipe_text(r)}"
                for r in gear_mod.CHARM_RECIPES.values()]
            prefix = (
                f"You can't craft **{text}** from fish.\n"
                if text
                else "Craft a fishing charm from caught fish "
                     "(or buy one with `!gear`):\n")
            return Reply(SUCCESS if not text else BLOCKED,
                         prefix + "\n".join(lines))
        recipe = gear_mod.charm_recipe(name)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        if crafting.plan_fish_spend(inventory, recipe) is None:
            return Reply(BLOCKED,
                         f"You need **{recipe.fish_count}** fish of size "
                         f"≤ **{recipe.max_size_rank}** to craft a "
                         f"**{recipe.charm}** — catch more fish with "
                         "`!fish`.")
        blocked, after = await _op_after(req, "fishing.craft_charm",
                                         {"charm_name": name})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.bait_buy_route")
    async def bait_buy_route(req) -> Reply:
        """The bait shop's buy select — buy one pack of the picked bait
        (views/fishing/bait_shop.py ``_BaitSelect`` →
        services/fishing_workflow.py ``buy_bait``). The unknown-bait /
        insufficient-funds refusals are computed as PURE READS (shelf +
        balance) so the failed attempt writes no coin ledger / audit
        row, exactly as the oracle's txn rolls back. Only a funded buy
        runs the audited debit-and-load op (#217 advisory-fenced locking
        read; economy.balance_changed emits after commit; same-bait
        stacks, different-bait replaces). No golden drives the pick —
        copy oracle-source-verbatim."""
        from sb.domain.economy.store import get_coins
        from sb.domain.fishing import bait as bait_mod

        bait = bait_mod.bait_by_key(_rest_arg(req))
        if bait is None:
            return Reply(BLOCKED,
                         "That bait doesn't exist on the shelf.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        balance = await get_coins(uid, gid)
        if balance < bait.price:
            return Reply(BLOCKED,
                         f"A pack of **{bait.name}** {bait.emoji} costs "
                         f"**{bait.price}** 🪙 — you only have "
                         f"**{balance}** 🪙.")
        blocked, after = await _op_after(req, "fishing.buy_bait",
                                         {"bait_key": bait.key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.curios_view")
    async def curios_view(req) -> Reply:
        """!curios — the coral-carving collection card (fishing_cog.py
        ``curios``, inline embed verbatim: the _FISHING_COLOR blue 🪸
        Coral Curios embed — coral count + owned/total description, one
        ✅/🔨/🔒 field per catalog curio, the carve footer). A pure
        read; goldens/fishing/sweep_curios pins the fresh 0-coral
        bytes."""
        from sb.domain.fishing import curios as curios_mod
        from sb.domain.fishing.ops import CORAL_ITEM
        from sb.domain.mining.store import get_mining_inventory
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        coral = inventory.get(CORAL_ITEM, 0)
        owned, total = curios_mod.collection_progress(inventory)
        fields = []
        for curio in curios_mod.CURIO_CATALOG:
            have = inventory.get(curio.item, 0)
            mark = "✅" if have > 0 else (
                "🔨" if coral >= curio.coral_cost else "🔒")
            owned_txt = f" ×{have}" if have > 0 else ""
            fields.append((
                f"{mark} {curio.emoji} {curio.name}{owned_txt}",
                f"{curios_mod.cost_text(curio)} · {curio.rarity}"))
        embed = RenderedEmbed(
            title="🪸 Coral Curios",
            description=(
                f"You have **{coral}** 🪸 coral · collection "
                f"**{owned}/{total}** carved.\n"
                "Coral drops rarely on a **deepwater** reel (`!sail` to "
                "the boat)."),
            fields=tuple(fields),
            footer="Carve with !craftcurio <name>",
            style_token="blue")
        return await _card(req, embed)

    @handler("fishing.craftcurio_route")
    async def craftcurio_route(req) -> Reply:
        """!craftcurio [curio] — carve a cosmetic curio from coral (the
        deepwater rare-material sink; fishing_cog.py ``craftcurio`` →
        services/fishing_workflow.py ``craft_curio``). No argument / an
        unknown curio answers the shipped carvable listing —
        goldens/fishing/sweep_craftcurio pins the no-arg bytes; the
        not-enough-coral refusal is a PURE READ so the failed attempt
        writes no row, exactly as the oracle's txn never opens. Only a
        stocked carve runs the audited coral-debit + curio-grant op."""
        from sb.domain.fishing import curios as curios_mod
        from sb.domain.fishing.ops import CORAL_ITEM
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        key = curios_mod.curio_craftable_key_for(text)
        if key is None:
            craftable = ", ".join(
                c.name for c in curios_mod.CURIO_CATALOG)
            return Reply(BLOCKED,
                         f"That isn't a carvable curio. Carvable: "
                         f"{craftable}. See `!curios` for your "
                         "collection.")
        curio = curios_mod.curio_by_key(key)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        have = inventory.get(CORAL_ITEM, 0)
        if have < curio.coral_cost:
            return Reply(BLOCKED,
                         f"You need **{curio.coral_cost}** 🪸 coral to "
                         f"carve **{curio.name}** {curio.emoji} — you "
                         f"have **{have}**. Coral drops rarely when you "
                         "reel in a fish out in **deepwater** (`!sail` "
                         "to the boat first).")
        blocked, after = await _op_after(req, "fishing.craft_curio",
                                         {"curio_key": key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    async def _structure_build(req, structure_key: str) -> Reply:
        """One structure panel's Build button — build/upgrade the coral
        structure one level (views/fishing/{tide_pool,dock,boathouse,
        fishery}.py ``build_btn`` → services/mining_workflow.py
        ``build_structure``). The maxed / short-on-materials /
        insufficient-funds refusals are computed as PURE READS (level +
        inventory + balance) so the failed attempt writes no coin
        ledger / audit row, exactly as the oracle's txn rolls back. Only
        a funded, stocked build runs the audited debit + consume + raise
        op (#217 advisory-fenced locking read;
        economy.balance_changed emits after commit;
        mining_structures written only via the mining.store sole-writer
        seam). No golden drives the click — copy
        oracle-source-verbatim."""
        from sb.domain.economy.store import get_coins
        from sb.domain.mining import structures, workshop
        from sb.domain.mining.store import (
            get_mining_inventory,
            get_structures,
        )

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        display = structures.display_name(structure_key)
        built = await get_structures(uid, gid)
        level = built.get(structure_key, 0)
        cost = structures.build_cost(structure_key, level)
        if cost is None:
            name = structures.level_name(structure_key, level)
            return Reply(BLOCKED,
                         f"Your {display} is already at its maximum "
                         f"level (**{name}**).")
        inventory = await get_mining_inventory(uid, gid)
        if any(inventory.get(mat, 0) < qty
               for mat, qty in cost.materials.items()):
            return Reply(BLOCKED,
                         f"Building the {display} needs "
                         f"{workshop.describe_materials(cost.materials)} "
                         f"plus {cost.coins} 🪙 — you're short on "
                         "materials.")
        balance = await get_coins(uid, gid)
        if balance < cost.coins:
            return Reply(BLOCKED,
                         f"Building the {display} costs "
                         f"**{cost.coins}** 🪙 — you only have "
                         f"**{balance}** 🪙.")
        blocked, after = await _op_after(req, "fishing.build_structure",
                                         {"structure": structure_key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.tidepool_build_route")
    async def tidepool_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.TIDE_POOL)

    @handler("fishing.dock_build_route")
    async def dock_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.DOCK)

    @handler("fishing.boathouse_build_route")
    async def boathouse_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.BOATHOUSE)

    @handler("fishing.fishery_build_route")
    async def fishery_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.FISHERY)

    @handler("fishing.menu_view")
    async def menu_view(req) -> Reply:
        from sb.domain.fishing import catalog

        return Reply(SUCCESS,
                     f"🎣 **Fishing** — {len(catalog.SPECIES)} species "
                     "across 7 size bands.\n`!fish` cast a line · "
                     "`!fishlog` your dex · `!fishtop` top anglers · "
                     "`!trophies` biggest catches")

    @handler("fishing.top_view")
    async def top_view(req) -> Reply:
        """!fishtop — the shipped 🎣 Top Anglers embed (fishing_cog.py
        fishtop: _FISHING_COLOR blue; the empty-world description is
        golden-pinned — goldens/fishing/sweep_fishtop). The populated
        leaderboard body keeps the port's numbered lines inside the
        shipped embed frame (not golden-pinned; the oracle fragment
        index surfaces only the empty branch — under-port note)."""
        from sb.domain.fishing import catalog, store

        rows = await store.top_fishers(int(req.guild_id or 0),
                                       catalog.fish_names())
        if not rows:
            desc = "No one has cast a line yet — be the first with `!fish`!"
        else:
            desc = "\n".join(
                f"{i + 1}. <@{r['user_id']}> — {r['total']} fish"
                for i, r in enumerate(rows))
        return await _card(req, _embed("🎣 Top Anglers", desc))

    @handler("fishing.trophies_view")
    async def trophies_view(req) -> Reply:
        """!trophies — the shipped 🏅 Biggest Catches embed
        (fishing_cog.py trophies: _FISHING_COLOR blue; the empty-world
        description is golden-pinned — goldens/fishing/sweep_trophies).
        The populated hall-of-fame body keeps the port's numbered lines
        inside the shipped embed frame (not golden-pinned — the same
        under-port note as fishtop)."""
        from sb.domain.fishing import catalog, store

        rows = await store.top_trophies(int(req.guild_id or 0),
                                        catalog.fish_names())
        if not rows:
            desc = ("No trophies landed yet — reel in a big one with "
                    "`!fish`!")
        else:
            desc = "\n".join(
                f"{i + 1}. <@{r['user_id']}> — {r['species']} "
                f"({float(r['best_weight']):g}kg)"
                for i, r in enumerate(rows))
        return await _card(req, _embed("🏅 Biggest Catches", desc))


#: The fishing deep-system commands (shipped names) → pending copy.
#: forecast/sail left this dict in slice 1 (weather + venue);
#: rod/rodrecipes/craftrod in slice 2 (the rod ladder);
#: bait/craftbait/craftpearl/craftcharm in slice 3 (the bait shelf).
#: curios/craftcurio/tidepool/dock/boathouse/fishery left in slice 4
#: (the coral sinks + structures — the FINAL slice): curios_view /
#: craftcurio_route in _register() carry the curio shelf card + the
#: not-carvable guard, and the four structure commands route straight
#: to their live PanelSpecs (the Build buttons run the audited
#: fishing.build_structure write op).
#: This EMPTIES the fishing deep-system PENDING roster — all 20 shipped
#: fishing commands are ported (the D-0043 fishing ladder is complete).
#: The cast LEG still runs the starter shore profile — the
#: venue/rod/bait/structure→cast wiring (deepwater species pool, coral
#: drop, rarity_pull, bite speed, the per-cast charge spend, the
#: pull/bite/regen/double-catch structure mults, minigame difficulty)
#: rides the minigame rung with the rest of the knobs.
PENDING: dict[str, str] = {}


def _register_hub_pending() -> None:
    """Hub-button-only pending surfaces (no command form — the shipped
    menu routed these to the rules embed view). Registered at module
    IMPORT (the role/handlers.py pattern — declaring IS reserving;
    never ensure-only). The 🏗 Structures button left this set in
    slice 4 — it now routes to the live structures sub-hub PanelSpec."""
    from sb.domain.operator_spine import pending_handler

    pending_handler(
        "fishing.howtofish_pending",
        "🎣 The how-to-fish guide rides the fishing depth port — named "
        "successor work (D-0043); cast with `!fish` and hit Reel when "
        "it bites.")


def ensure_handler_refs() -> None:
    _register()
    _register_hub_pending()
    from sb.domain.operator_spine import pending_handler

    for name, system in PENDING.items():
        pending_handler(
            f"fishing.{name}_pending",
            f"🎣 `!{name}` needs the fishing {system} — the fishing "
            "depth port is named successor work (D-0043); the core "
            "cast loop is live at the starter profile.")


_register()
_register_hub_pending()
