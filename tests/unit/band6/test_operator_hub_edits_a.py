"""Operator-hub edits slice A (ORDER 017 item 1, Top-gaps 6 — the
EDIT-controls family; the read-only nav slice is peer-claimed):

* utility.panel — 📊 Poll / 🔔 Remind Me are G-10 modal ingresses over
  the LIVE command-twin lanes (utility_cog `_PollModal`/`_RemindModal`,
  copy verbatim); 🍃 420 forwards to the PORTED `four_twenty.overview`.
* role.hub — 📝 Create opens the shipped `RoleCreateModal`
  (views/roles/creation_panel.py, name+colour) over the live
  `!createrole` lane (provisioning port + audit/lifecycle companions).
* counters — argful `!counterpreset <name>` APPLIES the curated preset:
  the shipped three audited template writes (counter_config
  `preset_setting_writes` order) through `settings.set_scalar`, the
  shipped ack/refusal copy verbatim.

Golden safety: the bare opens of utility.panel / role.hub and the bare
`!counterpreset` list card keep their pinned bytes — no label, style,
layout row or custom_id changed (asserted on the specs below).
"""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

run = asyncio.run


def _handler(name: str):
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    return resolve_ref(HandlerRef(name))


@dataclasses.dataclass
class Req:
    args: dict
    guild_id: int | None = 42
    channel_id: int | None = 7
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(default_factory=lambda: SimpleNamespace(
        user_id=7, member_tier="administrator"))


# --- utility.panel: the Poll / Remind modal ingress -------------------------------


def test_utility_poll_and_remind_are_modal_ingresses_over_live_lanes():
    """The moderation.hub.warn precedent: button → declared ModalSpec →
    the live lane; titles/labels/caps are utility_cog verbatim."""
    from sb.domain.utility.panels import utility_panel_spec
    from sb.spec.panels import DeferMode
    from sb.spec.refs import HandlerRef

    spec = utility_panel_spec()
    actions = {a.action_id: a for a in spec.actions}

    poll = actions["poll"]
    assert poll.defer_mode is DeferMode.MODAL
    assert poll.modal is not None
    assert poll.modal.modal_id == "utility.poll_form"
    assert poll.modal.title == "Create Poll"          # oracle verbatim
    assert [f.field_id for f in poll.modal.fields] == ["question", "options"]
    assert poll.modal.fields[0].label == "Poll question"
    assert poll.modal.fields[0].max_length == 200
    assert poll.modal.fields[1].label == "Options (one per line, 2–10)"
    assert poll.modal.fields[1].max_length == 500
    assert poll.modal.on_submit == HandlerRef("utility.poll_form_submit")

    remind = actions["remind"]
    assert remind.defer_mode is DeferMode.MODAL
    assert remind.modal is not None
    assert remind.modal.modal_id == "utility.remind_form"
    assert remind.modal.title == "Set Reminder"       # oracle verbatim
    assert [f.field_id for f in remind.modal.fields] == ["minutes", "message"]
    assert remind.modal.on_submit == HandlerRef("utility.remind_form_submit")


def test_utility_panel_bare_open_bytes_unchanged():
    """Golden safety (sweep_utilitymenu): labels, styles, layout rows and
    the persistent forwarding ids all keep the pinned bytes."""
    from sb.domain.utility.panels import utility_panel_spec

    spec = utility_panel_spec()
    actions = {a.action_id: a for a in spec.actions}
    assert actions["poll"].label == "📊 Poll"
    assert actions["remind"].label == "🔔 Remind Me"
    assert actions["invite"].label == "🔗 Invite"
    assert actions["open_four_twenty"].custom_id_override == (
        "utility:open:four_twenty")
    assert spec.layout.pages[0].rows == (
        ("server_info", "user_info", "avatar"),
        ("poll", "remind", "invite"),
        ("utility_overview",),
        ("open_general", "open_four_twenty"),
    )


def test_utility_420_child_forwards_to_the_ported_panel():
    from sb.domain.utility.panels import utility_panel_spec
    from sb.spec.refs import PanelRef

    spec = utility_panel_spec()
    actions = {a.action_id: a for a in spec.actions}
    assert actions["open_four_twenty"].handler == PanelRef(
        "four_twenty.overview")
    assert actions["open_general"].handler == PanelRef("general.menu")
    # the ported target is registered — the forward can never land on a
    # RefUnresolved envelope.
    import sb.manifest.four_twenty as ft

    ft.ENSURE_REFS()
    from sb.spec.refs import is_registered

    assert is_registered(PanelRef("four_twenty.overview"))


def test_poll_form_submit_guards_and_honest_refusal():
    """The shipped `_PollModal.on_submit` copy verbatim; the success lane
    stays the reaction-egress honest refusal (the command twin's)."""
    import sb.manifest.utility as m

    m.ENSURE_REFS()
    from sb.spec.outcomes import BLOCKED

    submit = _handler("utility.poll_form_submit")
    one = run(submit(Req(args={"question": "Best fruit?",
                               "options": "apples"})))
    assert one.outcome == BLOCKED
    assert one.user_message == "❌ Need at least 2 options."

    eleven = run(submit(Req(args={
        "question": "q", "options": "\n".join(f"o{i}" for i in range(11))})))
    assert eleven.outcome == BLOCKED
    assert eleven.user_message == "❌ Max 10 options."

    ok = run(submit(Req(args={"question": "q",
                              "options": "apples\n\n  pears  \n"})))
    assert ok.outcome == BLOCKED
    assert "reaction egress port" in ok.user_message


def test_remind_form_submit_guards_and_ack():
    """The shipped `_RemindModal.on_submit` copy verbatim — the ack is
    the live `!remind` twin's byte."""
    import sb.manifest.utility as m

    m.ENSURE_REFS()
    from sb.spec.outcomes import BLOCKED, SUCCESS

    submit = _handler("utility.remind_form_submit")
    for bad in ("nope", "0", "-5", ""):
        reply = run(submit(Req(args={"minutes": bad, "message": "hi"})))
        assert reply.outcome == BLOCKED
        assert reply.user_message == "❌ Minutes must be a positive integer."

    ok = run(submit(Req(args={"minutes": " 30 ", "message": "drink water"})))
    assert ok.outcome == SUCCESS
    assert ok.user_message == "⏳ Reminder set for **30** minute(s): drink water"


def test_utility_retired_pendings_are_gone_invite_stays():
    """The poll/remind/420 pending terminals are retired; Invite's stays
    (peer PR #332 wires it — this slice must not touch it)."""
    import importlib

    import sb.domain.utility.handlers as h

    importlib.reload(h)
    from sb.spec.refs import HandlerRef, is_registered

    assert is_registered(HandlerRef("utility.invite_pending"))
    assert is_registered(HandlerRef("utility.poll_form_submit"))
    assert is_registered(HandlerRef("utility.remind_form_submit"))
    src = open(h.__file__, encoding="utf-8").read()
    assert 'pending_handler("utility.poll_pending"' not in src
    assert 'pending_handler("utility.remind_pending"' not in src
    assert 'pending_handler("utility.four_twenty_pending"' not in src


# --- role.hub: the Create modal over the live createrole lane ---------------------


def test_role_create_button_is_the_shipped_modal_ingress():
    from sb.domain.role.panels import ROLE_CREATE_MODAL, role_hub_spec
    from sb.spec.panels import DeferMode
    from sb.spec.refs import HandlerRef

    spec = role_hub_spec()
    create = {a.action_id: a for a in spec.actions}["role_create"]
    # golden safety (sweep_rolemenu): label/style/custom_id unchanged.
    assert create.label == "📝 Create"
    assert create.custom_id_override == "role:create"
    assert create.defer_mode is DeferMode.MODAL
    assert create.modal is ROLE_CREATE_MODAL
    # oracle-verbatim form (views/roles/creation_panel.py RoleCreateModal)
    assert ROLE_CREATE_MODAL.title == "Create Role"
    assert [f.field_id for f in ROLE_CREATE_MODAL.fields] == ["name", "color"]
    assert ROLE_CREATE_MODAL.fields[0].label == "Role name"
    assert ROLE_CREATE_MODAL.fields[0].max_length == 100
    assert ROLE_CREATE_MODAL.fields[1].label == "Color (hex, e.g. #3498db)"
    assert ROLE_CREATE_MODAL.fields[1].required is False
    assert ROLE_CREATE_MODAL.fields[1].max_length == 7
    assert ROLE_CREATE_MODAL.on_submit == HandlerRef("role.create_form_submit")


def test_role_create_form_submit_color_guard_and_unarmed_refusal():
    import sb.manifest.role as m

    m.ENSURE_REFS()
    from sb.spec.outcomes import BLOCKED

    submit = _handler("role.create_form_submit")
    bad = run(submit(Req(args={"name": "VIP", "color": "chartreuse"})))
    assert bad.outcome == BLOCKED
    # the shipped modal refusal, verbatim (creation_panel.py)
    assert bad.user_message == "❌ Invalid color — use hex like `#3498db`."

    over = run(submit(Req(args={"name": "VIP", "color": "#1234567"})))
    assert over.outcome == BLOCKED
    assert over.user_message == "❌ Invalid color — use hex like `#3498db`."

    # unarmed provisioning port → the honest `!createrole` refusal shape
    unarmed = run(submit(Req(args={"name": "VIP", "color": "#3498db"})))
    assert unarmed.outcome == BLOCKED
    assert unarmed.user_message.startswith("❌ Could not create role:")


def test_role_create_form_submit_runs_the_live_lane():
    """An armed provisioning port creates the role and answers the
    shipped ✅ ack — the same lane `!createrole` runs (shared helper)."""
    from sb.domain.role import service
    from sb.spec.outcomes import SUCCESS

    calls = []

    class FakeProvisioning:
        async def create_guild_role(self, guild_id, *, name, color, reason):
            calls.append((guild_id, name, color, reason))
            return 4242

        async def delete_role(self, guild_id, role_id, *, reason):
            raise AssertionError("unused")

    prior = service.active_provisioning()
    service.install_role_provisioning(FakeProvisioning())
    try:
        submit = _handler("role.create_form_submit")
        ok = run(submit(Req(args={"name": "VIP", "color": "#3498DB"})))
    finally:
        service.install_role_provisioning(prior)
    assert ok.outcome == SUCCESS
    assert ok.user_message == "✅ Created role **VIP**."      # shipped ack byte
    assert calls == [(42, "VIP", 0x3498DB, None)]


def test_createrole_command_twin_still_answers_usage_guard():
    """The refactor to the shared lane keeps the command twin's guard."""
    import sb.manifest.role as m

    m.ENSURE_REFS()
    from sb.spec.outcomes import BLOCKED

    twin = _handler("role.createrole")
    reply = run(twin(Req(args={"argv": ()})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Usage: `!createrole <name> [color]`"


# --- counters: the argful preset APPLY --------------------------------------------


def test_preset_catalog_is_the_oracle_catalog():
    """counter_config verbatim: keys, labels, all three kind templates
    (`default` byte-identical to the canonical defaults)."""
    from sb.domain.counters import (
        DEFAULT_TEMPLATES,
        TEMPLATE_PRESETS,
        get_preset,
        preset_setting_writes,
    )

    assert [p.key for p in TEMPLATE_PRESETS] == [
        "default", "minimal", "brackets", "bullet"]
    assert TEMPLATE_PRESETS[0].templates == DEFAULT_TEMPLATES
    assert get_preset("  MINIMAL ").key == "minimal"
    assert get_preset("nope") is None
    assert preset_setting_writes(get_preset("brackets")) == (
        ("total_template", "Members [{count}]"),
        ("humans_template", "Humans [{count}]"),
        ("bots_template", "Bots [{count}]"),
    )
    # the list card renders the same TOTAL samples as before the reshape
    # (goldens/counters/sweep_counterpreset safety).
    assert TEMPLATE_PRESETS[1].template_for("total") == "Members: {count}"


def test_counterpreset_unknown_name_refusal():
    import sb.manifest.counters as m

    m.ENSURE_REFS()
    from sb.spec.outcomes import BLOCKED

    view = _handler("counters.preset_view")
    reply = run(view(Req(args={"argv": ("neon",)})))
    assert reply.outcome == BLOCKED
    # the shipped refusal, verbatim (counters_cog.counter_preset)
    assert reply.user_message == ("❌ Unknown preset `neon`. Try one of: "
                             "`default`, `minimal`, `brackets`, `bullet`.")


def test_counterpreset_apply_writes_all_three_templates(monkeypatch):
    """The apply branch runs three audited `settings.set_scalar` writes
    in the shipped kind order, then the shipped ack."""
    from sb.kernel import settings as ksettings
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.result import WorkflowResult
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import WorkflowRef

    import sb.manifest.counters as m

    m.ENSURE_REFS()
    seen = []

    async def fake_run(target, ctx):
        seen.append((target, dict(ctx.params)))
        return WorkflowResult(
            mutation_id="m1", guild_id=ctx.guild_id, domain="settings",
            operation="settings.set_scalar", outcome=SUCCESS,
            reversibility="reversible")

    monkeypatch.setattr(engine, "run", fake_run)
    view = _handler("counters.preset_view")
    reply = run(view(Req(args={"argv": ("bullet",)})))

    assert reply.outcome == SUCCESS
    # the shipped ack, verbatim (~10-min sync cadence interpolated)
    assert reply.user_message == (
        "✅ Applied the **Bullet — separator dot** preset to all three "
        "counter name templates. Bound channels refresh on the next sync "
        "(~10 min).")
    assert [t for t, _ in seen] == [WorkflowRef("settings.set_scalar")] * 3
    assert [(p["name"], p["value"]) for _, p in seen] == [
        ("total_template", "👥 Members • {count}"),
        ("humans_template", "🧑 Humans • {count}"),
        ("bots_template", "🤖 Bots • {count}"),
    ]
    expected_keys = [ksettings.persisted_key("counters", n)
                     for n in ("total_template", "humans_template",
                               "bots_template")]
    assert [p["key"] for _, p in seen] == expected_keys


def test_counterpreset_apply_short_circuits_on_a_failed_write(monkeypatch):
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.result import WorkflowResult
    from sb.spec.outcomes import BLOCKED, SUCCESS

    import sb.manifest.counters as m

    m.ENSURE_REFS()
    calls = []

    async def fake_run(target, ctx):
        calls.append(ctx.params["name"])
        return WorkflowResult(
            mutation_id="m1", guild_id=ctx.guild_id, domain="settings",
            operation="settings.set_scalar", outcome=BLOCKED,
            reversibility="reversible",
            user_message="setting key refused")

    monkeypatch.setattr(engine, "run", fake_run)
    view = _handler("counters.preset_view")
    reply = run(view(Req(args={"argv": ("default",)})))
    assert reply.outcome == BLOCKED
    # the shipped SettingsMutationError shape
    assert reply.user_message == "❌ Could not apply preset: setting key refused"
    assert calls == ["total_template"]      # short-circuited on the first


def test_counterpreset_bare_still_opens_the_list_card(monkeypatch):
    """The no-arg branch keeps the golden-pinned list-card open."""
    import sb.manifest.counters as m

    m.ENSURE_REFS()
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req, **kw):
        opened.append(str(ref))
        return None

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    view = _handler("counters.preset_view")
    reply = run(view(Req(args={"argv": ()})))
    assert reply is None
    assert opened == ["PanelRef(name='counters.presets')"]


def test_counters_preset_pending_terminal_is_retired():
    import sb.domain.counters.panels as p
    import sb.manifest.counters as m

    assert "preset_pending" not in open(p.__file__, encoding="utf-8").read()
    assert "preset_pending" not in open(m.__file__, encoding="utf-8").read()
