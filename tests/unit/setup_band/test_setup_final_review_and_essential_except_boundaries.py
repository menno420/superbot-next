"""Characterization of the setup-band except-boundary REMAINDER — the
``final_review.py`` best-effort / recovery-render arms and the
``essential_steps.py`` ``_save`` family the moderation pin (#516) and the
count/list soft-fail audit (#519) did not reach (backlog item C1).

Each swallow is pinned to ONE of three intended shapes by forcing the
guarded call to RAISE and asserting the observed boundary:

* **fail-CLOSED** — the swallow surfaces a ``BLOCKED`` refusal (the apply /
  recovery-retry staged-ops reads, the complete-delete session read, every
  essential ``_save`` write try);
* **best-effort / logged-never-raised** — the swallow logs and continues;
  the summary / outcome surface still answers and NO write is masked
  (``_restage_remainder``, ``_mark_complete``, ``_clear_workspace_pointers``,
  ``persist_progress``);
* **fail-SOFT / degrade** — the swallow degrades to an empty / default
  render or a ``None`` port result (the recovery + resume renders, the
  health read, the create-channel / create-role ports, and the
  ``complete_delete`` channel-resolve → "already gone" branch).

**No fail-open.** None of these swallows masks a real write that then
falsely reports success: the fail-CLOSED arms refuse, the best-effort arms
guard a mutation that already committed (or already raised on non-SUCCESS),
and the fail-SOFT arms feed a display / resolve a target and take a
non-destructive path. Additive, DB-free, changes NO product behavior
(mirrors ``test_setup_moderation_except_boundaries.py`` /
``test_setup_softfail_boundaries.py``).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.setup as m
    from sb.domain.setup import essential_steps, final_review, wizard

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    final_review.reset_final_review_state_for_tests()
    essential_steps.reset_essential_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    final_review.reset_final_review_state_for_tests()
    essential_steps.reset_essential_state_for_tests()


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


def _open_gate(monkeypatch):
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))


# =======================================================================================
# final_review.py — the fail-CLOSED staged-ops reads (L755 apply / L852 retry)
# =======================================================================================


def test_final_apply_staged_ops_read_failure_fails_closed(monkeypatch):
    """L755 — the apply lane reads the staged draft BEFORE the gate; an
    unreadable draft fails CLOSED with the shipped refusal, never applies."""
    from sb.domain.setup import final_review

    async def boom(guild_id):
        raise RuntimeError("staged draft unreadable")

    monkeypatch.setattr(final_review, "_staged_ops", boom)

    reply = run(_resolve("setup.final_apply")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == "Could not read the staged draft — see logs."


def test_recovery_retry_staged_ops_read_failure_fails_closed(monkeypatch):
    """L852 — Retry gates first, then reads the staged draft; an unreadable
    draft fails CLOSED with the same shipped refusal (never re-applies)."""
    from sb.domain.setup import final_review

    _open_gate(monkeypatch)

    async def boom(guild_id):
        raise RuntimeError("staged draft unreadable")

    monkeypatch.setattr(final_review, "_staged_ops", boom)

    reply = run(_resolve("setup.recovery_retry")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == "Could not read the staged draft — see logs."


# =======================================================================================
# final_review.complete_delete — L915 session read fail-CLOSED, L958 resolve fail-SOFT
# =======================================================================================


def test_complete_delete_session_read_failure_fails_closed(monkeypatch):
    """L915 — a destructive-delete flow whose session read raises must fail
    CLOSED (refuse), never proceed toward a delete on unknown state."""
    from sb.domain.setup import final_review, store

    _open_gate(monkeypatch)

    async def boom(guild_id):
        raise RuntimeError("session row unreadable")

    monkeypatch.setattr(store, "get_session_row", boom)

    reply = run(_resolve("setup.complete_delete")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == "Couldn't read the setup session — see logs."


def test_complete_delete_channel_resolve_failure_degrades_to_already_gone(
        monkeypatch):
    """L958 — an unreadable channel cache degrades ``resolved`` to ``None``,
    which routes into the "already gone" branch: it NEVER deletes, clears
    the session pointer and answers SUCCESS. The fail-SOFT that is closest
    to a fail-open — pinned here to prove it takes the non-destructive path
    (no delete, only a best-effort pointer clear)."""
    from sb.domain.channel import service as channel_service
    from sb.domain.setup import final_review, store, wizard

    _open_gate(monkeypatch)

    async def complete_session(guild_id):
        return {"setup_status": "complete", "setup_channel_id": 12345}

    async def no_pending(guild_id):
        return 0

    async def resolve_boom(guild_id, name):
        raise RuntimeError("gateway cache unreadable")

    cleared: list[object] = []

    async def fake_clear(req):
        cleared.append(req)

    monkeypatch.setattr(store, "get_session_row", complete_session)
    monkeypatch.setattr(wizard, "staged_ops_count", no_pending)
    monkeypatch.setattr(channel_service, "resolve_channel", resolve_boom)
    monkeypatch.setattr(final_review, "_clear_workspace_pointers", fake_clear)

    reply = run(_resolve("setup.complete_delete")(_req()))

    assert reply.outcome == SUCCESS
    # shipped already-gone copy, verbatim — the degrade path, not a delete.
    assert reply.user_message == (
        "⚠️ The setup channel is already gone — cleared the session "
        "pointer for you.")
    # the non-destructive branch ran: pointer cleared, no delete attempted.
    assert len(cleared) == 1


# =======================================================================================
# final_review.py — the best-effort / logged-never-raised arms
# =======================================================================================


def test_restage_remainder_failure_still_returns_the_summary(monkeypatch):
    """L459 — after apply partitions a failed op into the remainder,
    re-staging it is best-effort: a raise is logged and swallowed, and the
    ApplySummary still answers (the write it guards never committed — it is
    in ``failed`` precisely because the pipeline refused it)."""
    from sb.domain.setup import final_review, wizard

    op = SimpleNamespace(
        op_seq=1, op_kind="set_setting", subsystem="welcome",
        authority_ref="", payload={"subsystem": "welcome", "name": "enabled",
                                    "value": True},
        label="welcome.enabled", dedup_token="tok-1")
    draft = SimpleNamespace(draft_id="d1", operations=(op,))

    async def one_draft(guild_id):
        return [draft]

    class _BoomPipeline:
        async def preview(self, *a, **k):
            raise RuntimeError("preview refused")

        async def confirm_and_apply(self, *a, **k):  # pragma: no cover
            raise AssertionError("unreachable — preview raised first")

    async def restage_boom(guild_id, remainder):
        raise RuntimeError("re-stage draft create failed")

    import sb.kernel.draft.pipeline as pipeline_module

    monkeypatch.setattr(wizard, "_open_guild_drafts", one_draft)
    monkeypatch.setattr(pipeline_module, "DraftPipeline", _BoomPipeline)
    monkeypatch.setattr(final_review, "_restage_remainder", restage_boom)

    summary = run(final_review._apply_open_drafts(_req()))

    # the batch refusal folded the op into `failed`; the re-stage raise was
    # swallowed and the summary still answers (best-effort, never raised).
    assert not summary.applied
    assert len(summary.failed) == 1
    assert summary.failed[0].startswith("welcome.enabled")


def test_mark_complete_failure_is_logged_never_raised(monkeypatch):
    """L476 — marking the session complete after a full-success apply is
    best-effort: a K7 raise is logged and swallowed (the apply already
    landed through the pipeline; the complete flag is a trailing write)."""
    from sb.domain.setup import final_review
    from sb.kernel.workflow import engine

    async def boom(ref, ctx):
        raise RuntimeError("mark_complete op raised")

    monkeypatch.setattr(engine, "run", boom)

    # returns None, no exception propagates.
    assert run(final_review._mark_complete(_req())) is None


def test_clear_workspace_pointers_failure_is_logged_never_raised(monkeypatch):
    """L1021 — nulling the workspace pointers after a channel delete is
    best-effort: a K7 raise is logged and swallowed (the delete already
    happened; the pointer null is a trailing cleanup write)."""
    from sb.domain.setup import final_review
    from sb.kernel.workflow import engine

    async def boom(ref, ctx):
        raise RuntimeError("clear_workspace_pointer op raised")

    monkeypatch.setattr(engine, "run", boom)

    assert run(final_review._clear_workspace_pointers(_req())) is None


# =======================================================================================
# final_review._render_recovery L694 — the recovery render degrades to empty
# =======================================================================================


def test_recovery_render_survives_a_staged_ops_read_failure(monkeypatch):
    """L694 — with no stashed summary (a restart lost it), the recovery card
    reads the staged ops to degrade to the preserved draft's pre-apply
    render; a failed read degrades to ``ops=[]`` and the card still renders,
    never propagating."""
    from sb.domain.setup import final_review

    async def boom(guild_id):
        raise RuntimeError("staged-ops read failed")

    monkeypatch.setattr(final_review, "_staged_ops", boom)
    # fresh state ⇒ last_summary is None, so the read branch is taken.
    rendered = run(final_review._render_recovery(
        final_review.recovery_spec(), _ctx()))

    assert rendered is not None
    assert hasattr(rendered, "embed")


# =======================================================================================
# essential_steps.py — the fail-CLOSED `_save` write tries
# =======================================================================================


def _break_write(monkeypatch):
    """Force the shared scalar write seam (``wizard._write_setting``, behind
    ``_set``) to RAISE — the boundary each ``_save`` step's write try
    swallows into its shipped 'something went wrong' refusal."""
    from sb.domain.setup import wizard

    async def boom(req, subsystem, name, value):
        raise RuntimeError("settings write failed")

    monkeypatch.setattr(wizard, "_write_setting", boom)


def _flow():
    from sb.domain.setup.essential_steps import flow_state

    return flow_state(99, 42)


def test_mods_save_write_failure_fails_closed(monkeypatch):
    """L1494 — the moderators step's write try surfaces the shipped refusal
    (BLOCKED), never advancing the flow on a masked write."""
    _break_write(monkeypatch)
    _flow().mod_role_id = 777

    reply = run(_resolve("setup.essential_mods_save")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Something went wrong saving your moderators — please try again.")


def test_spam_save_write_failure_fails_closed(monkeypatch):
    """L1523 — the block-spam step's write try fails CLOSED with the shipped
    protection refusal."""
    _break_write(monkeypatch)

    reply = run(_resolve("setup.essential_spam_save")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Something went wrong turning on protection — please try again.")


def test_log_save_write_failure_fails_closed(monkeypatch):
    """L1606 — with channel creation past (the create seam handed back an
    id), the logging-settings write try fails CLOSED with the shipped
    log-channels refusal."""
    from sb.domain.setup import essential_steps as es

    async def fake_create(req, name):
        return 9001

    monkeypatch.setattr(es, "_create_channel", fake_create)
    _break_write(monkeypatch)

    reply = run(_resolve("setup.essential_log_save")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Something went wrong saving your log channels — please try again.")


def test_reward_save_write_failure_fails_closed(monkeypatch):
    """L1680 — the reward step (driven via the 🏅 next button with an XP
    rate and no role) fails CLOSED with the shipped rewards refusal when the
    XP write raises."""
    _break_write(monkeypatch)
    state = _flow()
    state.reward_xp_rate = "active"  # != "keep" ⇒ the XP scalar writes run
    state.reward_types = set()       # no role ⇒ next → apply-and-complete

    reply = run(_resolve("setup.essential_reward_next")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Something went wrong saving rewards — please try again.")


def test_helpdesk_save_op_failure_fails_closed(monkeypatch):
    """L1839 — the help-desk step routes ``ticket.update_config`` through
    the K7 engine; a raise fails CLOSED with the shipped help-desk refusal."""
    from sb.kernel.workflow import engine

    async def boom(ref, ctx):
        raise RuntimeError("ticket.update_config raised")

    monkeypatch.setattr(engine, "run", boom)
    _flow().helpdesk_staff_role_id = 555

    reply = run(_resolve("setup.essential_helpdesk_save")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Something went wrong setting up the help desk — please try again.")


def test_commands_save_write_failure_fails_closed(monkeypatch):
    """L1896 — the command-access step routes through the platform
    command_access seam; a raise fails CLOSED with the shipped
    where-commands-work refusal (default ``all_channels`` mode clears the
    channel guard)."""
    from sb.domain.platform import command_access

    async def boom(ctx, *, mode):
        raise RuntimeError("set_access_mode raised")

    monkeypatch.setattr(command_access, "set_access_mode", boom)

    reply = run(_resolve("setup.essential_commands_save")(_req()))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Something went wrong saving where commands work — please try again.")


# =======================================================================================
# essential_steps.py — the best-effort / fail-SOFT arms
# =======================================================================================


def test_persist_progress_failure_is_logged_never_raised(monkeypatch):
    """L365 — the wizard-position persist is best-effort ("a DB hiccup must
    never break the wizard"): a K7 raise is logged and swallowed. It guards
    only the POSITION write — the step's own setting already committed and
    raised on non-SUCCESS, so nothing is masked."""
    from sb.domain.setup import essential_steps as es
    from sb.kernel.workflow import engine

    async def boom(ref, ctx):
        raise RuntimeError("set_essential_step raised")

    monkeypatch.setattr(engine, "run", boom)
    state = _flow()
    state.index = 2

    assert run(es.persist_progress(_req(), state)) is None


def test_create_channel_port_failure_degrades_to_none(monkeypatch):
    """L443 — a channel-create port refusal / live Forbidden is logged and
    degrades to ``None`` (the caller then surfaces the shipped copy and
    stops WITHOUT writing anything)."""
    from sb.domain.channel import service as channel_service
    from sb.domain.setup import essential_steps as es

    async def create_boom(gid, *, name, overwrites, parent_id, reason):
        raise RuntimeError("Forbidden")

    monkeypatch.setattr(channel_service, "active_actions",
                        lambda: SimpleNamespace(create_text_channel=create_boom))

    assert run(es._create_channel(_req(), "mod-log")) is None


def test_create_role_port_failure_degrades_to_none(monkeypatch):
    """L472 — a role-provisioning port refusal / live Forbidden is logged
    and degrades to ``None`` (the caller surfaces the shipped copy)."""
    from sb.domain.role import service as role_service
    from sb.domain.setup import essential_steps as es

    async def role_boom(gid, *, name, color, reason):
        raise RuntimeError("Forbidden")

    monkeypatch.setattr(
        role_service, "active_provisioning",
        lambda: SimpleNamespace(create_guild_role=role_boom))

    assert run(es._create_role(_req(), "Champion")) is None


def test_build_check_setup_text_read_failure_degrades_to_nothing_configured(
        monkeypatch):
    """L532 — the "Check my setup" health read degrades an unreadable /
    headless DB to the empty configured-set, so the check reports the
    nothing-configured headline instead of raising."""
    from sb.domain.setup import essential_steps as es

    async def boom(guild_id):
        raise RuntimeError("health read failed")

    monkeypatch.setattr(es, "_configured_subsystems", boom)

    text = run(es.build_check_setup_text(99))

    # degraded to done==0 ⇒ the shipped nothing-configured headline.
    assert "Nothing essential is set up yet" in text


def test_render_resume_session_read_failure_degrades_to_step_one(monkeypatch):
    """L1369 — the paused-resume card reads the saved step to show where the
    user left off; a failed read degrades ``raw_step`` to ``None`` ⇒ the
    step-1 default, and the card still renders."""
    from sb.domain.setup import essential_steps as es
    from sb.domain.setup import store

    async def boom(guild_id):
        raise RuntimeError("session row unreadable")

    monkeypatch.setattr(store, "get_session_row", boom)

    rendered = run(es._render_resume(es.resume_spec(), _ctx()))

    assert rendered is not None
    # human_step = (None ⇒ 0) + 1 ⇒ the shipped "step 1" default copy.
    assert "step 1)" in rendered.embed.description


def test_resume_click_session_read_failure_degrades_to_default_step(
        monkeypatch):
    """L1968 — Resume gates, then reads the saved step to rebuild the flow;
    a failed read degrades ``session`` to ``None`` (the step stays at the
    flow's default) and still lands on the current card, never raising."""
    from sb.domain.setup import essential_steps as es
    from sb.domain.setup import store, wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def boom(guild_id):
        raise RuntimeError("resume_session failed")

    shown: list[int] = []

    async def fake_show(req, state):
        shown.append(state.index)

    monkeypatch.setattr(store, "get_session_row", boom)
    monkeypatch.setattr(es, "_show_current", fake_show)

    reply = run(_resolve("setup.essential_resume_click")(_req()))

    assert reply is None
    # session degraded to None ⇒ step untouched (default 0), card still shown.
    assert shown == [0]
