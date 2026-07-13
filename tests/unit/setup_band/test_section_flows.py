"""The section-flow spine + the first two per-section flows (the
section-flows slice — sb/domain/setup/section_card.py · wizard_nav.py ·
preset_select.py · channels.py).

DB-free like the wizard-interior suite: the K7/K9 write seams are
monkeypatched at their module functions and the assertions pin the
ORACLE bytes the click paths carry (no golden drives a click on these
components — the panels.py module pin; oracle sources:
views/setup/section_card.py, views/setup/wizard.py +
views/setup/wizard_nav.py, views/setup/sections/preset_select.py,
views/setup/sections/channels.py, services/setup_progress.py,
services/automation_templates.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import channels, preset_select, wizard, wizard_nav

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()


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


def _op(label, op_kind="bind_channel", subsystem="logging", payload=None,
        op_seq=1):
    return SimpleNamespace(label=label, op_kind=op_kind,
                           subsystem=subsystem,
                           payload=dict(payload or {"name": "mod_channel"}),
                           op_seq=op_seq, authority_ref="", dedup_token="")


def _section(slug):
    from sb.domain.setup.sections import REGISTRY, register_shipped_sections

    register_shipped_sections()
    section = REGISTRY.get(slug)
    assert section is not None
    return section


def _fake_session_row(monkeypatch, row):
    from sb.domain.setup import store

    async def fake_row(guild_id, conn=None):
        return dict(row) if row is not None else None

    monkeypatch.setattr(store, "get_session_row", fake_row)


def _fake_guild_drafts(monkeypatch, drafts):
    from sb.domain.setup import wizard

    async def fake_open(guild_id):
        return tuple(drafts)

    monkeypatch.setattr(wizard, "_open_guild_drafts", fake_open)


class _FakeStore:
    """The K9 DraftStore surface the spine drives (the wizard-interior
    FakeStore precedent)."""

    def __init__(self, drafts=()):
        self.drafts = list(drafts)
        self.removed: list[tuple[str, int]] = []
        self.added: list = []
        self.created = 0

    async def list_open(self, scope):
        return tuple(self.drafts)

    async def create(self, *, producer, owner_scope):
        self.created += 1
        draft = SimpleNamespace(draft_id="d-new", operations=())
        self.drafts.append(draft)
        return draft

    async def remove(self, draft_id, op_seq):
        self.removed.append((draft_id, op_seq))

    async def add(self, draft_id, op):
        self.added.append((draft_id, op))


def _patch_store(monkeypatch, store):
    from sb.kernel.draft import store as draft_store_module

    monkeypatch.setattr(draft_store_module, "DraftStore", lambda: store)


# --- the ported status vocabulary (services/setup_progress.py) --------------------------


def test_status_badges_and_labels_are_the_shipped_bytes():
    from sb.domain.setup import section_card as sc

    assert sc.badge_for(sc.NOT_STARTED) == "⬜"
    assert sc.badge_for(sc.RECOMMENDED) == "✅"
    assert sc.badge_for(sc.CUSTOMIZED) == "🟡"
    assert sc.badge_for(sc.SKIPPED) == "⚠️"
    assert sc.badge_for(sc.NEEDS_ATTENTION) == "❗"
    assert sc.badge_for(sc.APPLIED) == "✅"
    assert sc.status_label(sc.RECOMMENDED) == "Recommended selected"
    assert sc.status_label(sc.NOT_STARTED) == "Not started"


def test_compute_section_status_decision_order():
    from sb.domain.setup import section_card as sc

    channels = _section("channels")
    rec_row = _op("[recommended:channels] bind_channel")
    custom_row = _op("[channels] logging.mod_channel → #mod-log")
    # 1. skipped wins over staging state.
    p = sc.compute_section_status(
        channels, session={"skipped_sections": ["channels"]},
        ops=[rec_row])
    assert (p.status, p.pending_ops) == (sc.SKIPPED, 0)
    # 2. complete → applied (pending carried).
    p = sc.compute_section_status(
        channels, session={"setup_status": "complete"}, ops=[rec_row])
    assert (p.status, p.pending_ops) == (sc.APPLIED, 1)
    # 3. acknowledged with no staging → applied.
    p = sc.compute_section_status(
        channels, session={"acknowledged_sections": ["channels"],
                           "setup_status": "in_progress"}, ops=[])
    assert p.status == sc.APPLIED
    # 4. nothing → not started.
    p = sc.compute_section_status(channels, session=None, ops=[])
    assert p.status == sc.NOT_STARTED
    # 5. all recommended → recommended; any custom → customized.
    p = sc.compute_section_status(channels, session=None, ops=[rec_row])
    assert (p.status, p.pending_ops) == (sc.RECOMMENDED, 1)
    p = sc.compute_section_status(channels, session=None,
                                  ops=[rec_row, custom_row])
    assert (p.status, p.pending_ops) == (sc.CUSTOMIZED, 2)


def test_null_provenance_rows_fall_back_to_op_kinds():
    """The oracle matching strategy: a row with no section provenance
    (the suggestions lane, preset rows) matches by op kind."""
    from sb.domain.setup import section_card as sc

    channels = _section("channels")
    preset_row = _op("[Community] bind_channel · logging.mod_channel")
    p = sc.compute_section_status(channels, session=None, ops=[preset_row])
    assert p.status == sc.CUSTOMIZED
    # preset_select declares NO op_kinds — read-only fallback never
    # matches (the shipped quirk: preset rows count against channels).
    preset_section = _section("preset_select")
    p = sc.compute_section_status(preset_section, session=None,
                                  ops=[preset_row])
    assert p.status == sc.NOT_STARTED


# --- the section card embed (section_card.build_section_card) ---------------------------


def test_section_card_embed_pins_the_shipped_bytes():
    from sb.domain.setup import section_card as sc

    channels = _section("channels")
    progress = sc.SectionProgress(slug="channels", status=sc.NOT_STARTED,
                                  pending_ops=0)
    embed = sc.build_section_card_embed(
        section=channels, progress=progress,
        detected_state="Detected copy.", has_recommended=True,
        has_customize=True)
    assert embed.title == "📡 Channels & log routing"
    # channels is section 2 of the 10 registrants (order 40).
    assert embed.description == "**Step 2 of 10** · ⬜ *Not started*"
    fields = {f[0]: f[1] for f in embed.fields}
    assert fields["Detected"] == "Detected copy."
    assert fields["Recommended action"] == (
        "Click **Apply Recommended** to stage the section's safe defaults.")
    assert fields["If you skip this"].startswith(
        "SuperBot keeps the current command-channel rules")
    assert "Pending" not in fields
    assert embed.footer == ("Customize to open the detailed picker · "
                            "Final Review applies all staged ops")
    assert embed.style_token == "blurple"


def test_section_card_embed_pending_and_status_accents():
    from sb.domain.setup import section_card as sc

    channels = _section("channels")
    progress = sc.SectionProgress(slug="channels", status=sc.RECOMMENDED,
                                  pending_ops=2)
    embed = sc.build_section_card_embed(
        section=channels, progress=progress, detected_state="",
        has_recommended=False, has_customize=False)
    fields = {f[0]: f[1] for f in embed.fields}
    assert fields["Detected"] == "_(no state detected)_"
    assert fields["Recommended action"] == (
        "_(this section has no recommended defaults — use Customize.)_")
    assert fields["Pending"] == "2 operations staged for Final review."
    assert embed.footer == "Final Review applies all staged ops"
    assert embed.style_token == "green"


# --- the staging seams -------------------------------------------------------------------


def test_replace_recommended_drops_prior_and_preserves_conflicts(monkeypatch):
    from sb.domain.setup import section_card as sc

    stale = _op("[recommended:channels] bind_channel",
                payload={"subsystem": "logging", "name": "mod_channel"},
                op_seq=1)
    custom = _op("[channels] logging.audit_channel → #audit",
                 payload={"subsystem": "logging", "name": "audit_channel"},
                 op_seq=2)
    draft = SimpleNamespace(draft_id="d-1", operations=(stale, custom))
    store = _FakeStore([draft])
    _patch_store(monkeypatch, store)

    ops = [
        sc.StagedSectionOp(op_kind="bind_channel", subsystem="logging",
                           payload={"subsystem": "logging",
                                    "name": "mod_channel", "kind": "channel",
                                    "resource_id": 1, "target_name": "m"}),
        sc.StagedSectionOp(op_kind="bind_channel", subsystem="logging",
                           payload={"subsystem": "logging",
                                    "name": "audit_channel",
                                    "kind": "channel", "resource_id": 2,
                                    "target_name": "a"}),
    ]
    result = run(sc.replace_recommended_for_section(99, "channels", ops))
    # the stale recommended row dropped; the custom row's slot refused
    # the overwrite (conflict) — only mod_channel re-staged.
    assert result.deleted == 1
    assert store.removed == [("d-1", 1)]
    assert result.inserted == 1
    assert result.conflicts == ["[channels] logging.audit_channel → #audit"]
    _did, added = store.added[0]
    assert added.label == "[recommended:channels] bind_channel"
    assert added.payload["name"] == "mod_channel"


def test_stage_custom_replaces_the_same_slot(monkeypatch):
    from sb.domain.setup import section_card as sc

    prior = _op("[channels] logging.mod_channel → #old",
                payload={"subsystem": "logging", "name": "mod_channel"},
                op_seq=7)
    draft = SimpleNamespace(draft_id="d-1", operations=(prior,))
    store = _FakeStore([draft])
    _patch_store(monkeypatch, store)
    run(sc.stage_custom(99, "channels", sc.StagedSectionOp(
        op_kind="bind_channel", subsystem="logging",
        payload={"subsystem": "logging", "name": "mod_channel",
                 "kind": "channel", "resource_id": 5,
                 "target_name": "#new"},
        label_body="logging.mod_channel → #new")))
    assert store.removed == [("d-1", 7)]
    assert store.added[0][1].label == "[channels] logging.mod_channel → #new"


def test_delete_section_rows_is_provenance_strict(monkeypatch):
    from sb.domain.setup import section_card as sc

    rows = (
        _op("[recommended:channels] bind_channel", op_seq=1),
        _op("[channels] logging.mod_channel → #m", op_seq=2),
        _op("[suggestions] logging.bind_channel", op_seq=3),
        _op("[Community] bind_channel · logging.mod_channel", op_seq=4),
    )
    draft = SimpleNamespace(draft_id="d-1", operations=rows)
    store = _FakeStore([draft])
    _patch_store(monkeypatch, store)
    _fake_guild_drafts(monkeypatch, [draft])
    deleted = run(sc.delete_section_rows(99, "channels"))
    # only the section-OWNED rows drop; null-provenance rows are never
    # guessed at (the oracle list_by_section semantics).
    assert deleted == 2
    assert store.removed == [("d-1", 1), ("d-1", 2)]


# --- the card handlers -------------------------------------------------------------------


def test_card_gate_refusal_is_the_stage_or_skip_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.section_skip_channels")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (SectionCardView._gate_apply).
    assert reply.user_message == (
        "Only the server owner or a delegated setup admin can stage "
        "or skip setup operations. Ask the server owner to grant "
        "you `/setup-delegate`.")


def test_card_skip_records_and_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    ran = []

    async def fake_run(ref, ctx):
        ran.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    reply = run(_resolve("setup.section_skip_channels")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (SectionCardView._skip).
    assert reply.user_message == (
        "Marked **Channels & log routing** as skipped. "
        "Reopen the section any time to change your mind.")
    assert ran == [("setup.set_section_skip",
                    {"section": "channels", "skipped": True})]


def test_card_hub_answers_the_shipped_copy():
    reply = run(_resolve("setup.section_hub_channels")(_req()))
    assert reply.outcome == SUCCESS
    assert reply.user_message == "Returning to the setup hub above."


def test_card_apply_recommended_stages_and_answers(monkeypatch):
    from sb.domain.setup import section_card as sc
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)

    async def fake_builder(guild_id):
        return [sc.StagedSectionOp(
            op_kind="bind_channel", subsystem="logging",
            payload={"subsystem": "logging", "name": "mod_channel",
                     "kind": "channel", "resource_id": 1,
                     "target_name": "mod-log"})]

    monkeypatch.setitem(sc._RECOMMENDED_BUILDERS, "channels", fake_builder)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)

    reply = run(_resolve("setup.section_apply_channels")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (SectionCardView._apply_recommended).
    assert reply.user_message == (
        "Staged **1 recommended operation** for Channels & log routing. "
        "Open Final review to apply.")
    assert len(store.added) == 1


def test_card_apply_recommended_empty_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import section_card as sc
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def empty_builder(guild_id):
        return []

    monkeypatch.setitem(sc._RECOMMENDED_BUILDERS, "channels", empty_builder)
    reply = run(_resolve("setup.section_apply_channels")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == (
        "No recommended operations were generated for this section.")


def test_card_render_composes_the_embed(monkeypatch):
    from sb.domain.setup import section_card as sc

    _fake_session_row(monkeypatch, None)
    _fake_guild_drafts(monkeypatch, [])
    rendered = run(_resolve("setup.section_card_render_channels")(
        sc.card_spec_for("channels"), _ctx()))
    assert rendered.embed.description == "**Step 2 of 10** · ⬜ *Not started*"
    ids = [c.custom_id for c in rendered.components]
    assert ids == [
        "setup_card:channels:apply_recommended",
        "setup_card:channels:customize",
        "setup_card:channels:skip",
        "setup_card:channels:hub"]
    # channels registers both a builder and a customize panel — no
    # disabled buttons (the shipped construction).
    assert not any(c.disabled for c in rendered.components)


# --- the linear wizard steps (wizard_nav) ---------------------------------------------------


def test_back_to_wizard_gate_refusal_keeps_the_hub_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.back_to_wizard")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == wizard.GATE_MSG_WIZARD


def test_back_to_wizard_resumes_at_the_persisted_step(monkeypatch):
    from sb.domain.setup import wizard, wizard_nav
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": "logging_presets",
        "skipped_sections": [], "acknowledged_sections": []})
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.back_to_wizard")(_req())) is None
    assert opened == ["setup.wizard_step"]
    # quick depth: preset_select · channels · logging_presets ·
    # final_review — the persisted slug resolves to index 2.
    assert wizard_nav.step_index(99, 42) == 2


def test_wizard_step_render_pins_the_shipped_embed(monkeypatch):
    from sb.domain.setup import wizard_nav

    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    _fake_guild_drafts(monkeypatch, [])
    rendered = run(_resolve("setup.wizard_step_render")(
        wizard_nav.wizard_step_spec(), _ctx()))
    embed = rendered.embed
    assert embed.title == "🛰 SuperBot setup wizard · Step 1/4"
    assert embed.description == "⬜ **Load preset** (not started)"
    fields = {f[0]: f[1] for f in embed.fields}
    assert fields["Current state"] == "_(nothing staged for this step yet)_"
    # preset_select has no recommended builder — the shipped
    # no-defaults copy.
    assert fields["Recommended action"] == (
        "_(no recommended defaults — use Customize to open the "
        "section's detail view.)_")
    assert fields["If you skip this"].startswith("No bundled preset")
    assert embed.footer == ("Nothing changes until Final Review applies "
                            "the staged operations.")
    by_id = {c.custom_id: c for c in rendered.components}
    # step 0: Back disabled; preset_select has no builder/detail —
    # Apply Recommended + Customize disabled (the shipped construction).
    assert by_id["setup_wizard:back"].disabled
    assert by_id["setup_wizard:apply_recommended"].disabled
    assert by_id["setup_wizard:customize"].disabled
    assert not by_id["setup_wizard:skip"].disabled
    assert by_id["setup_wizard:continue"].label == "Continue ▶"
    assert by_id["setup_wizard:continue"].style == "secondary"
    # channels (in-depth) carries a builder → Apply-all renders.
    assert "setup_wizard:apply_all_recommended" in by_id
    assert "setup_wizard:jump" in by_id


def test_wizard_step_render_last_step_flips_continue(monkeypatch):
    from sb.domain.setup import wizard_nav

    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    _fake_guild_drafts(monkeypatch, [])
    wizard_nav._set_step_index(99, 42, 3)   # final_review — last of quick
    rendered = run(_resolve("setup.wizard_step_render")(
        wizard_nav.wizard_step_spec(), _ctx()))
    by_id = {c.custom_id: c for c in rendered.components}
    assert by_id["setup_wizard:continue"].label == "Final Review"
    assert by_id["setup_wizard:continue"].style == "primary"
    assert not by_id["setup_wizard:back"].disabled


def test_wizard_continue_last_step_opens_final_review(monkeypatch):
    from sb.domain.setup import wizard_nav
    from sb.kernel.panels import engine as panels_engine

    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    wizard_nav._set_step_index(99, 42, 3)
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.wizard_continue")(_req())) is None
    assert opened == ["setup.final_review"]


def test_wizard_cancel_answers_the_shipped_copy():
    reply = run(_resolve("setup.wizard_cancel")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (LinearWizardView._on_cancel).
    assert reply.user_message == (
        "Wizard closed.  Re-open with `/setup` or `!setup`; your draft "
        "is preserved.")


def test_wizard_skip_records_deletes_and_advances(monkeypatch):
    from sb.domain.setup import section_card as sc
    from sb.domain.setup import wizard, wizard_nav
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_delete(guild_id, slug):
        return 2

    monkeypatch.setattr(sc, "delete_section_rows", fake_delete)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    wizard_nav._set_step_index(99, 42, 0)
    reply = run(_resolve("setup.wizard_skip")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (wizard._on_skip).
    assert reply.user_message == (
        "⏭ Skipped **Load preset**.\n\n"
        "Removed 2 staged op(s) for this section.")
    assert wizard_nav.step_index(99, 42) == 1


def test_wizard_apply_recommended_answers_the_notice_copy(monkeypatch):
    from sb.domain.setup import section_card as sc
    from sb.domain.setup import wizard, wizard_nav
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    wizard_nav._set_step_index(99, 42, 1)   # channels

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)

    async def fake_builder(guild_id):
        return [sc.StagedSectionOp(
            op_kind="bind_channel", subsystem="logging",
            payload={"subsystem": "logging", "name": "mod_channel",
                     "kind": "channel", "resource_id": 1,
                     "target_name": "mod-log"})]

    monkeypatch.setitem(sc._RECOMMENDED_BUILDERS, "channels", fake_builder)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    reply = run(_resolve("setup.wizard_apply_recommended")(_req()))
    assert reply.outcome == SUCCESS
    # the shipped workspace-notice copy, carried as the text reply.
    assert reply.user_message == (
        "✅ Recommended staged · Channels & log routing — "
        "Staged **1 operation**.")


def test_wizard_apply_recommended_no_builder_copy(monkeypatch):
    from sb.domain.setup import wizard, wizard_nav

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    wizard_nav._set_step_index(99, 42, 0)   # preset_select — no builder
    reply = run(_resolve("setup.wizard_apply_recommended")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == (
        "This step has no recommended defaults — use Customize to open "
        "the detail view.")


def test_wizard_jump_clamps_and_moves(monkeypatch):
    from sb.domain.setup import wizard_nav
    from sb.kernel.panels import engine as panels_engine

    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    run(_resolve("setup.wizard_jump")(_req(args={"values": ["2"]})))
    assert wizard_nav.step_index(99, 42) == 2
    run(_resolve("setup.wizard_jump")(_req(args={"values": ["99"]})))
    assert wizard_nav.step_index(99, 42) == 3   # clamped to the last step


def test_wizard_customize_marks_the_detail_origin(monkeypatch):
    from sb.domain.setup import wizard, wizard_nav
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    wizard_nav._set_step_index(99, 42, 1)   # channels — has a detail view
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.wizard_customize")(_req())) is None
    assert opened == ["setup.channels_detail"]
    assert wizard_nav.detail_from_wizard(99, 42)


def test_wizard_customize_without_detail_answers_the_shipped_copy(
        monkeypatch):
    from sb.domain.setup import wizard, wizard_nav

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _fake_session_row(monkeypatch, {
        "depth": "quick", "current_step": None,
        "skipped_sections": [], "acknowledged_sections": []})
    wizard_nav._set_step_index(99, 42, 0)   # preset_select — no detail
    reply = run(_resolve("setup.wizard_customize")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This step has no detail view."


# --- the preset flow ---------------------------------------------------------------------


def test_preset_catalogue_carries_the_shipped_bundles():
    from sb.domain.setup.preset_select import SERVER_PRESETS, get_preset

    assert [p.slug for p in SERVER_PRESETS] == [
        "minimal", "community", "gaming", "moderation-heavy", "economy",
        "existing-safe", "custom"]
    community = get_preset("community")
    assert community.display_name == "Community"
    assert [op.kind for op in community.operations] == [
        "bind_channel", "bind_channel", "bind_channel", "add_rule",
        "add_rule"]
    heavy = get_preset("moderation-heavy")
    assert heavy.operations[-1].kind == "set_setting"
    assert heavy.operations[-1].payload == {
        "subsystem": "logging", "name": "enabled", "value": True}
    assert get_preset("custom").operations == ()


def test_preset_adapter_maps_the_shipped_kinds():
    from sb.domain.setup.preset_select import (
        get_preset, staged_ops_for_preset,
    )

    rows = staged_ops_for_preset(get_preset("moderation-heavy"))
    kinds = [r[0] for r in rows]
    assert kinds == ["bind_channel"] * 4 + ["set_setting"]
    # the preset bind rows stage TARGET-LESS (the oracle's own shape).
    op_kind, subsystem, payload, label = rows[0]
    assert payload == {"subsystem": "logging", "name": "rules_channel",
                       "kind": "channel", "resource_id": None,
                       "target_name": None}
    assert label == "[Moderation heavy] bind_channel · logging.rules_channel"
    # the scalar row rides the audited settings.set_scalar seam.
    op_kind, subsystem, payload, label = rows[-1]
    assert payload["value"] == "true"
    # the persisted key rides the declared settings_key vocabulary
    # (ksettings.persisted_key — "logging_enabled" once the manifest
    # settings registry is loaded; the dotted fallback headless).
    from sb.kernel import settings as ksettings

    assert payload["key"] == ksettings.persisted_key("logging", "enabled")
    assert label == ("[Moderation heavy] set_setting · logging.enabled "
                     "= True")
    # add_rule adapts to the automation kind (fail-closed, un-registered).
    community = staged_ops_for_preset(get_preset("community"))
    assert community[-1][0] == "add_automation_rule"
    assert community[-1][1] == "automation"


def test_preset_open_gate_and_landing(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.open_section_preset_select")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == wizard.GATE_MSG_WIZARD

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.open_section_preset_select")(_req())) is None
    assert opened == ["setup.preset_card"]


def test_preset_card_render_pins_the_shipped_bytes(monkeypatch):
    from sb.domain.setup.preset_select import preset_card_spec

    rendered = run(_resolve("setup.preset_card_render")(
        preset_card_spec(), _ctx()))
    embed = rendered.embed
    assert embed.title == "🎛 Load a preset"
    assert embed.description.startswith(
        "Pick a preset to stage every operation it ships with in one go.")
    assert embed.footer == "Picking a preset opens a preview before staging."
    names = [f[0] for f in embed.fields]
    assert names[0] == "Minimal (`minimal`)"
    assert names[-1] == "Custom (`custom`)"
    assert len(names) == 7


def test_preset_pick_opens_the_preview(monkeypatch):
    from sb.domain.setup.preset_select import preset_preview_spec
    from sb.kernel.panels import engine as panels_engine

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.preset_pick")(
        _req(args={"values": ["community"]}))) is None
    assert opened == ["setup.preset_preview"]

    rendered = run(_resolve("setup.preset_preview_render")(
        preset_preview_spec(), _ctx()))
    embed = rendered.embed
    assert embed.title == "🎛 Community · preview"
    assert embed.description == (
        "**5** operation(s) would be staged.  Confirm to add them to the "
        "draft; nothing applies yet.")
    ops_field = {f[0]: f[1] for f in embed.fields}["Operations"]
    assert ops_field.splitlines()[0] == (
        "• `bind_channel` — Bind the welcome channel.")
    assert embed.footer == "Confirm below to stage every op in the draft."


def test_preset_confirm_stages_and_answers(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    async def fake_open(ref, req):
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_count(guild_id):
        return 5

    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)
    run(_resolve("setup.preset_pick")(_req(args={"values": ["community"]})))
    reply = run(_resolve("setup.preset_confirm")(_req()))
    assert reply.outcome == SUCCESS
    # shipped summary lines, verbatim (_stage_preset).
    assert reply.user_message == (
        "✅ Staged **5** operation(s) from preset `community`.\n"
        "Pending operations: **5**.")
    assert len(store.added) == 5
    labels = [op.label for _d, op in store.added]
    assert labels[0] == ("[Community] bind_channel · "
                         "onboarding.welcome_channel")
    assert labels[-1] == "[Community] add_automation_rule · automation"


def test_preset_cancel_answers_the_shipped_copy():
    reply = run(_resolve("setup.preset_cancel")(_req()))
    assert reply.outcome == SUCCESS
    assert reply.user_message == "Preset staging cancelled — draft unchanged."


# --- the channels flow -------------------------------------------------------------------


def test_channel_binding_walk_reads_the_declared_manifest_slots():
    from sb.domain.setup.channels import all_channel_bindings

    declared = {(sub, name) for sub, name, _r, _h in all_channel_bindings()}
    assert ("logging", "mod_channel") in declared
    assert ("logging", "audit_channel") in declared
    assert ("welcome", "channel") in declared
    assert ("xp", "announce_channel") in declared
    # the one-select adaptation holds while the walk stays ≤ 25.
    assert len(declared) <= 25


def test_channels_open_lands_on_the_section_card(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    ran = []

    async def fake_run(ref, ctx):
        ran.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    monkeypatch.setattr(wf_engine, "run", fake_run)
    assert run(_resolve("setup.open_section_channels")(_req())) is None
    assert opened == ["setup.section_channels"]
    # the shipped mark_in_progress rides the card open.
    assert ran == [("setup.mark_in_progress", {"step": "channels"})]


def test_channels_embed_fields_pin_the_shipped_bytes():
    from sb.domain.setup.channels import build_channels_embed_fields

    rec = SimpleNamespace(confidence="high", target_name="mod-log",
                          reason="channel name `mod-log` matches token "
                                 "`mod-log` (high)")
    fields = build_channels_embed_fields(
        [("logging", "mod_channel", False, "Moderation log channel."),
         ("welcome", "channel", True, "Greeting channel.")],
        {("logging", "mod_channel"): rec})
    as_dict = {f[0]: f[1] for f in fields}
    assert as_dict["logging"] == (
        "• `mod_channel` · ✅ likely `#mod-log` (high — channel name "
        "`mod-log` matches token `mod-log` (high))")
    assert as_dict["welcome"] == "• `channel` · *required*"


def test_channels_binding_pick_unknown_answers_the_shipped_copy():
    reply = run(_resolve("setup.channels_binding_pick")(
        _req(args={"values": ["nope::missing"]})))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (_attach_binding_select._on_pick).
    assert reply.user_message == (
        "No channel bindings declared by any subsystem.")


def test_channels_detail_render_reveals_the_picker_after_a_pick(monkeypatch):
    from sb.domain.setup import channels
    from sb.kernel.panels import engine as panels_engine

    spec = channels.channels_detail_spec()
    rendered = run(_resolve("setup.channels_detail_render")(spec, _ctx()))
    leaves = [c.custom_id.removeprefix(f"{spec.panel_id}.")
              for c in rendered.components]
    # no binding picked, not wizard-native → only the binding select.
    assert leaves == ["channels_binding"]
    assert rendered.embed.footer == (
        "Pick a binding from the select to choose a channel.")

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    run(_resolve("setup.channels_binding_pick")(
        _req(args={"values": ["logging::mod_channel"]})))
    rendered = run(_resolve("setup.channels_detail_render")(spec, _ctx()))
    by_leaf = {c.custom_id.removeprefix(f"{spec.panel_id}."): c
               for c in rendered.components}
    assert set(by_leaf) == {"channels_binding", "channels_channel"}
    # the oracle's dynamic placeholder, patched on.
    assert by_leaf["channels_channel"].placeholder == (
        "Pick a channel for logging.mod_channel")


def test_channels_channel_pick_stages_and_answers(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)

    async def fake_count(guild_id):
        return 1

    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)

    async def fake_refresh(req, *, message_key, params, expire=False):
        return True

    monkeypatch.setattr(panels_engine, "refresh_session_view", fake_refresh)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)

    run(_resolve("setup.channels_binding_pick")(
        _req(args={"values": ["logging::mod_channel"]})))
    reply = run(_resolve("setup.channels_channel_pick")(
        _req(args={"values": ["123456"]})))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (_stage_channel_binding's confirmation;
    # the channel-index-less fallback renders the mention).
    assert reply.user_message == (
        "✅ Staged for Final review: `logging.mod_channel` → <#123456>.  "
        "Pending operations: **1**.")
    _did, added = store.added[0]
    assert added.op_kind == "bind_channel"
    assert added.payload == {
        "subsystem": "logging", "name": "mod_channel", "kind": "channel",
        "resource_id": 123456, "target_name": "<#123456>"}
    assert added.label == ("[channels] logging.mod_channel → <#123456>")


def test_channels_channel_pick_empty_answers_the_shipped_copy():
    reply = run(_resolve("setup.channels_channel_pick")(
        _req(args={"values": []})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "No channel picked."


def test_recommended_channel_ops_stage_only_high_confidence(monkeypatch):
    from sb.domain.setup import plan
    from sb.domain.setup.channels import recommended_channel_ops
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    async def index(guild_id):
        return (GuildChannel(id=1, name="mod-log"),
                GuildChannel(id=2, name="staff-audit"))

    install_channel_index(index)
    try:
        ops = run(recommended_channel_ops(99))
    finally:
        plan.reset_plan_ports_for_tests()
    # mod-log is an exact token hit (high) on the declared
    # logging.mod_channel slot; no medium pick ever auto-stages.
    assert [(o.subsystem, o.payload["name"]) for o in ops] == [
        ("logging", "mod_channel")]
    assert ops[0].payload["resource_id"] == 1
    assert ops[0].payload["target_name"] == "mod-log"


# --- wiring ---------------------------------------------------------------------------------


def test_mark_in_progress_op_registered():
    from sb.kernel.workflow.registry import REGISTRY

    assert REGISTRY.resolve("setup.mark_in_progress").audit_verb == \
        "setup.session.step_marked"


def test_set_setting_op_kind_binds_the_scalar_seam():
    from sb.kernel.draft.registry import OP_KINDS

    binding = OP_KINDS.get("set_setting")
    assert binding is not None
    assert binding.workflow_ref.name == "settings.set_scalar"
    # add_automation_rule stays fail-closed (un-registered) — the
    # automation seam is a named successor.
    assert OP_KINDS.get("add_automation_rule") is None


def test_every_section_flow_route_resolves():
    from sb.spec.refs import HandlerRef, resolve

    for name in (
            "setup.back_to_wizard", "setup.wizard_back",
            "setup.wizard_continue", "setup.wizard_cancel",
            "setup.wizard_apply_recommended", "setup.wizard_apply_all",
            "setup.wizard_skip", "setup.wizard_customize",
            "setup.wizard_jump", "setup.wizard_back_to_step",
            "setup.open_section_preset_select", "setup.preset_pick",
            "setup.preset_confirm", "setup.preset_cancel",
            "setup.open_section_channels", "setup.channels_binding_pick",
            "setup.channels_channel_pick",
            "setup.section_apply_channels",
            "setup.section_customize_channels",
            "setup.section_skip_channels", "setup.section_hub_channels"):
        assert resolve(HandlerRef(name)) is not None


def test_remaining_two_sections_stay_honest_terminals(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    for slug in ("cog_routing", "ticket"):
        reply = run(_resolve(f"setup.open_section_{slug}")(_req()))
        assert reply.outcome == BLOCKED
        assert "section-flows slice" in reply.user_message
