"""UTILITY subsystem manifest (band 6) — the shipped info-tool surface
(disbot/cogs/utility_cog.py): the 🔧 Utility Panel (``!utilitymenu`` /
``/utility``), the ``!ping`` round-trip probe, ``!avatar``,
``!serverinfo`` (the shipped `!info server` alias surface) and the
``!/myprofile`` hero-card send. The sibling shipped commands (!info,
!userinfo, !remind, !clear/!purge) join when their entry points port —
the subsystem's seven goldens drive these entry points only.

No stores, no events, no settings: the whole surface is reads over the
guild-directory port (sb/domain/utility/service.py).
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
    ),
    panels=(
        _panels.utility_panel_spec(),
        _panels.pong_spec(),
        _panels.avatar_card_spec(),
        _panels.server_info_spec(),
        _panels.user_info_spec(),
        _panels.profile_card_spec(),
    ),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
