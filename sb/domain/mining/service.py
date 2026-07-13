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


def _no_args(req) -> bool:
    """True when the invocation carried no item argument — the shipped
    arg-optional ``item: str = None`` bare-call branch (mining_cog.py
    ``!sell`` / ``!buy``)."""
    return (not tuple(req.args.get("argv", ()) or ())
            and not tuple(req.args.get("values", ()) or ()))


async def _card(req, embed) -> Reply:
    """Present one read card as the shipped public embed reply
    (``ctx.send(embed=…)`` — the ai.card/karma.card open_panel lane)."""
    import dataclasses

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("mining.card"), dataclasses.replace(
        req, args={**dict(req.args), "_card": embed}))
    return Reply(SUCCESS, None)


async def _card_with_file(req, embed, filename: str) -> Reply:
    """Present one read card carrying a single file attachment (the shipped
    ``ctx.send(embed=…, file=discord.File(…, filename=…))`` — the paper-doll
    sends). The parity transport collapses any attachment-bearing panel to
    ``{"_files": [filename]}`` (the multipart-serializer information loss both
    capture and replay share — goldens/mining/sweep_gear pins
    ``character_doll.png``, sweep_character pins ``character.png``)."""
    import dataclasses

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("mining.card"), dataclasses.replace(
        req, args={**dict(req.args), "_card": embed,
                   "_attachment": filename}))
    return Reply(SUCCESS, None)


def _durability_bar(remaining: int, maximum: int) -> str:
    """A 5-segment ``▰▰▰▱▱ 23/60`` bar — shipped
    ``utils/mining/workshop.durability_bar`` verbatim (the ``!minestats``
    Game Level gauge; goldens/mining/sweep_minestats pins the bytes)."""
    import math

    if maximum <= 0:
        return f"{remaining}/{maximum}"
    filled = math.ceil(remaining / maximum * 5)
    filled = max(0, min(5, filled))
    return f"{'▰' * filled}{'▱' * (5 - filled)} {remaining}/{maximum}"


def _author_name(req) -> str | None:
    """The invoker's username off the surface origin — the shipped
    ``ctx.author.name`` read (``!minestats`` title); ``None`` when the
    origin carries no member (the directory-port fallback's cue)."""
    origin = getattr(req, "origin", None)
    member = (getattr(origin, "author", None)
              or getattr(origin, "user", None))
    name = (str(getattr(member, "name", "") or "")
            or str(getattr(member, "display_name", "") or ""))
    return name or None


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

    @handler("mining.sell_route")
    async def sell_route(req) -> Reply:
        """`!sell [item] [qty]` — shipped arg-optional (mining_cog.py
        ``sell(self, ctx, item: str = None, …)``): the bare invocation
        answers the usage copy plain (goldens/mining/sweep_sell pins the
        bytes); argful calls run the audited op unchanged."""
        if _no_args(req):
            return Reply(BLOCKED, "Specify what to sell, e.g. "
                                  "`!sell iron 10` — or `!sellall`.")
        return await _run_op("mining.sell")(req)

    @handler("mining.sellall_route")
    async def sellall_route(req) -> Reply:
        """`!sellall` — the shipped empty-pack pre-check reads BEFORE the
        txn (services/mining_workflow.sell_all: inventory →
        ``sellable_inventory`` → ``TradeResult(False, …)``, sent with the
        cog's mention prefix — goldens/mining/sweep_sellall pins the
        bytes). Non-empty packs run the audited op (its FOR UPDATE
        inventory read + in-txn guard untouched)."""
        from sb.domain.mining import market
        from sb.domain.mining.store import get_mining_inventory

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        inventory = await get_mining_inventory(uid,
                                               int(req.guild_id or 0))
        if not market.sellable_inventory(inventory):
            return Reply(BLOCKED, f"<@{uid}> You have no resources to "
                                  "sell — go mine some!")
        return await _run_op("mining.sell_all")(req)

    @handler("mining.buy_route")
    async def buy_route(req) -> Reply:
        """`!buy [item]` — shipped arg-optional (mining_cog.py
        ``buy(self, ctx, *, item: str = None)``): the bare invocation
        answers the usage copy plain (goldens/mining/sweep_buy pins the
        bytes); argful calls run the audited op unchanged."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify what to buy — see `!market` for the "
                         "shop.")
        return await _run_op("mining.buy")(req)

    @handler("mining.inventory_view")
    async def inventory_view(req) -> Reply:
        """`!mineinv` — the shipped compatibility alias delegation
        (mining_cog.py ``mineinv``, classification "legacy_duplicate":
        ``ctx.bot.get_command("inventory")`` → invoke): route into the
        unified inventory hub handler verbatim
        (goldens/mining/sweep_mineinv pins the same bytes the green
        goldens/inventory/sweep_inventory pins)."""
        from sb.spec.refs import resolve

        return await resolve(HandlerRef("inventory.view"))(req)

    @handler("mining.stats_view")
    async def stats_view(req) -> Reply:
        """`!minestats` — the shipped stats embed (mining_cog.py:
        ``{ctx.author.name}'s Mining Stats``, MINING_COLOR dark_grey,
        Location + 🎮 Game Level non-inline, the four inline counters —
        goldens/mining/sweep_minestats pins the bytes). Deepest reads the
        current depth: the shipped ``max_depth`` record only diverges
        through descend/ascend, which ride the D-0043 deep-system port.
        Net worth values resources/fish only (the hub Wealth field's
        ledgered D-0043 boundary — shipped ``items.total_value`` also
        valued tools/gear)."""
        from sb.domain.games import store as games_store
        from sb.domain.mining import market
        from sb.domain.mining.store import get_depth, get_mining_inventory
        from sb.domain.mining.world import describe_position
        from sb.domain.xp.levels import level_progress
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        depth = await get_depth(uid, gid)
        level, into, needed = level_progress(
            await games_store.total_game_xp(uid, gid))
        worth = sum(qty * (market.sell_price(item) or 0)
                    for item, qty in inventory.items())
        name = _author_name(req) or await _member_name(uid, gid)
        return await _card(req, RenderedEmbed(
            title=f"{name}'s Mining Stats", description="",
            style_token="dark_grey",
            fields=(
                ("Location", describe_position(depth), False),
                ("🎮 Game Level",
                 f"Level **{level}** — {_durability_bar(into, needed)} "
                 "XP", False),
                ("Total Items Collected",
                 str(sum(inventory.values())), True),
                ("Unique Items", str(len(inventory)), True),
                ("Net Worth", str(worth), True),
                ("Deepest", describe_position(depth), True),
            )))

    @handler("mining.market_view")
    async def market_view(req) -> Reply:
        """`!market` — the shipped market embed (mining_cog.py
        ``market_cmd``: 🛒 Mining Market, the sellables field when the
        pack holds any, the price-then-name ordered 🛍️ Buy gear listing,
        the dynamic balance footer — goldens/mining/sweep_market pins
        the empty-pack bytes)."""
        from sb.domain.economy.store import get_coins
        from sb.domain.mining import market
        from sb.domain.mining.store import get_mining_inventory
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        balance = await get_coins(uid, gid)
        sellables = market.sellable_inventory(inventory)
        sale_total = sum(qty * price for _, qty, price in sellables)
        fields: list[tuple[str, str, bool]] = []
        if sellables:
            fields.append((
                f"💰 Sell (total {sale_total} 🪙)",
                "\n".join(f"**{name.title()}** ×{qty} → {qty * price} 🪙"
                          for name, qty, price in sellables), False))
        fields.append((
            "🛍️ Buy gear",
            "\n".join(f"**{name.title()}** — {price} 🪙"
                      for name, price in market.shop_listing()), False))
        return await _card(req, RenderedEmbed(
            title="🛒 Mining Market", description="",
            style_token="dark_grey", fields=tuple(fields),
            footer=f"Balance: {balance} 🪙  •  !sell <item> [n] · "
                   "!sellall · !buy <item>"))

    async def _buildlist_card(req) -> Reply:
        """The shipped `!buildlist` reply (mining_cog.py ``buildlist``): the
        SUCCESS_COLOR (green) `Available Structures` embed listing every recipe
        in the shipped catalogue order as `**{Name}**: Requires {mats}` (the
        material list is the recipe's insertion order, NOT sorted), footer
        `Tip: !minemenu → 📖 Recipes browses and crafts by category.`
        (goldens/mining/sweep_buildlist pins every byte)."""
        from sb.domain.mining.recipes import load_recipes
        from sb.kernel.panels.render import RenderedEmbed

        lines = [
            f"**{name.title()}**: Requires "
            + ", ".join(f"{mat}: {amt}" for mat, amt in reqs.items())
            for name, reqs in load_recipes().items()
        ]
        return await _card(req, RenderedEmbed(
            title="Available Structures", description="\n".join(lines),
            style_token="green",
            footer="Tip: !minemenu → 📖 Recipes browses and crafts by "
                   "category."))

    @handler("mining.build_route")
    async def build_route(req) -> Reply:
        """`!build [*structure]` (alias `craft`) — shipped arg-optional
        (mining_cog.py ``build(self, ctx, *, structure: str = None)``): with NO
        structure it invokes `!buildlist` (the Available Structures embed —
        goldens/mining/sweep_build pins the identical bytes); an argful
        `!build <item>` runs the shared atomic craft write (materials → product)
        which rides the deferred structures/craft port — no golden drives it —
        so it stays an honest D-0043 pending terminal (the argful cook/use
        precedent)."""
        if _no_args(req):
            return await _buildlist_card(req)
        return Reply(BLOCKED,
                     "🏗️ `!build <item>` / `!craft` crafting rides the mining "
                     "structures/craft build lane — the deep mining port is "
                     "named successor work (D-0043); the core loop "
                     "(mine/chop/explore/sell/buy) is live.")

    @handler("mining.buildlist_route")
    async def buildlist_route(req) -> Reply:
        """`!buildlist` — the Available Structures embed (see _buildlist_card;
        goldens/mining/sweep_buildlist pins the bytes)."""
        return await _buildlist_card(req)

    @handler("mining.buildable_view")
    async def buildable_view(req) -> Reply:
        """`!buildable` — list only what the player's inventory can currently
        build (mining_cog.py ``buildable``). A fresh player (empty pack) can
        afford nothing → the plain refusal
        (goldens/mining/sweep_buildable pins ``You currently don't have enough
        resources to build anything.``) — a PURE READ. The row-bearing
        non-empty branch (the `{name}'s Buildable Structures` embed) exists in
        no imported golden."""
        from sb.domain.mining.recipes import load_recipes
        from sb.domain.mining.store import get_mining_inventory
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        can_build = [
            name for name, reqs in load_recipes().items()
            if all(inventory.get(item, 0) >= amt
                   for item, amt in reqs.items())
        ]
        if not can_build:
            return Reply(BLOCKED,
                         "You currently don't have enough resources to build "
                         "anything.")
        name = _author_name(req) or await _member_name(uid, gid)
        return await _card(req, RenderedEmbed(
            title=f"{name}'s Buildable Structures",
            description="\n".join(s.title() for s in can_build),
            style_token="green"))

    @handler("mining.equip_route")
    async def equip_route(req) -> Reply:
        """`!equip [*item]` — shipped arg-optional (mining_cog.py
        ``equip(self, ctx, *, item: str = None)``): the bare invocation
        answers the usage copy plain (goldens/mining/sweep_equip pins the
        bytes); argful calls run the audited equip op and prefix the
        invoker mention (the shipped ``ctx.send(f"{mention} …")`` success
        lane), while a business-rule refusal (can't-equip / don't-own)
        sends plain."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify what to equip, e.g. `!equip iron "
                         "pickaxe`.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        blocked, after = await _op_after(
            req, "mining.equip", {"argv": argv, "values": values})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.unequip_route")
    async def unequip_route(req) -> Reply:
        """`!unequip [*slot]` — the bare invocation answers the usage copy
        plain, enumerating ``equipment.SLOTS`` in order
        (goldens/mining/sweep_unequip pins the bytes); argful calls run
        the audited unequip op and prefix the mention on success."""
        from sb.domain.mining import equipment

        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify a slot to clear: "
                         f"{', '.join(equipment.SLOTS)}.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        blocked, after = await _op_after(
            req, "mining.unequip", {"argv": argv, "values": values})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.loadout_route")
    async def loadout_route(req) -> Reply:
        """`!loadout [action] [*name]` (aliases: loadouts) — the bare
        invocation (verb ∈ {"", list, ls}) with NO saved loadouts answers
        the pinned prompt plain (goldens/mining/sweep_loadout); with
        loadouts it lists them prefixed with the mention. The
        save/apply/delete verbs run their audited ops (each prefixes the
        mention on success, sends the per-verb prompt or business refusal
        plain); a bare ``!loadout <name>`` applies that preset."""
        from sb.domain.mining import store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        argv = [str(t) for t in tuple(req.args.get("argv", ()) or ())]
        verb = (argv[0].strip().lower() if argv else "")
        name = " ".join(argv[1:]).strip()

        if verb in ("", "list", "ls"):
            names = await store.list_loadouts(uid, gid)
            if not names:
                return Reply(BLOCKED,
                             "You have no saved loadouts yet. Equip some "
                             "gear, then `!loadout save <name>` (e.g. "
                             "`mining`).")
            listed = ", ".join(f"**{n}**" for n in names)
            return Reply(SUCCESS,
                         f"<@{uid}> your loadouts: {listed}\n"
                         "Swap with `!loadout <name>`.")

        if verb == "save":
            if not name:
                return Reply(BLOCKED,
                             "Name it, e.g. `!loadout save mining`.")
            op_key, arg = "mining.save_loadout", name
        elif verb in ("delete", "del", "remove", "rm"):
            if not name:
                return Reply(BLOCKED,
                             "Which one? e.g. `!loadout delete mining`.")
            op_key, arg = "mining.delete_loadout", name
        elif verb == "apply":
            if not name:
                return Reply(BLOCKED,
                             "Which one? e.g. `!loadout apply mining`.")
            op_key, arg = "mining.apply_loadout", name
        else:
            # Bare `!loadout <name>` is the common case: apply that loadout.
            op_key = "mining.apply_loadout"
            arg = " ".join(argv).strip()

        blocked, after = await _op_after(req, op_key, {"loadout_name": arg})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.gear_view")
    async def gear_view(req) -> Reply:
        """`!gear` — the shipped gear embed + paper-doll send
        (mining_cog.py ``gear``; views/mining/gear_panel.py builds the
        ``🧍 {name}'s Gear`` embed and attaches ``character_doll.png``).
        The parity transport records only the attachment filename
        (goldens/mining/sweep_gear pins ``{"_files": ["character_doll.png"]}``);
        the embed layout + PNG bytes are dropped by the multipart
        serializer on both capture and replay."""
        from sb.domain.mining import equipment as _eq
        from sb.domain.mining import store
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        equipped = await store.get_equipment(uid, gid)
        wear = await store.get_gear_wear(uid, gid)
        name = _author_name(req) or await _member_name(uid, gid)
        fields: list[tuple[str, str, bool]] = []
        for slot in _eq.SLOTS:
            held = equipped.get(slot)
            if held:
                maximum = _eq.max_durability(held)
                cond = (f"  {_durability_bar(wear.get(held, maximum), maximum)}"
                        if maximum is not None else "")
                fields.append((slot.title(), f"{held.title()}{cond}", True))
            else:
                fields.append((slot.title(), "*(empty)*", True))
        stats = _eq.compute_stats(equipped)
        lines = [f"{label}: **+{value}**"
                 for label, value in _eq.describe_stats(stats)]
        fields.append(("Stats",
                       "\n".join(lines) or "No bonuses yet — equip some "
                       "gear!", False))
        progress = _eq.set_progress(equipped)
        active = _eq.active_set_tier(equipped)
        if active:
            fields.append(("✨ Set bonus",
                           f"Full **{active.title()}** set", False))
        elif progress:
            tier, pieces = progress
            fields.append(("🧩 Set progress",
                           f"{tier.title()} set {pieces}/"
                           f"{len(_eq.SET_SLOTS)}", False))
        embed = RenderedEmbed(
            title=f"🧍 {name}'s Gear", description="",
            style_token="dark_grey", fields=tuple(fields),
            footer="Tip: !minemenu → 🧰 Gear equips with clicks (and ✨ "
                   "Equip Best).")
        return await _card_with_file(req, embed, "character_doll.png")

    @handler("mining.character_view")
    async def character_view(req) -> Reply:
        """`!character` (aliases: profile, char) — the shipped character
        card + paper-doll send (mining_cog.py ``character``;
        views/mining/character_panel.py builds the ``🧍 {name}'s
        Character`` embed and attaches ``character.png``). The parity
        transport records only the attachment filename
        (goldens/mining/sweep_character pins ``{"_files": ["character.png"]}``)."""
        from sb.domain.games import store as games_store
        from sb.domain.mining import character as _char
        from sb.domain.mining import equipment as _eq
        from sb.domain.mining import market, store
        from sb.domain.mining.store import get_depth, get_mining_inventory
        from sb.domain.mining.world import describe_position
        from sb.domain.xp.levels import level_progress
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        equipped = await store.get_equipment(uid, gid)
        alloc = await store.get_skills(uid, gid)
        inventory = await get_mining_inventory(uid, gid)
        depth = await get_depth(uid, gid)
        level, _into, _needed = level_progress(
            await games_store.total_game_xp(uid, gid))
        worth = sum(qty * (market.sell_price(item) or 0)
                    for item, qty in inventory.items())
        name = _author_name(req) or await _member_name(uid, gid)
        stats = _char.character_stats(equipped, alloc)
        stat_lines = [f"{label}: **+{value}**"
                      for label, value in _eq.describe_stats(stats)]
        gear_overview = ", ".join(
            f"{slot}: {equipped[slot].title()}" for slot in _eq.SLOTS
            if slot in equipped) or "*(nothing equipped)*"
        embed = RenderedEmbed(
            title=f"🧍 {name}'s Character", description="",
            style_token="dark_grey",
            fields=(
                ("📍 Location", describe_position(depth), True),
                ("🎮 Game Level", f"Level **{level}**", True),
                ("🧰 Gear", gear_overview, False),
                ("📊 Stats", "\n".join(stat_lines) or "No bonuses yet.",
                 False),
                ("💰 Wealth", f"Inventory net worth: **{worth}**", False),
            ))
        return await _card_with_file(req, embed, "character.png")

    @handler("mining.descend_route")
    async def descend_route(req) -> Reply:
        """`!descend` — the shipped depth move (mining_cog.py ``descend``;
        services/mining_workflow.py ``descend``). The move is gated by the
        equipped light's ``depth_access`` stat (persistent, not consumed):
        a fresh gearless player reads all-zero stats and CANNOT descend, so
        the bare invocation answers the mention-prefixed refusal
        (goldens/mining/sweep_descend pins ``<@…> can't descend any deeper.
        Equip a brighter light to descend to Cavern (needs depth access
        1).``) — a pure read, no write, no audit row. A geared descent runs
        the audited depth op (set_depth + one-time depth_record game XP) and
        answers the moved position; that row-bearing lane exists in no
        imported golden (depth.exemptions.mining guard-only-capture)."""
        from sb.domain.mining import character, store, world

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        depth = await store.get_depth(uid, gid)
        equipped = await store.get_equipment(uid, gid)
        alloc = await store.get_skills(uid, gid)
        stats = character.character_stats(equipped, alloc)
        if world.descend(depth, stats) == depth:
            return Reply(BLOCKED,
                         f"<@{uid}> can't descend any deeper. "
                         f"{world.descend_hint(stats)}")
        blocked, after = await _op_after(req, "mining.descend")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.ascend_route")
    async def ascend_route(req) -> Reply:
        """`!ascend` — the shipped climb (mining_cog.py ``ascend``;
        services/mining_workflow.py ``ascend``). A player at the Surface
        cannot ascend, so the bare fresh-player invocation answers the
        mention-prefixed refusal (goldens/mining/sweep_ascend pins ``<@…>
        is already at the Surface.``) — a pure read, no write. Below the
        Surface the audited op writes the new band and answers the moved
        position (no imported golden drives it)."""
        from sb.domain.mining import store, world

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        depth = await store.get_depth(uid, gid)
        if world.ascend(depth) == depth:
            return Reply(BLOCKED, f"<@{uid}> is already at the Surface.")
        blocked, after = await _op_after(req, "mining.ascend")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.mineworld_route")
    async def mineworld_route(req) -> Reply:
        """`!mineworld [seed]` — the shipped shared-world seed (mining_cog.py
        ``mineworld``). Bare: reads the guild's world seed (a guild with no
        row defaults to ``seed = guild_id`` in the store) and answers the
        seed-share copy plain (goldens/mining/sweep_mineworld pins the
        default-seed byte with no row). With a numeric seed: the manage_guild
        re-seed (ActorRef.is_guild_operator — the shipped
        ``member_has_perms_or_owner(manage_guild=True)`` port home) runs the
        audited reseed op; a non-manager is refused, an unparseable seed
        degrades through the generic copy. The reseed WRITE exists in no
        imported golden (depth.exemptions.mining guard-only-capture)."""
        from sb.domain.mining import store

        gid = int(req.guild_id or 0)
        argv = [str(t) for t in tuple(req.args.get("argv", ()) or ())]
        values = [str(t) for t in tuple(req.args.get("values", ()) or ())]
        tokens = argv or values
        if not tokens:
            current = await store.get_world_seed(gid)
            return Reply(SUCCESS,
                         f"🌐 This server's mining world seed is "
                         f"**{current}**. Everyone here roams the same "
                         "world — share the seed to compare maps. Server "
                         "managers can reseed with `!mineworld <number>`.")
        try:
            seed = int(tokens[0])
        except ValueError:
            return Reply(BLOCKED, _GENERIC_ERROR)
        if not getattr(req.actor, "is_guild_operator", False):
            return Reply(BLOCKED,
                         "Only server managers can reseed the mining world.")
        blocked, _after = await _op_after(req, "mining.reseed_world",
                                          {"seed": seed})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS,
                     f"🌐 Reseeded this server's mining world to **{seed}**. "
                     "The whole grid regenerated; your position and explored "
                     "map carry over.")

    @handler("mining.stash_route")
    async def stash_route(req) -> Reply:
        """`!stash [item] [amount]` — the shipped vault deposit (mining_cog.py
        ``stash``; services/mining_workflow.py ``vault_deposit``). The bare
        invocation answers the usage copy plain (goldens/mining/sweep_stash
        pins the byte) — a pure read, no write; an argful call runs the audited
        deposit op (inventory debit + vault credit in one txn) and prefixes the
        invoker mention on success, sending a business refusal plain. The
        row-bearing deposit exists in no imported golden
        (depth.exemptions.mining guard-only-capture)."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify what to stash, e.g. `!stash diamond 5` "
                         "— or `!vault`.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        blocked, after = await _op_after(
            req, "mining.stash", {"argv": argv, "values": values})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.unstash_route")
    async def unstash_route(req) -> Reply:
        """`!unstash [item] [amount]` — the shipped vault withdraw
        (mining_cog.py ``unstash``; services/mining_workflow.py
        ``vault_withdraw``). The bare invocation answers the usage copy plain
        (goldens/mining/sweep_unstash pins the byte); an argful call runs the
        audited withdraw op and prefixes the mention on success."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify what to withdraw, e.g. `!unstash diamond 5` "
                         "— or `!vault`.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        blocked, after = await _op_after(
            req, "mining.unstash", {"argv": argv, "values": values})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.vaultupgrade_route")
    async def vaultupgrade_route(req) -> Reply:
        """`!vaultupgrade` — buy one vault-capacity tier (mining_cog.py
        ``vaultupgrade``; services/mining_workflow.py ``vault_upgrade``). The
        shipped handler always prefixes the mention (both ok and refusal). A
        fresh player reads vault level 0 → cost 2000 and balance 0 → the
        insufficient-funds refusal (goldens/mining/sweep_vaultupgrade pins
        ``<@…> A vault upgrade costs **2000** 🪙 — you only have **0** 🪙.``) —
        computed as a PURE READ (get_vault_level + get_coins) so the failed
        attempt writes no coin ledger / audit row, exactly as the oracle's txn
        rolls back. Only a funded upgrade runs the audited debit-and-bump op
        (mining_player_state.vault_level write); that lane exists in no imported
        golden (depth.exemptions.mining guard-only-capture)."""
        from sb.domain.economy.store import get_coins
        from sb.domain.mining import capacity, store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        level = await store.get_vault_level(uid, gid)
        cost = capacity.vault_upgrade_cost(level)
        if cost is None:
            cap = capacity.vault_capacity(level)
            return Reply(BLOCKED,
                         f"<@{uid}> Your vault is already at its maximum "
                         f"capacity (**{cap}** item types).")
        balance = await get_coins(uid, gid)
        if balance < cost:
            return Reply(BLOCKED,
                         f"<@{uid}> A vault upgrade costs **{cost}** 🪙 — "
                         f"you only have **{balance}** 🪙.")
        blocked, after = await _op_after(req, "mining.vault_upgrade")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.stash_all_route")
    async def stash_all_route(req) -> Reply:
        """The 🏦 Vault panel's 📦 Stash All Ore button — tuck every raw
        resource into the vault in one txn (mining_workflow
        ``vault_deposit_all_resources``). No command binds it and no golden
        drives the click; the audited stash-all op carries the write, the
        empty-pack case answers the shipped nudge plain."""
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        blocked, after = await _op_after(req, "mining.stash_all")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.repair_route")
    async def repair_route(req) -> Reply:
        """`!repair [item]` — repair worn gear for coins (mining_cog.py
        ``repair``; services/mining_workflow.py ``repair``). The bare invocation
        answers the usage copy PLAIN (goldens/mining/sweep_repair pins the byte)
        — a pure read, no write; an argful call runs the audited repair op
        (economy debit + wear clear in one txn, advisory-fenced) and prefixes the
        invoker mention on success. No golden drives a funded repair
        (depth.exemptions.mining guard-only-capture: mining_gear_wear)."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify what to repair, e.g. `!repair pickaxe` "
                         "— or `!workshop`.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        blocked, after = await _op_after(
            req, "mining.repair", {"argv": argv, "values": values})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.quickcraft_route")
    async def quickcraft_route(req) -> Reply:
        """`!quickcraft` — re-craft the last gear item that broke and equip it
        (mining_cog.py ``quick_craft``; services/mining_workflow.py
        ``quick_craft``). The shipped handler always prefixes the mention. A
        fresh player has no broken item (NULL last_broken_item) → the "nothing
        broken" refusal (goldens/mining/sweep_quickcraft pins ``<@…> Nothing has
        broken recently — craft or repair gear below.``) — computed as a PURE
        READ (get_last_broken) so the no-op attempt writes no audit row, exactly
        as the oracle's ok=False result never opened a txn. Only a real
        quick-craft runs the audited material-consume + equip + marker-clear op;
        that lane exists in no imported golden (depth.exemptions.mining
        guard-only-capture)."""
        from sb.domain.mining import store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        last = await store.get_last_broken(uid, gid)
        if not last:
            return Reply(BLOCKED,
                         f"<@{uid}> Nothing has broken recently — craft or "
                         "repair gear below.")
        blocked, after = await _op_after(req, "mining.quick_craft")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")

    @handler("mining.cook_route")
    async def cook_route(req) -> Reply:
        """`!cook [fish]` — cook a caught fish into food (mining_cog.py
        ``cook``). The bare invocation answers the usage copy PLAIN
        (goldens/mining/sweep_cook pins the byte). The argful cook write
        (fish → cooked fish, gated on a built 🔥 Campfire, refilling mining
        energy) rides the deferred mining energy/consumable system — no golden
        drives it — so it stays an honest D-0043 pending terminal."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Specify a fish to cook, e.g. `!cook minnow` "
                         "(needs a 🔥 Campfire).")
        return Reply(BLOCKED,
                     "🔥 `!cook` needs the mining campfire/energy system — the "
                     "deep mining port is named successor work (D-0043); the "
                     "core loop (mine/chop/explore/sell/buy) is live.")

    @handler("mining.use_route")
    async def use_route(req) -> Reply:
        """`!use [item]` — use a consumable from your pack (mining_cog.py
        ``use``). The bare invocation answers the usage copy PLAIN
        (goldens/mining/sweep_use pins the byte). The argful consume (torch /
        dynamite flavour + food/booster energy refill) rides the deferred mining
        energy/consumable system — no golden drives it — so it stays an honest
        D-0043 pending terminal."""
        if _no_args(req):
            return Reply(BLOCKED,
                         "Please specify an item to use, e.g. `!use torch`.")
        return Reply(BLOCKED,
                     "🎒 `!use` needs the mining consumable/energy system — the "
                     "deep mining port is named successor work (D-0043); the "
                     "core loop (mine/chop/explore/sell/buy) is live.")

    @handler("mining.skill_route")
    async def skill_route(req) -> Reply:
        """`!skill [branch] [amount]` — spend skill points into a branch
        (mining_cog.py ``skill_cmd``; services/skill_service.py ``allocate``).
        The bare invocation answers the branch-picker guard PLAIN
        (goldens/mining/sweep_skill pins the byte:
        ``Pick a branch to train: mining, combat, fortune, crafting — e.g.
        `!skill mining`, or `!skills` for the panel.``) — a pure read, no write.
        The argful point spend runs the audited ``mining.skill`` op
        (record_skill: the ported allocate, self-service upsert of the
        player_skills row, advisory-fenced against the shared-budget race) and
        prefixes the invoker mention on BOTH the success and the business-refusal
        face — the shipped ``ctx.send(f"{mention} {result.message}")`` lane
        (goldens/mining/mining_skill_write drives the spend, mining_skill_bad_branch
        pins the refusal). Constants/copy are oracle-verbatim (skill_service /
        utils/mining/skills)."""
        from sb.domain.mining import skills

        if _no_args(req):
            names = ", ".join(skills.BRANCHES)
            return Reply(BLOCKED,
                         f"Pick a branch to train: {names} — e.g. "
                         "`!skill mining`, or `!skills` for the panel.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        values = tuple(req.args.get("values", ()) or ())
        blocked, after = await _op_after(
            req, "mining.skill", {"argv": argv, "values": values})
        if blocked is not None:
            return Reply(blocked.outcome, f"<@{uid}> {blocked.user_message}")
        return Reply(SUCCESS, f"<@{uid}> {after.get('message', '')}")


#: The deep-system commands (shipped names) → pending copy. The mining
#: depth port (equipment/wear/energy/grid/vault/structures/skills/
#: forge/workshop/titles/loadouts/character) is D-0043 successor work.
PENDING: dict[str, str] = {
    # build / buildlist / buildable are LIVE (slice 6 port): build_route /
    # buildlist_route / buildable_view in _register() carry the Available
    # Structures recipe embed + the fresh-player "not enough resources" guard
    # (the argful `!build <item>` / craft write stays a D-0043 pending
    # terminal). home / workshop are LIVE (slice 6 port): the mining.home +
    # mining.workshop session PanelSpecs carry the not-built Home card + the
    # Workshop craft/repair panel bytes (the 🏠 Build structure write, the
    # craft-select write, and the ↩ Workshop sub-hub stay deferred).
    # This EMPTIES the mining deep-system PENDING roster — all 26 original
    # deep-system commands are ported (the D-0043 ladder is complete).
    # equip / unequip / gear / loadout / character are LIVE (slice 1 port):
    # their real handlers are the *_route / *_view registered in _register()
    # (mirroring the sell/buy/market lanes), so they leave the PENDING roster.
    # descend / ascend / mineworld are LIVE (slice 2 port): descend_route /
    # ascend_route / mineworld_route in _register() carry the depth-traversal
    # + world-seed bytes, so they too leave the PENDING roster.
    # vault / stash / unstash / vaultupgrade are LIVE (slice 3 port): the
    # mining.vault session PanelSpec + stash_route / unstash_route /
    # vaultupgrade_route carry the safe-stash + capacity-sink bytes.
    # mineinv already routes to the live mining.inventory_view (re-homed #250),
    # so it too leaves the PENDING roster.
    # forge / repair / quickcraft / cook / use are LIVE (slice 4 port): the
    # mining.forge session PanelSpec + repair_route / quickcraft_route /
    # cook_route / use_route carry the workshop/campfire/consumable bytes (the
    # forge not-built card + the repair/cook/use usage guards + the quickcraft
    # "nothing broken" pure read). The structures BUILD write (🔥 Build) and the
    # argful cook/use energy lanes stay deferred (D-0043 pending terminals).
    # skills / skill / titles are LIVE (slice 5 port): the mining.skills +
    # mining.titles session PanelSpecs carry the skill-tree + earned-title
    # render bytes, and skill_route carries the `!skill` branch-picker guard AND
    # the argful `!skill <branch>` spend (WP-5 PORT: mining.skill -> record_skill,
    # the ported skill_service.allocate — goldens/mining/mining_skill_write drives
    # the player_skills upsert). The skills-panel respec button (no command form —
    # a panel-button coin sink) and the titles select-menu equip (select-driven)
    # stay deferred (D-0043 pending terminals — no golden drives those writes).
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
