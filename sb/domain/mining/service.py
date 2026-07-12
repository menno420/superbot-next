"""Mining handlers (band 6 / parity flip) — the SHIPPED core-loop reply
bytes verbatim (goldens/mining pin them), the reads, the inventory merge
source, and honest pending terminals for the deep systems
(equipment/wear, energy, grid, vault, structures, skills, forge,
workshop, titles, loadouts, descend/ascend, character — the D-0043
named successor port).

Shipped command mapping (disbot/cogs/mining_cog.py, oracle-verbatim):

* ``!fastmine`` — \"One quick mining swing — no buttons (the old
  !fastmine, reborn)\" — runs the swing and answers
  ``{mention} mined **{amount}x {found}** in {describe_position(depth)}!``
  (goldens/mining/sweep_fastmine pins the bytes).
* ``!chop`` — ``{mention} chopped wood and collected {amount}x wood!``
  (goldens/mining/sweep_chop; the cog line is UNbolded — the hub panel's
  harvest lane bolded the amount, a different shipped surface).
* ``!explore`` — ``{mention} {text}\\n_{describe_position(depth)}_``
  (goldens/mining/sweep_explore).
* ``!mine`` — \"Open the grid Mine navigator — roam the world and dig\":
  the grid dig system is D-0043 successor work, and in the CAPTURE world
  the shipped open RAISED — every captured ``!mine`` pins bot1.py's
  global on_command_error copy (goldens/mining/sweep_mine), so the
  prefix lane carries that capture-pinned literal (the xp ``!rank`` /
  moderation timeout precedent, playbook 11b/18b).
* ``!reset_inventory @member`` — admin, guild-scoped:
  ``{member.name}'s inventory has been reset.``
  (goldens/mining/sweep_reset_inventory).

The shipped ``result.xp_note`` / wear-note tails append only on level-up
or a wear event — no golden carries one (every capture awarded
single-digit game XP at level 0 on fresh gearless players), and the
note surfaces ride the D-0043 equipment/wear port."""

from __future__ import annotations

import re as _re

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs", "install_inventory_source"]

#: bot1.py on_command_error's generic fallback, verbatim — the copy the
#: shipped bot sent when a command raised anything unclassified. The
#: capture world's ``!mine`` grid-navigator open raised there, so every
#: captured ``!mine`` pins this byte (goldens/mining/sweep_mine); the
#: shipped MemberConverter raise on an unparseable ``!reset_inventory``
#: target degrades through the same copy (unpinned, the starboard
#: converter-failure posture).
_GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again."


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


async def _op_after(req, op_key: str, params: dict | None = None):
    """Run a one-leg mining op; (outcome-reply, after) — reply is None on
    SUCCESS so the caller composes the shipped copy from `after`."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    result = await engine.run(WorkflowRef(op_key),
                              _ctx_from_req(req, dict(params or {})))
    if result.outcome != SUCCESS:
        return (Reply(result.outcome,
                      result.user_message or "Couldn't do that."), {})
    return (None, next(iter((result.after or {}).values()), {}))


#: member mention / bare id — the shipped MemberConverter's mention lane
#: (the moderation `_MENTION` shape).
_MENTION = _re.compile(r"^<@!?(\d{15,20})>$|^(\d{15,20})$")


async def _member_name(user_id: int, guild_id: int) -> str:
    """The target's name through the guild-directory read port (the
    economy/karma author-line recipe); degrades to the mention — never
    invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ mention fallback
        return f"<@{user_id}>"
    return member.tag.rsplit("#", 1)[0] or f"<@{user_id}>"


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("mining.mine_route")):
        return

    @handler("mining.mine_route")
    async def mine_route(req) -> Reply:
        """Shipped `!mine` opened the grid Mine navigator — a D-0043
        deep-system surface whose capture-world open RAISED; the corpus
        pins bot1.py's generic copy for every `!mine` (goldens/mining/
        sweep_mine — no swing, no rows, no game XP). The quick swing the
        old port answered here is the SHIPPED `!fastmine` lane (below)."""
        return Reply(BLOCKED, _GENERIC_ERROR)

    @handler("mining.fastmine_route")
    async def fastmine_route(req) -> Reply:
        from sb.domain.mining.world import describe_position

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        blocked, after = await _op_after(req, "mining.mine")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS,
                     f"<@{uid}> mined **{after.get('amount', 0)}x "
                     f"{after.get('found', '')}** in "
                     f"{describe_position(int(after.get('depth', 0)))}!")

    @handler("mining.chop_route")
    async def chop_route(req) -> Reply:
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        blocked, after = await _op_after(req, "mining.harvest")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS,
                     f"<@{uid}> chopped wood and collected "
                     f"{after.get('amount', 0)}x wood!")

    @handler("mining.explore_route")
    async def explore_route(req) -> Reply:
        from sb.domain.mining.world import describe_position

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        blocked, after = await _op_after(req, "mining.explore")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS,
                     f"<@{uid}> {after.get('description', '')}\n"
                     f"_{describe_position(int(after.get('depth', 0)))}_")

    @handler("mining.reset_inventory_route")
    async def reset_inventory_route(req) -> Reply:
        """Admin `!reset_inventory @member` — guild-scoped (shipped PR
        M3). The administrator gate rides the manifest tier (the shipped
        in-handler `member_has_perms_or_owner` check's port home); an
        unparseable target degrades through the bot1.py generic copy
        (the shipped MemberConverter raise — starboard posture)."""
        argv = [str(t) for t in tuple(req.args.get("argv", ()) or ())]
        match = _MENTION.match(argv[0].strip()) if argv else None
        if match is None:
            return Reply(BLOCKED, _GENERIC_ERROR)
        subject = int(match.group(1) or match.group(2))
        blocked, _after = await _op_after(
            req, "mining.reset_inventory", {"subject_user_id": subject})
        if blocked is not None:
            return blocked
        name = await _member_name(subject, int(req.guild_id or 0))
        return Reply(SUCCESS, f"{name}'s inventory has been reset.")

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
    "mineinv": "pack detail panel",
    "build": "structures", "buildlist": "structures",
    "buildable": "structures", "use": "consumables", "cook": "campfire",
    "equip": "equipment", "unequip": "equipment", "gear": "equipment",
    "loadout": "loadout presets", "character": "character sheet",
    "descend": "depth bands", "ascend": "depth bands",
    "mineworld": "world grid", "vault": "vault", "stash": "vault",
    "unstash": "vault", "vaultupgrade": "vault", "skills": "skills",
    "skill": "skills", "titles": "titles", "forge": "forge",
    "home": "structures", "workshop": "workshop", "repair": "workshop",
    "quickcraft": "workshop",
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
