"""Curation rework 2026-07-13 — the utility panel's 📊 Poll and
🔔 Remind Me buttons arm via G-10 modal ingress (evidence:
docs/review/curation-report-2026-07-13.md REWORK rows for
utility.panel.poll + utility.panel.remind).

The shipped cog opened modals for both tools; the rework restores that
shape declaratively: each button carries a ModalSpec whose submit
handler normalizes the form fields into the SAME outcome lane the live
prefix twin runs (`!poll` → utility.poll_view, `!remind` →
utility.remind_view — the shared `_poll_outcome`/`_remind_outcome`
helpers in sb/domain/utility/handlers.py). The retired terminals
(`utility.poll_pending`, `utility.remind_pending`) must stay gone. The
swap is byte-neutral on the panel-open wire: labels/styles stay exactly
as goldens/utility/sweep_utilitymenu + sweep_slash_utility pin them
(session panels mint <cid:N> ids; defer_mode/modal are server-side).
"""

from __future__ import annotations

import asyncio
import dataclasses

run = asyncio.run


@dataclasses.dataclass
class _Req:
    """Minimal dataclass request — `_open_with` drives
    ``dataclasses.replace(req, args=...)``, so SimpleNamespace won't do."""

    args: dict
    guild_id: int = 1
    channel_id: int = 1


def _resolve(name: str):
    from sb.domain.utility import handlers  # noqa: F401 — registers refs
    from sb.spec.refs import HandlerRef, resolve

    handlers.ensure_handler_refs()
    return resolve(HandlerRef(name))


# --- the spec: modal ingress on golden-pinned button bytes ------------------------


def test_poll_and_remind_buttons_open_the_modals():
    from sb.spec.outcomes import DeferMode
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import HandlerRef
    from sb.domain.utility.panels import (
        POLL_MODAL,
        REMIND_MODAL,
        utility_panel_spec,
    )

    by_id = {a.action_id: a for a in utility_panel_spec().actions}

    assert by_id["poll"].defer_mode is DeferMode.MODAL
    assert by_id["poll"].modal is POLL_MODAL
    assert by_id["poll"].handler == HandlerRef("utility.poll_submit")
    assert POLL_MODAL.on_submit == HandlerRef("utility.poll_submit")

    assert by_id["remind"].defer_mode is DeferMode.MODAL
    assert by_id["remind"].modal is REMIND_MODAL
    assert by_id["remind"].handler == HandlerRef("utility.remind_submit")
    assert REMIND_MODAL.on_submit == HandlerRef("utility.remind_submit")

    # the golden-pinned wire bytes survive verbatim (sweep_utilitymenu +
    # sweep_slash_utility): label/style unchanged, emoji stays IN-label,
    # no custom_id_override grew (rows 0-2 mint session <cid:N> ids).
    for aid, label in (("poll", "📊 Poll"), ("remind", "🔔 Remind Me")):
        assert by_id[aid].label == label
        assert by_id[aid].style is ActionStyle.SECONDARY
        assert by_id[aid].emoji == ""
        assert by_id[aid].custom_id_override == ""


def test_modal_field_ids_feed_the_submit_lanes():
    from sb.spec.panels import ModalFieldStyle
    from sb.domain.utility.panels import POLL_MODAL, REMIND_MODAL

    assert POLL_MODAL.modal_id == "utility.poll_form"
    assert [f.field_id for f in POLL_MODAL.fields] == ["question", "options"]
    assert all(f.required for f in POLL_MODAL.fields)
    # options collect one-per-line — the PARAGRAPH input.
    assert POLL_MODAL.fields[1].style is ModalFieldStyle.PARAGRAPH

    assert REMIND_MODAL.modal_id == "utility.remind_form"
    assert [f.field_id for f in REMIND_MODAL.fields] == ["minutes", "message"]
    assert all(f.required for f in REMIND_MODAL.fields)


def test_panel_spec_passes_the_compile_fences():
    from sb.kernel.panels.compile import check_panel
    from sb.domain.utility.panels import utility_panel_spec

    check_panel(utility_panel_spec())  # raises PanelCompileError on drift


def test_layout_rows_stay_the_golden_shape():
    from sb.domain.utility.panels import utility_panel_spec

    assert utility_panel_spec().layout.pages[0].rows == (
        ("server_info", "user_info", "avatar"),
        ("poll", "remind", "invite"),
        ("utility_overview",),
        ("open_general", "open_four_twenty"),
    )


# --- the refs: submits registered, retired terminals stay gone --------------------


def test_submit_refs_registered_and_pendings_stay_retired():
    from sb.domain.utility import handlers, panels
    from sb.spec.refs import HandlerRef, is_registered

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    for name in ("utility.poll_view", "utility.poll_submit",
                 "utility.remind_view", "utility.remind_submit"):
        assert is_registered(HandlerRef(name)), name
    # a re-registration means a regression re-parked the live surfaces.
    for name in ("utility.poll_pending", "utility.remind_pending"):
        assert not is_registered(HandlerRef(name)), name


# --- remind: the modal submit rides the command twin's lane -----------------------


def test_remind_submit_matches_the_command_twin():
    from sb.spec.outcomes import SUCCESS

    via_modal = run(_resolve("utility.remind_submit")(
        _Req({"minutes": "5", "message": "drink water"})))
    via_command = run(_resolve("utility.remind_view")(
        _Req({"argv": ("5", "drink", "water")})))
    assert via_modal.outcome == SUCCESS
    assert via_command.outcome == SUCCESS
    # byte-identical ack — the golden-pinned `!remind` copy
    # (goldens/utility/sweep_remind).
    assert via_modal.user_message == via_command.user_message == (
        "⏳ Reminder set for **5** minute(s): drink water")


def test_remind_malformed_duration_matches_the_command_copy():
    from sb.spec.outcomes import BLOCKED

    via_modal = run(_resolve("utility.remind_submit")(
        _Req({"minutes": "soon", "message": "hi"})))
    via_command = run(_resolve("utility.remind_view")(
        _Req({"argv": ("soon", "hi")})))
    for reply in (via_modal, via_command):
        assert reply.outcome == BLOCKED
        # the shipped int-converter raise → bot1.py's generic envelope.
        assert reply.user_message == (
            "⚠️ An unexpected error occurred. Please try again.")


def test_remind_zero_minutes_opens_the_shipped_error_card(monkeypatch):
    import sb.kernel.panels.engine as engine
    from sb.spec.outcomes import BLOCKED

    opened: list[tuple[str, str]] = []

    async def fake_open(ref, req):
        opened.append((ref.name, str(req.args.get("error_text"))))

    monkeypatch.setattr(engine, "open_panel", fake_open)
    via_modal = run(_resolve("utility.remind_submit")(
        _Req({"minutes": "0", "message": "hi"})))
    via_command = run(_resolve("utility.remind_view")(
        _Req({"argv": ("0", "hi")})))
    for reply in (via_modal, via_command):
        assert reply.outcome == BLOCKED
        assert reply.user_message is None      # the red card carries the copy
    assert opened == [
        ("utility.error_card",
         "Please specify a time greater than 0 minutes."),
    ] * 2


def test_remind_blank_message_matches_the_command_copy():
    from sb.spec.outcomes import BLOCKED

    # Discord marks the field required, but the handler still guards the
    # whitespace-only submit with the command twin's copy (`!remind 5`).
    via_modal = run(_resolve("utility.remind_submit")(
        _Req({"minutes": "5", "message": "   "})))
    via_command = run(_resolve("utility.remind_view")(
        _Req({"argv": ("5",)})))
    for reply in (via_modal, via_command):
        assert reply.outcome == BLOCKED
        assert reply.user_message == (
            "⚠️ An unexpected error occurred. Please try again.")


# --- poll: the modal submit rides the command twin's lane -------------------------


def test_poll_submit_valid_matches_the_command_refusal():
    from sb.spec.outcomes import BLOCKED

    # the LIVE `!poll` lane today: guards pass, then the honest
    # reaction-egress refusal — the modal produces EXACTLY that (no new
    # egress capability rides in with the rework).
    via_modal = run(_resolve("utility.poll_submit")(
        _Req({"question": "Lunch?", "options": "Pizza\nSushi"})))
    via_command = run(_resolve("utility.poll_view")(
        _Req({"argv": ("Lunch?", "Pizza", "Sushi")})))
    for reply in (via_modal, via_command):
        assert reply.outcome == BLOCKED
        assert reply.user_message == (
            "📊 Poll creation needs the reaction egress port "
            "(arms with the live adapter).")


def test_poll_too_few_options_opens_the_golden_error_card(monkeypatch):
    import sb.kernel.panels.engine as engine
    from sb.spec.outcomes import BLOCKED

    opened: list[tuple[str, str]] = []

    async def fake_open(ref, req):
        opened.append((ref.name, str(req.args.get("error_text"))))

    monkeypatch.setattr(engine, "open_panel", fake_open)
    # one option, blank-line noise, and none at all — every shape lands on
    # the golden-pinned copy (goldens/utility/sweep_poll's red envelope).
    for options in ("Pizza", "\n  \nPizza\n", ""):
        reply = run(_resolve("utility.poll_submit")(
            _Req({"question": "Lunch?", "options": options})))
        assert reply.outcome == BLOCKED
        assert reply.user_message is None
    via_command = run(_resolve("utility.poll_view")(
        _Req({"argv": ("test", "test")})))
    assert via_command.outcome == BLOCKED
    assert opened == [
        ("utility.error_card", "You need at least two options for a poll."),
    ] * 4


def test_poll_too_many_options_opens_the_shipped_error_card(monkeypatch):
    import sb.kernel.panels.engine as engine
    from sb.spec.outcomes import BLOCKED

    opened: list[tuple[str, str]] = []

    async def fake_open(ref, req):
        opened.append((ref.name, str(req.args.get("error_text"))))

    monkeypatch.setattr(engine, "open_panel", fake_open)
    eleven = "\n".join(f"option{i}" for i in range(11))
    via_modal = run(_resolve("utility.poll_submit")(
        _Req({"question": "Lunch?", "options": eleven})))
    via_command = run(_resolve("utility.poll_view")(
        _Req({"argv": ("Lunch?",) + tuple(f"o{i}" for i in range(11))})))
    for reply in (via_modal, via_command):
        assert reply.outcome == BLOCKED
        assert reply.user_message is None
    assert opened == [
        ("utility.error_card", "You can only provide up to 10 options."),
    ] * 2


def test_poll_blank_question_matches_the_bare_command():
    from sb.spec.outcomes import BLOCKED

    via_modal = run(_resolve("utility.poll_submit")(
        _Req({"question": "   ", "options": "a\nb"})))
    via_command = run(_resolve("utility.poll_view")(_Req({"argv": ()})))
    for reply in (via_modal, via_command):
        assert reply.outcome == BLOCKED
        # the shipped MissingRequiredArgument → generic envelope.
        assert reply.user_message == (
            "⚠️ An unexpected error occurred. Please try again.")
