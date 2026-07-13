"""Fishing handlers (band 6) — the shipped cast-open lane (energy gate →
spend → the waiting-for-a-bite panel), the Reel commit route,
dex/leaderboard/trophy reads + the slice-1 weather/venue surfaces
(``!forecast`` / ``!sail``); rod/bait/craft/structure surfaces are
honest pending terminals until the gear systems port (D-0043 successor
work). ``goldens/fishing/sweep_fish.json`` pins the cast-open bytes
(the spent ``fishing_energy`` row + the panel), sweep_forecast the Rain
forecast embed, sweep_sail the deepwater toggle + its ``fishing_venue``
row; the dex embed lives on ``fishing.log``
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


#: Gear/craft/structure surfaces awaiting the fishing depth port
#: (D-0043). forecast/sail left this dict in slice 1 (weather + venue);
#: the cast LEG still runs the starter shore profile — the venue→cast
#: wiring (deepwater species pool, coral drop, minigame difficulty)
#: rides the rod/bait/minigame rung with the rest of the gear knobs.
PENDING = {
    "rod": "rod ladder", "bait": "bait system",
    "craftbait": "bait crafting", "craftcharm": "charm crafting",
    "craftrod": "rod crafting", "rodrecipes": "rod crafting",
    "craftpearl": "pearl bait crafting", "curios": "curio collection",
    "craftcurio": "curio crafting", "tidepool": "tide pool structure",
    "dock": "dock structure", "boathouse": "boathouse structure",
    "fishery": "fishery structure",
}


def _register_hub_pending() -> None:
    """Hub-button-only pending surfaces (no command form — the shipped
    menu routed these to the structures hub / rules embed views).
    Registered at module IMPORT (the role/handlers.py pattern — declaring
    IS reserving; never ensure-only)."""
    from sb.domain.operator_spine import pending_handler

    pending_handler(
        "fishing.structures_pending",
        "🎣 The Structures hub needs the fishing structure systems "
        "(tide pool / dock / boathouse / fishery) — the fishing depth "
        "port is named successor work (D-0043); the core cast loop is "
        "live at the starter profile.")
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
