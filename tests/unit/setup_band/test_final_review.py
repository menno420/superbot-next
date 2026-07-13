"""The FINAL-REVIEW APPLY LANE (final-review slice —
sb/domain/setup/final_review.py): the FinalReviewView card + gated
apply + apply summary + partial-apply recovery + setup-complete view.

DB-free like the wizard-interior suite: the K7/K9 seams are
monkeypatched at their module functions and the assertions pin the
ORACLE bytes the lanes carry (no golden drives a click on these
components — the module pin; oracle sources:
disbot/views/setup/final_review.py, services/setup_operations.py,
services/setup_advisor_review.py, services/setup_channel.py,
views/setup/draft_render.py)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import final_review, wizard

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    final_review.reset_final_review_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    final_review.reset_final_review_state_for_tests()


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


def _op(*, op_seq=1, subsystem="logging", name="audit_channel",
        resource_id=1234, op_kind="bind_channel", dedup_token="tok-1"):
    return SimpleNamespace(
        op_seq=op_seq, op_kind=op_kind, subsystem=subsystem,
        authority_ref="",
        payload={"subsystem": subsystem, "name": name, "kind": "channel",
                 "resource_id": resource_id},
        label=f"[suggestions] {subsystem}.{op_kind}",
        dedup_token=dedup_token)


class _Gate:
    def __init__(self, allow: bool) -> None:
        self.allow = allow

    async def __call__(self, req) -> bool:
        del req
        return self.allow


def _staged(monkeypatch, ops):
    from sb.domain.setup import final_review as fr

    async def fake_staged(guild_id):
        return list(ops)

    monkeypatch.setattr(fr, "_staged_ops", fake_staged)


# --- the op-line render (draft_render._short_label / render_op_line) -------------------


def test_short_label_branches_carry_the_oracle_shapes():
    from sb.domain.setup.final_review import _pending_line, _short_label

    assert _short_label(_op()) == "logging.audit_channel → <1234>"
    assert _pending_line(_op()) == "◐· `logging.audit_channel → <1234>`"
    clear = SimpleNamespace(op_kind="clear_binding", subsystem="logging",
                            payload={"subsystem": "logging",
                                     "name": "mod_channel"})
    assert _short_label(clear) == "logging.mod_channel ← clear"
    setting = SimpleNamespace(op_kind="set_setting", subsystem="automod",
                              payload={"subsystem": "automod",
                                       "name": "enabled", "value": "true"})
    assert _short_label(setting) == "automod.enabled = true"
    create = SimpleNamespace(op_kind="create_channel", subsystem="logging",
                             payload={"subsystem": "logging",
                                      "resource_name": "mod-log"})
    assert _short_label(create) == "create channel 'mod-log'"
    other = SimpleNamespace(op_kind="set_cog_routing", subsystem="admin",
                            payload={"subsystem": "admin"})
    assert _short_label(other) == "set_cog_routing (admin)"


# --- build_final_review_embed (the oracle three states, bytes verbatim) ----------------


def test_embed_empty_state_is_the_shipped_copy():
    from sb.domain.setup.final_review import build_final_review_embed

    embed = build_final_review_embed([])
    assert embed.title == "🛰 Final review"
    assert embed.description == (
        "No staged work yet. Visit a wizard section to stage the first "
        "change, then come back here to apply.")
    assert embed.style_token == "dark_grey"


def test_embed_pre_apply_pins_the_shipped_bytes():
    from sb.domain.setup.final_review import build_final_review_embed

    embed = build_final_review_embed([_op()])
    assert embed.title == "🛰 Final review"
    # shipped description, verbatim (double spaces included).
    assert embed.description == (
        "Final review — **nothing has changed yet**.  **1** operation(s) "
        "are staged and ready to apply.  Click **Apply staged setup** to "
        "route each through the audit pipelines.")
    fields = {f[0]: f[1] for f in embed.fields}
    assert fields["Pending"] == "• ◐· `logging.audit_channel → <1234>`"
    # the shipped no-rollback caveat, verbatim.
    assert fields["⚠️ Heads-up"] == (
        "Apply has **no automatic rollback**. Each operation commits "
        "through its pipeline in order; if one fails partway, earlier "
        "ones stay applied and you'll be able to retry the rest.")
    assert embed.footer == "Owner-gated. Nothing has applied yet."
    assert embed.style_token == "blurple"


def test_embed_pre_apply_caps_the_pending_list_at_ten():
    from sb.domain.setup.final_review import build_final_review_embed

    ops = [_op(op_seq=i, name=f"binding_{i}") for i in range(1, 13)]
    embed = build_final_review_embed(ops)
    pending = {f[0]: f[1] for f in embed.fields}["Pending"]
    lines = pending.splitlines()
    assert len(lines) == 11
    assert lines[-1] == "_+2 more_"
    assert "**12** operation(s)" in embed.description


def test_embed_partial_pins_the_shipped_bytes():
    from sb.domain.setup.final_review import (
        ApplySummary, build_final_review_embed)

    summary = ApplySummary(applied=["a → b"], failed=["c: boom"],
                           skipped=["d (not yet implemented)"])
    embed = build_final_review_embed([], summary=summary)
    assert embed.title == "🛰 Final review · partially applied"
    assert embed.description == (
        "**Setup partially applied.**  Some changes succeeded, but setup "
        "is **not** complete.  Your remaining draft has been preserved so "
        "you can retry or cancel.\n\n"
        "Applied **1**, failed **1**, skipped **1**.")
    fields = {f[0]: f[1] for f in embed.fields}
    assert fields["Applied"] == "• a → b"
    assert fields["Failed"] == "• c: boom"
    assert fields["Skipped"] == "• d (not yet implemented)"
    assert embed.footer == (
        "Draft preserved. Retry re-runs the failed/skipped operations; "
        "Cancel leaves the draft for later. Note: Cancel does NOT undo "
        "operations that already applied.")
    assert embed.style_token == "gold"


def test_embed_full_success_pins_the_shipped_bytes():
    from sb.domain.setup.final_review import (
        ApplySummary, build_final_review_embed)

    summary = ApplySummary(applied=["a → b", "c → d"])
    embed = build_final_review_embed([], summary=summary)
    assert embed.title == "🛰 Setup complete"
    assert embed.description == (
        "**Setup complete.**  Applied **2** operation(s); nothing failed "
        "or was skipped.")
    assert embed.style_token == "green"
    assert embed.footer == ""


# --- the section entry + the stage destination -----------------------------------------


def test_final_review_section_click_opens_the_card(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.open_section_final_review")(_req())) is None
    assert opened == ["setup.final_review"]


def test_final_review_section_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.open_section_final_review")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == wizard.GATE_MSG_WIZARD


# --- the apply lane ---------------------------------------------------------------------


def test_apply_with_nothing_staged_answers_the_shipped_copy(monkeypatch):
    _staged(monkeypatch, [])
    reply = run(_resolve("setup.final_apply")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (FinalReviewView._apply).
    assert reply.user_message == "Nothing to apply."


def test_apply_gate_refusal_is_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard
    from sb.domain.setup.final_review import GATE_MSG_APPLY

    _staged(monkeypatch, [_op()])
    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    reply = run(_resolve("setup.final_apply")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (final_review._gate_apply).
    assert reply.user_message == GATE_MSG_APPLY
    assert reply.user_message.startswith(
        "Only the server owner or a delegated setup admin can apply "
        "staged setup operations.")


def test_apply_single_flight_lock_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard

    _staged(monkeypatch, [_op()])
    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    fr._apply_inflight.add(99)
    reply = run(_resolve("setup.final_apply")(_req()))
    assert reply.outcome == BLOCKED
    # shipped copy, verbatim.
    assert reply.user_message == (
        "Setup apply is already in progress — wait for the result "
        "message before retrying.")


def test_apply_full_success_marks_complete_and_mounts_the_complete_view(
        monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    _staged(monkeypatch, [_op()])
    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_apply(req):
        return fr.ApplySummary(applied=["logging.audit_channel → <1234>"])

    monkeypatch.setattr(fr, "_apply_open_drafts", fake_apply)
    ran = []

    async def fake_run(ref, ctx):
        ran.append(getattr(ref, "name", str(ref)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.final_apply")(_req())) is None
    assert ran == ["setup.mark_complete"]
    assert opened == ["setup.complete_card"]
    assert fr.last_summary(99).applied == [
        "logging.audit_channel → <1234>"]
    # the lock released cleanly.
    assert 99 not in fr._apply_inflight


def test_apply_partial_mounts_the_recovery_view(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    _staged(monkeypatch, [_op()])
    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_apply(req):
        return fr.ApplySummary(applied=["a"], failed=["b: boom"])

    monkeypatch.setattr(fr, "_apply_open_drafts", fake_apply)
    ran = []

    async def fake_run(ref, ctx):
        ran.append(getattr(ref, "name", str(ref)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.final_apply")(_req())) is None
    # partial NEVER marks the session complete (the oracle full_success
    # guard).
    assert ran == []
    assert opened == ["setup.apply_recovery"]


def test_apply_drive_maps_the_k9_partitions_onto_the_summary(monkeypatch):
    """The DraftApplyResult → ApplySummary fold: applied labels, the
    ran-failure with its error text, SF-f skips, and the binding-less
    kind folded into skipped as not-yet-implemented (the oracle
    partition). The remainder re-stages."""
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard as wizard_module
    from sb.kernel.draft import pipeline as pipeline_module

    ops = (_op(op_seq=1, name="audit_channel", resource_id=1),
           _op(op_seq=2, name="mod_channel", resource_id=2),
           _op(op_seq=3, name="bot_channel", resource_id=3))
    draft = SimpleNamespace(draft_id="d-1", operations=ops)

    async def fake_open_drafts(guild_id):
        return (draft,)

    monkeypatch.setattr(wizard_module, "_open_guild_drafts",
                        fake_open_drafts)

    class FakePipeline:
        async def preview(self, draft_id, ctx):
            return SimpleNamespace(
                preview_hash="h",
                confirmation=SimpleNamespace(
                    challenge=SimpleNamespace(value="button")))

        async def confirm_and_apply(self, draft_id, req, actor, *,
                                    preview_hash, confirmation):
            return SimpleNamespace(
                applied=(1,), failed=(2,), skipped=(3,),
                op_results=(
                    SimpleNamespace(outcome=SUCCESS, user_message=None),
                    SimpleNamespace(outcome=BLOCKED,
                                    user_message="boom happened"),
                ))

    monkeypatch.setattr(pipeline_module, "DraftPipeline", FakePipeline)
    restaged = []

    async def fake_restage(guild_id, remainder):
        restaged.append([op.op_seq for op in remainder])

    monkeypatch.setattr(fr, "_restage_remainder", fake_restage)
    summary = run(fr._apply_open_drafts(_req()))
    assert summary.applied == ["logging.audit_channel → <1>"]
    assert summary.failed == ["logging.mod_channel → <2>: boom happened"]
    assert summary.skipped == ["logging.bot_channel → <3>"]
    assert restaged == [[2, 3]]


def test_apply_drive_folds_bindingless_kinds_into_skipped(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard as wizard_module
    from sb.kernel.draft import pipeline as pipeline_module

    ops = (_op(op_seq=1, name="audit_channel", resource_id=1),)
    draft = SimpleNamespace(draft_id="d-1", operations=ops)

    async def fake_open_drafts(guild_id):
        return (draft,)

    monkeypatch.setattr(wizard_module, "_open_guild_drafts",
                        fake_open_drafts)

    class FakePipeline:
        async def preview(self, draft_id, ctx):
            return SimpleNamespace(
                preview_hash="h",
                confirmation=SimpleNamespace(challenge=object()))

        async def confirm_and_apply(self, draft_id, req, actor, *,
                                    preview_hash, confirmation):
            # a failed op that never RAN (no op_result) = the
            # fail-closed registry refusal.
            return SimpleNamespace(applied=(), failed=(1,), skipped=(),
                                   op_results=())

    monkeypatch.setattr(pipeline_module, "DraftPipeline", FakePipeline)

    async def fake_restage(guild_id, remainder):
        pass

    monkeypatch.setattr(fr, "_restage_remainder", fake_restage)
    summary = run(fr._apply_open_drafts(_req()))
    assert summary.applied == []
    assert summary.failed == []
    assert summary.skipped == [
        "logging.audit_channel → <1> (not yet implemented)"]


def test_apply_drive_batch_refusal_fails_every_op(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard as wizard_module
    from sb.kernel.draft import pipeline as pipeline_module

    ops = (_op(op_seq=1, name="audit_channel", resource_id=1),
           _op(op_seq=2, name="mod_channel", resource_id=2))
    draft = SimpleNamespace(draft_id="d-1", operations=ops)

    async def fake_open_drafts(guild_id):
        return (draft,)

    monkeypatch.setattr(wizard_module, "_open_guild_drafts",
                        fake_open_drafts)

    class FakePipeline:
        async def preview(self, draft_id, ctx):
            raise RuntimeError("preview exploded")

    monkeypatch.setattr(pipeline_module, "DraftPipeline", FakePipeline)
    restaged = []

    async def fake_restage(guild_id, remainder):
        restaged.append([op.op_seq for op in remainder])

    monkeypatch.setattr(fr, "_restage_remainder", fake_restage)
    summary = run(fr._apply_open_drafts(_req()))
    assert summary.applied == []
    assert summary.failed == [
        "logging.audit_channel → <1>: preview exploded",
        "logging.mod_channel → <2>: preview exploded"]
    assert restaged == [[1, 2]]


# --- the close/cancel lanes (copy verbatim) --------------------------------------------


def test_edit_back_cancel_carry_the_shipped_copy():
    reply = run(_resolve("setup.final_edit")(_req()))
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "Closed Final review — open the wizard or hub above to edit your "
        "staged operations.  Nothing has been applied.")
    reply = run(_resolve("setup.final_back")(_req()))
    assert reply.user_message == (
        "Closed Final review — your wizard / hub anchor is still open "
        "above.  Nothing has been applied.")
    reply = run(_resolve("setup.final_cancel")(_req()))
    assert reply.user_message == (
        "Final review cancelled — nothing was applied.")


# --- the 🧠 AI review lane ---------------------------------------------------------------


def test_ai_review_renders_the_advisory_lines(monkeypatch):
    from sb.domain.setup import plan
    from sb.domain.setup.plan import SetupPlanDraft, SetupRecommendation

    rec = SetupRecommendation(
        subsystem="logging", binding_name="audit_channel",
        target_kind="channel", target_id=1, target_name="audit",
        confidence="high", reason="r")

    async def fake_suggest(guild_id):
        return SetupPlanDraft(recommendations=(rec,))

    monkeypatch.setattr(plan, "suggest", fake_suggest)
    reply = run(_resolve("setup.final_ai_review")(_req()))
    assert reply.outcome == SUCCESS
    assert "1 suggestion(s) from the advisor" in reply.user_message
    assert "• `logging.audit_channel` (high)" in reply.user_message
    # the shipped advisory footer, verbatim.
    assert ("Advisory only (DeterministicAdvisor) — nothing has been "
            "staged or applied. Use the wizard to make any changes "
            "yourself.") in reply.user_message


def test_ai_review_empty_draft_says_setup_looks_good(monkeypatch):
    from sb.domain.setup import plan
    from sb.domain.setup.plan import SetupPlanDraft

    async def fake_suggest(guild_id):
        return SetupPlanDraft()

    monkeypatch.setattr(plan, "suggest", fake_suggest)
    reply = run(_resolve("setup.final_ai_review")(_req()))
    # shipped copy, verbatim (review_draft's empty branch).
    assert ("No additional changes recommended — your setup looks good."
            in reply.user_message)


def test_ai_review_failure_degrades_to_the_shipped_notice(monkeypatch):
    from sb.domain.setup import plan

    async def fake_suggest(guild_id):
        raise RuntimeError("advisor down")

    monkeypatch.setattr(plan, "suggest", fake_suggest)
    reply = run(_resolve("setup.final_ai_review")(_req()))
    assert reply.outcome == SUCCESS
    # shipped copy, verbatim (advisory-only: never raises, never blocks).
    assert ("The AI advisor couldn't produce a review right now."
            in reply.user_message)


# --- partial-apply recovery ---------------------------------------------------------------


def test_recovery_retry_reruns_the_apply_flow(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard
    from sb.kernel.panels import engine as panels_engine
    from sb.kernel.workflow import engine as wf_engine

    _staged(monkeypatch, [_op()])
    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def fake_apply(req):
        return fr.ApplySummary(applied=["a"])

    monkeypatch.setattr(fr, "_apply_open_drafts", fake_apply)

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)
        return "msg-key"

    monkeypatch.setattr(panels_engine, "open_panel", fake_open)
    assert run(_resolve("setup.recovery_retry")(_req())) is None
    assert opened == ["setup.complete_card"]


def test_recovery_finish_drops_the_remainder_and_marks_complete(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    cleared = []

    async def fake_clear(guild_id):
        cleared.append(guild_id)
        return 2

    monkeypatch.setattr(wizard, "clear_guild_drafts", fake_clear)
    ran = []

    async def fake_run(ref, ctx):
        ran.append(getattr(ref, "name", str(ref)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    fr._SUMMARY[99] = fr.ApplySummary(applied=["a", "b"],
                                      failed=["c: boom"], skipped=["d"])
    reply = run(_resolve("setup.recovery_finish")(_req()))
    assert reply.outcome == SUCCESS
    assert cleared == [99]
    assert ran == ["setup.mark_complete"]
    # shipped copy (the '🛰 Setup finished (with skips)' embed
    # description, verbatim).
    assert reply.user_message == (
        "🛰 Setup finished (with skips) — Applied **2** operation(s). "
        "Dropped **2** un-appliable operations from the draft. Re-run "
        "`/setup` any time to revisit them.")


def test_recovery_cancel_carries_the_shipped_copy():
    reply = run(_resolve("setup.recovery_cancel")(_req()))
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "Recovery cancelled — your draft is preserved. Re-open Final "
        "review when you're ready to retry.")


# --- the setup-complete view ----------------------------------------------------------------


def _session(**over):
    base = {"setup_status": "complete", "setup_channel_id": 555,
            "setup_message_id": 666}
    base.update(over)
    return base


def _wire_delete(monkeypatch, *, session, pending=0, resolved=555,
                 delete_raises=False):
    from sb.domain.channel import service as channel_service
    from sb.domain.setup import store, wizard

    async def fake_row(guild_id, conn=None):
        return dict(session) if session is not None else None

    async def fake_count(guild_id):
        return pending

    async def fake_resolve(guild_id, token):
        return resolved

    monkeypatch.setattr(store, "get_session_row", fake_row)
    monkeypatch.setattr(wizard, "staged_ops_count", fake_count)
    monkeypatch.setattr(channel_service, "resolve_channel", fake_resolve)

    deleted = []

    class FakeActions:
        async def delete_channel(self, channel_id, *, reason=None):
            if delete_raises:
                raise RuntimeError("forbidden")
            deleted.append((channel_id, reason))

    monkeypatch.setattr(channel_service, "active_actions",
                        lambda: FakeActions())
    return deleted


def test_delete_refuses_before_setup_is_complete(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _wire_delete(monkeypatch, session=_session(setup_status="in_progress"))
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == BLOCKED
    # shipped guard copy, verbatim.
    assert reply.user_message == (
        "⚠️ Setup isn't complete yet — finish a Final Review apply "
        "before deleting the setup channel.")


def test_delete_refuses_while_the_draft_is_not_empty(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _wire_delete(monkeypatch, session=_session(), pending=3)
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ There are still **3** staged operation(s) — Final Review "
        "left them in the draft for recovery.  Apply them (or run "
        "`/setup-reset`) before deleting the channel.")


def test_delete_without_a_pointer_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _wire_delete(monkeypatch, session=_session(setup_channel_id=None))
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ No setup channel is recorded for this guild — nothing to "
        "delete.")


def test_delete_with_a_gone_channel_clears_the_pointer(monkeypatch):
    from sb.domain.setup import wizard
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _wire_delete(monkeypatch, session=_session(), resolved=None)
    ran = []

    async def fake_run(ref, ctx):
        ran.append(getattr(ref, "name", str(ref)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == SUCCESS
    assert ran == ["setup.clear_workspace_pointer"]
    # shipped already-gone copy, verbatim.
    assert reply.user_message == (
        "⚠️ The setup channel is already gone — cleared the session "
        "pointer for you.")


def test_delete_with_a_mismatched_pointer_refuses(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _wire_delete(monkeypatch, session=_session(), resolved=777)
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ The session's setup_channel_id doesn't match the resolved "
        "channel; refusing to delete.")


def test_delete_refused_by_discord_answers_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    _wire_delete(monkeypatch, session=_session(), delete_raises=True)
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ Discord refused the delete — check the bot's Manage "
        "Channels permission and see logs.")


def test_delete_success_deletes_then_nulls_the_pointers(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup import wizard
    from sb.kernel.workflow import engine as wf_engine

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    deleted = _wire_delete(monkeypatch, session=_session())
    ran = []

    async def fake_run(ref, ctx):
        ran.append(getattr(ref, "name", str(ref)))
        return SimpleNamespace(outcome=SUCCESS)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    fr._SUMMARY[99] = fr.ApplySummary(applied=["a", "b", "c"])
    reply = run(_resolve("setup.complete_delete")(_req()))
    assert reply.outcome == SUCCESS
    # the shipped delete reason, verbatim (delete_setup_channel).
    assert deleted == [
        (555, "Setup complete — operator confirmed auto-cleanup")]
    assert ran == ["setup.clear_workspace_pointer"]
    # shipped confirmation copy, verbatim.
    assert reply.user_message == (
        "✅ Setup channel deleted.  Applied **3** operation(s); re-run "
        "`/setup` later to recreate it.")


def test_keep_carries_the_shipped_copy(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))
    reply = run(_resolve("setup.complete_keep")(_req()))
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "✅ Setup channel kept.  Re-run `/setup` any time to revisit the "
        "wizard.")


def test_complete_buttons_re_check_the_gate(monkeypatch):
    from sb.domain.setup import wizard
    from sb.domain.setup.final_review import GATE_MSG_APPLY

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(False))
    for name in ("setup.complete_delete", "setup.complete_keep",
                 "setup.recovery_retry", "setup.recovery_finish"):
        reply = run(_resolve(name)(_req()))
        assert reply.outcome == BLOCKED
        assert reply.user_message == GATE_MSG_APPLY


# --- renderers + registration -----------------------------------------------------------


def test_final_review_render_drops_apply_when_nothing_is_staged(monkeypatch):
    from sb.domain.setup.final_review import final_review_spec

    from sb.domain.setup import final_review as fr

    async def fake_staged(guild_id):
        return []

    monkeypatch.setattr(fr, "_staged_ops", fake_staged)
    rendered = run(_resolve("setup.final_review_render")(
        final_review_spec(), _ctx()))
    ids = [c.custom_id for c in rendered.components]
    assert "setup_final_review:apply" not in ids
    assert "setup_final_review:cancel" in ids
    assert rendered.embed.description.startswith("No staged work yet.")


def test_final_review_render_keeps_apply_with_staged_ops(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup.final_review import final_review_spec

    async def fake_staged(guild_id):
        return [_op()]

    monkeypatch.setattr(fr, "_staged_ops", fake_staged)
    rendered = run(_resolve("setup.final_review_render")(
        final_review_spec(), _ctx()))
    ids = [c.custom_id for c in rendered.components]
    assert ids[0] == "setup_final_review:apply"
    labels = {c.custom_id: c.label for c in rendered.components}
    # oracle button labels, verbatim.
    assert labels["setup_final_review:apply"] == "Apply staged setup"
    assert labels["setup_final_review:ai_review"] == "🧠 Ask AI to review"
    assert labels["setup_final_review:edit"] == "Edit setup"
    assert labels["setup_final_review:back"] == "Back"
    assert labels["setup_final_review:cancel"] == "Cancel"
    assert "**1** operation(s) are staged" in rendered.embed.description


def test_recovery_render_uses_the_stashed_summary(monkeypatch):
    from sb.domain.setup import final_review as fr
    from sb.domain.setup.final_review import recovery_spec

    fr._SUMMARY[99] = fr.ApplySummary(applied=["a"], failed=["b: boom"])
    rendered = run(_resolve("setup.recovery_render")(recovery_spec(), _ctx()))
    assert rendered.embed.title == "🛰 Final review · partially applied"
    labels = [c.label for c in rendered.components]
    assert labels == ["Retry", "Finish anyway", "Cancel"]


def test_complete_render_uses_the_stashed_summary():
    from sb.domain.setup import final_review as fr
    from sb.domain.setup.final_review import complete_spec

    fr._SUMMARY[99] = fr.ApplySummary(applied=["a", "b"])
    rendered = run(_resolve("setup.complete_render")(complete_spec(), _ctx()))
    assert rendered.embed.title == "🛰 Setup complete"
    assert "**2** operation(s)" in rendered.embed.description
    labels = {c.custom_id: c.label for c in rendered.components}
    assert labels["setup_complete:delete"] == "Delete now"
    assert labels["setup_complete:keep"] == "Keep setup channel"


def test_final_review_ops_registered():
    from sb.kernel.workflow.registry import REGISTRY

    assert REGISTRY.resolve("setup.mark_complete").audit_verb == \
        "setup.session.completed"
    assert REGISTRY.resolve("setup.clear_workspace_pointer").audit_verb == \
        "setup.session.workspace_cleared"


def test_restage_remainder_preserves_the_dedup_token(monkeypatch):
    """The K9-PARTIAL divergence contract: the re-staged remainder
    carries the ORIGINAL dedup tokens so K7 once() keys survive the
    retry."""
    from sb.domain.setup import final_review as fr
    from sb.kernel.draft import store as draft_store_module

    created = []
    added = []

    class FakeStore:
        async def create(self, *, producer, owner_scope):
            created.append((producer, owner_scope))
            return SimpleNamespace(draft_id="d-new")

        async def add(self, draft_id, op):
            added.append((draft_id, op))

    monkeypatch.setattr(draft_store_module, "DraftStore", FakeStore)
    run(fr._restage_remainder(99, [_op(op_seq=7, dedup_token="orig-tok")]))
    assert len(created) == 1
    assert added[0][0] == "d-new"
    assert added[0][1].dedup_token == "orig-tok"
    assert added[0][1].op_kind == "bind_channel"
    # an empty remainder never creates a draft.
    created.clear()
    run(fr._restage_remainder(99, []))
    assert created == []
