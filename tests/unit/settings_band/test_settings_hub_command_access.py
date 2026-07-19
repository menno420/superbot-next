"""The armed settings-hub Command Access panel (settings-admin slice 3 —
the set's ONE write surface): the 🚪 Command access hub button routes to
the declared ``settings.command_access`` PanelRef open-child sub-panel —
oracle disbot/views/settings/edit_command_access.py (PR-6: the three
mode buttons, the multi-ChannelSelect allowlist replace, Back-to-Hub;
copy verbatim) whose writes REUSE the live platform command-access K7
lanes (``platform.set_access_mode`` / ``set_access_channels`` —
sb/domain/platform/command_access.py, the setup-wizard step-8 seam).
The frozen ``settings_hub.command_access`` custom_id never moves (only
the server-side route did); the panel's own controls are run-minted.
The oracle's ``delete_blocked_commands`` toggle has no store column
here — the ledgered under-port (no dead control renders)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, CHAN = 1, 200


@pytest.fixture(autouse=True)
def _armed_refs():
    """Re-arm the settings refs (suite-order registry resets)."""
    from sb.domain.settings import handlers, panels

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    yield


def _ctx(params=None, guild_id=GID):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id, actor=SimpleNamespace(user_id=42),
        channel_id=CHAN, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


def _req(guild_id=GID, args=None):
    """A click request shaped like the handlers read it (args +
    ctx_from_request's actor/guild/request_id/confirmed + the
    message-key origin the refresh path walks)."""
    return SimpleNamespace(
        args=dict(args or {}), guild_id=guild_id, channel_id=CHAN,
        actor=SimpleNamespace(user_id=42), request_id="req-1",
        confirmed=False,
        origin=SimpleNamespace(message=SimpleNamespace(id="777")))


def _fields():
    from sb.spec.refs import ProviderRef, resolve

    return resolve(ProviderRef("settings.command_access_fields"))


def _handler(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _snapshot(mode=None, channels=()):
    from sb.kernel.authority.channel_access import CommandAccessSnapshot

    return CommandAccessSnapshot(mode=mode,
                                 allowed_channels=frozenset(channels))


def _install_snapshot(monkeypatch, snapshot):
    """Stub the cached policy read (the K8 reader body)."""
    from sb.domain.platform import command_access

    calls: list[int] = []

    async def fake_read(guild_id):
        calls.append(guild_id)
        return snapshot

    monkeypatch.setattr(command_access, "read_policy_snapshot", fake_read)
    return calls


def _install_mode_write(monkeypatch, outcome=None, user_message=""):
    """Stub the platform.set_access_mode K7 lane; records (ctx, mode)."""
    from sb.domain.platform import command_access
    from sb.spec.outcomes import SUCCESS

    calls: list[tuple] = []

    async def fake_mode(ctx, *, mode):
        calls.append((ctx, mode))
        return SimpleNamespace(outcome=outcome or SUCCESS,
                               user_message=user_message)

    monkeypatch.setattr(command_access, "set_access_mode", fake_mode)
    return calls


def _install_channels_write(monkeypatch, outcome=None, user_message=""):
    """Stub the platform.set_access_channels K7 lane; records the call."""
    from sb.domain.platform import command_access
    from sb.spec.outcomes import SUCCESS

    calls: list[tuple] = []

    async def fake_channels(ctx, *, channel_ids, allow_empty=False):
        calls.append((ctx, tuple(channel_ids), allow_empty))
        return SimpleNamespace(outcome=outcome or SUCCESS,
                               user_message=user_message)

    monkeypatch.setattr(command_access, "set_access_channels",
                        fake_channels)
    return calls


# --- the spec + hub route ---------------------------------------------------------


def test_command_access_spec_shape_is_the_shipped_view():
    from sb.domain.settings.panels import settings_command_access_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.panels import ActionStyle, Audience, FooterMode, SelectorKind
    from sb.spec.refs import HandlerRef, PanelRef, ProviderRef

    spec = settings_command_access_spec()
    check_panel(spec)
    assert spec.panel_id == "settings.command_access"
    assert spec.title == "🚪 Command Access"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "blurple"    # discord.Color.blurple()
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True
    assert spec.navigation.parent == PanelRef("settings.hub")
    assert spec.renderer_override == HandlerRef(
        "settings.render_command_access")
    assert spec.body[1].provider == ProviderRef(
        "settings.command_access_fields")

    # the shipped mode-button trio (label/emoji/style verbatim), all on
    # the ONE mode handler (session_action discriminates) + admin-gated.
    by_id = {a.action_id: a for a in spec.actions}
    expected = {
        "ca_all_channels": ("All channels", "🌐", ActionStyle.SUCCESS),
        "ca_selected_channels": ("Selected channels", "📋",
                                 ActionStyle.PRIMARY),
        "ca_disabled": ("Disabled except bootstrap", "🚫",
                        ActionStyle.DANGER),
    }
    for aid, (label, emoji, style) in expected.items():
        assert by_id[aid].label == label, aid
        assert by_id[aid].emoji == emoji, aid
        assert by_id[aid].style is style, aid
        assert by_id[aid].handler == HandlerRef("settings.ca_mode"), aid
        assert by_id[aid].audience_tier == "administrator", aid
        # run-minted (no new compat pin) — the shipped
        # settings_command_access.* ids are not in the freeze.
        assert by_id[aid].custom_id_override == "", aid

    # the shipped multi-ChannelSelect: blank selection = clear (min 0).
    (select,) = spec.selectors
    assert select.selector_id == "ca_channels"
    assert select.kind is SelectorKind.CHANNEL
    assert select.min_values == 0
    assert select.max_values == 25
    assert select.on_select == HandlerRef("settings.ca_channels")
    assert select.audience_tier == "administrator"
    assert select.custom_id_override == ""
    assert select.placeholder == ("Set allowed channels "
                                  "(selected_channels mode)…")

    # Back-to-Hub — the PanelRef open-child terminal (slice-1 shape).
    back = by_id["command_access_back"]
    assert back.handler == PanelRef("settings.hub")
    assert back.label == "Back to Hub"
    assert back.emoji == "↩"
    assert back.custom_id_override == ""

    # the shipped rows: modes / select / back (the delete-blocked
    # toggle's row is the ledgered under-port).
    assert spec.layout.pages[0].rows == (
        ("ca_all_channels", "ca_selected_channels", "ca_disabled"),
        ("ca_channels",),
        ("command_access_back",),
    )


def test_hub_command_access_button_routes_on_the_frozen_wire_id():
    from sb.domain.settings.panels import settings_hub_spec
    from sb.spec.refs import PanelRef

    by_id = {a.action_id: a for a in settings_hub_spec().actions}
    assert by_id["command_access"].handler == PanelRef(
        "settings.command_access")
    assert (by_id["command_access"].custom_id_override
            == "settings_hub.command_access")
    assert by_id["command_access"].label == "Command access"
    assert by_id["command_access"].emoji == "🚪"


# --- the fields provider: the shipped embed body over the live read ---------------


def test_fields_no_guild_is_the_shipped_placeholder(monkeypatch):
    calls = _install_snapshot(monkeypatch, _snapshot())
    fields = run(_fields()(_ctx(guild_id=0)))
    assert fields == (("Current mode", "*Guild context not available.*"),)
    assert calls == []                  # the guard returns before the read


def test_fields_default_no_policy_row(monkeypatch):
    calls = _install_snapshot(monkeypatch, _snapshot())
    fields = run(_fields()(_ctx()))
    assert fields == (
        ("Current mode",
         "**All channels (default — no policy row)**\n"
         "Normal prefix + slash commands work in every guild channel "
         "(subject to per-command permissions and governance)."),
        ("Allowed channels (0)", "*(none configured)*"),
    )
    assert calls == [GID]


def test_fields_selected_channels_renders_the_sorted_mentions(monkeypatch):
    _install_snapshot(monkeypatch,
                      _snapshot("selected_channels", (30, 10, 20)))
    fields = run(_fields()(_ctx()))
    assert fields[0] == (
        "Current mode",
        "**Selected channels**\n"
        "Normal commands only work in the channels you list below. "
        "Bootstrap commands (`/setup`, `/help`, `/settings`, etc.) "
        "still work everywhere for guild operators.")
    assert fields[1] == ("Allowed channels (3)", "<#10> <#20> <#30>")
    assert len(fields) == 2             # no Recovery field outside disabled


def test_fields_disabled_mode_carries_the_recovery_field(monkeypatch):
    _install_snapshot(monkeypatch, _snapshot("disabled_except_bootstrap"))
    fields = run(_fields()(_ctx()))
    assert fields[0] == (
        "Current mode",
        "**Disabled except bootstrap**\n"
        "Normal commands are denied. Only bootstrap commands "
        "remain reachable so an operator can re-enable from "
        "`!setup` or this panel.")
    assert fields[2] == (
        "Recovery",
        "Normal commands are currently denied.  Pick **All "
        "channels** or **Selected channels** above to re-enable, "
        "or run `!setup` to revisit onboarding.")


def test_channel_list_truncates_at_the_shipped_cap():
    from sb.domain.settings.panels import _format_channel_list

    ids = frozenset(range(100000000000000000, 100000000000000050))
    rendered = _format_channel_list(ids)
    assert rendered.endswith("… (+20 more)")
    assert rendered.count("<#") == 30   # the shipped 30-head truncation


# --- the renderer override: the shipped footer literal ----------------------------


def test_render_carries_the_shipped_footer(monkeypatch):
    from sb.domain.settings.panels import (
        _render_command_access,
        settings_command_access_spec,
    )

    _install_snapshot(monkeypatch, _snapshot())
    rendered = run(_render_command_access(settings_command_access_spec(),
                                          _ctx()))
    assert rendered.embed.footer == (
        "Applies to prefix + slash commands.  "
        "Mode buttons + the channel selector are admin-only.")
    assert rendered.embed.description.startswith(
        "Configure where prefix and slash commands are allowed in "
        "this server.")


# --- the mode writes: the platform.set_access_mode K7 lane ------------------------


@pytest.mark.parametrize("action,mode,label", [
    ("ca_all_channels", "all_channels", "All channels"),
    ("ca_selected_channels", "selected_channels", "Selected channels"),
    ("ca_disabled", "disabled_except_bootstrap",
     "Disabled except bootstrap"),
])
def test_each_mode_button_writes_through_the_live_lane(
        monkeypatch, action, mode, label):
    from sb.spec.outcomes import SUCCESS

    calls = _install_mode_write(monkeypatch)
    reply = run(_handler("settings.ca_mode")(
        _req(args={"session_action": action})))
    (ctx, written_mode), = calls
    assert written_mode == mode
    assert ctx.guild_id == GID          # ctx_from_request threads the click
    assert ctx.actor.user_id == 42
    assert reply.outcome == SUCCESS
    # shipped confirmation copy, verbatim.
    assert reply.user_message == (
        f"✅ Command access mode set to **{label}**.")


def test_mode_write_failure_answers_honestly(monkeypatch):
    _install_mode_write(monkeypatch, outcome="error",
                        user_message="write failed downstream")
    reply = run(_handler("settings.ca_mode")(
        _req(args={"session_action": "ca_all_channels"})))
    assert reply.outcome == "error"
    assert "Couldn't set the command access mode" in reply.user_message
    assert "write failed downstream" in reply.user_message


def test_unknown_mode_click_is_blocked_before_the_seam(monkeypatch):
    from sb.spec.outcomes import BLOCKED

    calls = _install_mode_write(monkeypatch)
    reply = run(_handler("settings.ca_mode")(
        _req(args={"session_action": "ca_bogus"})))
    assert reply.outcome == BLOCKED
    assert calls == []


# --- the channel replace: the platform.set_access_channels K7 lane ----------------


def test_channel_select_replaces_the_allowlist(monkeypatch):
    from sb.spec.outcomes import SUCCESS

    calls = _install_channels_write(monkeypatch)
    reply = run(_handler("settings.ca_channels")(
        _req(args={"values": ("10", "20")})))
    (ctx, channel_ids, allow_empty), = calls
    assert channel_ids == (10, 20)
    assert allow_empty is True          # the atomic-replace contract
    assert ctx.guild_id == GID
    assert reply.outcome == SUCCESS
    # shipped confirmation copy, verbatim (plural branch).
    assert reply.user_message == "✅ Allowed channels updated (2 channels)."


def test_channel_select_single_channel_uses_the_singular(monkeypatch):
    _install_channels_write(monkeypatch)
    reply = run(_handler("settings.ca_channels")(
        _req(args={"values": ("10",)})))
    assert reply.user_message == "✅ Allowed channels updated (1 channel)."


def test_blank_channel_selection_clears_the_list(monkeypatch):
    from sb.spec.outcomes import SUCCESS

    calls = _install_channels_write(monkeypatch)
    reply = run(_handler("settings.ca_channels")(_req(args={"values": ()})))
    (_, channel_ids, allow_empty), = calls
    assert channel_ids == ()
    assert allow_empty is True
    assert reply.outcome == SUCCESS
    # shipped confirmation copy, verbatim (clear branch).
    assert reply.user_message == "✅ Allowed channel list cleared."


def test_channels_write_failure_answers_honestly(monkeypatch):
    _install_channels_write(monkeypatch, outcome="error",
                            user_message="nope")
    reply = run(_handler("settings.ca_channels")(
        _req(args={"values": ("10",)})))
    assert reply.outcome == "error"
    assert "Couldn't update the allowed channels" in reply.user_message
    assert "nope" in reply.user_message


# --- the guards --------------------------------------------------------------------


def test_no_guild_guard_blocks_both_writes_before_the_seam(monkeypatch):
    from sb.spec.outcomes import BLOCKED

    mode_calls = _install_mode_write(monkeypatch)
    channel_calls = _install_channels_write(monkeypatch)
    guard = "❌ Command access can only be configured inside a server."

    reply = run(_handler("settings.ca_mode")(
        _req(guild_id=0, args={"session_action": "ca_all_channels"})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == guard          # shipped copy, verbatim

    reply = run(_handler("settings.ca_channels")(
        _req(guild_id=0, args={"values": ("10",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == guard
    assert mode_calls == [] and channel_calls == []


# --- the retired pending terminal ---------------------------------------------------


def test_command_access_and_group_pending_terminals_are_retired():
    from sb.domain.settings import handlers
    from sb.spec.refs import HandlerRef, is_registered

    handlers.ensure_handler_refs()
    assert not is_registered(HandlerRef("settings.command_access_pending"))
    # settings epic S0 retired the last terminal — settings.group_pending
    # was displaced by the ported per-group edit page (option A).
    assert not is_registered(HandlerRef("settings.group_pending"))
