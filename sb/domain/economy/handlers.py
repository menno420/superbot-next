"""Economy read/command handlers (band 3) — thin HandlerRef routes.

Reads render from the K3 seam; the ONE pointer write (`!setlogchannel`)
routes through the band-1 settings ops (§4.1 one-write-path — economy never
touches the bindings table itself). `!work <job>` runs the K7 op; bare
`!work` lists eligible jobs (the shipped dropdown becomes the panel-action
slice, successor work).
"""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]


def _target_id(req) -> int:
    """Optional member arg (mention) else the invoker — shipped !balance."""
    argv = tuple(req.args.get("argv", ()) or ())
    for token in argv:
        stripped = str(token).strip("<@!>")
        if stripped.isdigit():
            return int(stripped)
    return int(getattr(req.actor, "user_id", 0) or 0)


def _author_display(req) -> tuple[str, str]:
    """(display name, avatar url) for the invoking member — the shipped
    ``set_author(ctx.author.display_name, ctx.author.display_avatar.url)``
    line, duck-typed over the surface origin. Members without a custom
    avatar get discord's default-avatar URL (index ``(id >> 22) % 6``)."""
    origin = getattr(req, "origin", None)
    member = (getattr(origin, "author", None)
              or getattr(origin, "user", None))
    uid = int(getattr(member, "id", 0) or getattr(req.actor, "user_id", 0)
              or 0)
    name = (str(getattr(member, "display_name", "") or "")
            or str(getattr(member, "name", "") or "") or f"<@{uid}>")
    icon = str(getattr(getattr(member, "display_avatar", None), "url", "")
               or "")
    if not icon:
        icon = f"https://cdn.discordapp.com/embed/avatars/{(uid >> 22) % 6}.png"
    return name, icon


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("economy.balance_view")):
        return

    @handler("economy.balance_view")
    async def balance_view(req) -> Reply:
        """!balance [@user] — the shipped Wallet embed (economy_cog.py
        balance: name-titled, avatar thumbnail, bold coins + level fields;
        goldens/economy/sweep_balance + economy_balance_and_daily pin the
        bytes). A pure read — the shipped command never ensured the
        economy tracking row."""
        import dataclasses

        from sb.domain.economy import service, store
        from sb.domain.economy.panels import (
            WALLET_CARD_PANEL_ID,
            _member_display,
        )
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        gid = int(req.guild_id or 0)
        invoker = int(getattr(req.actor, "user_id", 0) or 0)
        target = _target_id(req)
        if target == invoker:
            name, icon = _author_display(req)
        else:
            name, icon = await _member_display(target, gid)
            if not name:
                name = f"<@{target}>"
        coins = await store.get_coins(target, gid)
        level = await service.active_level_reader()(target, gid)
        card_req = dataclasses.replace(
            req, args={**dict(req.args), "wallet_name": name,
                       "wallet_icon": icon, "coins": coins, "level": level})
        await open_panel(PanelRef(WALLET_CARD_PANEL_ID), card_req)
        return Reply(SUCCESS, None)

    @handler("economy.daily_view")
    async def daily_view(req) -> Reply:
        """!daily — run the audited K7 claim, then send the shipped Daily
        Reward embed (cogs/economy_cog.py: author line + gold accent + four
        inline fields + the odds footer). Refusals (cooldown) keep their
        verbatim domain copy as a plain reply."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(
            WorkflowRef("economy.daily"),
            _ctx_from_req(req, dict(req.args)))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not claim today.")
        after = (result.after or {}).get("daily", {})
        from sb.domain.economy.panels import DAILY_CARD_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        import dataclasses

        name, icon = _author_display(req)
        card_req = dataclasses.replace(
            req, args={**dict(req.args), **after,
                       "author_name": name, "author_icon": icon})
        await open_panel(PanelRef(DAILY_CARD_PANEL_ID), card_req)
        return Reply(SUCCESS, None)

    @handler("economy.joblist_view")
    async def joblist_view(req) -> Reply:
        """!joblist — the shipped All Jobs embed (cogs/economy_cog.py
        joblist: INFO_COLOR blue, one field per tier, the level footer;
        goldens/economy/sweep_joblist pins the bytes). The embed is
        composed by the joblist card's renderer_override."""
        from sb.domain.economy.panels import JOBLIST_CARD_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(JOBLIST_CARD_PANEL_ID), req)
        return Reply(SUCCESS, None)

    @handler("economy.work_view")
    async def work_view(req) -> Reply:
        """!work — open the shipped Job Center dropdown (economy_cog.work
        took NO argument: the job pick is ONLY the select, whose pick runs
        the audited economy.work op; discord.py ignored trailing tokens, so
        argv is ignored here too). The shipped command started with the
        ensure_and_get_economy read-that-writes — goldens/economy/
        sweep_work pins the zero-row economy db_delta."""
        from sb.domain.economy import store
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        await store.ensure_tracking_row(uid, gid)
        await open_panel(PanelRef("economy.jobcenter"), req)
        return Reply(SUCCESS, None)

    @handler("economy.shop_view")
    async def shop_view(req) -> Reply:
        from sb.domain.economy import catalogue

        lines = ["🛒 **Item Shop** — buy items to unlock higher-tier jobs."]
        for name, data in catalogue.SHOP_ITEMS.items():
            lines.append(f"{data['emoji']} "
                         f"**{name.replace('_', ' ').title()}** — "
                         f"{data['price']:,} 🪙 · {data['desc']}")
        lines.append("Purchases run through the shop panel "
                     "(the economy hub).")
        return Reply(SUCCESS, "\n".join(lines))

    @handler("economy.setlogchannel")
    async def setlogchannel(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!setlogchannel #channel`")
        token = str(argv[0]).lstrip("<#").rstrip(">")
        if not token.isdigit():
            return Reply(BLOCKED, "That doesn't look like a channel mention.")
        result = await engine.run(
            WorkflowRef("settings.bind"),
            _ctx_from_req(req, {"subsystem": "economy", "name": "log_channel",
                                "kind": "channel", "resource_id": int(token)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not bind the channel.")
        return Reply(SUCCESS,
                     f"✅ Economy log channel set to <#{int(token)}>.")


_register()


def ensure_handler_refs() -> None:
    _register()
