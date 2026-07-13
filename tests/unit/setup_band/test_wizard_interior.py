"""The setup wizard INTERIOR (wizard-lifecycle slice, ORDER 017) — the
click lanes behind the four golden-pinned setup cards + the two interior
panels (sb/domain/setup/wizard.py + panels.py).

DB-free like the band-7 siblings: the K7/K9 write seams are monkeypatched
at their module functions and the assertions pin the ORACLE bytes the
click paths carry (no golden drives a click on these components — the
module pin; oracle sources: views/setup/depth_panel.py,
essential_setup.py, hub.py, ai_review/main_panel.py +
per_recommendation.py, cogs/setup_cog.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import wizard

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()


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


def _rec(subsystem="logging", binding="audit_channel", confidence="high",
         target_id=1234, target_name="audit", mode="bind"):
    from sb.domain.setup.plan import SetupRecommendation

    return SetupRecommendation(
        subsystem=subsystem, binding_name=binding, target_kind="channel",
        target_id=target_id, target_name=target_name,
        confidence=confidence,
        reason=f"channel `{target_name}` matches token `{binding}` "
               f"({confidence})",
        mode=mode)


def _draft(*recs):
    from sb.domain.setup.plan import SetupPlanDraft

    return SetupPlanDraft(recommendations=tuple(recs))


class _Gate:
    """Monkeypatch target for the apply-authority gate."""

    def __init__(self, allow: bool) -> None:
        self.allow = allow

    async def __call__(self, req) -> bool:
        del req
        return self.allow


# --- the shipped data, verbatim spot-checks -------------------------------------------


def test_server_types_carry_the_shipped_bundles():
    from sb.domain.setup.wizard import SERVER_TYPES, XP_RATES, server_type

    assert [p.key for p in SERVER_TYPES] == [
        "community", "gaming", "support", "creator", "exploring"]
    gaming = server_type("gaming")
    assert ("automod", "invites_enabled", False) in gaming.settings
    assert gaming.xp_rate == "active"
    assert server_type("exploring").settings == (
        ("automod", "enabled", True), ("automod", "spam_enabled", True))
    assert XP_RATES["standard"] == ("Standard — balanced", 15, 25, 60)


def test_depth_filter_matches_the_shipped_sections():
    from sb.domain.setup.wizard import sections_for_depth

    assert [s.slug for s in sections_for_depth("quick")] == [
        "preset_select", "channels", "logging_presets", "final_review"]
    assert [s.slug for s in sections_for_depth("standard")] == [
        "preset_select", "channels", "logging_presets", "roles",
        "role_templates", "moderation", "ticket", "final_review"]
    assert len(sections_for_depth("advanced")) == 10
    # None (no persisted choice) keeps the hub full — the shipped
    # legacy-path behavior.
    assert len(sections_for_depth(None)) == 10


def test_store_set_depth_refuses_unknown_values():
    from sb.domain.setup import store

    with pytest.raises(ValueError, match="depth must be one of"):
        run(store.set_depth(object(), guild_id=1, depth="ultra"))


def test_wizard_ops_registered():
    from sb.kernel.workflow.registry import REGISTRY

    assert REGISTRY.resolve("setup.set_depth").audit_verb == \
        "setup.session.depth_set"
    assert REGISTRY.resolve("setup.set_section_skip").audit_verb == \
        "setup.session.section_skip"


# --- the depth chooser's three buttons -------------------------------------------------


def test_depth_click_persists_then_opens_the_sections_hub(monkeypatch):
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    ran = []

    async def fake_run(ref, ctx):
        ran.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS)

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr(panels_engine, "open_panel", fake_open)

    reply = run(_resolve("setup.depth_pick_standard")(_req()))
    assert reply is None
    assert ran == [("setup.set_depth", {"depth": "standard"})]
    assert opened == ["setup.sections_hub"]


def test_depth_click_failure_answers_the_shipped_copy(monkeypatch):
    from sb.kernel.workflow import engine as wf_engine

    async def fake_run(ref, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(wf_engine, "run", fake_run)
    reply = run(_resolve("setup.depth_pick_quick")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (depth_panel._select).
    assert reply.user_message == "Could not save your depth choice. See logs."


# --- the sections hub -------------------------------------------------------------------


def test_section_click_holds_the_named_successor_terminal(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    reply = run(_resolve("setup.open_section_cleanup")(_req()))
    assert reply.outcome == BLOCKED
    assert "section-flows slice" in reply.user_message
    assert "`cleanup`" in reply.user_message


def test_hub_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.open_section_channels")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (hub.SetupHubView._gate_apply).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can run the "
        "wizard. Ask the server owner to grant you `/setup-delegate`.")


def test_change_depth_reopens_the_chooser(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.change_depth")(_req())) is None
    assert opened == ["setup.hub"]


def test_sections_hub_render_pins_the_shipped_hub_bytes(monkeypatch):
    from sb.domain.setup import store, wizard
    from sb.domain.setup.panels import sections_hub_spec

    session = {
        "setup_status": "in_progress", "depth": "quick",
        "current_step": "depth", "last_readiness_score": None,
        "skipped_sections": ["channels"], "acknowledged_sections": [],
    }

    async def fake_row(guild_id, conn=None):
        return dict(session)

    async def fake_count(guild_id):
        return 2

    monkeypatch.setattr(store, "get_session_row", fake_row)
    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)

    rendered = run(_resolve("setup.sections_hub_render")(
        sections_hub_spec(), _ctx()))
    embed = rendered.embed
    assert embed.title == "🛰 SuperBot setup wizard"
    # the shipped status line + pending-operations rider.
    assert "**Status:** `in_progress` · depth: `quick`" in embed.description
    assert "current step: `depth`" in embed.description
    assert "**Pending operations:** `2`" in embed.description
    sections_field = dict((f[0], f[1]) for f in embed.fields)["Sections"]
    # quick depth → the four shipped quick sections, badge-prefixed;
    # the skipped slug carries the shipped ⚠️ badge.
    assert sections_field.splitlines() == [
        "⬜ 1. Load preset",
        "⚠️ 2. Channels & log routing",
        "⬜ 3. Logging presets",
        "⬜ 4. Final review",
    ]
    hint = dict((f[0], f[1]) for f in embed.fields)["Next step"]
    assert hint == ("📝 **2** op(s) staged. Either open more sections "
                    "or go to **Final Review**.")
    # the shipped footer byte.
    assert embed.footer.startswith("Owner-gated. No mutation runs until")
    # components: the four quick sections + the two nav buttons, nav on
    # its own row (the shipped add_item flow).
    ids = [c.custom_id for c in rendered.components]
    assert ids == [
        "setup_section:preset_select", "setup_section:channels",
        "setup_section:logging_presets", "setup_section:final_review",
        "setup_hub:change_depth", "setup_hub:back_to_wizard",
    ]
    rows = {c.custom_id: c.row for c in rendered.components}
    assert rows["setup_section:final_review"] == 0
    assert rows["setup_hub:change_depth"] == 1


def test_sections_hub_render_sessionless_keeps_every_section(monkeypatch):
    from sb.domain.setup import store, wizard
    from sb.domain.setup.panels import sections_hub_spec

    async def fake_row(guild_id, conn=None):
        return None

    async def fake_count(guild_id):
        return 0

    monkeypatch.setattr(store, "get_session_row", fake_row)
    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)
    rendered = run(_resolve("setup.sections_hub_render")(
        sections_hub_spec(), _ctx()))
    embed = rendered.embed
    assert "**Status:**" not in embed.description
    assert "**Pending operations:** `0`" in embed.description
    sections_field = dict((f[0], f[1]) for f in embed.fields)["Sections"]
    assert len(sections_field.splitlines()) == 10
    hint = dict((f[0], f[1]) for f in embed.fields)["Next step"]
    assert hint == "👉 Pick a section to begin."
    # ten sections repack five-per-row; nav lands on row 2.
    rows = {c.custom_id: c.row for c in rendered.components}
    assert rows["setup_section:preset_select"] == 0
    assert rows["setup_section:ticket"] == 1
    assert rows["setup_hub:back_to_wizard"] == 2


# --- the essential Step-1 interior ------------------------------------------------------


def test_essential_pick_records_and_rerenders(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    refreshed = []

    async def fake_refresh(req, *, message_key, params, expire=False):
        refreshed.append((message_key, dict(params)))
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    reply = run(_resolve("setup.essential_pick")(
        _req(args={"values": ["gaming"]})))
    assert reply is None
    assert wizard.essential_pick(99, 42) == "gaming"
    assert refreshed and refreshed[0][0] == "777"
    assert refreshed[0][1]["essential_kind"] == "gaming"


def test_essential_pick_unknown_value_answers_the_shipped_copy():
    reply = run(_resolve("setup.essential_pick")(
        _req(args={"values": ["metaverse"]})))
    assert reply.outcome == BLOCKED
    # shipped defensive copy, verbatim (ServerTypeStep.apply).
    assert reply.user_message == ("That server type isn't available — "
                                  "please pick another.")


def test_essential_save_without_pick_answers_the_shipped_guard():
    reply = run(_resolve("setup.essential_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped guard copy, verbatim (ServerTypeStep.apply).
    assert reply.user_message == ("Pick the kind of server you run first — "
                                  "or press Skip.")


def test_essential_save_applies_the_starter_set(monkeypatch):
    from sb.domain.setup import essential_steps, wizard

    writes = []
    shown = []

    async def fake_write(req, subsystem, name, value):
        writes.append((subsystem, name, value))
        return SimpleNamespace(outcome=SUCCESS)

    async def fake_show(req, state):
        shown.append(state.index)

    monkeypatch.setattr(wizard, "_write_setting", fake_write)
    monkeypatch.setattr(essential_steps, "_show_current", fake_show)

    wizard.set_essential_pick(99, 42, "support")
    reply = run(_resolve("setup.essential_save")(_req()))
    # the essential-steps slice: Save advances the flow onto the Step-2
    # card (the shipped complete() — no text confirmation, the card moves).
    assert reply is None
    # the shipped starter bundle, applied verbatim + the relaxed XP rate.
    assert ("automod", "caps_enabled", True) in writes
    assert ("moderation", "dm_on_action", True) in writes
    assert ("xp", "xp_min", 10) in writes
    assert ("xp", "xp_cooldown", 120) in writes
    assert len(writes) == 9
    # the shipped applied-summary line lands in the flow recap + advance.
    state = essential_steps.flow_state(99, 42)
    assert state.applied == ["🛟 Support / Help desk starter set on · "
                             "strict protection on everything, members "
                             "told why, relaxed XP"]
    assert state.index == 1
    assert shown == [1]


def test_essential_save_failure_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    async def fake_write(req, subsystem, name, value):
        raise RuntimeError("boom")

    monkeypatch.setattr(wizard, "_write_setting", fake_write)
    wizard.set_essential_pick(99, 42, "community")
    reply = run(_resolve("setup.essential_save")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (ServerTypeStep.apply).
    assert reply.user_message == ("Something went wrong applying the "
                                  "starter set — please try again.")


def test_essential_skip_records_and_advances(monkeypatch):
    from sb.domain.setup import essential_steps

    shown = []

    async def fake_show(req, state):
        shown.append(state.index)

    monkeypatch.setattr(essential_steps, "_show_current", fake_show)
    reply = run(_resolve("setup.essential_skip")(_req()))
    assert reply is None
    state = essential_steps.flow_state(99, 42)
    # the shipped skip: record the step title, move to Step 2 — nothing
    # was written.
    assert state.applied == []
    assert state.skipped == ["What kind of server is this?"]
    assert state.index == 1
    assert shown == [1]


def test_essential_render_shows_the_picked_starter_set():
    from sb.domain.setup.panels import essential_card_spec

    rendered = run(_resolve("setup.essential_render")(
        essential_card_spec(), _ctx(params={"essential_kind": "gaming"})))
    fields = dict((f[0], f[1]) for f in rendered.embed.fields)
    # the shipped picked-branch field byte (ServerTypeStep.render).
    assert fields["Starter set"] == (
        "🎮 **Gaming** — spam & mass-ping protection (invite links "
        "allowed), faster XP")
    assert rendered.embed.footer == "Step 1 of 8"


def test_essential_render_fresh_open_stays_golden():
    from sb.domain.setup.panels import essential_card_spec

    rendered = run(_resolve("setup.essential_render")(
        essential_card_spec(), _ctx()))
    fields = dict((f[0], f[1]) for f in rendered.embed.fields)
    assert fields["Starter set"] == "_pick one above_"


# --- the smart-suggestions review lanes -------------------------------------------------


def test_accept_high_mutates_the_accepted_set(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    refreshed = []

    async def fake_refresh(req, *, message_key, params, expire=False):
        refreshed.append(dict(params))
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    state = wizard.seed_review_state(99, 42, _draft(
        _rec(), _rec(binding="mod_channel", confidence="medium")))
    reply = run(_resolve("setup.review_accept_high")(_req()))
    assert reply is None
    assert state.count == 1
    # shipped status line, verbatim (main_panel._accept_high).
    assert refreshed[0]["review_status"] == (
        "Accepted 1 high-confidence recommendation(s); total accepted: 1.")
    # re-click adds nothing (the AcceptedSet dedup key).
    run(_resolve("setup.review_accept_high")(_req()))
    assert state.count == 1


def test_reject_ai_reports_zero_on_the_deterministic_draft(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    state = wizard.seed_review_state(99, 42, _draft(_rec()))
    state.add(_rec())
    run(_resolve("setup.review_reject_ai")(_req()))
    assert len(state.draft.recommendations) == 1
    # shipped status line, verbatim (main_panel._reject_ai).
    assert state.last_status == (
        "Rejected 0 AI suggestion(s); accepted set refreshed to 1.")


def test_one_by_one_empty_draft_answers_the_shipped_guard():
    from sb.domain.setup import wizard

    wizard.seed_review_state(99, 42, _draft())
    reply = run(_resolve("setup.review_one_by_one")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (main_panel._review_each).
    assert reply.user_message == "Nothing to review — the draft is empty."


def test_one_by_one_walkthrough_accept_deny_and_return(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)

    state = wizard.seed_review_state(99, 42, _draft(
        _rec(), _rec(binding="mod_channel", confidence="medium")))
    run(_resolve("setup.review_one_by_one")(_req()))
    assert opened == ["setup.review_item"]
    assert state.index == 0

    run(_resolve("setup.review_item_accept")(_req()))
    assert state.count == 1
    assert state.index == 1
    # denying the second advances past the end → back to the overview
    # with the shipped finished status line.
    run(_resolve("setup.review_item_deny")(_req()))
    assert opened == ["setup.review_item", "setup.suggestions_card"]
    assert state.last_status == (
        "Per-recommendation review finished; accepted set: 1.")


def test_review_item_render_pins_the_shipped_walkthrough_bytes():
    from sb.domain.setup import wizard
    from sb.domain.setup.panels import review_item_spec

    state = wizard.seed_review_state(99, 42, _draft(
        _rec(), _rec(binding="mod_channel", confidence="medium")))
    state.add(_rec())
    rendered = run(_resolve("setup.review_item_render")(
        review_item_spec(), _ctx()))
    embed = rendered.embed
    assert embed.title == "🤖 Suggestion 1 / 2 · ✅ accepted"
    assert "**Subsystem:** `logging`" in embed.description
    assert "**Binding:** `audit_channel` (`channel`)" in embed.description
    assert "**Target:** `audit` (id `1234`)" in embed.description
    assert embed.footer == ("Accepted set: 1 · Accept / Deny / Edit · "
                            "Skip to defer, Back to return.")
    assert embed.style_token == "green"
    state.index = 1
    rendered = run(_resolve("setup.review_item_render")(
        review_item_spec(), _ctx()))
    assert rendered.embed.title == "🤖 Suggestion 2 / 2 · ⬜ pending"
    assert rendered.embed.style_token == "gold"


def test_review_item_render_keeps_one_edit_face_per_mode():
    """The mode-dependent Edit control (per_recommendation._edit): the
    bind face keeps the explain button, the create face keeps the
    rename-modal button, never both."""
    from sb.domain.setup import wizard
    from sb.domain.setup.panels import review_item_spec

    wizard.seed_review_state(99, 42, _draft(_rec()))
    rendered = run(_resolve("setup.review_item_render")(
        review_item_spec(), _ctx()))
    ids = {c.custom_id for c in rendered.components}
    assert "setup.review_item.item_edit" in ids
    assert "setup.review_item.item_edit_rename" not in ids

    wizard.seed_review_state(99, 42, _draft(_rec(mode="create")))
    rendered = run(_resolve("setup.review_item_render")(
        review_item_spec(), _ctx()))
    ids = {c.custom_id for c in rendered.components}
    assert "setup.review_item.item_edit_rename" in ids
    assert "setup.review_item.item_edit" not in ids


def test_review_item_render_create_mode_pins_the_oracle_bytes():
    """build_per_recommendation_embed's create branch, verbatim: the
    Create & bind target line + the Edit-to-rename footer hint."""
    from sb.domain.setup import wizard
    from sb.domain.setup.panels import review_item_spec

    wizard.seed_review_state(99, 42, _draft(_rec(mode="create")))
    rendered = run(_resolve("setup.review_item_render")(
        review_item_spec(), _ctx()))
    embed = rendered.embed
    assert ("**Create & bind:** ➕ `audit` (new `channel`)"
            in embed.description)
    assert "**Target:**" not in embed.description
    assert embed.footer == (
        "Accepted set: 0 · Accept / Deny / Edit · Edit to rename before "
        "accepting · Skip to defer, Back to return.")


def test_review_item_edit_on_a_bind_suggestion_explains():
    """per_recommendation._edit's can't-re-pick branch, verbatim — the
    suggestion-edit slice's bind face (the native picker sub-view is
    the flagged follow-up)."""
    from sb.domain.setup import wizard

    wizard.seed_review_state(99, 42, _draft(_rec()))
    reply = run(_resolve("setup.review_item_edit")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "**Edit** can't re-pick a `channel` here — **Deny** this "
        "suggestion and bind a different one if it isn't right.")


def test_review_item_edit_rename_swaps_accepts_and_advances(monkeypatch):
    """_EditRecommendationModal.on_submit → apply_edit →
    _swap_and_accept, ported: the create suggestion's target name is
    rewritten in the shared draft, the edited row is accepted under
    the unchanged binding key, and the walkthrough advances."""
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    old = _rec(mode="create")
    state = wizard.seed_review_state(99, 42, _draft(
        old, _rec(binding="mod_channel", confidence="medium")))
    state.add(old)
    reply = run(_resolve("setup.review_item_edit_rename")(
        _req(args={"new_name": "  audit-log  "})))
    assert reply is None
    edited = state.draft.recommendations[0]
    assert edited.target_name == "audit-log"       # stripped, oracle body
    assert edited.mode == "create"
    assert edited.binding_name == old.binding_name  # key unchanged
    # re-accepted: the OLD row is out, the EDITED row is in.
    assert state.count == 1
    assert state.contains(edited)
    assert state.accepted[0].target_name == "audit-log"
    assert state.index == 1                        # advanced


def test_review_item_edit_rename_empty_name_answers_the_shipped_copy():
    from sb.domain.setup import wizard

    state = wizard.seed_review_state(99, 42, _draft(_rec(mode="create")))
    reply = run(_resolve("setup.review_item_edit_rename")(
        _req(args={"new_name": "   "})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (_EditRecommendationModal.on_submit).
    assert reply.user_message == (
        "The name can't be empty — nothing was changed.")
    assert state.index == 0                        # did not advance
    assert state.draft.recommendations[0].target_name == "audit"


def test_review_item_edit_rename_on_a_bind_row_refuses_stale_form():
    """A submit landing after the walkthrough moved onto a bind row
    (stale form) changes nothing — the bind explanation answers."""
    from sb.domain.setup import wizard

    state = wizard.seed_review_state(99, 42, _draft(_rec()))
    reply = run(_resolve("setup.review_item_edit_rename")(
        _req(args={"new_name": "audit-log"})))
    assert reply.outcome == BLOCKED
    assert "can't re-pick" in reply.user_message
    assert state.draft.recommendations[0].target_name == "audit"
    assert state.count == 0


def test_review_item_edit_out_of_range_returns_to_overview(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    state = wizard.seed_review_state(99, 42, _draft(_rec()))
    state.index = 5
    run(_resolve("setup.review_item_edit")(_req()))
    assert opened == ["setup.suggestions_card"]
    state.index = 5
    run(_resolve("setup.review_item_edit_rename")(
        _req(args={"new_name": "audit-log"})))
    assert opened == ["setup.suggestions_card", "setup.suggestions_card"]


def test_stage_without_accepts_answers_the_shipped_guard():
    from sb.domain.setup import wizard

    wizard.seed_review_state(99, 42, _draft(_rec()))
    reply = run(_resolve("setup.review_stage")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (main_panel._stage_final).
    assert reply.user_message == (
        "Accept at least one suggestion first — use **Accept all "
        "high-confidence** or **Review one-by-one**.")


def test_stage_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    state = wizard.seed_review_state(99, 42, _draft(_rec()))
    state.add(_rec())
    reply = run(_resolve("setup.review_stage")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (main_panel._stage_final).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can stage setup "
        "operations. Ask the owner to grant you `/setup-delegate`.")


def test_stage_writes_the_draft_then_opens_final_review(monkeypatch):
    """The shipped _stage_final flow: stage the accepted set, then land
    on the FinalReviewView (the final-review slice's live destination —
    the earlier staged-confirmation text retired with the honest
    terminal it carried)."""
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    staged = []

    async def fake_stage(guild_id, accepted):
        staged.append((guild_id, list(accepted)))
        return len(accepted)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(wizard, "stage_accepted", fake_stage)
    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    state = wizard.seed_review_state(99, 42, _draft(_rec()))
    state.add(_rec())
    reply = run(_resolve("setup.review_stage")(_req()))
    assert reply is None
    assert staged == [(99, state.accepted)]
    assert opened == ["setup.final_review"]
    assert state.last_status == "Staged 1 operation into the setup draft."


def test_stage_accepted_replaces_the_suggestions_rows(monkeypatch):
    """The oracle replace_recommended_for_section semantics over the K9
    store: prior [suggestions] rows drop, the accepted set appends as
    draftable bind_channel operations."""
    from sb.domain.setup import wizard
    from sb.kernel.draft import store as draft_store_module
    from sb.spec.draft import DraftStatus

    prior_op = SimpleNamespace(label="[suggestions] logging.bind_channel",
                               op_seq=1)
    open_draft = SimpleNamespace(draft_id="d-1", operations=(prior_op,),
                                 status=DraftStatus.OPEN)
    calls = {"removed": [], "added": [], "created": 0}

    class FakeStore:
        async def list_open(self, scope):
            return (open_draft,)

        async def remove(self, draft_id, op_seq):
            calls["removed"].append((draft_id, op_seq))

        async def add(self, draft_id, op):
            calls["added"].append((draft_id, op))

    monkeypatch.setattr(draft_store_module, "DraftStore", FakeStore)
    staged = run(wizard.stage_accepted(99, [_rec(), _rec(
        binding="mod_channel", target_id=5678, target_name="mod-log")]))
    assert staged == 2
    assert calls["removed"] == [("d-1", 1)]
    kinds = [op.op_kind for _d, op in calls["added"]]
    assert kinds == ["bind_channel", "bind_channel"]
    payload = calls["added"][0][1].payload
    # ``target_name`` rides above the op-kind's declared minimum so the
    # (possibly Edit-renamed) name round-trips into the final-review
    # pending line (the suggestion-edit slice).
    assert payload == {"subsystem": "logging", "name": "audit_channel",
                       "kind": "channel", "resource_id": 1234,
                       "target_name": "audit"}
    assert calls["added"][0][1].label == "[suggestions] logging.bind_channel"
    # the op kind is DRAFTABLE (fail-closed registry) and bound to the
    # audited settings.bind K7 op.
    from sb.kernel.draft.registry import OP_KINDS

    binding = OP_KINDS.get("bind_channel")
    assert binding is not None
    assert binding.workflow_ref.name == "settings.bind"


def test_staged_target_name_round_trips_into_the_final_review_line(
        monkeypatch):
    """The suggestion-edit slice's round-trip: an Edit-renamed create
    suggestion stages with its new name, and the final-review pending
    line renders it (draft_render._short_label's bind branch prefers
    ``target_name`` over the raw id)."""
    from sb.domain.setup import wizard
    from sb.domain.setup.final_review import _short_label
    from sb.kernel.draft import store as draft_store_module

    calls = {"added": []}

    class FakeStore:
        async def list_open(self, scope):
            return ()

        async def create(self, *, producer, owner_scope):
            return SimpleNamespace(draft_id="d-1", operations=())

        async def add(self, draft_id, op):
            calls["added"].append(op)

    monkeypatch.setattr(draft_store_module, "DraftStore", FakeStore)
    run(wizard.stage_accepted(
        99, [_rec(mode="create", target_id=0, target_name="audit-log")]))
    assert _short_label(calls["added"][0]) == (
        "logging.audit_channel → audit-log")


# --- /setup-skip · /setup-unskip · /setup-reset ----------------------------------------


def test_skip_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.skip_section")(
        _req(args={"section": "cleanup"})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (setup_cog._toggle_skip).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can change a "
        "section's skipped state.")


def test_skip_unknown_section_stays_golden(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    reply = run(_resolve("setup.skip_section")(_req(args={"section": "test"})))
    assert reply.outcome == BLOCKED
    # the golden-pinned refusal byte (goldens/setup/sweep_slash_setup-skip).
    assert reply.user_message.startswith("Unknown section `test`. Available:")


def test_skip_and_unskip_ride_the_k7_op(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    ran = []

    async def fake_run(ref, ctx):
        ran.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    reply = run(_resolve("setup.skip_section")(
        _req(args={"section": "cleanup"})))
    assert reply.outcome == SUCCESS
    # shipped ack, verbatim.
    assert reply.user_message == "✅ Section `cleanup` skipped."
    reply = run(_resolve("setup.unskip_section")(
        _req(args={"section": "cleanup"})))
    assert reply.user_message == "✅ Section `cleanup` un-skipped."
    assert ran == [
        ("setup.set_section_skip", {"section": "cleanup", "skipped": True}),
        ("setup.set_section_skip", {"section": "cleanup", "skipped": False}),
    ]


def test_skip_write_failure_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_run(ref, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(wf_engine, "run", fake_run)
    reply = run(_resolve("setup.skip_section")(
        _req(args={"section": "cleanup"})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == "Could not update the skip state — see logs."


def test_reset_empty_draft_stays_golden(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_count(guild_id):
        return 0

    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)
    reply = run(_resolve("setup.reset_view")(_req()))
    assert reply.outcome == SUCCESS
    # the golden-pinned byte (goldens/setup/sweep_slash_setup-reset).
    assert reply.user_message == ("No staged operations to clear — the "
                                  "draft is already empty.")


def test_reset_clears_the_staged_draft(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_count(guild_id):
        return 3

    cleared = []

    async def fake_clear(guild_id):
        cleared.append(guild_id)
        return 3

    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)
    monkeypatch.setattr(wizard, "clear_guild_drafts", fake_clear)
    reply = run(_resolve("setup.reset_view")(_req()))
    assert reply.outcome == SUCCESS
    assert cleared == [99]
    # shipped copy, verbatim (setup_reset_slash's cleared reply).
    assert reply.user_message == (
        "✅ Cleared **3** staged operations. The session keeps its status "
        "and depth — run `!setupadvanced` or `/setup-advanced` to "
        "continue.")


def test_reset_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.reset_view")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (setup_reset_slash).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can reset "
        "staged setup operations.")


# --- the apply-authority gate ladder ----------------------------------------------------


def test_gate_ladder_owner_delegate_and_deny(monkeypatch):
    from sb.domain.setup import store, wizard

    async def fake_row(guild_id, conn=None):
        return {"owner_id": 42, "delegated_admins": [7]}

    monkeypatch.setattr(store, "get_session_row", fake_row)
    assert run(wizard.can_apply_setup(_req(user_id=42))) is True     # owner
    assert run(wizard.can_apply_setup(_req(user_id=7))) is True      # delegate
    assert run(wizard.can_apply_setup(_req(user_id=13))) is False    # admin w/o delegation


def test_gate_fails_closed_when_the_session_read_breaks(monkeypatch):
    from sb.domain.setup import store, wizard

    async def broken_row(guild_id, conn=None):
        raise RuntimeError("no db")

    monkeypatch.setattr(store, "get_session_row", broken_row)
    assert run(wizard.can_apply_setup(_req(user_id=42))) is False


# --- wiring -----------------------------------------------------------------------------


def test_interior_panels_ride_the_manifest():
    import sb.manifest.setup as m

    panel_ids = [p.panel_id for p in m.MANIFEST.panels]
    assert panel_ids == [
        "setup.hub", "setup.essential_card", "setup.status_card",
        "setup.suggestions_card", "setup.sections_hub", "setup.review_item",
        "setup.final_review", "setup.apply_recovery", "setup.complete_card",
        # the essential-steps slice: steps 2–8 + summary/extras + resume.
        "setup.essential_greet", "setup.essential_mods",
        "setup.essential_spam", "setup.essential_log",
        "setup.essential_reward", "setup.essential_reward_role",
        "setup.essential_helpdesk", "setup.essential_commands",
        "setup.essential_summary", "setup.essential_extras",
        "setup.essential_resume",
        # the section-flows slice: the linear wizard steps + the
        # channels card/detail pair + the preset card/preview pair.
        "setup.wizard_step", "setup.section_channels",
        "setup.channels_detail", "setup.preset_card",
        "setup.preset_preview"]
    hub = m.MANIFEST.panels[0]
    routes = {a.action_id: a.handler.name for a in hub.actions}
    assert routes == {
        "depth_quick": "setup.depth_pick_quick",
        "depth_standard": "setup.depth_pick_standard",
        "depth_advanced": "setup.depth_pick_advanced"}
    essential = m.MANIFEST.panels[1]
    assert essential.selectors[0].on_select.name == "setup.essential_pick"
    suggestions = m.MANIFEST.panels[3]
    assert {a.handler.name for a in suggestions.actions} == {
        "setup.review_accept_high", "setup.review_one_by_one",
        "setup.review_reject_ai", "setup.review_rerun",
        "setup.review_stage"}


def test_review_item_edit_pair_carries_the_g10_form():
    """The suggestion-edit slice's wiring: two Edit faces (both labeled
    Edit — the renderer keeps one per mode); the create face is the
    declared G-10 rename modal, submit routed to the rename handler."""
    from sb.spec.outcomes import DeferMode

    import sb.manifest.setup as m

    review_item = m.MANIFEST.panels[5]
    assert review_item.panel_id == "setup.review_item"
    actions = {a.action_id: a for a in review_item.actions}
    plain = actions["item_edit"]
    assert plain.label == "Edit"
    assert plain.handler.name == "setup.review_item_edit"
    assert plain.modal is None
    rename = actions["item_edit_rename"]
    assert rename.label == "Edit"
    assert rename.defer_mode is DeferMode.MODAL
    assert rename.modal is not None
    assert rename.modal.modal_id == "setup.review_item_edit_form"
    assert rename.modal.title == "Edit suggestion"
    field = rename.modal.fields[0]
    assert field.field_id == "new_name"
    assert (field.required, field.min_length, field.max_length) == (
        True, 1, 100)
    assert rename.modal.on_submit.name == "setup.review_item_edit_rename"
    assert rename.handler.name == "setup.review_item_edit_rename"


def test_every_interior_route_resolves():
    from sb.spec.refs import HandlerRef, resolve

    for name in (
            "setup.depth_pick_quick", "setup.depth_pick_standard",
            "setup.depth_pick_advanced", "setup.change_depth",
            "setup.back_to_wizard", "setup.essential_pick",
            "setup.essential_save", "setup.essential_skip",
            "setup.review_accept_high", "setup.review_one_by_one",
            "setup.review_reject_ai", "setup.review_rerun",
            "setup.review_stage", "setup.review_item_accept",
            "setup.review_item_deny", "setup.review_item_skip",
            "setup.review_item_back", "setup.review_item_edit",
            "setup.review_item_edit_rename",
            *(f"setup.open_section_{slug}" for slug in (
                "preset_select", "channels", "logging_presets", "roles",
                "role_templates", "cleanup", "moderation", "cog_routing",
                "ticket", "final_review"))):
        assert resolve(HandlerRef(name)) is not None
