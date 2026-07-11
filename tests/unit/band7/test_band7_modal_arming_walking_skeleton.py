"""Band 7 — the ORDER-004 walking-skeleton drive for the MODAL-ARMING slice:
boot the replay composition root (DB-free) and drive the G-10 form
round-trip through the REAL pipeline — settings pick → text widget page →
Edit…/Override… click ISSUES the declared form (the modal-issued terminal,
wire type 9) → the wire-type-5 SUBMIT re-enters through the frozen modal
adapter (``dispatch_modal``, the seam the live component feed's armed lane
drives) with the kernel-stashed opening args restored — asserting the
shipped bytes (views/settings/edit_text.py TextSettingModal +
edit_number.py NumberSettingModal + edit_number_presets._OverrideButton
@7f7628e1).

The WRITE legs (settings.set_scalar — DB + audit in one transaction) ride
the live drive with real Postgres; here the workflow engine seam is
recorded so the suite stays DB-free like its band-7 siblings, while the
submit → handler → ack path is the real spine end-to-end.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture()
def skeleton():
    from sb.adapters.parity.boot import Harness
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    yield h
    run(h.close())


@pytest.fixture()
def engine_recorder(monkeypatch):
    """Record settings.set_scalar invocations DB-free: the write lane's
    engine seam answers SUCCESS (optionally with an in-transaction prior)
    while the whole submit → adapter → resolve() → handler path stays
    real."""
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls: list = []
    prior: dict = {}

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before=dict(prior))

    monkeypatch.setattr(engine, "run", fake_run)
    return SimpleNamespace(calls=calls, prior=prior)


def _panel_payload(calls):
    assert [c.method for c in calls] == ["interaction_response",
                                         "followup_send"]
    return calls[1].payload


def _open_settings(skeleton):
    run(skeleton.send_command("!ai settings", persona="admin"))
    calls = skeleton.take_calls()
    payload = calls[0].payload
    selects = [c["custom_id"] for row in payload["components"]
               for c in row["components"] if c.get("type") == 3]
    assert len(selects) == 2
    return payload, selects[0], selects[1]


def _open_widget(skeleton, setting: str, *, message_id: int):
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=message_id, custom_id=edit_cid,
                       component_type=3, values=[setting], persona="admin"))
    return _panel_payload(skeleton.take_calls())


def _button(payload, label: str) -> str:
    return next(c["custom_id"] for row in payload["components"]
                for c in row["components"] if c.get("label") == label)


# --- the form ISSUE (G-10: the click answers with the modal, never a dispatch) ----


def test_text_edit_click_issues_the_text_form(skeleton, engine_recorder):
    payload = _open_widget(skeleton, "ai_default_model", message_id=910)
    run(skeleton.click(message_id=911, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["interaction_response"]
    assert calls[0].payload["type"] == 9
    assert calls[0].payload["data"]["custom_id"] == "ai.settings_text_form"
    assert engine_recorder.calls == []       # the open NEVER dispatches


# --- the SUBMIT re-entry (wire type 5 → modal adapter → resolve() → write) --------


def test_text_submit_writes_and_speaks_shipped_ack(skeleton, engine_recorder):
    """TextSettingModal.on_submit's ack, verbatim: ``✅ Updated
    `ai.<key>` = `<new>`.`` (no "(was …)" on the text form) — the
    `setting` param arrives through the kernel modal-args stash."""
    payload = _open_widget(skeleton, "ai_guild_instruction_profile",
                           message_id=912)
    run(skeleton.click(message_id=913, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=913,
                              custom_id="ai.settings_text_form",
                              fields={"new_value": "focused_helper"},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        "✅ Updated `ai.ai_guild_instruction_profile` = `'focused_helper'`.")
    (op_name, params), = engine_recorder.calls
    assert op_name == "settings.set_scalar"
    assert params["key"] == "ai_guild_instruction_profile"
    assert params["value"] == "focused_helper"
    assert params["subsystem"] == "ai"


def test_text_submit_empty_writes_empty_string(skeleton, engine_recorder):
    """The shipped optional input: an empty submit writes '' ("empty =
    routing default")."""
    payload = _open_widget(skeleton, "ai_default_model", message_id=914)
    run(skeleton.click(message_id=915, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=915,
                              custom_id="ai.settings_text_form",
                              fields={"new_value": ""}, persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        "✅ Updated `ai.ai_default_model` = `''`.")
    (_, params), = engine_recorder.calls
    assert params["value"] == ""


def test_override_submit_writes_with_in_transaction_prior(skeleton,
                                                          engine_recorder):
    """NumberSettingModal.on_submit's ack, verbatim: ``✅ Updated
    `ai.<key>` = `<new>` (was `<old>`).`` — the prior derives from the
    write leg's IN-TRANSACTION LegOutcome.before (the #160 codex-P3
    posture, shared by the armed free-form write)."""
    engine_recorder.prior["write_scalar"] = {"value": "120"}
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=916, custom_id=edit_cid, component_type=3,
                       values=["ai_cooldown_seconds"], persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    run(skeleton.click(message_id=917,
                       custom_id=_button(payload, "Override…"),
                       persona="admin"))
    skeleton.take_calls()                     # the type-9 issue
    run(skeleton.modal_submit(message_id=917,
                              custom_id="ai.settings_number_form",
                              fields={"new_value": " 45 "},   # shipped .strip()
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        "✅ Updated `ai.ai_cooldown_seconds` = `45` (was `120`).")
    (_, params), = engine_recorder.calls
    assert params["key"] == "ai_cooldown_seconds"
    assert params["value"] == "45"


def test_override_submit_refuses_uncoercible_value(skeleton, engine_recorder):
    """The shipped coercion refusal (SettingsCoercionError's sentence body
    on the #160-ledgered K7 envelope form) — refused BEFORE any write."""
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=918, custom_id=edit_cid, component_type=3,
                       values=["ai_minimum_level_default"], persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    run(skeleton.click(message_id=919,
                       custom_id=_button(payload, "Override…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=919,
                              custom_id="ai.settings_number_form",
                              fields={"new_value": "banana"},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "❌ Couldn't update `ai.ai_minimum_level_default`: cannot coerce "
        "value='banana' to int")
    assert engine_recorder.calls == []


def test_override_submit_refuses_out_of_bounds_value(skeleton,
                                                     engine_recorder):
    """bounds ride the same coercer the read path uses (the declared
    (0, 86400) cooldown bounds) — refused before any write."""
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=920, custom_id=edit_cid, component_type=3,
                       values=["ai_cooldown_seconds"], persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    run(skeleton.click(message_id=921,
                       custom_id=_button(payload, "Override…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=921,
                              custom_id="ai.settings_number_form",
                              fields={"new_value": "999999"},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "❌ Couldn't update `ai.ai_cooldown_seconds`: cannot coerce "
        "value='999999' to int")
    assert engine_recorder.calls == []


def test_submit_without_open_hits_unknown_setting_guard(skeleton,
                                                        engine_recorder):
    """A stash miss (restart / eviction / a form the kernel never issued):
    the submit carries only its field values, so the handler's own guard
    answers — no write."""
    run(skeleton.modal_submit(message_id=922,
                              custom_id="ai.settings_number_form",
                              fields={"new_value": "5"}, persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == "❌ Unknown setting `ai.`."
    assert engine_recorder.calls == []


def test_submit_authority_re_resolves_on_the_modal_surface(skeleton,
                                                           engine_recorder):
    """K6 re-resolves on the SUBMIT re-entry (surface=MODAL): a plain
    member driving the raw wire bytes is refused before any write —
    the form's static custom_id grants nothing."""
    payload = _open_widget(skeleton, "ai_default_model", message_id=923)
    run(skeleton.click(message_id=924, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=924,
                              custom_id="ai.settings_text_form",
                              fields={"new_value": "sneaky"},
                              persona="member"))
    calls = skeleton.take_calls()
    assert engine_recorder.calls == []        # refused before any write
    assert "✅" not in (calls[-1].payload.get("content") or "")


# --- the kernel stash (the confirm-args-stash twin, pure) --------------------------


def test_modal_args_stash_pops_once_per_user_and_origin():
    from sb.kernel.interaction.resolve import (
        _pending_modal_args,
        pop_modal_args,
    )

    _pending_modal_args[("ai.settings_number_form", 7, "901")] = {
        "setting": "x"}
    # keyed per originating message: another message's submit misses.
    assert pop_modal_args("ai.settings_number_form", 7, "902") == {}
    assert pop_modal_args("ai.settings_number_form", 7,
                          "901") == {"setting": "x"}
    assert pop_modal_args("ai.settings_number_form", 7, "901") == {}  # popped
    assert pop_modal_args("ai.settings_number_form", None, "901") == {}


def test_two_concurrent_opens_stay_isolated(skeleton, engine_recorder):
    """codex P2 on this PR (verified real): the same user with the SAME
    static form open from TWO panel pages (two clients / two channels) —
    submitting the OLDER form must write ITS setting, never the newer
    open's (the shipped per-instance modal custom_ids carried per-open
    closure state; the stash's originating-message key is the twin)."""
    # open 1: Override… on the ai_cooldown_seconds presets page.
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=930, custom_id=edit_cid, component_type=3,
                       values=["ai_cooldown_seconds"], persona="admin"))
    page_a = _panel_payload(skeleton.take_calls())
    run(skeleton.click(message_id=931,
                       custom_id=_button(page_a, "Override…"),
                       persona="admin"))
    skeleton.take_calls()
    # open 2 (same user, same form id): Override… on the
    # ai_minimum_level_default presets page — must NOT clobber open 1.
    run(skeleton.click(message_id=932, custom_id=edit_cid, component_type=3,
                       values=["ai_minimum_level_default"], persona="admin"))
    page_b = _panel_payload(skeleton.take_calls())
    run(skeleton.click(message_id=933,
                       custom_id=_button(page_b, "Override…"),
                       persona="admin"))
    skeleton.take_calls()
    # submit the OLDER form (message 931) — writes ai_cooldown_seconds.
    run(skeleton.modal_submit(message_id=931,
                              custom_id="ai.settings_number_form",
                              fields={"new_value": "60"}, persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "✅ Updated `ai.ai_cooldown_seconds` = `60`")
    # the newer open's stash is untouched — its submit still writes ITS key.
    run(skeleton.modal_submit(message_id=933,
                              custom_id="ai.settings_number_form",
                              fields={"new_value": "3"}, persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "✅ Updated `ai.ai_minimum_level_default` = `3`")
    assert [(params["key"]) for _, params in engine_recorder.calls] == [
        "ai_cooldown_seconds", "ai_minimum_level_default"]


def test_failed_form_open_never_dispatches():
    """G-10: the handler runs on submit, never on open — an open_modal
    fault terminates as an unissued form (with the live wire-type-5 lane
    armed, the old fallthrough would have run the submit handler with no
    form data)."""
    from sb.kernel.interaction.request import (
        ActorRef,
        ResolveRequest,
        Surface,
        TargetRef,
    )
    from sb.kernel.interaction.resolve import resolve
    from sb.spec.outcomes import DeferMode, SUCCESS
    from sb.spec.panels import ModalFieldSpec, ModalSpec, PanelActionSpec
    from sb.spec.refs import HandlerRef, handler, is_registered

    ref_name = "band7.modal_arming_never_dispatches"
    dispatched: list = []
    if not is_registered(HandlerRef(ref_name)):
        @handler(ref_name)
        async def _h(req):  # pragma: no cover — must never run
            dispatched.append(req)
            return None

    spec = PanelActionSpec(
        action_id="edit", label="Edit…", defer_mode=DeferMode.MODAL,
        handler=HandlerRef(ref_name),
        modal=ModalSpec(modal_id="band7.broken_form", title="Edit",
                        fields=(ModalFieldSpec(field_id="v", label="v"),)))

    class BrokenResponder:
        surface = Surface.COMPONENT

        def is_acked(self):
            return False

        def committed_visibility(self):
            return None

        async def ack(self, *, ephemeral):
            return None

        async def deny(self, message, *, ephemeral):
            return None

        async def open_modal(self, modal_ref):
            raise RuntimeError("send_modal exploded")

        async def render(self, result):
            return None

    req = ResolveRequest(
        surface=Surface.COMPONENT,
        target=TargetRef(key="band7.panel.edit", spec=spec),
        actor=ActorRef(user_id=1, is_guild_operator=True,
                       is_bot_owner=True, is_dm=False,
                       member_tier="administrator"),
        guild_id=1, channel_id=1, args={}, responder=BrokenResponder(),
        origin=None)
    result = run(resolve(req))
    assert result.outcome == SUCCESS          # the modal-issued terminal
    assert dispatched == []                   # …and NOTHING dispatched
