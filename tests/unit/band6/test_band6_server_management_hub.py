"""The SERVER MANAGEMENT hub panel (the shipped ServerManagementHubView
as a declarative panel): the golden-pinned spec bytes, the compile
fences, the manifest surface (both front doors; the direct-answer slash
twin), the footer renderer_override, the verbatim persistent custom_ids,
and the pending manager terminals.

Oracle: menno420/superbot disbot/cogs/server_management_cog.py +
disbot/views/server_management/hub.py (build_server_management_hub) +
disbot/services/server_management_hub.py (the read-only badge composer);
parity/goldens/servermanagement/sweep_slash_server-management.json pins
the slash wire bytes (the sibling server_management row's prefix golden
pins the message surface and flips separately).
"""

from __future__ import annotations

import asyncio

run = asyncio.run


# --- the spec: golden-pinned bytes ---------------------------------------------------


def test_hub_spec_shape_matches_the_golden():
    from sb.domain.server_management.panels import server_management_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = server_management_hub_spec()
    assert spec.panel_id == "server_management.hub"
    assert spec.subsystem == "server_management"
    assert spec.title == "🧭 Server Management Hub"
    # the shipped slash twin answered EPHEMERAL (flags 64 in the golden).
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "red"           # discord.Color.red()
    assert spec.frame.footer_mode is FooterMode.NONE
    # no nav row (the golden pins exactly three component rows); the
    # never-strand fence takes the session-view exemption — every id is
    # override-pinned so nothing is run-minted.
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False

    by_id = {a.action_id: a for a in spec.actions}
    # the shipped buttons carried the emoji INSIDE the label (no separate
    # emoji field in the golden) + the PERSISTENT custom_id verbatim.
    expected = {
        "moderation": ("🛡️ Moderation", ActionStyle.PRIMARY,
                       "server_management:moderation"),
        "channels": ("📺 Channels", ActionStyle.PRIMARY,
                     "server_management:channels"),
        "roles": ("🎭 Roles", ActionStyle.PRIMARY,
                  "server_management:roles"),
        "cleanup": ("🧹 Cleanup", ActionStyle.SECONDARY,
                    "server_management:cleanup"),
        "setup": ("🧩 Setup", ActionStyle.SUCCESS,
                  "server_management:setup"),
        "access_map": ("🔓 Access Map", ActionStyle.SECONDARY,
                       "server_management:access_map"),
        "help_preview": ("👁 Help Preview", ActionStyle.SECONDARY,
                         "server_management:help_preview"),
        "help_editor": ("✏️ Help editor", ActionStyle.SECONDARY,
                        "server_management:help_editor"),
        "sm_refresh": ("🔄 Refresh", ActionStyle.SECONDARY,
                       "server_management:refresh"),
    }
    assert set(by_id) == set(expected)
    for aid, (label, style, custom_id) in expected.items():
        assert by_id[aid].label == label, aid
        assert by_id[aid].style is style, aid
        assert by_id[aid].custom_id_override == custom_id, aid
        assert not by_id[aid].emoji, aid          # emoji lives in the label
        assert by_id[aid].audience_tier == "administrator", aid

    assert spec.layout.pages[0].rows == (
        ("moderation", "channels", "roles"),
        ("cleanup", "setup"),
        ("access_map", "help_preview", "help_editor", "sm_refresh"),
    )


def test_ported_forwards_and_pending_terminals():
    from sb.domain.server_management.panels import server_management_hub_spec
    from sb.spec.refs import HandlerRef, PanelRef

    by_id = {a.action_id: a for a in server_management_hub_spec().actions}
    # the shipped hub routed into the managers: Channels → the PORTED
    # channel.hub (#131); Setup → the band-1 setup hub; Refresh → self.
    assert by_id["channels"].handler == PanelRef("channel.hub")
    assert by_id["setup"].handler == PanelRef("setup.hub")
    assert by_id["sm_refresh"].handler == PanelRef("server_management.hub")
    # unported managers land on declared pending terminals.
    for aid in ("moderation", "roles", "cleanup", "access_map",
                "help_preview", "help_editor"):
        assert by_id[aid].handler == HandlerRef(
            f"server_management.{aid}_pending"), aid


def test_hub_spec_passes_the_compile_fences():
    from sb.domain.server_management.panels import server_management_hub_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(server_management_hub_spec())


# --- the render: footer literal + the badge fields ------------------------------------


def _ctx():
    from types import SimpleNamespace

    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


def test_render_carries_the_footer_and_the_two_health_fields():
    from sb.domain.server_management.panels import (
        _render_hub,
        server_management_hub_spec,
    )

    rendered = run(_render_hub(server_management_hub_spec(), _ctx()))
    assert rendered.embed.footer == (
        "Read-only summary · click a manager to open it")
    assert rendered.embed.description.startswith(
        "Your single entry point to the server's operator tools.")
    assert rendered.embed.fields[0][0] == "Managers"
    assert rendered.embed.fields[0][1].startswith(
        "🟢 🛡️ **Moderation** — Can ban, kick and timeout members")
    assert "🟡 🧩 **Setup** — Not configured yet — run setup" in (
        rendered.embed.fields[0][1])
    assert rendered.embed.fields[1][0] == "Overall configuration health"
    assert rendered.embed.fields[1][1] == (
        "🟢 No configuration issues need attention")
    # no engine-injected nav components (the golden's exactly-three rows).
    assert all(not c.custom_id.startswith("nav:") for c in rendered.components)
    # every wire id is the shipped persistent id, never a minted one.
    assert {c.custom_id for c in rendered.components} == {
        f"server_management:{k}" for k in (
            "moderation", "channels", "roles", "cleanup", "setup",
            "access_map", "help_preview", "help_editor", "refresh")}


def test_red_style_token_is_the_shipped_color():
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    assert STYLE_TOKEN_COLORS["red"] == 15158332  # discord.Color.red()


# --- the refs + manifest --------------------------------------------------------------


def test_panel_and_handler_refs_registered():
    from sb.domain.server_management import handlers, panels
    from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, is_registered

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    assert is_registered(PanelRef("server_management.hub"))
    assert is_registered(ProviderRef("server_management.hub_health"))
    for name in ("server_management.render_hub",
                 "server_management.moderation_pending",
                 "server_management.roles_pending",
                 "server_management.cleanup_pending",
                 "server_management.access_map_pending",
                 "server_management.help_preview_pending",
                 "server_management.help_editor_pending"):
        assert is_registered(HandlerRef(name)), name


def test_manifest_declares_both_front_doors():
    from sb.manifest.server_management import MANIFEST
    from sb.spec.commands import CommandKind
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import PanelRef

    assert MANIFEST.key == "server_management"
    (prefix, slash) = MANIFEST.commands
    assert prefix.name == "servermanagement"
    assert prefix.kind is CommandKind.PREFIX
    assert prefix.aliases == ("servermenu", "guildmenu")
    assert prefix.route == PanelRef("server_management.hub")
    assert prefix.audience_tier == "administrator"
    # the shipped slash twin: direct type-4 answer, no defer (the golden
    # pins the bare type-4 with flags 64 — the utility-flip trap rule).
    assert slash.name == "server-management"
    assert slash.kind is CommandKind.SLASH
    assert slash.route == PanelRef("server_management.hub")
    assert slash.defer_mode is DeferMode.NONE
    assert slash.audience_tier == "administrator"
    (spec,) = MANIFEST.panels
    assert spec.panel_id == "server_management.hub"
    # R2 stays vacuous: no declared stores/events/settings.
    assert MANIFEST.stores == () and MANIFEST.events == ()
    assert MANIFEST.settings == ()


def test_manager_clicks_land_on_the_polite_pending_terminal():
    from types import SimpleNamespace

    from sb.domain.server_management import handlers  # noqa: F401
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    reply = run(resolve(HandlerRef("server_management.moderation_pending"))(
        SimpleNamespace(args={}, guild_id=1)))
    assert reply.outcome == BLOCKED
    assert "Moderation manager" in reply.user_message
