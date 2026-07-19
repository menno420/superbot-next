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

    for name in (*_HUB_GROUPS, "role", "moderation", "karma", "btd6", "xp"):
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
            "settings.group_edit_enum", "settings.group_edit_number",
            "settings.group_edit_text", "settings.group_edit_channel",
            "settings.group_edit_presets"]

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
        """A pick whose widget hasn't landed yet degrades honestly (no write).
        After S5 every real editable scalar routes to a live widget
        (bool/enum/number/free-text/channel), so a role-pointer-hinted str — the
        S6–S7 territory the oracle routes by input_hint before the free-text
        fallback — stands in for the still-unported case."""
        from sb.domain.settings import panels
        from sb.spec.outcomes import SUCCESS
        from sb.spec.settings import SettingSpec

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # a role-pointer scalar (input_hint="role") — the S6 role-select arm
        # (not yet ported) claims it, so it is NEITHER the free-text modal (the
        # _POINTER_HINTS exclusion) NOR the S5 channel picker.
        pointer = SettingSpec(name="staff_role", value_type=str,
                              settings_key="role_staff_role",
                              input_hint="role")
        monkeypatch.setattr(panels, "_group_edit_spec",
                            lambda group, name: pointer)
        reply = run(_handler("settings.group_edit_pick")(
            self._req("staff_role")))
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


# --- the S3 number-modal edit widget (K7 set_scalar) -------------------------------
#
# `moderation.warn_threshold` is a NON-HUB group int scalar
# (value_type=int, default=3, bounds=(1, 50)) — the concrete port target.
# Its typed input coerces + range-validates through the settings-service
# coerce_value seam before the audited write.

_NUM_GROUP = "moderation"
_NUM_SETTING = "warn_threshold"


class TestNumberWidgetFrame:
    def test_number_spec_compiles_and_is_a_session_view(self):
        from sb.domain.settings.panels import settings_group_edit_number_spec
        from sb.kernel.panels.compile import check_panel
        from sb.spec.outcomes import DeferMode
        from sb.spec.panels import Audience, FooterMode
        from sb.spec.refs import HandlerRef

        spec = settings_group_edit_number_spec()
        check_panel(spec)
        assert spec.panel_id == "settings.group_edit_number"
        assert spec.audience is Audience.INVOKER
        assert spec.frame.footer_mode is FooterMode.NONE
        assert spec.session_lifecycle is True
        by_act = {a.action_id: a for a in spec.actions}
        # the "Enter a number…" button ISSUES the G-10 numeric modal.
        edit = by_act["number_edit"]
        assert edit.defer_mode is DeferMode.MODAL
        assert edit.modal is not None
        assert edit.modal.modal_id == "settings.group_edit_number_form"
        assert len(edit.modal.fields) == 1
        assert edit.modal.fields[0].field_id == "number_value"
        assert edit.handler == HandlerRef("settings.group_edit_number_submit")
        # ↩ Back re-opens the group edit page via its own handler.
        assert (by_act["number_back"].handler
                == HandlerRef("settings.group_edit_number_back"))

    def test_number_fields_show_current_default_and_range(self, monkeypatch):
        from sb.domain.settings import panels, service

        # deterministic current = 7 (avoid a DB-backed resolver).
        async def fake_resolve(guild_id, subsystem, name, spec=None):
            return SimpleNamespace(value=7)

        monkeypatch.setattr(service, "resolve_setting", fake_resolve)
        fields = run(panels._group_edit_number_fields(_ctx(
            **{panels.GROUP_EDIT_PARAM: _NUM_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _NUM_SETTING})))
        assert fields[0][0] == f"Editing `{_NUM_GROUP}.{_NUM_SETTING}`"
        body = fields[0][1]
        assert "current = `7`" in body
        assert "default = `3`" in body
        # warn_threshold declares bounds=(1, 50) — the range copy renders.
        assert "Allowed range" in body and "`1`" in body and "`50`" in body

    def test_number_fields_degrade_on_an_expired_session(self):
        from sb.domain.settings import panels

        fields = run(panels._group_edit_number_fields(_ctx()))
        assert "session expired" in fields[0][1]


class TestNumberDispatchAndCommit:
    def _pick_req(self, name):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        return _Req(args={GROUP_EDIT_PARAM: _NUM_GROUP, "values": (name,)})

    def _submit_req(self, raw, *, group=_NUM_GROUP, name=_NUM_SETTING):
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        # the modal-args stash restores (group, setting); the submitted field
        # value rides `number_value` (the ModalFieldSpec field_id).
        return _Req(args={GROUP_EDIT_PARAM: group,
                          GROUP_EDIT_SETTING_PARAM: name,
                          "number_value": raw})

    def test_number_pick_opens_the_number_widget(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        reply = run(_handler("settings.group_edit_pick")(
            self._pick_req(_NUM_SETTING)))
        assert reply is None                         # open_panel took over
        assert [name for name, _ in opened] == ["settings.group_edit_number"]
        args = opened[0][1]
        assert args[GROUP_EDIT_PARAM] == _NUM_GROUP
        assert args[GROUP_EDIT_SETTING_PARAM] == _NUM_SETTING

    def test_number_submit_persists_the_coerced_scalar(self, monkeypatch):
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_number_submit")(
            self._submit_req(" 5 ")))            # whitespace trims, coerces
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": ksettings.persisted_key(
                              _NUM_GROUP, _NUM_SETTING),
                           "value": "5"})]
        assert "set to **5**" in reply.user_message

    def test_number_submit_rejects_non_numeric_without_a_write(
            self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_number_submit")(
            self._submit_req("not-a-number")))
        assert reply.outcome == BLOCKED
        assert calls == []                       # no write for a bad value
        assert "cannot coerce" in reply.user_message

    def test_number_submit_rejects_out_of_range_without_a_write(
            self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # warn_threshold bounds=(1, 50) — 9999 is a well-formed int that the
        # coercer's range check rejects.
        reply = run(_handler("settings.group_edit_number_submit")(
            self._submit_req("9999")))
        assert reply.outcome == BLOCKED
        assert calls == []                       # no write for out-of-range
        assert "cannot coerce" in reply.user_message

    def test_number_submit_rejects_a_non_number_setting(self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # warn_escalation_action is a str/enum setting — not number-shaped.
        reply = run(_handler("settings.group_edit_number_submit")(
            self._submit_req("5", name="warn_escalation_action")))
        assert reply.outcome == BLOCKED
        assert calls == []
        assert "not a number setting" in reply.user_message

    def test_number_reset_clears_through_clear_scalar(self, monkeypatch):
        """The S0 reset select is type-agnostic — resetting a number setting
        clears its explicit row through settings.clear_scalar (no new path)."""
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_reset")(
            _Req(args={GROUP_EDIT_PARAM: _NUM_GROUP,
                       "values": (_NUM_SETTING,)})))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.clear_scalar",
                          {"key": ksettings.persisted_key(
                              _NUM_GROUP, _NUM_SETTING)})]

    def test_number_back_reopens_the_group_edit_page(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        reply = run(_handler("settings.group_edit_number_back")(
            _Req(args={GROUP_EDIT_PARAM: _NUM_GROUP})))
        assert reply is None
        assert opened == [("settings.group_edit",
                           {GROUP_EDIT_PARAM: _NUM_GROUP})]


# --- the S4 free-text-modal edit widget (K7 set_scalar) ----------------------------
#
# `karma.reaction_emoji` is a NON-HUB group free-text str scalar
# (value_type=str, no allowed_values, default="", bounds=(64,)) — the concrete
# port target. Its typed string is validated (non-empty + the declared
# 64-char max-length) before the audited write; a str WITH allowed_values goes
# to the S2 enum select, not here.

_TEXT_GROUP = "karma"
_TEXT_SETTING = "reaction_emoji"


class TestTextWidgetFrame:
    def test_text_spec_compiles_and_is_a_session_view(self):
        from sb.domain.settings.panels import settings_group_edit_text_spec
        from sb.kernel.panels.compile import check_panel
        from sb.spec.outcomes import DeferMode
        from sb.spec.panels import Audience, FooterMode, ModalFieldStyle
        from sb.spec.refs import HandlerRef

        spec = settings_group_edit_text_spec()
        check_panel(spec)
        assert spec.panel_id == "settings.group_edit_text"
        assert spec.audience is Audience.INVOKER
        assert spec.frame.footer_mode is FooterMode.NONE
        assert spec.session_lifecycle is True
        by_act = {a.action_id: a for a in spec.actions}
        # the "Enter text…" button ISSUES the G-10 free-text modal.
        edit = by_act["text_edit"]
        assert edit.defer_mode is DeferMode.MODAL
        assert edit.modal is not None
        assert edit.modal.modal_id == "settings.group_edit_text_form"
        assert len(edit.modal.fields) == 1
        assert edit.modal.fields[0].field_id == "text_value"
        # the shipped paragraph (multi-line) TextInput.
        assert edit.modal.fields[0].style is ModalFieldStyle.PARAGRAPH
        assert edit.handler == HandlerRef("settings.group_edit_text_submit")
        # ↩ Back re-opens the group edit page via its own handler.
        assert (by_act["text_back"].handler
                == HandlerRef("settings.group_edit_text_back"))

    def test_text_fields_show_current_default_and_max_length(self, monkeypatch):
        from sb.domain.settings import panels, service

        # deterministic current = "⭐" (avoid a DB-backed resolver).
        async def fake_resolve(guild_id, subsystem, name, spec=None):
            return SimpleNamespace(value="⭐")

        monkeypatch.setattr(service, "resolve_setting", fake_resolve)
        fields = run(panels._group_edit_text_fields(_ctx(
            **{panels.GROUP_EDIT_PARAM: _TEXT_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _TEXT_SETTING})))
        assert fields[0][0] == f"Editing `{_TEXT_GROUP}.{_TEXT_SETTING}`"
        body = fields[0][1]
        assert "current = `'⭐'`" in body
        assert "type = `str`" in body
        # reaction_emoji declares bounds=(64,) — the max-length copy renders.
        assert "Max length" in body and "`64`" in body

    def test_text_fields_degrade_on_an_expired_session(self):
        from sb.domain.settings import panels

        fields = run(panels._group_edit_text_fields(_ctx()))
        assert "session expired" in fields[0][1]


class TestTextDispatchAndCommit:
    def _pick_req(self, name, *, group=_TEXT_GROUP):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        return _Req(args={GROUP_EDIT_PARAM: group, "values": (name,)})

    def _submit_req(self, raw, *, group=_TEXT_GROUP, name=_TEXT_SETTING):
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        # the modal-args stash restores (group, setting); the submitted field
        # value rides `text_value` (the ModalFieldSpec field_id).
        return _Req(args={GROUP_EDIT_PARAM: group,
                          GROUP_EDIT_SETTING_PARAM: name,
                          "text_value": raw})

    def test_text_pick_opens_the_text_widget(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        reply = run(_handler("settings.group_edit_pick")(
            self._pick_req(_TEXT_SETTING)))
        assert reply is None                         # open_panel took over
        assert [name for name, _ in opened] == ["settings.group_edit_text"]
        args = opened[0][1]
        assert args[GROUP_EDIT_PARAM] == _TEXT_GROUP
        assert args[GROUP_EDIT_SETTING_PARAM] == _TEXT_SETTING

    def test_text_submit_persists_the_string(self, monkeypatch):
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_text_submit")(
            self._submit_req("⭐")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": ksettings.persisted_key(
                              _TEXT_GROUP, _TEXT_SETTING),
                           "value": "⭐"})]
        assert "set to **'⭐'**" in reply.user_message

    def test_text_submit_rejects_empty_without_a_write(self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # a whitespace-only value is empty — the widget requires a value
        # (Reset clears a setting through clear_scalar).
        reply = run(_handler("settings.group_edit_text_submit")(
            self._submit_req("   ")))
        assert reply.outcome == BLOCKED
        assert calls == []                       # no write for an empty value
        assert "can't be empty" in reply.user_message

    def test_text_submit_rejects_over_length_without_a_write(self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # reaction_emoji bounds=(64,) — a 65-char value trips the max-length
        # gate (coerce_value does not apply str bounds; the submit does).
        reply = run(_handler("settings.group_edit_text_submit")(
            self._submit_req("x" * 65)))
        assert reply.outcome == BLOCKED
        assert calls == []                       # no write for over-length
        assert "too long" in reply.user_message

    def test_text_submit_rejects_a_non_text_setting(self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # warn_escalation_action is a str/enum setting (allowed_values) — routed
        # to the S2 enum select, not the free-text modal.
        reply = run(_handler("settings.group_edit_text_submit")(
            self._submit_req("anything", group="moderation",
                             name="warn_escalation_action")))
        assert reply.outcome == BLOCKED
        assert calls == []
        assert "not a free-text setting" in reply.user_message

    def test_text_reset_clears_through_clear_scalar(self, monkeypatch):
        """The S0 reset select is type-agnostic — resetting a text setting
        clears its explicit row through settings.clear_scalar (no new path)."""
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_reset")(
            _Req(args={GROUP_EDIT_PARAM: _TEXT_GROUP,
                       "values": (_TEXT_SETTING,)})))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.clear_scalar",
                          {"key": ksettings.persisted_key(
                              _TEXT_GROUP, _TEXT_SETTING)})]

    def test_text_back_reopens_the_group_edit_page(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        reply = run(_handler("settings.group_edit_text_back")(
            _Req(args={GROUP_EDIT_PARAM: _TEXT_GROUP})))
        assert reply is None
        assert opened == [("settings.group_edit",
                           {GROUP_EDIT_PARAM: _TEXT_GROUP})]


# --- the S5 channel-select edit widget (K7 set_scalar) -----------------------------
#
# `btd6.strategy_submission_channel` is a NON-HUB group channel-pointer scalar
# (value_type=int, default=0, input_hint="channel") — the concrete port target.
# It is `int`-typed, so before S5 it MISROUTED to the S3 number modal
# (`_is_number_spec` matches int); the S5 arm intercepts input_hint=="channel"
# BEFORE the number check so it opens the channel picker instead. The chosen
# channel id commits through the same K7 settings.set_scalar lane.

_CHAN_GROUP = "btd6"
_CHAN_SETTING = "strategy_submission_channel"


class _FakeChannelDirectory:
    """A channel-directory READ stub (the _WorldChannelDirectory shape) —
    yields ChannelSnapshot-duck rows for the options provider."""

    def __init__(self, rows):
        self._rows = rows

    async def list_channels(self, guild_id):
        del guild_id
        return tuple(
            SimpleNamespace(channel_id=cid, name=name, kind=kind)
            for cid, name, kind in self._rows)


def _patch_channel_directory(monkeypatch, rows):
    from sb.domain.channel import service

    monkeypatch.setattr(service, "active_directory",
                        lambda: _FakeChannelDirectory(rows))


class TestChannelWidgetFrame:
    def test_channel_spec_compiles_and_is_a_session_view(self):
        from sb.domain.settings.panels import settings_group_edit_channel_spec
        from sb.kernel.panels.compile import check_panel
        from sb.spec.panels import Audience, FooterMode, SelectorKind
        from sb.spec.refs import HandlerRef

        spec = settings_group_edit_channel_spec()
        check_panel(spec)
        assert spec.panel_id == "settings.group_edit_channel"
        assert spec.audience is Audience.INVOKER
        assert spec.frame.footer_mode is FooterMode.NONE
        assert spec.session_lifecycle is True
        by_sel = {s.selector_id: s for s in spec.selectors}
        # the channel picker is a windowed component select (NOT a modal).
        assert by_sel["channel_select"].windowed is True
        assert by_sel["channel_select"].kind is SelectorKind.ENUM
        assert (by_sel["channel_select"].on_select
                == HandlerRef("settings.group_edit_channel_pick"))
        by_act = {a.action_id: a for a in spec.actions}
        assert (by_act["channel_back"].handler
                == HandlerRef("settings.group_edit_channel_back"))

    def test_channel_options_are_the_guild_channels_current_marked(
            self, monkeypatch):
        from sb.domain.settings import panels, service

        # deterministic current = channel id 111 (avoid a DB-backed resolver).
        async def fake_resolve(guild_id, subsystem, name, spec=None):
            return SimpleNamespace(value=111)

        monkeypatch.setattr(service, "resolve_setting", fake_resolve)
        _patch_channel_directory(monkeypatch, [
            (111, "general", "text"),
            (222, "commands", "text"),
            (333, "the-category", "category"),   # categories are filtered out
        ])
        opts = run(panels._group_edit_channel_options(_ctx(
            **{panels.GROUP_EDIT_PARAM: _CHAN_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _CHAN_SETTING})))
        # only the two text channels materialize (the category is dropped).
        assert [o["value"] for o in opts] == ["111", "222"]
        assert [o["label"] for o in opts] == ["#general", "#commands"]
        # the current channel is pre-marked (default=True, description "current").
        marked = [o for o in opts if o.get("default")]
        assert len(marked) == 1
        assert marked[0]["value"] == "111"
        assert marked[0]["description"] == "current"

    def test_channel_options_empty_for_a_non_channel_setting(self, monkeypatch):
        from sb.domain.settings import panels

        _patch_channel_directory(monkeypatch, [(111, "general", "text")])
        # a bool setting is not channel-hinted → no options materialize.
        opts = run(panels._group_edit_channel_options(_ctx(
            **{panels.GROUP_EDIT_PARAM: "role",
               panels.GROUP_EDIT_SETTING_PARAM: "time_roles_stack"})))
        assert opts == ()

    def test_channel_options_empty_when_directory_unarmed(self, monkeypatch):
        from sb.domain.channel import service
        from sb.domain.settings import panels

        def _raise():
            raise RuntimeError("directory not installed")

        monkeypatch.setattr(service, "active_directory", _raise)
        opts = run(panels._group_edit_channel_options(_ctx(
            **{panels.GROUP_EDIT_PARAM: _CHAN_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _CHAN_SETTING})))
        assert opts == ()


class TestChannelDispatchAndCommit:
    def _pick_req(self, name, *, group=_CHAN_GROUP):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        return _Req(args={GROUP_EDIT_PARAM: group, "values": (name,)})

    def _commit_req(self, chosen, *, group=_CHAN_GROUP, name=_CHAN_SETTING):
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        return _Req(args={GROUP_EDIT_PARAM: group,
                          GROUP_EDIT_SETTING_PARAM: name,
                          "values": (chosen,)})

    def test_channel_pick_opens_the_picker_not_the_number_modal(
            self, monkeypatch):
        """THE S5 REGRESSION: `btd6.strategy_submission_channel` is an `int`
        with input_hint="channel"; before S5 the value_type-only dispatch
        misrouted it to the S3 number modal. The channel arm now intercepts the
        hint FIRST, so it opens the channel picker instead."""
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        reply = run(_handler("settings.group_edit_pick")(
            self._pick_req(_CHAN_SETTING)))
        assert reply is None                         # open_panel took over
        # the channel picker — NOT settings.group_edit_number.
        assert [name for name, _ in opened] == ["settings.group_edit_channel"]
        args = opened[0][1]
        assert args[GROUP_EDIT_PARAM] == _CHAN_GROUP
        assert args[GROUP_EDIT_SETTING_PARAM] == _CHAN_SETTING

    def test_channel_pick_persists_the_channel_id(self, monkeypatch):
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_channel_pick")(
            self._commit_req("222")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": ksettings.persisted_key(
                              _CHAN_GROUP, _CHAN_SETTING),
                           "value": "222"})]
        assert "set to <#222>" in reply.user_message

    def test_channel_pick_rejects_a_non_numeric_value_without_a_write(
            self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_channel_pick")(
            self._commit_req("not-a-channel")))
        assert reply.outcome == BLOCKED
        assert calls == []                       # no write for a bad value
        assert "not a valid channel" in reply.user_message

    def test_channel_pick_rejects_a_non_channel_setting(self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # warn_threshold is a plain int (no channel hint) — not channel-shaped.
        reply = run(_handler("settings.group_edit_channel_pick")(
            self._commit_req("222", group="moderation", name="warn_threshold")))
        assert reply.outcome == BLOCKED
        assert calls == []
        assert "not a channel setting" in reply.user_message

    def test_out_of_window_channel_pick_still_resolves(self, monkeypatch):
        """A >25-channel guild windows the select; the chosen channel id rides
        the `values` round-trip, so a page-2 channel commits the same as a
        page-1 one (the window is a render concern, never a resolution one)."""
        from sb.domain.settings import panels, service
        from sb.spec.outcomes import SUCCESS
        from sb.spec.settings import SettingSpec

        big = SettingSpec(name=_CHAN_SETTING, value_type=int, default=0,
                          settings_key="btd6_strategy_submission_channel",
                          input_hint="channel")
        monkeypatch.setattr(panels, "_group_edit_spec",
                            lambda group, name: big)

        # 30 channels — the options provider windows past Discord's 25 ceiling.
        rows = [(1000 + i, f"chan-{i}", "text") for i in range(30)]

        async def fake_resolve(guild_id, subsystem, name, spec=None):
            return SimpleNamespace(value=0)

        monkeypatch.setattr(service, "resolve_setting", fake_resolve)
        _patch_channel_directory(monkeypatch, rows)
        opts = run(panels._group_edit_channel_options(_ctx(
            **{panels.GROUP_EDIT_PARAM: _CHAN_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _CHAN_SETTING})))
        assert len(opts) == 30            # every channel is an option (windowed)

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)
        # a page-2 channel (index 28) commits the same as any first-window one.
        reply = run(_handler("settings.group_edit_channel_pick")(
            self._commit_req("1028")))
        assert reply.outcome == SUCCESS
        assert calls[0][0] == "settings.set_scalar"
        assert calls[0][1]["value"] == "1028"

    def test_channel_reset_clears_through_clear_scalar(self, monkeypatch):
        """The S0 reset select is type-agnostic — resetting a channel setting
        clears its explicit row through settings.clear_scalar (no new path)."""
        from sb.domain.settings.panels import GROUP_EDIT_PARAM
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_reset")(
            _Req(args={GROUP_EDIT_PARAM: _CHAN_GROUP,
                       "values": (_CHAN_SETTING,)})))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.clear_scalar",
                          {"key": ksettings.persisted_key(
                              _CHAN_GROUP, _CHAN_SETTING)})]

    def test_channel_back_reopens_the_group_edit_page(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        reply = run(_handler("settings.group_edit_channel_back")(
            _Req(args={GROUP_EDIT_PARAM: _CHAN_GROUP})))
        assert reply is None
        assert opened == [("settings.group_edit",
                           {GROUP_EDIT_PARAM: _CHAN_GROUP})]


# --- the S7 numeric-presets quick-set widget (K7 set_scalar) -----------------------
#
# `xp.xp_cooldown` is a NON-HUB group numeric-presets scalar (value_type=int,
# default=60, input_hint="numeric_presets", presets=(0,15,30,60,120,300)) — the
# concrete port target. It is `int`-typed, so before S7 it MISROUTED to the S3
# number modal (`_is_number_spec` matches int); the S7 arm intercepts
# input_hint=="numeric_presets" BEFORE the number check so it opens the quick-set
# buttons instead. Clicking a preset commits its fixed value through the same K7
# settings.set_scalar lane (the index rides session_action; the value is
# re-derived from the spec's presets tuple, never the wire).

_PRESET_GROUP = "xp"
_PRESET_SETTING = "xp_cooldown"
_PRESETS = (0, 15, 30, 60, 120, 300)


def _render_override(spec, ctx):
    """Drive the presets renderer override (the engine calls it via the
    render_group_edit_presets handler ref)."""
    from sb.domain.settings.panels import _render_group_edit_presets

    return run(_render_group_edit_presets(spec, ctx))


class TestPresetsWidgetFrame:
    def test_presets_spec_compiles_and_is_a_session_view(self):
        from sb.domain.settings.panels import settings_group_edit_presets_spec
        from sb.kernel.panels.compile import check_panel
        from sb.spec.panels import Audience, FooterMode
        from sb.spec.refs import HandlerRef

        spec = settings_group_edit_presets_spec()
        check_panel(spec)
        assert spec.panel_id == "settings.group_edit_presets"
        assert spec.audience is Audience.INVOKER
        assert spec.frame.footer_mode is FooterMode.NONE
        assert spec.session_lifecycle is True
        # the widget is BUTTONS (no selectors) — the quick-set posture.
        assert spec.selectors == ()
        by_act = {a.action_id: a for a in spec.actions}
        # every preset slot dispatches to the presets-pick handler.
        assert (by_act["pval_0"].handler
                == HandlerRef("settings.group_edit_presets_pick"))
        assert (by_act["presets_back"].handler
                == HandlerRef("settings.group_edit_presets_back"))

    def test_all_declared_presets_render_as_buttons(self):
        """The regression the S7 slice pins: one quick-set button per declared
        preset value (label == the preset), surplus slots dropped, the current
        value marked primary, Back kept."""
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
            settings_group_edit_presets_spec,
        )

        spec = settings_group_edit_presets_spec()
        # current == the declared default (60) — the DM/no-resolver path.
        ctx = _ctx(**{GROUP_EDIT_PARAM: _PRESET_GROUP,
                      GROUP_EDIT_SETTING_PARAM: _PRESET_SETTING})
        ctx = SimpleNamespace(**{**ctx.__dict__, "guild_id": None})
        rendered = _render_override(spec, ctx)
        buttons = [c for c in rendered.components if c.kind == "button"]
        preset_btns = [c for c in buttons
                       if c.custom_id.rsplit(".", 1)[-1].startswith("pval_")]
        # exactly one button per declared preset — no surplus slots.
        assert len(preset_btns) == len(_PRESETS)
        assert [c.label for c in preset_btns] == [str(v) for v in _PRESETS]
        # the current value (default 60) is marked primary; the rest secondary.
        primary = [c for c in preset_btns if c.style == "primary"]
        assert len(primary) == 1 and primary[0].label == "60"
        # Back survives the override.
        assert any(c.custom_id.endswith("presets_back") for c in buttons)

    def test_presets_fields_show_current_default_and_roster(self):
        from sb.domain.settings import panels

        fields = run(panels._group_edit_presets_fields(_ctx(
            **{panels.GROUP_EDIT_PARAM: _PRESET_GROUP,
               panels.GROUP_EDIT_SETTING_PARAM: _PRESET_SETTING})))
        body = fields[0][1]
        assert "default = `60`" in body
        assert "`300`" in body                       # the roster is listed
        assert "type = `int`" in body

    def test_presets_fields_degrade_on_an_expired_session(self):
        from sb.domain.settings import panels

        fields = run(panels._group_edit_presets_fields(_ctx()))
        assert "session expired" in fields[0][1]

    def test_render_override_drops_all_slots_for_a_non_presets_spec(self):
        """A stranded render (no group/setting) drops every preset slot — only
        Back stands, the honest degrade (never a wall of placeholder buttons)."""
        from sb.domain.settings.panels import settings_group_edit_presets_spec

        spec = settings_group_edit_presets_spec()
        rendered = _render_override(spec, _ctx())     # empty params
        preset_btns = [c for c in rendered.components
                       if c.kind == "button"
                       and c.custom_id.rsplit(".", 1)[-1].startswith("pval_")]
        assert preset_btns == []


class TestPresetsDispatchAndCommit:
    def _pick_req(self, name, *, group=_PRESET_GROUP):
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        return _Req(args={GROUP_EDIT_PARAM: group, "values": (name,)})

    def _commit_req(self, slot, *, group=_PRESET_GROUP, name=_PRESET_SETTING):
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        return _Req(args={GROUP_EDIT_PARAM: group,
                          GROUP_EDIT_SETTING_PARAM: name,
                          "session_action": slot})

    def test_presets_pick_opens_the_buttons_not_the_number_modal(
            self, monkeypatch):
        """THE S7 REGRESSION: `xp.xp_cooldown` is an `int` with
        input_hint="numeric_presets"; before S7 the value_type dispatch matched
        _is_number_spec and misrouted it to the S3 number modal. The presets arm
        now intercepts the hint FIRST, so it opens the quick-set buttons."""
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import (
            GROUP_EDIT_PARAM,
            GROUP_EDIT_SETTING_PARAM,
        )

        reply = run(_handler("settings.group_edit_pick")(
            self._pick_req(_PRESET_SETTING)))
        assert reply is None                         # open_panel took over
        # the presets widget — NOT settings.group_edit_number.
        assert [name for name, _ in opened] == ["settings.group_edit_presets"]
        args = opened[0][1]
        assert args[GROUP_EDIT_PARAM] == _PRESET_GROUP
        assert args[GROUP_EDIT_SETTING_PARAM] == _PRESET_SETTING

    def test_preset_click_persists_the_fixed_value(self, monkeypatch):
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # click slot pval_2 → presets[2] == 30.
        reply = run(_handler("settings.group_edit_presets_pick")(
            self._commit_req("pval_2")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": ksettings.persisted_key(
                              _PRESET_GROUP, _PRESET_SETTING),
                           "value": "30"})]
        assert "set to **30**" in reply.user_message

    def test_preset_click_value_is_derived_from_the_spec_not_the_wire(
            self, monkeypatch):
        """The index rides session_action but the VALUE is re-read from the
        spec's presets tuple — a first-slot click writes presets[0], never a
        wire-supplied number."""
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        reply = run(_handler("settings.group_edit_presets_pick")(
            self._commit_req("pval_0")))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.set_scalar",
                          {"key": ksettings.persisted_key(
                              _PRESET_GROUP, _PRESET_SETTING),
                           "value": "0"})]           # presets[0] == 0

    def test_preset_click_rejects_an_out_of_range_slot_without_a_write(
            self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # pval_9 is a declared slot but xp_cooldown declares only 6 presets.
        reply = run(_handler("settings.group_edit_presets_pick")(
            self._commit_req("pval_9")))
        assert reply.outcome == BLOCKED
        assert calls == []                           # no write for a stale slot
        assert "no longer available" in reply.user_message

    def test_preset_click_rejects_a_non_presets_setting(self, monkeypatch):
        from sb.spec.outcomes import BLOCKED

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # warn_threshold is a plain int (no presets hint) — not presets-shaped.
        reply = run(_handler("settings.group_edit_presets_pick")(
            self._commit_req("pval_0", group="moderation",
                             name="warn_threshold")))
        assert reply.outcome == BLOCKED
        assert calls == []
        assert "not a numeric-presets" in reply.user_message

    def test_presets_reset_clears_through_clear_scalar(self, monkeypatch):
        from sb.kernel import settings as ksettings
        from sb.spec.outcomes import SUCCESS
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        calls = _patch_scalar_run(monkeypatch)
        _patch_refresh(monkeypatch)

        # reset rides the shared type-agnostic S0 reset select (clear_scalar).
        reply = run(_handler("settings.group_edit_reset")(
            _Req(args={GROUP_EDIT_PARAM: _PRESET_GROUP,
                       "values": (_PRESET_SETTING,)})))
        assert reply.outcome == SUCCESS
        assert calls == [("settings.clear_scalar",
                          {"key": ksettings.persisted_key(
                              _PRESET_GROUP, _PRESET_SETTING)})]

    def test_presets_back_reopens_the_group_edit_page(self, monkeypatch):
        opened = _patch_open_panel(monkeypatch)
        from sb.domain.settings.panels import GROUP_EDIT_PARAM

        reply = run(_handler("settings.group_edit_presets_back")(
            _Req(args={GROUP_EDIT_PARAM: _PRESET_GROUP})))
        assert reply is None
        assert opened == [("settings.group_edit",
                           {GROUP_EDIT_PARAM: _PRESET_GROUP})]
