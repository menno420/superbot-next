"""Fishing handlers (band 6) — the shipped cast-open lane (energy gate →
spend → the waiting-for-a-bite panel), the Reel commit route +
dex/leaderboard/trophy reads; rod/bait/craft/venue/structure surfaces are
honest pending terminals until the gear systems port (D-0043 successor
work). ``goldens/fishing/sweep_fish.json`` pins the cast-open bytes
(the spent ``fishing_energy`` row + the panel); the dex embed lives on
``fishing.log`` (sb/domain/fishing/panels.py)."""

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
        from sb.domain.fishing import catalog, store

        rows = await store.top_fishers(int(req.guild_id or 0),
                                       catalog.fish_names())
        if not rows:
            return Reply(SUCCESS, "🎣 No anglers yet — try `!fish`!")
        lines = ["🎣 **Top anglers**"] + [
            f"{i + 1}. <@{r['user_id']}> — {r['total']} fish"
            for i, r in enumerate(rows)]
        return Reply(SUCCESS, "\n".join(lines))

    @handler("fishing.trophies_view")
    async def trophies_view(req) -> Reply:
        from sb.domain.fishing import catalog, store

        rows = await store.top_trophies(int(req.guild_id or 0),
                                        catalog.fish_names())
        if not rows:
            return Reply(SUCCESS, "🏆 No trophy catches recorded yet.")
        lines = ["🏆 **Trophy records**"] + [
            f"{i + 1}. <@{r['user_id']}> — {r['species']} "
            f"({float(r['best_weight']):.2f} kg)"
            for i, r in enumerate(rows)]
        return Reply(SUCCESS, "\n".join(lines))


#: Gear/venue/craft surfaces awaiting the fishing depth port (D-0043).
PENDING = {
    "forecast": "weather system", "sail": "venue (boat) system",
    "rod": "rod ladder", "bait": "bait system",
    "craftbait": "bait crafting", "craftcharm": "charm crafting",
    "craftrod": "rod crafting", "rodrecipes": "rod crafting",
    "craftpearl": "pearl bait crafting", "curios": "curio collection",
    "craftcurio": "curio crafting", "tidepool": "tide pool structure",
    "dock": "dock structure", "boathouse": "boathouse structure",
    "fishery": "fishery structure",
}


def ensure_handler_refs() -> None:
    _register()
    from sb.domain.operator_spine import pending_handler

    for name, system in PENDING.items():
        pending_handler(
            f"fishing.{name}_pending",
            f"🎣 `!{name}` needs the fishing {system} — the fishing "
            "depth port is named successor work (D-0043); the core "
            "cast loop is live at the starter profile.")


_register()
