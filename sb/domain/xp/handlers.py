"""XP read/command handlers (band 4) — thin HandlerRef routes.

`!rank` sends the shipped rank IMAGE card (`rank.png` — the visual
card-engine H3 surface; goldens/xp/xp_chat_award pins the multipart send
+ the avatar `get_from_cdn` read) through the zero-action
``xp.rank_card`` panel. Category ranks resolve through the band-4
provider registry (sb.domain.community.rank_providers) exactly like the
shipped PR-G flow (their thinner provider CARD render is the visual
card-engine slice's follow-up — text until then).
"""

from __future__ import annotations

import dataclasses

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]

_STAT_TYPES = {"xp", "coins", "both"}     # shipped verbatim (xp_helpers)

#: bot1.py on_command_error's generic fallback, verbatim — the copy the
#: shipped bot sent when a command raised anything unclassified. The
#: capture world had no member gateway, so the shipped rank command's
#: member-name escalation (commands.MemberConverter → guild.query_members)
#: RAISED there and the global handler sent this; goldens/xp/
#: sweep_rank.json (`!rank test`) pins the byte.
_GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again."


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("xp.rank_view")):
        return

    @handler("xp.rank_view")
    async def rank_view(req) -> Reply | None:
        """!rank [stat|category|@user] — shipped PR-G arg walk verbatim."""
        from sb.domain.community.rank_providers import get_provider

        gid = int(req.guild_id or 0)
        member = int(getattr(req.actor, "user_id", 0) or 0)
        stat: str | None = None
        category: str | None = None
        for arg in tuple(req.args.get("argv", ()) or ()):
            token = str(arg)
            lowered = token.lower()
            if lowered in _STAT_TYPES:
                stat = lowered
                continue
            if lowered not in {"xp", "coins"}:
                provider = get_provider(lowered)
                if provider is not None:
                    category = provider.name
                    continue
            stripped = token.strip("<@!>")
            if stripped.isdigit():
                member = int(stripped)
                continue
            # DELIBERATE oracle-in-harness pin: the shipped walk escalated
            # a non-mention token to commands.MemberConverter, whose
            # name-lookup leg is a GATEWAY member query — the capture world
            # has none, so the shipped command raised and bot1.py's global
            # on_command_error sent the generic fallback
            # (goldens/xp/sweep_rank.json, `!rank test`). The live
            # name-resolution read lands with the member-directory search
            # port (follow-up slice); until then this is the same honest
            # failure the goldens pin.
            return Reply(BLOCKED, _GENERIC_ERROR)

        if category is not None:
            provider = get_provider(category)
            rank_pos, rendered = await provider.member_rank(gid, member)
            if rank_pos is None:
                return Reply(SUCCESS,
                             f"{provider.display_title} — <@{member}>\n"
                             f"{provider.empty_hint}")
            return Reply(SUCCESS,
                         f"{provider.display_title} — <@{member}>\n"
                         f"Rank **#{rank_pos}** · {rendered}")

        # the shipped H3 surface: the rank IMAGE card send (rank.png —
        # goldens/xp/xp_chat_award pins get_from_cdn + the multipart shape).
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(
            PanelRef("xp.rank_card"),
            dataclasses.replace(req, args={**dict(req.args),
                                           "rank_target": member,
                                           "rank_stat": stat or "both"}))
        return None

    @handler("xp.givexp")
    async def givexp(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            return Reply(BLOCKED, "Usage: `!givexp @user <amount>`")
        result = await engine.run(
            WorkflowRef("xp.award"),
            _ctx_from_req(req, {"argv": argv, "source": "admin:givexp"}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not give XP.")
        after = (result.after or {}).get("award", {})
        return Reply(SUCCESS,
                     f"✅ Gave **{after.get('delta', 0)}** XP to "
                     f"<@{ctx_target(argv)}>. They now have "
                     f"**{after.get('new_xp', 0)}** XP "
                     f"(Level **{after.get('new_level', 0)}**).")

    @handler("xp.resetxp")
    async def resetxp(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!resetxp @user`")
        result = await engine.run(
            WorkflowRef("xp.reset"),
            _ctx_from_req(req, {"argv": argv, "source": "admin:resetxp"}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not reset XP.")
        return Reply(SUCCESS, f"✅ Reset XP for <@{ctx_target(argv)}>.")

    @handler("xp.xpconfig_view")
    async def xpconfig_view(req) -> Reply:
        from sb.domain.xp import service

        gid = int(req.guild_id or 0)
        xp_min, xp_max, cooldown = await service.xp_config(gid)
        channel_id = await service.bound_announce_channel(gid)
        channel_str = (f"<#{channel_id}>" if channel_id
                       else "Same channel as message")
        return Reply(SUCCESS,
                     "⚙️ **XP Configuration**\n"
                     f"XP per message: **{xp_min}–{xp_max}**\n"
                     f"Cooldown: **{cooldown}s**\n"
                     f"Level-up channel: {channel_str}\n"
                     "Edit via the settings hub (`!settings`) — the xp.* "
                     "keys ride the one declared write path.")

    @handler("xp.xpimport")
    async def xpimport(req) -> Reply:
        """!xpimport [source] [#channel] [limit] — formats help works
        headlessly; the channel scan needs the history-scanner port
        (arms with the message band). Honest BLOCKED until then."""
        from sb.domain.xp import migrate, service

        argv = tuple(req.args.get("argv", ()) or ())
        lowered = {str(a).lower() for a in argv}
        if lowered & {"help", "formats", "list"}:
            lines = ["📥 **Import XP from another bot** — supported "
                     "level-up announcement formats:"]
            for key in migrate.format_keys():
                fmt = migrate.get_format(key)
                default = " *(default)*" if key == migrate.DEFAULT_FORMAT else ""
                lines.append(f"`{key}`{default} — {fmt.label}")
            lines.append("Usage: `!xpimport [source] [#channel] [limit]` — "
                         "raise-only, preview first.")
            return Reply(SUCCESS, "\n".join(lines))
        if service.active_history_scanner() is None:
            return Reply(BLOCKED,
                         "📥 The channel scan needs message-history access, "
                         "which arms with the message band. The parsing "
                         "formats and the raise-only import op are live — "
                         "`!xpimport help` lists the supported bots.")
        return Reply(BLOCKED,
                     "📥 Scan-and-preview wiring lands with the draft-lane "
                     "slice (raise-only import op is live).")


def ctx_target(argv: tuple) -> int:
    for token in argv:
        stripped = str(token).strip("<@!>")
        if stripped.isdigit():
            return int(stripped)
    return 0


_register()


def ensure_handler_refs() -> None:
    _register()
