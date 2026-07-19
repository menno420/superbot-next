"""Settings epic S0 — the ported per-group scalar EDIT page
(``settings.group_edit``) + the S1 bool toggle widget.

Pins the load-bearing OPTION-A boundary (docs/question-router.md → Answered,
2026-07-18; docs/decisions.md): ``settings.open_group``'s NON-HUB arm now
opens ``settings.group_edit``, while the 5 operator-spine hub arms
(welcome / counters / security / automod / image_moderation) and the
``games`` dedicated-panel arm route UNCHANGED — a slice that widened the
edit page to a hub group would silently re-home a shipped hub route and
contradict the owner ruling. Also covers the frame's spec shape, the
provider-fed edit/reset option sets, and the S1 bool toggle dispatch onto
the K7 ``settings.set_scalar`` / ``clear_scalar`` lanes (no new op)."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, CHAN = 700000000000000001, 200

# the 5 operator-spine hub groups (option A leaves these on <group>.hub) +
# the games dedicated-panel arm (routes to games.sections).
_HUB_GROUPS = ("welcome", "counters", "security", "automod",
               "image_moderation")


@dataclass
class _Req:
    """A click request shaped like the settings handlers read it — a real
    dataclass so ``open_group``'s ``dataclasses.replace(req, args=…)`` (the
    access_view precedent) works, plus the message-key origin the refresh
    path walks."""

    args: dict = field(default_factory=dict)
    guild_id: int | None = GID
    channel_id: int = CHAN
    actor: object = field(default_factory=lambda: SimpleNamespace(user_id=42))
    request_id: str = "req-1"
    confirmed: bool = False
    origin: object = field(
        default_factory=lambda: SimpleNamespace(
            message=SimpleNamespace(id="777")))


@pytest.fixture(autouse=True)
def _armed_refs():
    """Re-arm the settings refs (suite-order registry resets) and import the
    real operator-hub + role manifests so the routing branches resolve
    against genuine registrations (never a fake ensure_hub)."""
    from sb.domain.settings import handlers, panels

    for name in (*_HUB_GROUPS, "role", "moderation"):
        importlib.import_module(f"sb.manifest.{name}")
    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    yield


def _handler(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _open_group():
    return _handler("settings.open_group")


def _patch_open_panel(monkeypatch):
    """Record every open_panel(ref, req) the handler drives."""
    import sb.kernel.panels.engine as engine

    opened: list[tuple[str, dict]] = []

    async def fake_open(ref, req):
        opened.append((ref.name, dict(getattr(req, "args", {}) or {})))
        return "msg-key"

    monkeypatch.setattr(engine, "open_panel", fake_open)
    return opened


# --- option A: the routing boundary ------------------------------------------------


class TestOptionABoundary:
    def test_non_hub_group_opens_the_group_edit_page(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        # `role` and `moderation` are non-hub, non-games groups — the arm
        # option A re-points to the ported edit page.
        for group in ("role", "moderation"):
            reply = run(_open_group()(_Req(args={"values": (group,)})))
            assert reply is None                     # open_panel took over
        assert [name for name, _ in opened] == [
            "settings.group_edit", "settings.group_edit"]
        # the selected group rides the opening args (GROUP_EDIT_PARAM) so the
        # engine bakes it onto every session-minted child.
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        assert opened[0][1][GROUP_EDIT_PARAM] == "role"
        assert opened[1][1][GROUP_EDIT_PARAM] == "moderation"

    def test_the_five_hub_arms_are_untouched(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        for group in _HUB_GROUPS:
            assert run(_open_group()(_Req(args={"values": (group,)}))) is None
        assert [name for name, _ in opened] == [
            f"{g}.hub" for g in _HUB_GROUPS]

    def test_the_games_panel_arm_is_untouched(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        assert run(_open_group()(_Req(args={"values": ("games",)}))) is None
        assert opened == [("games.sections", {"values": ("games",)})]

    def test_empty_selection_opens_nothing(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.spec.outcomes import BLOCKED

        reply = run(_open_group()(_Req(args={"values": ()})))
        assert reply.outcome == BLOCKED
        assert opened == []

    def test_group_pending_terminal_is_retired(self):
        from sb.spec.refs import HandlerRef, is_registered

        assert not is_registered(HandlerRef("settings.group_pending"))


# --- the page frame -----------------------------------------------------------------


class TestGroupEditFrame:
    def test_spec_compiles_and_is_a_session_view(self):
        from sb.domain.settings.panels import settings_group_edit_spec
        from sb.kernel.panels.compile import check_panel
        from sb.spec.panels import Audience, FooterMode
        from sb.spec.refs import HandlerRef, PanelRef

        spec = settings_group_edit_spec()
        check_panel(spec)
        assert spec.panel_id == "settings.group_edit"
        assert spec.audience is Audience.INVOKER
        assert spec.frame.style_token == "blurple"
        assert spec.frame.footer_mode is FooterMode.NONE
        assert spec.session_lifecycle is True
        assert spec.renderer_override == HandlerRef("settings.render_group_edit")
        by_sel = {s.selector_id: s for s in spec.selectors}
        assert by_sel["edit_select"].windowed is True
        assert by_sel["reset_select"].windowed is True
        by_act = {a.action_id: a for a in spec.actions}
        # Back to Hub is a PanelRef open-child terminal back to the hub.
        assert by_act["group_back"].handler == PanelRef("settings.hub")

    def test_manifest_declares_the_group_edit_pages_last(self):
        from sb.manifest.settings import MANIFEST

        assert [p.panel_id for p in MANIFEST.panels[2:]] == [
            "settings.needs_setup", "settings.invalid",
            "settings.missing_bindings", "settings.audit",
            "settings.command_access", "settings.group_edit",
            "settings.group_edit_enum"]

    def test_edit_and_reset_options_are_the_editable_specs(self):
        from sb.domain.settings import panels
        from sb.kernel.panels.context import PanelContext, PanelOrigin
        from sb.kernel.interaction.locale import LocaleContext
        from sb.spec.panels import Audience

        ctx = PanelContext(
            bot=None, guild_id=GID, actor=SimpleNamespace(user_id=42),
            channel_id=CHAN, origin=PanelOrigin.INTERACTION,
            audience=Audience.INVOKER, locale=LocaleContext(),
            params={panels.GROUP_EDIT_PARAM: "role"})
        edit = run(panels._group_edit_edit_options(ctx))
        reset = run(panels._group_edit_reset_options(ctx))
        # role's editable specs (settings_key present): skip_roles +
        # three bools — the same set in both selects, verbatim names.
        edit_values = [o["value"] for o in edit]
        assert "time_roles_stack" in edit_values
        assert edit_values == [o["value"] for o in reset]
        assert all(o["label"].startswith("Reset ") for o in reset)


# --- the S1 bool toggle + reset (K7 scalar lanes) ----------------------------------


def _patch_scalar_run(monkeypatch, outcome="success"):
    """Stub the K7 op runner; records (op_key, params)."""
    import sb.kernel.workflow.engine as engine

    calls: list[tuple[str, dict]] = []

    async def fake_run(op, ctx):
        calls.append((op.op_key, dict(ctx.params)))
        return SimpleNamespace(outcome=outcome, user_message="")

    monkeypatch.setattr(engine, "run", fake_run)
    return calls


def _patch_refresh(monkeypatch):
    import sb.kernel.panels.engine as engine

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(engine, "refresh_session_view", fake_refresh)


def _patch_resolve(monkeypatch, value):
    import sb.kernel.settings as ksettings

    async def fake_resolve(guild_id, subsystem, name):
        return value

    monkeypatch.setattr(ksettings, "resolve", fake_resolve)


class TestBoolToggleAndReset:
    def _req(self, name):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        return _Req(args={GROUP_EDIT_PARAM: "role", "values": (name,)})

    @staticmethod
    def _key(name):
        """The persisted KV key the handler writes — resolved the same way
        the handler does (settings_key when the manifest declarations are
        registered, the `subsystem.name` fallback otherwise)."""
        from sb.kernel import settings as ksettings

        return ksettings.persisted_key("role", name)

    def test_bool_pick_emits_set_scalar_with_the_inverted_value(
            self, monkeypatch):
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)
        _patch_resolve(monkeypatch, False)          # current = False → flip on

        reply = run(_handler("settings.group_edit_pick")(
            self._req("time_roles_stack")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": self._key("time_roles_stack"),
                           "value": "true"})]
        assert "set to **True**" in reply.user_message

    def test_bool_pick_flips_a_true_setting_off(self, monkeypatch):
        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)
        _patch_resolve(monkeypatch, True)           # current = True → flip off

        run(_handler("settings.group_edit_pick")(
            self._req("xp_roles_stack")))
        assert calls == [("settings.set_scalar",
                          {"key": self._key("xp_roles_stack"),
                           "value": "false"})]

    def test_non_bool_pick_degrades_honestly_without_a_write(
            self, monkeypatch):
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_pick")(
            self._req("skip_roles")))               # str — S4 text widget
        assert reply.outcome == SUCCESS
        assert calls == []                          # no write for unported type
        assert "later settings slice" in reply.user_message

    def test_reset_emits_clear_scalar(self, monkeypatch):
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_reset")(
            self._req("time_roles_stack")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.clear_scalar",
                          {"key": self._key("time_roles_stack")})]
        assert "reset to its default" in reply.user_message

    def test_open_panel_button_is_the_honest_no_panel_fallback(self):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.spec.outcomes import SUCCESS

        reply = run(_handler("settings.group_open_panel")(
            _Req(args={GROUP_EDIT_PARAM: "role"})))
        assert reply.outcome == SUCCESS
        assert "no dedicated interactive panel" in reply.user_message


# --- the S2 enum-select edit widget (K7 set_scalar) --------------------------------
#
# `moderation.warn_escalation_action` is a NON-HUB group enum scalar
# (value_type=str, allowed_values=("timeout","kick","ban","none"),
# default="timeout") — the concrete port target.

_ENUM_GROUP = "moderation"
_ENUM_SETTING = "warn_escalation_action"
_ENUM_CHOICES = ("timeout", "kick", "ban", "none")


def _ctx(**params):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=42),
        channel_id=CHAN, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params=params)


class TestEnumPickerFrame:
    def test_enum_spec_compiles_and_is_a_session_view(self):
        from sb.domain.settings.panels import settings_group_edit_enum_spec
        from sb.kernel.panels.compile import check_panel
        from sb.spec.panels import Audience, FooterMode
        from sb.spec.refs import HandlerRef

        spec = settings_group_edit_enum_spec()
        check_panel(spec)
        assert spec.panel_id == "settings.group_edit_enum"
        assert spec.audience is Audience.INVOKER
        assert spec.frame.footer_mode is FooterMode.NONE
        assert spec.session_lifecycle is True
        by_sel = {s.selector_id: s for s in spec.selectors}
        assert by_sel["enum_select"].windowed is True
        assert (by_sel["enum_select"].on_select
                == HandlerRef("settings.group_edit_enum_pick"))
        by_act = {a.action_id: a for a in spec.actions}
        assert (by_act["enum_back"].handler
                == HandlerRef("settings.group_edit_enum_back"))

    def test_enum_options_are_the_declared_choices_current_marked(
            self, monkeypatch):
        from sb.domain.settings import panels, service

        # deterministic current = "kick" (avoid a DB-backed resolver).
        async def fake_resolve(guild_id, subsystem, name, spec=None):
            return SimpleNamespace(value="kick")

        monkeypatch.setattr(service, "resolve_setting", fake_resolve)
        opts = run(panels._group_edit_enum_options(_ctx(
            **{panels.GROUP_EDIT_PARAM: _ENUM_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _ENUM_SETTING})))
        assert [o["value"] for o in opts] == list(_ENUM_CHOICES)
        # the current value is pre-marked (default=True, description "current").
        marked = [o for o in opts if o.get("default")]
        assert len(marked) == 1
        assert marked[0]["value"] == "kick"
        assert marked[0]["description"] == "current"

    def test_enum_options_empty_for_a_non_enum_setting(self):
        from sb.domain.settings import panels

        # a bool setting is not enum-shaped → no options materialize.
        opts = run(panels._group_edit_enum_options(_ctx(
            **{panels.GROUP_EDIT_PARAM: "role",
               panels.GROUP_EDIT_SETTING_PARAM: "time_roles_stack"})))
        assert opts == ()


class TestEnumDispatchAndCommit:
    def _pick_req(self, name):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        return _Req(args={GROUP_EDIT_PARAM: _ENUM_GROUP, "values": (name,)})

    def _commit_req(self, chosen, *, group=_ENUM_GROUP, name=_ENUM_SETTING):
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        return _Req(args={GROUP_EDIT_PARAM: group,
                          GROUP_EDIT_SETTING_PARAM: name,
                          "values": (chosen,)})

    def test_enum_pick_opens_the_windowed_picker(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        reply = run(_handler("settings.group_edit_pick")(
            self._pick_req(_ENUM_SETTING)))
        assert reply is None                         # open_panel took over
        assert [name for name, _ in opened] == ["settings.group_edit_enum"]
        args = opened[0][1]
        assert args[GROUP_EDIT_PARAM] == _ENUM_GROUP
        assert args[GROUP_EDIT_SETTING_PARAM] == _ENUM_SETTING

    def test_enum_commit_emits_set_scalar_with_the_chosen_member(
            self, monkeypatch):
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_enum_pick")(
            self._commit_req("kick")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": ksettings.persisted_key(
                              _ENUM_GROUP, _ENUM_SETTING),
                           "value": "kick"})]
        assert "set to **kick**" in reply.user_message

    def test_enum_commit_rejects_a_non_allowed_value_without_a_write(
            self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_enum_pick")(
            self._commit_req("banana")))         # not in allowed_values
        assert reply.outcome == BLOCKED
        assert calls == []                       # no write for a bad value
        assert "not an allowed value" in reply.user_message

    def test_out_of_window_pick_still_resolves(self, monkeypatch):
        """A >25-choice enum windows its select; the chosen value rides the
        `values` round-trip, so a page-2 option commits the same as a page-1
        one (the window is a render concern, never a resolution one)."""
        from sb.domain.settings import panels
        from sb.spec.outcomes import SUCCESS
        from sb.spec.settings import SettingSpec

        big = SettingSpec(name="big_enum", value_type=str, default="opt_0",
                          settings_key="big_enum",
                          allowed_values=tuple(f"opt_{i}" for i in range(30)))
        monkeypatch.setattr(panels, "_group_edit_spec",
                            lambda group, name: big)
        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_enum_pick")(
            self._commit_req("opt_28", name="big_enum")))   # window page 2
        assert reply.outcome == SUCCESS
        assert calls[0][0] == "settings.set_scalar"
        assert calls[0][1]["value"] == "opt_28"

    def test_enum_reset_clears_through_clear_scalar(self, monkeypatch):
        """The S0 reset select is type-agnostic — resetting an enum setting
        clears its explicit row through settings.clear_scalar (no new path)."""
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_reset")(
            _Req(args={GROUP_EDIT_PARAM: _ENUM_GROUP,
                       "values": (_ENUM_SETTING,)})))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.clear_scalar",
                          {"key": ksettings.persisted_key(
                              _ENUM_GROUP, _ENUM_SETTING)})]

    def test_enum_back_reopens_the_group_edit_page(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        reply = run(_handler("settings.group_edit_enum_back")(
            _Req(args={GROUP_EDIT_PARAM: _ENUM_GROUP})))
        assert reply is None
        assert opened == [("settings.group_edit",
                           {GROUP_EDIT_PARAM: _ENUM_GROUP})]
