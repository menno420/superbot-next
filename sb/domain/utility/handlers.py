"""Utility entry-point handlers — thin HandlerRef routes over the read
ports (disbot/cogs/utility_cog.py's shipped commands and panel actions).
All read-only: no ops, no writes, no compensator surface.
"""

from __future__ import annotations

import dataclasses
import re
import time

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]

_MENTION_RE = re.compile(r"^<@!?(\d{15,20})>$|^(\d{15,20})$")

#: the shipped date rendering (utility_cog: strftime("%Y-%m-%d") on
#: guild.created_at / member.created_at / member.joined_at).
_DATE = "%Y-%m-%d"

_DIRECTORY_DOWN = ("ℹ️ Server/member info needs the live guild view "
                   "(arms with the live adapter).")

#: bot1.py's global on_command_error fallback, verbatim — the capture
#: world's answer whenever a command body raised (the fake_http canned
#: create_invite response was unparseable to discord.py, so every
#: captured `!invite` died here — goldens/utility/sweep_invite pins the
#: byte). Converter-failure lanes (bad `!remind`/`!clear`/`!info` args)
#: degrade through the same copy (unpinned, the starboard posture) —
#: NEVER the new kernel's own error-envelope copy.
_GENERIC_ERROR = "⚠️ An unexpected error occurred. Please try again."

#: the shipped unarmed-effect refusals (the role-band honest-refusal
#: precedent) — ONE copy per tool, shared by the panel button's pending
#: handler and the prefix command's success lane.
_POLL_DOWN = ("📊 Poll creation needs the reaction egress port "
              "(arms with the live adapter).")
_INVITE_DOWN = ("🔗 Invite creation needs the live invite port "
                "(arms with the live adapter).")
_CLEAR_DOWN = ("🧹 Purging needs the live message view "
               "(arms with the live adapter).")


def _format_uptime(total_s: int) -> str:
    """The shipped utility_cog ``_format_uptime`` verbatim: ``Dd Hh Mm``
    with days/hours only when non-zero, minutes always
    (goldens/utility/sweep_botinfo pins the capture bot's "0m")."""
    days, rem = divmod(int(total_s), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


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

    async def _open_server_card(req):
        """The shipped `!info server` embed — shared by !serverinfo and
        the bare !info (goldens/utility/sweep_serverinfo + sweep_info
        pin byte-identical embeds)."""
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

    @handler("utility.server_info_view")
    async def server_info_view(req):
        """!serverinfo (the shipped `!info server` embed;
        goldens/utility/sweep_serverinfo)."""
        return await _open_server_card(req)

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

    # --- the shipped sibling entry points (utility_cog.py command bodies;
    # goldens/utility/sweep_botinfo, sweep_info, sweep_userinfo,
    # sweep_membercount, sweep_poll, sweep_remind, sweep_invite,
    # sweep_clear pin the bytes). All composed at the handler from the
    # read ports; the param cards only assemble. ---------------------------

    async def _requester_tag(req) -> str:
        """The shipped footer's ``str(ctx.author)`` — through the guild
        directory (the trap-14h no-origin-message lane)."""
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(
            int(req.guild_id or 0), int(req.actor.user_id))
        return member.tag

    async def _open_error_card(req, message: str) -> Reply:
        """The shipped ``ctx.send(embed=em.error(...))`` red envelope —
        rides utility.error_card (the karma.error_card lane); the honest
        refusal outcome carries no extra text reply."""
        await _open_with(req, "utility.error_card", {"error_text": message})
        return Reply(BLOCKED, None)

    @handler("utility.botinfo_view")
    async def botinfo_view(req):
        """!botinfo (alias !about) — the shipped bot census embed
        (utility_cog.botinfo; goldens/utility/sweep_botinfo). The
        Commands/Users/Uptime values are the bot-identity port's census
        (the parity root arms the CAPTURE environment's own values —
        sb/adapters/parity/boot.py)."""
        from sb.domain.utility.service import (
            BotIdentityNotInstalled,
            GuildDirectoryNotInstalled,
            bot_identity,
            gateway_latency_ms,
        )

        try:
            ident = bot_identity()
            requester = await _requester_tag(req)
        except (BotIdentityNotInstalled, GuildDirectoryNotInstalled):
            return Reply(BLOCKED, _DIRECTORY_DOWN)
        fields = [
            ("Servers", str(ident.guild_count), True),
            ("Users", str(ident.user_count), True),
            ("Commands", str(ident.command_count), True),
            # the shipped f"{bot.latency * 1000:.0f} ms" — the capture
            # world's no-heartbeat latency renders "nan ms".
            ("Gateway", f"{gateway_latency_ms():.0f} ms", True),
        ]
        if ident.uptime_s is not None:
            fields.append(("Uptime", _format_uptime(ident.uptime_s), True))
        fields.append(("Library", ident.library, True))
        await _open_with(req, "utility.bot_info", {
            "card_title": f"🤖 {ident.name}",
            "card_description": "Bot information and statistics",
            "card_fields": tuple(fields),
            "card_footer": f"Requested by {requester}",
            "card_thumbnail": ident.avatar_url,
        })
        return None

    @handler("utility.membercount_view")
    async def membercount_view(req):
        """!membercount (alias !members) — the shipped census embed
        (utility_cog.membercount: total = guild.member_count, bots = the
        per-member bot flags, humans = the difference;
        goldens/utility/sweep_membercount)."""
        from sb.domain.utility.service import (
            GuildDirectoryNotInstalled,
            guild_directory,
        )

        try:
            info = await guild_directory().guild_info(int(req.guild_id or 0))
            requester = await _requester_tag(req)
        except GuildDirectoryNotInstalled:
            return Reply(BLOCKED, _DIRECTORY_DOWN)
        await _open_with(req, "utility.member_census", {
            "card_title": f"👥 {info.name} — Members",
            "card_fields": (
                ("Total", str(info.member_count), True),
                ("Humans", str(info.member_count - info.bots), True),
                ("Bots", str(info.bots), True),
            ),
            "card_footer": f"Requested by {requester}",
        })
        return None

    async def _open_user_card(req, user_id: int):
        """The shipped `!info user` / `!userinfo` six-field member card
        (utility_cog.info user branch, SUCCESS_COLOR;
        goldens/utility/sweep_userinfo pins field order + bytes)."""
        from sb.domain.utility.service import (
            GuildDirectoryNotInstalled,
            guild_directory,
        )

        try:
            member = await guild_directory().member_info(
                int(req.guild_id or 0), int(user_id))
            requester = await _requester_tag(req)
        except GuildDirectoryNotInstalled:
            return Reply(BLOCKED, _DIRECTORY_DOWN)
        await _open_with(req, "utility.user_card", {
            "card_title": f"User Info — {member.tag}",
            "card_fields": (
                # the shipped member.name — the tag minus the
                # discriminator (world payloads carry "#0000").
                ("Username", member.tag.rsplit("#", 1)[0], True),
                ("User ID", str(member.user_id), True),
                ("Joined Server", member.joined_at.strftime(_DATE), True),
                ("Joined Discord", member.created_at.strftime(_DATE), True),
                # the shipped str(member.status).capitalize() /
                # member.activity.name-or-"None" presence reads.
                ("Status", str(member.status).capitalize(), True),
                ("Activity", member.activity_name or "None", True),
            ),
            "card_footer": f"Requested by {requester}",
            "card_thumbnail": member.display_avatar_url,
        })
        return None

    @handler("utility.userinfo_view")
    async def userinfo_view(req):
        """!userinfo [@member] — the shipped alias for `!info user`
        (goldens/utility/sweep_userinfo)."""
        return await _open_user_card(
            req, _target_user_id(req) or int(req.actor.user_id))

    @handler("utility.info_view")
    async def info_view(req):
        """!info [server|user] [@member] — the shipped two-branch info
        command (utility_cog.info: `target: str = "server"` then
        `if target.lower() in ("user", "u") or member:`; bare `!info`
        renders the SAME server embed as !serverinfo —
        goldens/utility/sweep_info pins the bytes byte-identical to
        sweep_serverinfo)."""
        argv = tuple(req.args.get("argv", ()) or ())
        target = str(argv[0]).lower() if argv else "server"
        member_id = None
        if len(argv) > 1:
            m = _MENTION_RE.match(str(argv[1]))
            if m:
                member_id = int(m.group(1) or m.group(2))
            else:
                # the shipped discord.Member converter raise on a
                # non-member second token — bot1.py's generic envelope.
                return Reply(BLOCKED, _GENERIC_ERROR)
        if target in ("user", "u") or member_id:
            return await _open_user_card(
                req, member_id or int(req.actor.user_id))
        return await _open_server_card(req)

    @handler("utility.poll_view")
    async def poll_view(req):
        """!poll <question> <options...> — the shipped argument guards
        (utility_cog.poll; goldens/utility/sweep_poll pins the
        two-options red envelope for `!poll test test`). The success
        lane (poll embed + numbered reactions) needs the reaction
        egress port — the panel button's honest-refusal posture, never
        a silent stub."""
        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            # the shipped MissingRequiredArgument raise (question).
            return Reply(BLOCKED, _GENERIC_ERROR)
        options = argv[1:]
        if len(options) < 2:
            return await _open_error_card(
                req, "You need at least two options for a poll.")
        if len(options) > 10:
            return await _open_error_card(
                req, "You can only provide up to 10 options.")
        return Reply(BLOCKED, _POLL_DOWN)

    @handler("utility.remind_view")
    async def remind_view(req):
        """!remind <minutes> <message> — the shipped ack
        (utility_cog.remind; goldens/utility/sweep_remind pins the byte).
        The shipped flow then armed a `tasks.spawn` timer that sent the
        reminder after `time` minutes — the timed-delivery port is a
        named successor (the golden's capture window closed before any
        delivery; only the ack is pinned)."""
        argv = tuple(req.args.get("argv", ()) or ())
        try:
            minutes = int(str(argv[0]))
        except (IndexError, ValueError):
            # the shipped int-converter/MissingRequiredArgument raise.
            return Reply(BLOCKED, _GENERIC_ERROR)
        if minutes <= 0:
            return await _open_error_card(
                req, "Please specify a time greater than 0 minutes.")
        message = " ".join(str(a) for a in argv[1:])
        if not message:
            # the shipped keyword-only `*, message: str` raise.
            return Reply(BLOCKED, _GENERIC_ERROR)
        return Reply(
            SUCCESS,
            f"⏳ Reminder set for **{minutes}** minute(s): {message}")

    @handler("utility.poll_form_submit")
    async def poll_form_submit(req):
        """The 📊 Poll button's `_PollModal` submit (utility_cog.py) —
        the shipped validation copy verbatim (one option per LINE, the
        modal's own guards — distinct from the `!poll` argv copy). The
        success lane (poll embed + numbered reactions) still needs the
        reaction egress port — the command twin's honest refusal, never
        a silent stub."""
        opts = [o.strip()
                for o in str(req.args.get("options", "") or "").split("\n")
                if o.strip()]
        if len(opts) < 2:
            return Reply(BLOCKED, "❌ Need at least 2 options.")
        if len(opts) > 10:
            return Reply(BLOCKED, "❌ Max 10 options.")
        return Reply(BLOCKED, _POLL_DOWN)

    @handler("utility.remind_form_submit")
    async def remind_form_submit(req):
        """The 🔔 Remind Me button's `_RemindModal` submit
        (utility_cog.py) — the shipped validation + ack copy verbatim.
        Same lane as the live `!remind` twin: the ack is real, the
        delivery itself rides the timed-delivery port (the twin's
        documented named successor — the golden capture window closed
        before any delivery, so only the ack is pinned)."""
        try:
            minutes = int(str(req.args.get("minutes", "")).strip())
            if minutes <= 0:
                raise ValueError
        except ValueError:
            return Reply(BLOCKED, "❌ Minutes must be a positive integer.")
        message = str(req.args.get("message", "") or "").strip()
        if not message:
            # required field — an empty submit only reaches here through
            # a non-Discord surface; the shipped generic net answers.
            return Reply(BLOCKED, _GENERIC_ERROR)
        return Reply(
            SUCCESS,
            f"⏳ Reminder set for **{minutes}** minute(s): {message}")

    @handler("utility.invite_view")
    async def invite_view(req):
        """!invite — the shipped one-use channel invite
        (utility_cog.invite: `ctx.channel.create_invite(max_uses=1,
        unique=True)` then the link reply) through the D-0077
        channel-ops port. In the capture world the create POST was
        answered with a canned payload discord.py could not parse, so
        every captured `!invite` recorded the wire call then died in
        bot1.py's generic handler — goldens/utility/sweep_invite pins
        exactly that pair; ANY raise from the create leg (including a
        not-armed live port) degrades through the same shipped copy."""
        from sb.domain.channel.service import active_actions

        actions = active_actions()
        try:
            url = await actions.create_invite(
                int(req.channel_id or 0), max_age=0, max_uses=1,
                temporary=False, unique=True, reason=None)
        except Exception:  # noqa: BLE001 — the shipped on_command_error net
            return Reply(BLOCKED, _GENERIC_ERROR)
        return Reply(
            SUCCESS, f"Here is your invite link (valid for 1 use): {url}")

    @handler("utility.clear_view")
    async def clear_view(req):
        """!clear [amount] (alias !purge) — the shipped bounded purge
        (utility_cog.clear: guards, `ctx.channel.purge(limit=amount)`,
        the count reply; goldens/utility/sweep_clear pins the logs_from
        read + 'Cleared 0 messages.' over the capture world's empty
        backlog). The shipped confirmation self-delete
        (`msg.delete(delay=5)`) and the invoker delete are the ruled
        invoking-message-deletion class — no port."""
        from sb.domain.utility.service import (
            MessagePurgerNotInstalled,
            message_purger,
        )

        argv = tuple(req.args.get("argv", ()) or ())
        try:
            amount = int(str(argv[0])) if argv else 5
        except ValueError:
            # the shipped int-converter raise.
            return Reply(BLOCKED, _GENERIC_ERROR)
        if amount <= 0:
            return await _open_error_card(
                req, "Please specify a number greater than 0.")
        if amount > 100:
            return await _open_error_card(
                req, "You can only clear up to 100 messages at a time.")
        try:
            purger = message_purger()
        except MessagePurgerNotInstalled:
            return Reply(BLOCKED, _CLEAR_DOWN)
        deleted = await purger(int(req.channel_id or 0), limit=amount)
        return Reply(SUCCESS, f"Cleared {len(deleted)} messages.")


def _register_pending() -> None:
    """The shipped Invite tool still needs its mint port (a sibling
    lane's — PR #332 wires the button to the live `utility.invite_view`)
    — declared + honest refusal, never silent (the role-band precedent).
    The Poll/Remind terminals are retired (G-10 modal ingress over the
    live twin lanes) and the 420 child forwards to the ported
    `four_twenty.overview` (2026-07-13 operator-hub edits A)."""
    from sb.domain.operator_spine import pending_handler

    pending_handler("utility.invite_pending", _INVITE_DOWN)


_register()
_register_pending()


def ensure_handler_refs() -> None:
    _register()
    _register_pending()
