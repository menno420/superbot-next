"""Utility entry-point handlers — thin HandlerRef routes over the read
ports (disbot/cogs/utility_cog.py's shipped commands and panel actions).
All read-only: no ops, no writes, no compensator surface.
"""

from __future__ import annotations

import dataclasses
import re
import time

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED

__all__ = ["Reply", "ensure_handler_refs"]

_MENTION_RE = re.compile(r"^<@!?(\d{15,20})>$|^(\d{15,20})$")

#: the shipped date rendering (utility_cog: strftime("%Y-%m-%d") on
#: guild.created_at / member.created_at / member.joined_at).
_DATE = "%Y-%m-%d"

_DIRECTORY_DOWN = ("ℹ️ Server/member info needs the live guild view "
                   "(arms with the live adapter).")


def _target_user_id(req) -> int | None:
    """The shipped optional-member argument: first token mention/id, else
    the invoker."""
    argv = tuple(req.args.get("argv", ()) or ())
    if argv:
        m = _MENTION_RE.match(str(argv[0]))
        if m:
            return int(m.group(1) or m.group(2))
    return None


async def _open_with(req, panel_id: str, params: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef(panel_id),
                     dataclasses.replace(req, args={**dict(req.args), **params}))


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("utility.menu_view")):
        return

    @handler("utility.menu_view")
    async def menu_view(req):
        """!utilitymenu / /utility — the shipped Utility Panel
        (_UtilityPanelView; goldens/utility/sweep_utilitymenu +
        sweep_slash_utility)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef("utility.panel"), req)
        return None

    @handler("utility.ping_view")
    async def ping_view(req):
        """!ping — the shipped send-then-edit round-trip probe
        (utility_cog.ping: bare Pong embed, perf_counter RTT around the
        send, then the Gateway/Round-trip field edit;
        goldens/utility/sweep_ping)."""
        from sb.domain.utility.service import gateway_latency_ms
        from sb.kernel.panels.engine import open_panel, refresh_session_view
        from sb.spec.refs import PanelRef

        before = time.perf_counter()
        key = await open_panel(PanelRef("utility.pong"), req)
        rtt_ms = (time.perf_counter() - before) * 1000
        await refresh_session_view(
            req, message_key=key,
            params={"gateway_ms": gateway_latency_ms(), "rtt_ms": rtt_ms},
            expire=True)
        return None

    @handler("utility.avatar_view")
    async def avatar_view(req):
        """!avatar [member] — the shipped avatar embed
        (goldens/utility/sweep_avatar)."""
        from sb.domain.utility.service import (
            GuildDirectoryNotInstalled,
            guild_directory,
        )

        try:
            member = await guild_directory().member_info(
                int(req.guild_id or 0),
                _target_user_id(req) or int(req.actor.user_id))
        except GuildDirectoryNotInstalled:
            return Reply(BLOCKED, _DIRECTORY_DOWN)
        await _open_with(req, "utility.avatar_card",
                         {"tag": member.tag,
                          "avatar_url": member.display_avatar_url})
        return None

    @handler("utility.server_info_view")
    async def server_info_view(req):
        """!serverinfo (the shipped `!info server` embed;
        goldens/utility/sweep_serverinfo)."""
        from sb.domain.utility.service import (
            GuildDirectoryNotInstalled,
            guild_directory,
        )

        try:
            info = await guild_directory().guild_info(int(req.guild_id or 0))
        except GuildDirectoryNotInstalled:
            return Reply(BLOCKED, _DIRECTORY_DOWN)
        await _open_with(req, "utility.server_info", {
            "name": info.name,
            "owner_id": info.owner_id,
            "member_count": info.member_count,
            "premium_tier": info.premium_tier,
            "created": info.created_at.strftime(_DATE),
            "text_channels": info.text_channels,
            "voice_channels": info.voice_channels,
        })
        return None

    @handler("utility.user_info_view")
    async def user_info_view(req):
        """The panel's 👤 User Info action (the shipped `!info user`
        embed; unpinned by goldens — panel-reachable)."""
        from sb.domain.utility.service import (
            GuildDirectoryNotInstalled,
            guild_directory,
        )

        try:
            member = await guild_directory().member_info(
                int(req.guild_id or 0),
                _target_user_id(req) or int(req.actor.user_id))
        except GuildDirectoryNotInstalled:
            return Reply(BLOCKED, _DIRECTORY_DOWN)
        await _open_with(req, "utility.user_info",
                         {"tag": member.tag,
                          "created": member.created_at.strftime(_DATE),
                          "joined": member.joined_at.strftime(_DATE)})
        return None

    @handler("utility.myprofile_view")
    async def myprofile_view(req):
        """!myprofile / /myprofile — the hero-card send
        (goldens/utility/sweep_myprofile + sweep_slash_myprofile pin the
        multipart shape; pixels are the profile band's parked renderer)."""
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef("utility.profile_card"), req)
        return None


def _register_pending() -> None:
    """The shipped Poll/Remind/Invite tools and the 420 child panel need
    Discord effect ports that have not armed (reaction egress, timed
    delivery, invite mint) or bands that have not ported (four_twenty) —
    declared + honest refusal, never silent (the role-band precedent)."""
    from sb.domain.operator_spine import pending_handler

    pending_handler("utility.poll_pending",
                    "📊 Poll creation needs the reaction egress port "
                    "(arms with the live adapter).")
    pending_handler("utility.remind_pending",
                    "🔔 Reminders need the timed-delivery port "
                    "(arms with the live adapter).")
    pending_handler("utility.invite_pending",
                    "🔗 Invite creation needs the live invite port "
                    "(arms with the live adapter).")
    pending_handler("utility.four_twenty_pending",
                    "🍃 The 420 panel ports with its own band.")


_register()
_register_pending()


def ensure_handler_refs() -> None:
    _register()
    _register_pending()
