"""UTILITY subsystem manifest (band 6) — the shipped info-tool surface
(disbot/cogs/utility_cog.py): the 🔧 Utility Panel (``!utilitymenu`` /
``/utility``), the ``!ping`` round-trip probe, ``!avatar``,
``!serverinfo`` / ``!info`` / ``!userinfo``, ``!botinfo``,
``!membercount``, the ``!poll`` / ``!remind`` / ``!invite`` tools,
``!clear``/``!purge`` and the ``!/myprofile`` hero-card send — the
subsystem's fifteen goldens drive these entry points.

No stores, no events, no settings: the surface is reads over the
guild-directory / bot-identity / purge ports
(sb/domain/utility/service.py) plus the one Discord effect the shipped
``!invite`` performed — the channel-invite POST, riding the D-0077
channel-ops port (sb/domain/channel/service.py ``create_invite``).
"""

from __future__ import annotations

from sb.domain.utility import handlers as _handlers
from sb.domain.utility import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec, CooldownScope, CooldownSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import DeferMode
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="utility",
    version=1,
    commands=(
        CommandSpec(name="utilitymenu", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.menu_view"),
                    audience_tier="user", capability="utility",
                    summary="Open the interactive utility panel.",
                    usage="!utilitymenu"),
        # the shipped slash surfaces answered DIRECTLY (type-4 message, no
        # defer — goldens/utility/sweep_slash_utility, sweep_slash_myprofile).
        CommandSpec(name="utility", kind=CommandKind.SLASH,
                    route=HandlerRef("utility.menu_view"),
                    defer_mode=DeferMode.NONE,
                    audience_tier="user", capability="utility",
                    summary="Open the interactive utility panel.",
                    usage="/utility"),
        CommandSpec(name="ping", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.ping_view"),
                    audience_tier="user", capability="utility",
                    summary="Check the bot's gateway and round-trip latency.",
                    usage="!ping"),
        CommandSpec(name="avatar", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.avatar_view"),
                    audience_tier="user", capability="utility",
                    summary="Display a user's avatar.",
                    usage="!avatar [@member]"),
        CommandSpec(name="serverinfo", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.server_info_view"),
                    audience_tier="user", capability="utility",
                    summary="Show server information.",
                    usage="!serverinfo"),
        # the shipped @commands.cooldown(rate=3, per=15, BucketType.user).
        CommandSpec(name="myprofile", kind=CommandKind.BOTH,
                    route=HandlerRef("utility.myprofile_view"),
                    defer_mode=DeferMode.NONE,
                    audience_tier="user", capability="utility",
                    cooldown=CooldownSpec(rate=3, per_s=15,
                                          scope=CooldownScope.USER),
                    summary="View your per-server profile card.",
                    usage="!myprofile"),
        # --- the shipped sibling entry points (utility_cog.py), joined at
        # the wave-9 re-home: goldens/utility/sweep_botinfo, sweep_info,
        # sweep_userinfo, sweep_membercount, sweep_poll, sweep_remind,
        # sweep_invite, sweep_clear pin the bytes.
        CommandSpec(name="botinfo", kind=CommandKind.PREFIX,
                    aliases=("about",),
                    route=HandlerRef("utility.botinfo_view"),
                    audience_tier="user", capability="utility",
                    summary="Show information about the bot — servers, "
                            "uptime, latency, version.",
                    usage="!botinfo"),
        CommandSpec(name="info", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.info_view"),
                    audience_tier="user", capability="utility",
                    summary="Show server or user info.",
                    usage="!info [server|user] [@mention]"),
        CommandSpec(name="userinfo", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.userinfo_view"),
                    audience_tier="user", capability="utility",
                    summary="Show a member's profile details.",
                    usage="!userinfo [@member]"),
        CommandSpec(name="membercount", kind=CommandKind.PREFIX,
                    aliases=("members",),
                    route=HandlerRef("utility.membercount_view"),
                    audience_tier="user", capability="utility",
                    summary="Show this server's member count — humans, "
                            "bots, and total.",
                    usage="!membercount"),
        CommandSpec(name="poll", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.poll_view"),
                    audience_tier="user", capability="utility",
                    summary="Create a simple reaction poll.",
                    usage="!poll <question> <option1> <option2> [...]"),
        CommandSpec(name="remind", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.remind_view"),
                    audience_tier="user", capability="utility",
                    summary="Set a reminder.",
                    usage="!remind <minutes> <message>"),
        # the shipped @perms_or_owner(create_instant_invite=True) — no
        # tier in TIER_DISCORD_PERMISSION carries that bit (Discord
        # grants it to @everyone by default), so the floor stays "user";
        # the create leg still refuses honestly when no port is armed.
        CommandSpec(name="invite", kind=CommandKind.PREFIX,
                    route=HandlerRef("utility.invite_view"),
                    audience_tier="user", capability="utility",
                    summary="Generate a one-use server invite.",
                    usage="!invite"),
        # the shipped @perms_or_owner(manage_messages=True) — the
        # moderator tier (TIER_DISCORD_PERMISSION's closest floor, the
        # cleanup-scan precedent).
        CommandSpec(name="clear", kind=CommandKind.PREFIX,
                    aliases=("purge",),
                    route=HandlerRef("utility.clear_view"),
                    audience_tier="moderator", capability="utility",
                    summary="Purge messages. Max 100.",
                    usage="!clear [amount]"),
    ),
    panels=(
        _panels.utility_panel_spec(),
        _panels.pong_spec(),
        _panels.avatar_card_spec(),
        _panels.server_info_spec(),
        _panels.user_info_spec(),
        _panels.profile_card_spec(),
        _panels.bot_info_spec(),
        _panels.member_census_spec(),
        _panels.user_card_spec(),
        _panels.error_card_spec(),
    ),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
