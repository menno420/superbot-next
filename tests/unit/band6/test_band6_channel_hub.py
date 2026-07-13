"""The CHANNEL management hub panel (the shipped _ChannelManagerView as a
session-lifecycle panel): the golden-pinned spec bytes, the compile fences,
the manifest surface, the footer renderer_override, the shipped nav row
(nav:help + nav:hub:admin with the hub's display label), and the pending
action terminals.

Oracle: menno420/superbot disbot/cogs/channel_cog.py (channel_menu,
@is_admin_or_owner) + disbot/views/channels/main_panel.py
(_ChannelManagerView.build_embed); parity/goldens/channel/
sweep_channelmenu.json pins the wire bytes.
"""

from __future__ import annotations

import asyncio

run = asyncio.run


# --- the spec: golden-pinned bytes ---------------------------------------------------


def test_hub_spec_shape_matches_the_golden():
    from sb.domain.channel.panels import channel_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = channel_hub_spec()
    assert spec.panel_id == "channel.hub"
    assert spec.subsystem == "channel"
    assert spec.title == "🛠️ Channel Management Panel"
    # the shipped view was author-locked to ctx.author (HubView).
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "blurple"       # CHANNEL_COLOR
    assert spec.frame.footer_mode is FooterMode.NONE
    # the shipped session view: run-minted ids, no anchor row — WITH the
    # standard nav row (the golden pins nav:help + nav:hub:admin next to
    # five <cid:N> buttons).
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is True
    assert spec.navigation.show_home is True
    assert spec.navigation.home_hub == "admin"

    by_id = {a.action_id: a for a in spec.actions}
    # the shipped buttons carried a SEPARATE emoji field (the golden pins
    # an "emoji" key on every action button).
    assert by_id["create"].label == "Create Channel"
    assert by_id["create"].emoji == "➕"
    assert by_id["create"].style is ActionStyle.SUCCESS       # wire style 3
    assert by_id["delete"].label == "Delete Channel"
    assert by_id["delete"].emoji == "🗑️"
    assert by_id["delete"].style is ActionStyle.DANGER        # wire style 4
    assert by_id["restrict"].label == "Manage Restrictions"
    assert by_id["restrict"].emoji == "🔒"
    assert by_id["restrict"].style is ActionStyle.PRIMARY     # wire style 1
    assert by_id["move"].label == "Move / Reorder"
    assert by_id["move"].emoji == "↔️"
    assert by_id["move"].style is ActionStyle.PRIMARY
    assert by_id["visibility"].label == "Subsystem Visibility"
    assert by_id["visibility"].emoji == "🔍"
    assert by_id["visibility"].style is ActionStyle.SECONDARY  # wire style 2

    assert spec.layout.pages[0].rows == (
        ("create", "delete", "restrict"),
        ("move", "visibility"),
    )


def test_hub_spec_passes_the_compile_fences():
    from sb.domain.channel.panels import channel_hub_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(channel_hub_spec())  # raises PanelCompileError on drift


# --- the render: footer literal + the shipped nav row --------------------------------


def _ctx():
    from types import SimpleNamespace

    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


def test_render_carries_the_author_lock_footer_and_the_admin_nav_row():
    from sb.domain.channel.panels import _render_hub, channel_hub_spec

    rendered = run(_render_hub(channel_hub_spec(), _ctx()))
    # the shipped footer literal (main_panel.build_embed set_footer).
    assert rendered.embed.footer == (
        "Only the command author can interact with this panel.")
    # the shipped four-line legend, verbatim (the fifth button was never
    # in the shipped description).
    assert rendered.embed.description.startswith(
        "Select an action below to manage your server's channels.")
    assert "**➕ Create Channel** — interactive channel creator" in (
        rendered.embed.description)
    assert "Subsystem Visibility" not in rendered.embed.description
    # the shipped standard nav row, labeled with the HUB'S display name.
    nav = {c.custom_id: c for c in rendered.components if c.row == 4}
    assert nav["nav:help"].label == "📚 Help"
    assert nav["nav:hub:admin"].label == "↩ Administration"
    # INVOKER audience — the shipped ctx.author lock.
    assert rendered.invoker_lock == 42


# --- the refs + manifest --------------------------------------------------------------


def test_panel_and_handler_refs_registered():
    from sb.domain.channel import handlers, panels
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    assert is_registered(PanelRef("channel.hub"))
    # the sub-panel flows are LIVE (operator-hub edits B): the pending
    # terminals are retired; the sub-panels + commit handlers register.
    for pid in ("channel.create", "channel.delete", "channel.restrict",
                "channel.move", "channel.visibility",
                "channel.visibility_grid"):
        assert is_registered(PanelRef(pid)), pid
    for name in ("channel.render_hub", "channel.create_commit",
                 "channel.delete_commit", "channel.restrict_lock",
                 "channel.restrict_unlock", "channel.move_commit",
                 "channel.visibility_configure"):
        assert is_registered(HandlerRef(name)), name


def test_manifest_declares_the_menu_and_keeps_the_op_roster():
    from sb.manifest.channel import MANIFEST
    from sb.spec.commands import CommandKind
    from sb.spec.refs import PanelRef

    assert MANIFEST.key == "channel"
    by_name = {c.name: c for c in MANIFEST.commands}
    menu = by_name["channelmenu"]
    assert menu.kind is CommandKind.PREFIX
    assert menu.route == PanelRef("channel.hub")
    # the shipped @is_admin_or_owner() gate — administrator tier.
    assert menu.audience_tier == "administrator"
    # the band-2 declared op roster stays intact (names verbatim).
    assert {"channelmenu", "set", "evt", "create", "bulkdelete", "del",
            "list", "clone", "move", "lock", "unlock", "channelinfo",
            "rename", "slowmode", "topic", "permissions",
            "bulkcreate"} <= set(by_name)
    assert by_name["slowmode"].aliases == ("slow",)
    # the hub + the two D-0030 read-only info cards + the five shipped
    # sub-panels and the visibility toggle grid (operator-hub edits B).
    assert [p.panel_id for p in MANIFEST.panels] == [
        "channel.hub", "channel.info_card", "channel.list_card",
        "channel.create", "channel.delete", "channel.restrict",
        "channel.move", "channel.visibility", "channel.visibility_grid"]
    spec = MANIFEST.panels[0]
    assert spec.panel_id == "channel.hub"
    # the strays re-home declared the shipped lifecycle event (goldens/
    # channel/sweep_slowmode + sweep_lock + sweep_unlock cover it);
    # stores/settings stay undeclared.
    assert MANIFEST.stores == ()
    assert [e.name for e in MANIFEST.events] == ["channel.lifecycle_changed"]
    assert MANIFEST.settings == ()


def test_action_clicks_open_the_live_subpanels():
    """The D-0030 named successor landed (operator-hub edits B): every
    hub click opens its sub-panel — no pending terminal remains."""
    from sb.domain.channel import handlers  # noqa: F401 — registers refs
    from sb.domain.channel.panels import channel_hub_spec
    from sb.spec.refs import PanelRef

    actions = {a.action_id: a for a in channel_hub_spec().actions}
    for aid in ("create", "delete", "restrict", "move", "visibility"):
        assert actions[aid].handler == PanelRef(f"channel.{aid}"), aid
