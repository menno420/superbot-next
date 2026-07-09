"""Fishing handlers (band 6) — the core cast route + dex/leaderboard/
trophy reads; rod/bait/craft/venue/structure surfaces are honest pending
terminals until the gear systems port (D-0043 successor work)."""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("fishing.fish_route")):
        return

    @handler("fishing.fish_route")
    async def fish_route(req) -> Reply:
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

    @handler("fishing.log_view")
    async def log_view(req) -> Reply:
        from sb.domain.fishing import catalog, store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        rows = await store.get_catch_log(uid, int(req.guild_id or 0))
        total = len(catalog.SPECIES)
        if not rows:
            return Reply(SUCCESS,
                         f"🎣 Your fish dex is empty (0/{total}) — try "
                         "`!fish`!")
        lines = [f"🎣 **Your fish dex** — {len(rows)}/{total} species"]
        for r in rows:
            species = catalog.species_by_name(str(r["species"]))
            emoji = species.emoji if species else "🐟"
            best = (f" (best {float(r['best_weight']):.2f} kg)"
                    if float(r["best_weight"]) > 0 else "")
            lines.append(f"{emoji} **{r['species']}** ×{r['count']}{best}")
        return Reply(SUCCESS, "\n".join(lines))

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
