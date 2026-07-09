"""Mining handlers (band 6) — core-loop routes + reads + the inventory
merge source, and honest pending terminals for the deep systems
(equipment/wear, energy, grid, vault, structures, skills, forge,
workshop, titles, loadouts, descend/ascend, character — the D-0043
named successor port)."""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs", "install_inventory_source"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


async def _mining_inventory_source(user_id: int, guild_id: int) -> dict:
    from sb.domain.mining.store import get_mining_inventory

    return await get_mining_inventory(user_id, guild_id)


def install_inventory_source() -> None:
    """Fill the D-0032 waiting port: mining_inventory (which also holds
    caught fish + pearls/coral) merges into !inventory. Idempotent —
    guarded by a module flag."""
    global _source_installed
    if _source_installed:
        return
    from sb.domain.inventory.service import install_extra_inventory_source

    install_extra_inventory_source(_mining_inventory_source)
    _source_installed = True


_source_installed = False


def _run_op(ref: str):
    async def route(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        result = await engine.run(
            WorkflowRef(ref),
            _ctx_from_req(req, {"argv": argv, "values": values}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't do that.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Done."))
    return route


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("mining.mine_route")):
        return

    handler("mining.mine_route")(_run_op("mining.mine"))
    handler("mining.chop_route")(_run_op("mining.harvest"))
    handler("mining.explore_route")(_run_op("mining.explore"))
    handler("mining.sell_route")(_run_op("mining.sell"))
    handler("mining.sellall_route")(_run_op("mining.sell_all"))
    handler("mining.buy_route")(_run_op("mining.buy"))

    @handler("mining.inventory_view")
    async def inventory_view(req) -> Reply:
        from sb.domain.mining.store import get_mining_inventory

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        inventory = await get_mining_inventory(uid,
                                               int(req.guild_id or 0))
        if not inventory:
            return Reply(SUCCESS,
                         "🎒 Your pack is empty — `!mine` to fill it!")
        lines = ["🎒 **Your mining pack**"] + [
            f"• {name} ×{qty}"
            for name, qty in sorted(inventory.items())]
        return Reply(SUCCESS, "\n".join(lines))

    @handler("mining.stats_view")
    async def stats_view(req) -> Reply:
        from sb.domain.games import xp as game_xp
        from sb.domain.games.store import game_xp_rows
        from sb.domain.mining.store import get_depth

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        depth = await get_depth(uid, gid)
        rows = {str(r["game"]): int(r["xp"])
                for r in await game_xp_rows(uid, gid)}
        return Reply(SUCCESS,
                     f"⛏️ **Mining stats** — depth band **{depth}**, "
                     f"mining XP **{rows.get(game_xp.GAME_MINING, 0):,}**")

    @handler("mining.market_view")
    async def market_view(req) -> Reply:
        from sb.domain.mining import market

        lines = ["🏪 **Market** — sell resources with `!sell <item> "
                 "[qty]` / `!sellall`; buy gear with `!buy <item>`.",
                 "Sell values: " + ", ".join(
                     f"{k} {v}🪙"
                     for k, v in market.RESOURCE_VALUES.items())]
        return Reply(SUCCESS, "\n".join(lines))


#: The deep-system commands (shipped names) → pending copy. The mining
#: depth port (equipment/wear/energy/grid/vault/structures/skills/
#: forge/workshop/titles/loadouts/character) is D-0043 successor work.
PENDING = {
    "fastmine": "grid dig", "mineinv": "pack detail panel",
    "build": "structures", "buildlist": "structures",
    "buildable": "structures", "use": "consumables", "cook": "campfire",
    "equip": "equipment", "unequip": "equipment", "gear": "equipment",
    "loadout": "loadout presets", "character": "character sheet",
    "descend": "depth bands", "ascend": "depth bands",
    "mineworld": "world grid", "vault": "vault", "stash": "vault",
    "unstash": "vault", "vaultupgrade": "vault", "skills": "skills",
    "skill": "skills", "titles": "titles", "forge": "forge",
    "home": "structures", "workshop": "workshop", "repair": "workshop",
    "quickcraft": "workshop", "reset_inventory": "admin reset",
}


def ensure_handler_refs() -> None:
    _register()
    install_inventory_source()
    from sb.domain.operator_spine import pending_handler

    for name, system in PENDING.items():
        pending_handler(
            f"mining.{name}_pending",
            f"⛏️ `!{name}` needs the mining {system} system — the deep "
            "mining port is named successor work (D-0043); the core "
            "loop (mine/chop/explore/sell/buy) is live.")


_register()
install_inventory_source()
