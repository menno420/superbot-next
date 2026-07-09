"""Creature handlers (band 6) — catch route, dex/dextop reads, battle
record reads; the interactive PvP battle (cbattle) is an honest pending
terminal (live-adapter successor work; the record lane is live)."""

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

    if is_registered(HandlerRef("creature.catch_route")):
        return

    @handler("creature.catch_route")
    async def catch_route(req) -> Reply:
        """!catch (alias hunt) — one outing through the audited lane."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef("creature.catch"),
                                  _ctx_from_req(req, {}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "The wilds are quiet.")
        after = (result.after or {}).get("catch", {})
        return Reply(SUCCESS, after.get("message", ""))

    @handler("creature.dex_view")
    async def dex_view(req) -> Reply:
        """!dex (alias collection) — the player's collection log."""
        from sb.domain.creature import catalog, store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        collection = await store.get_collection(uid, gid)
        total = len(catalog.CREATURES)
        if not collection:
            return Reply(SUCCESS,
                         f"🐾 Your dex is empty (0/{total}) — try "
                         "`!catch`!")
        lines = [f"🐾 **Your dex** — {len(collection)}/{total} species"]
        for creature in catalog.CREATURES:
            count = collection.get(creature.name)
            if count:
                lines.append(f"{creature.emoji} **{creature.name}** "
                             f"({creature.rarity}) ×{count}")
        return Reply(SUCCESS, "\n".join(lines))

    @handler("creature.dextop_view")
    async def dextop_view(req) -> Reply:
        """!dextop (alias topcatchers)."""
        from sb.domain.creature import store

        rows = await store.top_catchers(int(req.guild_id or 0))
        if not rows:
            return Reply(SUCCESS, "🐾 No catchers yet — try `!catch`!")
        lines = ["🐾 **Top catchers**"] + [
            f"{i + 1}. <@{r['user_id']}> — {r['species']} species "
            f"({r['total']} caught)" for i, r in enumerate(rows)]
        return Reply(SUCCESS, "\n".join(lines))

    @handler("creature.battle_record_view")
    async def battle_record_view(req) -> Reply:
        """!cbrecord (alias battlerecord)."""
        from sb.domain.creature import store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        wins, losses = await store.get_battle_record(uid,
                                                     int(req.guild_id or 0))
        return Reply(SUCCESS,
                     f"⚔️ Your battle record: **{wins}W / {losses}L**")

    @handler("creature.battletop_view")
    async def battletop_view(req) -> Reply:
        """!cbattletop (aliases pvptop, battletop)."""
        from sb.domain.creature import store

        rows = await store.top_battlers(int(req.guild_id or 0))
        if not rows:
            return Reply(SUCCESS, "⚔️ No battles fought yet.")
        lines = ["⚔️ **Battle leaderboard**"] + [
            f"{i + 1}. <@{r['user_id']}> — {r['wins']}W / {r['losses']}L"
            for i, r in enumerate(rows)]
        return Reply(SUCCESS, "\n".join(lines))

    @handler("creature.menu_view")
    async def menu_view(req) -> Reply:
        """!creatures (aliases creaturemenu, pets) — the text menu."""
        from sb.domain.creature import catalog

        return Reply(SUCCESS,
                     f"🐾 **Creatures** — {len(catalog.CREATURES)} species "
                     "in the wild.\n`!catch` hunt a wild creature · "
                     "`!dex` your collection · `!dextop` top catchers · "
                     "`!cbattle @player` battle (soon) · `!cbrecord` "
                     "your record")


def ensure_handler_refs() -> None:
    _register()
    from sb.domain.operator_spine import pending_handler

    pending_handler(
        "creature.battle_pending",
        "⚔️ Interactive creature battles need the live battle view "
        "(arms with the live adapter; the audited result lane is "
        "already live).")


_register()
