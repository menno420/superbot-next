"""The roles-family section flows (the roles-family slice —
sb/domain/setup/roles.py · role_templates.py).

DB-free like the section-flows suite: the K7/K9 write seams are
monkeypatched at their module functions and the assertions pin the
ORACLE bytes the click paths carry (no golden drives a click on these
components — the panels.py module pin; oracle sources:
views/setup/sections/roles.py, views/setup/sections/role_templates.py,
services/setup_role_templates.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import role_templates, roles, wizard, wizard_nav

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    roles.reset_roles_state_for_tests()
    role_templates.reset_role_templates_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    roles.reset_roles_state_for_tests()
    role_templates.reset_role_templates_state_for_tests()


def _req(*, user_id=42, guild_id=99, args=None, message_id=777):
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=user_id),
        guild_id=guild_id,
        args=dict(args or {}),
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)),
        request_id="req-1",
        confirmed=False,
    )


def _resolve(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _ctx(*, guild_id=99, user_id=42, params=None):
    from sb.kernel.interaction.request import ActorRef
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=guild_id,
        actor=ActorRef(user_id=user_id, is_guild_operator=True,
                       is_bot_owner=False, is_dm=False),
        channel_id=1, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, params=dict(params or {}))


class _Gate:
    def __init__(self, allow: bool) -> None:
        self.allow = allow

    async def __call__(self, req) -> bool:
        del req
        return self.allow


class _FakeStore:
    """A draft store whose added rows REFLECT into the open draft's
    operations (the fold test reads the prior slot back)."""

    def __init__(self, drafts=()):
        self.drafts = list(drafts)
        self.removed: list[tuple[str, int]] = []
        self.added: list = []
        self._seq = 0

    async def list_open(self, scope):
        return tuple(self.drafts)

    async def create(self, *, producer, owner_scope):
        draft = SimpleNamespace(draft_id="d-new", operations=())
        self.drafts.append(draft)
        return draft

    async def remove(self, draft_id, op_seq):
        self.removed.append((draft_id, op_seq))
        for d in self.drafts:
            if d.draft_id == draft_id:
                d.operations = tuple(o for o in d.operations
                                     if o.op_seq != op_seq)

    async def add(self, draft_id, op):
        self.added.append((draft_id, op))
        self._seq += 1
        row = SimpleNamespace(op_seq=self._seq, op_kind=op.op_kind,
                              subsystem=op.subsystem,
                              payload=dict(op.payload), label=op.label)
        for d in self.drafts:
            if d.draft_id == draft_id:
                d.operations = (*d.operations, row)


def _patch_store(monkeypatch, store):
    from sb.kernel.draft import store as draft_store_module

    monkeypatch.setattr(draft_store_module, "DraftStore", lambda: store)


def _patch_write_seams(monkeypatch, *, pending=1):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_count(guild_id):
        return pending

    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)


# =======================================================================================
# roles
# =======================================================================================


def test_roles_embed_is_the_shipped_bytes():
    from sb.domain.setup.roles import build_roles_embed

    embed = build_roles_embed()
    assert embed.title == "🎖️ Auto roles (time & XP)"
    assert embed.description == (
        "Automatically grant a role when a member has been in the server "
        "long enough (**time tier**) or reaches an **XP level** (XP tier). "
        "Pick a role below, then enter the threshold — each submission "
        "stages a `set_role_threshold` operation that **Final review** "
        "applies through the audited role-automation seam.")
    assert embed.fields[0][0] == "How it works"
    assert embed.fields[0][1] == (
        "• **Time tier** — granted after N days in the server\n"
        "• **XP tier** — granted at XP level N (auto-assigned)\n"
        "• Configure each tier for an **existing** role; create roles "
        "first in Discord or via the role manager.")
    assert embed.footer == (
        "Final Review applies all staged tiers · clear/edit tiers in "
        "!roles.")
    # no summary supplied → no Detected field (the section-card face).
    assert [f[0] for f in embed.fields] == ["How it works"]
    # the empty-summary Detected placeholder, verbatim.
    embed = build_roles_embed(current_summary="")
    assert embed.fields[1] == (
        "Detected", "_(no auto-role tiers configured yet)_", False)


def test_parse_positive_int_carries_the_shipped_bounds():
    from sb.domain.setup.roles import _MAX_DAYS, _parse_positive_int

    assert _parse_positive_int("7", _MAX_DAYS) == 7
    assert _parse_positive_int("3650", _MAX_DAYS) == 3650
    assert _parse_positive_int("0", _MAX_DAYS) is None
    assert _parse_positive_int("3651", _MAX_DAYS) is None
    assert _parse_positive_int("seven", _MAX_DAYS) is None
    assert _parse_positive_int("", _MAX_DAYS) is None


def test_set_role_threshold_op_kind_binds_the_k7_op():
    from sb.kernel.draft.registry import OP_KINDS

    binding = OP_KINDS.get("set_role_threshold")
    assert binding is not None
    assert binding.workflow_ref.name == "role.set_threshold"
    assert binding.is_resource_create is False
    declared = {f.name for f in binding.payload_schema}
    assert declared == {"role_name", "role_id", "days_required",
                        "xp_auto_assign"}


def test_time_submit_requires_a_pick_first():
    reply = run(_resolve("setup.roles_time_submit")(
        _req(args={"days": "7"})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Time tier: pick a role to grant after N days first.")


def test_time_submit_invalid_days_is_the_shipped_copy():
    from sb.domain.setup import roles

    roles._PICKED_TIME_ROLE["99:42"] = 555
    reply = run(_resolve("setup.roles_time_submit")(
        _req(args={"days": "0"})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (_TimeDaysModal.on_submit).
    assert reply.user_message == (
        "⚠️ Enter a whole number of days between 1 and 3650.")


def test_xp_submit_invalid_level_is_the_shipped_copy():
    from sb.domain.setup import roles

    roles._PICKED_XP_ROLE["99:42"] = 555
    reply = run(_resolve("setup.roles_xp_submit")(
        _req(args={"level": "1001"})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (_XpLevelModal.on_submit).
    assert reply.user_message == (
        "⚠️ Enter a whole number level between 1 and 1000.")


def test_time_submit_gate_refusal_is_the_card_copy(monkeypatch):
    from sb.domain.setup import roles, section_card, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    roles._PICKED_TIME_ROLE["99:42"] = 555
    reply = run(_resolve("setup.roles_time_submit")(
        _req(args={"days": "7"})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == section_card.GATE_MSG_CARD


def test_time_submit_stages_the_threshold_row(monkeypatch):
    from sb.domain.setup import roles

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_write_seams(monkeypatch, pending=1)
    roles._PICKED_TIME_ROLE["99:42"] = 555

    reply = run(_resolve("setup.roles_time_submit")(
        _req(args={"days": "7"})))
    assert reply.outcome == SUCCESS
    # shipped confirmation, verbatim (roles._stage_threshold).
    assert reply.user_message == (
        "✅ Staged for Final review: `role tier: @555 after 7d`.  "
        "Pending operations: **1**.")
    assert len(store.added) == 1
    _draft_id, op = store.added[0]
    assert op.op_kind == "set_role_threshold"
    assert op.subsystem == "roles"
    assert op.payload["name"] == "tier:555"
    assert op.payload["role_name"] == "555"
    assert op.payload["role_id"] == 555
    assert op.payload["days_required"] == 7
    assert op.payload["level_required"] is None
    assert op.payload["xp_auto_assign"] is False
    # section provenance rides the label prefix (the spine's micro-grammar).
    assert op.label == "[roles] role tier: @555 after 7d"


def test_time_and_xp_fold_onto_one_row_per_role(monkeypatch):
    """The K7 full-row-upsert fold (module docstring ledger): staging a
    time tier then an XP tier for the SAME role merges into ONE slot
    carrying both columns — the essential_steps reward-step fold."""
    from sb.domain.setup import roles

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_write_seams(monkeypatch, pending=1)
    roles._PICKED_TIME_ROLE["99:42"] = 555
    roles._PICKED_XP_ROLE["99:42"] = 555

    run(_resolve("setup.roles_time_submit")(_req(args={"days": "30"})))
    reply = run(_resolve("setup.roles_xp_submit")(
        _req(args={"level": "10"})))
    assert reply.outcome == SUCCESS
    # the second stage REPLACED the first slot row (never duplicated).
    draft = store.drafts[0]
    rows = [o for o in draft.operations
            if o.op_kind == "set_role_threshold"]
    assert len(rows) == 1
    payload = rows[0].payload
    assert payload["days_required"] == 30       # merged forward
    assert payload["level_required"] == 10
    assert payload["xp_auto_assign"] is True
    # a DIFFERENT role keeps its own slot.
    roles._PICKED_XP_ROLE["99:42"] = 777
    run(_resolve("setup.roles_xp_submit")(_req(args={"level": "5"})))
    rows = [o for o in store.drafts[0].operations
            if o.op_kind == "set_role_threshold"]
    assert {r.payload["name"] for r in rows} == {"tier:555", "tier:777"}


def test_roles_renderer_reveals_the_forms_stepwise(monkeypatch):
    from sb.domain.setup import roles

    spec = roles.roles_detail_spec()

    def leaves(rendered):
        return {c.custom_id.removeprefix(f"{spec.panel_id}.")
                for c in rendered.components}

    # nothing picked: the two role pickers only (no forms, no back).
    rendered = run(roles._render_roles_detail(spec, _ctx()))
    assert leaves(rendered) == {"roles_time_role", "roles_xp_role"}
    # a time pick reveals the time form button only.
    roles._PICKED_TIME_ROLE["99:42"] = 555
    rendered = run(roles._render_roles_detail(spec, _ctx()))
    assert leaves(rendered) == {"roles_time_role", "roles_xp_role",
                                "roles_time_days"}
    # the wizard origin injects ↩ Back to step (the shipped row-4 ride).
    from sb.domain.setup import wizard_nav

    wizard_nav.mark_detail_from_wizard(99, 42)
    rendered = run(roles._render_roles_detail(spec, _ctx()))
    assert "roles_back_step" in leaves(rendered)


def test_roles_pick_handlers_stash_the_role(monkeypatch):
    from sb.domain.setup import roles
    from sb.kernel.panels import engine as panels_engine

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    reply = run(_resolve("setup.roles_time_role_pick")(
        _req(args={"values": ("555",)})))
    assert reply is None
    assert roles._PICKED_TIME_ROLE["99:42"] == 555
    reply = run(_resolve("setup.roles_xp_role_pick")(
        _req(args={"values": ("x",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "No role picked."


def test_open_section_roles_lands_on_the_card(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    monkeypatch.setattr(wf_engine, "run", fake_run)
    assert run(_resolve("setup.open_section_roles")(_req())) is None
    assert opened == ["setup.section_roles"]


def test_roles_has_no_recommended_builder():
    from sb.domain.setup import section_card

    assert section_card.recommended_builder("roles") is None
    assert (section_card.customize_panel("roles")
            == "setup.roles_detail")


# =======================================================================================
# role_templates — the catalogue (setup_role_templates.py, data verbatim)
# =======================================================================================


def test_catalogue_is_the_shipped_data():
    from sb.domain.setup import role_templates as rt

    assert [t.slug for t in rt.list_templates()] == [
        "community-hierarchy", "moderation-team", "gaming-community",
        "time-progression", "xp-progression", "support-server"]
    assert {t.slug: t.role_count for t in rt.list_templates()} == {
        "community-hierarchy": 4, "moderation-team": 4,
        "gaming-community": 5, "time-progression": 4,
        "xp-progression": 5, "support-server": 4}
    time_prog = rt.get_template("time-progression")
    assert [s.time_days for s in time_prog.suggestions] == [7, 30, 90, 365]
    xp_prog = rt.get_template("xp-progression")
    assert [s.xp_level for s in xp_prog.suggestions] == [5, 10, 25, 50, 100]
    # the structural safety property: NO suggestion carries permissions
    # (RoleSuggestion has no permissions field by design).
    assert not hasattr(time_prog.suggestions[0], "permissions")


def test_builtin_catalogue_validates_clean():
    from sb.domain.setup import role_templates as rt

    for template in rt.list_templates():
        assert rt.validate_template(template) == []


def test_validation_carries_the_shipped_bounds():
    from sb.domain.setup import role_templates as rt

    assert rt.validate_suggestion(rt.RoleSuggestion("")) == [
        "role name is empty"]
    assert ("a template must not create @everyone"
            in rt.validate_suggestion(rt.RoleSuggestion("@everyone")))
    assert rt.validate_suggestion(
        rt.RoleSuggestion("X", color="nope")) == ["unparseable color 'nope'"]
    assert rt.validate_suggestion(
        rt.RoleSuggestion("X", time_days=3651)) == [
        "time_days 3651 out of range 1..3650"]
    assert rt.validate_suggestion(
        rt.RoleSuggestion("X", xp_level=0)) == [
        "xp_level 0 out of range 1..1000"]
    assert rt.parse_color("#E91E63") == 0xE91E63
    assert rt.parse_color("2ECC71") == 0x2ECC71
    assert rt.parse_color("nope") is None
    assert rt.parse_color(None) is None


def test_plan_template_partitions_create_vs_exists():
    from sb.domain.setup import role_templates as rt

    template = rt.get_template("community-hierarchy")
    plan = rt.plan_template(template,
                            existing_roles={"MODERATOR": 5, "member": 6})
    assert plan.create_count == 2
    assert plan.exists_count == 2
    assert {p.suggestion.name for p in plan.to_create} == {"Owner", "Admin"}
    exists = {p.suggestion.name: p.existing_role_id for p in plan.existing}
    assert exists == {"Moderator": 5, "Member": 6}
    # the Manage-Roles warning arm, verbatim.
    plan = rt.plan_template(template, bot_can_manage_roles=False)
    assert plan.warnings == (
        "the bot lacks the Manage Roles permission — creation will be "
        "blocked at Final Review until it is granted",)


def test_suggestion_to_spec_round_trip_shape():
    from sb.domain.setup import role_templates as rt

    s = rt.RoleSuggestion("Regular", "7 days in the server", "#1ABC9C",
                          hoist=True, time_days=7)
    assert rt.suggestion_to_spec(s, template_slug="time-progression") == {
        "color": "#1ABC9C", "hoist": True, "mentionable": False,
        "time_days": 7, "xp_level": None, "purpose": "7 days in the server",
        "template_slug": "time-progression"}


# =======================================================================================
# role_templates — embeds (bytes verbatim)
# =======================================================================================


def test_role_templates_picker_embed_is_the_shipped_bytes():
    from sb.domain.setup.role_templates import build_role_templates_embed

    embed = build_role_templates_embed()
    assert embed.title == "🧩 Role templates"
    assert embed.description == (
        "Pick a built-in template below to preview a set of roles, then "
        "stage the ones you don't have yet. **Staging creates nothing** — "
        "**Final review** applies the draft.\n\n"
        "Templates only *create roles* (for an existing server); they never "
        "grant permissions — set those up separately.")
    assert len(embed.fields) == 6
    assert embed.fields[0][0] == "Community hierarchy · 4 roles"
    # the tier note rides only the progression templates.
    assert embed.fields[3][0] == "Time-in-server progression · 4 roles"
    assert embed.fields[3][1].endswith(" · 4 auto-role tier(s)")
    assert " · " not in embed.fields[0][1][-20:]
    assert embed.footer == (
        "Pick a template to preview · Final review applies staged roles.")


def test_template_preview_embed_is_the_shipped_bytes():
    from sb.domain.setup import role_templates as rt

    template = rt.get_template("time-progression")
    plan = rt.plan_template(template, existing_roles={"regular": 11})
    embed = rt.build_template_preview_embed(template, plan)
    assert embed.title == "🧩 Time-in-server progression"
    lines = embed.fields[0][1].split("\n")
    assert lines[0] == ("✅ @Regular (hoisted, #1ABC9C, 7d tier) — already "
                        "exists (skip)")
    assert lines[1] == "➕ @Veteran (hoisted, #3498DB, 30d tier)"
    assert embed.fields[1] == (
        "Summary", "➕ **3** to create · ✅ 1 already exist", False)
    assert embed.footer == (
        "“Stage new roles” adds them to the draft · Final review creates "
        "them.")


# =======================================================================================
# role_templates — the flow
# =======================================================================================


def test_template_pick_stashes_and_unknown_is_refused(monkeypatch):
    from sb.domain.setup import role_templates as rt
    from sb.kernel.panels import engine as panels_engine

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    reply = run(_resolve("setup.role_template_pick")(
        _req(args={"values": ("time-progression",)})))
    assert reply is None
    assert rt._SELECTED["99:42"] == "time-progression"
    reply = run(_resolve("setup.role_template_pick")(
        _req(args={"values": ("nope",)})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (on_template_selected).
    assert reply.user_message == "Could not load that template."


def test_stage_without_a_pick_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    reply = run(_resolve("setup.role_template_stage")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (_on_stage).
    assert reply.user_message == "Pick a template first."


def test_stage_gate_refusal_is_the_card_copy(monkeypatch):
    from sb.domain.setup import role_templates as rt
    from sb.domain.setup import section_card, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    rt._SELECTED["99:42"] = "community-hierarchy"
    reply = run(_resolve("setup.role_template_stage")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == section_card.GATE_MSG_CARD


def test_stage_drafts_one_op_per_missing_role(monkeypatch):
    from sb.domain.setup import role_templates as rt

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_write_seams(monkeypatch, pending=4)
    rt._SELECTED["99:42"] = "community-hierarchy"

    reply = run(_resolve("setup.role_template_stage")(_req()))
    assert reply.outcome == SUCCESS
    # shipped confirmation, verbatim (_stage_creations).
    assert reply.user_message == (
        "✅ Staged **4** new role(s) from **Community hierarchy** for "
        "Final review. Pending operations: **4**. Nothing is created "
        "until you apply.")
    assert len(store.added) == 4
    ops = [op for _d, op in store.added]
    assert all(op.op_kind == "create_managed_role" for op in ops)
    assert all(op.subsystem == "roles" for op in ops)
    first = ops[0].payload
    assert first["name"] == "role:owner"        # the per-role slot key
    assert first["resource_name"] == "Owner"
    assert first["resource_mode"] == "create"
    assert first["role_template"]["template_slug"] == "community-hierarchy"
    assert first["role_template"]["color"] == "#E91E63"
    # the shipped op label bytes (+ the section provenance prefix).
    assert ops[0].label == "[role_templates] create role @Owner"


def test_stage_label_carries_the_tier_suffixes(monkeypatch):
    from sb.domain.setup import role_templates as rt

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_write_seams(monkeypatch, pending=4)
    rt._SELECTED["99:42"] = "time-progression"
    run(_resolve("setup.role_template_stage")(_req()))
    labels = [op.label for _d, op in store.added]
    assert labels[0] == "[role_templates] create role @Regular +7d"


def test_stage_when_everything_exists_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import role_templates as rt

    _patch_write_seams(monkeypatch)
    rt._SELECTED["99:42"] = "community-hierarchy"

    async def all_exist(guild_id):
        return {"owner": 1, "admin": 2, "moderator": 3, "member": 4}

    monkeypatch.setattr(rt, "_existing_roles", all_exist)
    reply = run(_resolve("setup.role_template_stage")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (_stage_creations).
    assert reply.user_message == (
        "✅ Every role in **Community hierarchy** already exists — "
        "nothing to create.")


def test_role_templates_renderer_swaps_embed_and_syncs_the_button():
    from sb.domain.setup import role_templates as rt

    spec = rt.role_templates_detail_spec()

    def by_leaf(rendered):
        return {c.custom_id.removeprefix(f"{spec.panel_id}."): c
                for c in rendered.components}

    # nothing picked: the catalogue picker embed, NO stage button (the
    # oracle created it on first selection).
    rendered = run(rt._render_role_templates_detail(spec, _ctx()))
    assert rendered.embed.title == "🧩 Role templates"
    assert set(by_leaf(rendered)) == {"tmpl_pick"}
    # picked: the preview embed + the synced count label
    # (_sync_stage_button bytes verbatim).
    rt._SELECTED["99:42"] = "community-hierarchy"
    rendered = run(rt._render_role_templates_detail(spec, _ctx()))
    assert rendered.embed.title == "🧩 Community hierarchy"
    stage = by_leaf(rendered)["tmpl_stage"]
    assert stage.label == "Stage 4 new roles"
    assert not stage.disabled


def test_open_section_role_templates_lands_on_the_card(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    monkeypatch.setattr(wf_engine, "run", fake_run)
    assert run(_resolve("setup.open_section_role_templates")(_req())) is None
    assert opened == ["setup.section_role_templates"]


def test_role_templates_has_no_recommended_builder():
    from sb.domain.setup import section_card

    assert section_card.recommended_builder("role_templates") is None
    assert (section_card.customize_panel("role_templates")
            == "setup.role_templates_detail")


def test_create_managed_role_op_kind_binds_the_k7_op():
    """The compound-ops slice retired the fail-closed posture: the
    create_managed_role op kind binds the audited K7
    ``role.create_managed_role`` compound op (module docstring's named
    successor, landed)."""
    from sb.domain.setup.role_templates import (
        _register_create_managed_role_op_kind,
    )
    from sb.kernel.draft.registry import OP_KINDS

    _register_create_managed_role_op_kind()
    binding = OP_KINDS.get("create_managed_role")
    assert binding is not None
    assert binding.workflow_ref.name == "role.create_managed_role"
    assert binding.is_resource_create is True
    declared = {f.name for f in binding.payload_schema}
    assert declared == {"resource_name", "role_template"}
    # the staged payload (_build_create_op) carries every declared field.
    from sb.domain.setup import role_templates as rt

    op = rt._build_create_op(rt.RoleSuggestion("Regular", time_days=7),
                             template=rt.get_template("time-progression"))
    assert declared <= set(op.payload)


# =======================================================================================
# final review — the new pending-line branches
# =======================================================================================


def test_final_review_short_label_carries_the_roles_bytes():
    from sb.domain.setup.final_review import _short_label

    merged = SimpleNamespace(
        op_kind="set_role_threshold", subsystem="roles",
        payload={"name": "tier:555", "role_name": "555", "role_id": 555,
                 "days_required": 30, "level_required": 10,
                 "xp_auto_assign": True, "target_name": "555"})
    assert _short_label(merged) == "role tier: @555 after 30d + at XP level 10"
    time_only = SimpleNamespace(
        op_kind="set_role_threshold", subsystem="roles",
        payload={"name": "tier:555", "role_name": "555", "role_id": 555,
                 "days_required": 7, "level_required": None,
                 "xp_auto_assign": False, "target_name": "555"})
    assert _short_label(time_only) == "role tier: @555 after 7d"


def test_final_review_short_label_carries_the_template_bytes():
    from sb.domain.setup.final_review import _short_label

    op = SimpleNamespace(
        op_kind="create_managed_role", subsystem="roles",
        payload={"name": "role:regular", "resource_name": "Regular",
                 "resource_mode": "create",
                 "role_template": {"color": "#1ABC9C", "hoist": True,
                                   "mentionable": False, "time_days": 7,
                                   "xp_level": None, "purpose": "",
                                   "template_slug": "time-progression"}})
    # the shipped _op_label bytes, re-derived (create role @X +7d).
    assert _short_label(op) == "create role @Regular +7d"
    plain = SimpleNamespace(
        op_kind="create_managed_role", subsystem="roles",
        payload={"name": "role:helper", "resource_name": "Helper",
                 "resource_mode": "create", "role_template": {}})
    assert _short_label(plain) == "create role @Helper"


def test_wizard_live_sections_cover_the_roles_family():
    """The hub route registration: the roles-family slugs resolve to
    the LIVE section openers (their own modules), and the remaining
    two stay the honest named-successor terminals."""
    from sb.spec.refs import HandlerRef, resolve

    for slug in ("roles", "role_templates"):
        assert resolve(HandlerRef(f"setup.open_section_{slug}")) is not None
