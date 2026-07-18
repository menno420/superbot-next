"""Characterization of the setup-band "count / list soft-fail" swallows —
the fail-OPEN audit twin of ``test_setup_moderation_except_boundaries.py``.

The prod-readiness backlog flagged a family of ``except Exception`` arms
that degrade an INFORMATIONAL pending-count / ops-list read to ``0`` /
empty (``cog_routing.py``, ``cleanup.py``, ``roles.py``,
``role_templates.py``, ``handlers.py``, ``panels.py``,
``final_review.py``). The hypothesis under test: such a swallow is benign
ONLY IF it sits STRICTLY AFTER the paired write has already committed —
if the ``try`` also enclosed the write, a failure there would be masked
and the handler would falsely report SUCCESS on a write that never
landed (a fail-OPEN correctness bug).

The audit finding (verified against the source at the born-red HEAD):
**every** audited swallow is BENIGN. The write (``section_card.
stage_custom`` — a real ``DraftStore.add`` that commits and returns) sits
in its OWN ``try`` that fails CLOSED (returns ``BLOCKED`` on failure); the
count/list read is a SEPARATE call in a SEPARATE ``try`` reached only
after the commit. This suite PINS that boundary at each site: with a REAL
draft store recording the row, the count read is forced to RAISE and the
handler still answers SUCCESS with the write's effect persisted — success
is real, only the display count degrades.

Two deliberate contrasts are pinned alongside the benign degraders:

* ``final_review.complete_delete`` L926 — the staged-ops count is a
  destructive-delete GUARD, not a display feed: a count read failure
  fails CLOSED (``BLOCKED``), never proceeds. The asymmetry is the point.
* the two pure-render soft-fails (``panels._render_sections_hub`` L717,
  ``final_review._render_final_review`` L669) — read-only cards that must
  degrade to ``0`` / empty and NEVER propagate the read failure.

Additive, DB-free, changes NO product behavior (mirrors the settings-
write / moderation-except harnesses).
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
    from sb.domain.setup import (channels, cleanup, cog_routing, preset_select,
                                 role_templates, roles, wizard, wizard_nav)

    m.ENSURE_REFS()
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    roles.reset_roles_state_for_tests()
    role_templates.reset_role_templates_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    cleanup.reset_cleanup_state_for_tests()
    cog_routing.reset_cog_routing_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    roles.reset_roles_state_for_tests()
    role_templates.reset_role_templates_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    cleanup.reset_cleanup_state_for_tests()
    cog_routing.reset_cog_routing_state_for_tests()


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


class _Gate:
    def __init__(self, allow: bool) -> None:
        self.allow = allow

    async def __call__(self, req) -> bool:
        del req
        return self.allow


class _FakeStore:
    """A draft store whose added rows REFLECT into the open draft's
    operations — the real ``stage_custom`` commits through it, so the
    write's effect is observable even when the trailing count read is
    forced to raise (the roles-family suite's twin)."""

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


def _patch_stage_seams(monkeypatch):
    """Gate open + K7 mark no-op + own-panel refresh no-op — everything
    the stage path touches AROUND the real ``stage_custom`` write and the
    (about-to-be-broken) count read."""
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


def _break_count(monkeypatch):
    """Force the shared ``wizard.staged_ops_count`` read to RAISE — the
    boundary every "count soft-fail" arm swallows."""
    from sb.domain.setup import wizard

    async def boom(guild_id):
        raise RuntimeError("staged_ops_count read failed")

    monkeypatch.setattr(wizard, "staged_ops_count", boom)


# =======================================================================================
# roles._stage_threshold L291 — count raises ⇒ SUCCESS, pending degrades to 0
# =======================================================================================


def test_roles_count_failure_still_stages_the_row_and_answers_success(
        monkeypatch):
    """The threshold row commits through the real ``stage_custom``
    (store.added records it); only the trailing display count raises. The
    pick still answers SUCCESS and pending soft-fails to **0** — the write
    is real, the degradation is display-only."""
    from sb.domain.setup import roles

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_stage_seams(monkeypatch)
    _break_count(monkeypatch)
    roles._PICKED_TIME_ROLE["99:42"] = 555

    reply = run(_resolve("setup.roles_time_submit")(
        _req(args={"days": "7"})))

    assert reply.outcome == SUCCESS
    # the write DID land — the count swallow rides strictly AFTER commit.
    assert len(store.added) == 1
    assert store.added[0][1].op_kind == "set_role_threshold"
    # shipped confirmation shape, pending degraded to 0.
    assert reply.user_message == (
        "✅ Staged for Final review: `role tier: @555 after 7d`.  "
        "Pending operations: **0**.")


# =======================================================================================
# role_templates._stage_creations L662 — count raises ⇒ pending degrades to `staged`
# =======================================================================================


def test_role_templates_count_failure_degrades_to_the_staged_count(
        monkeypatch):
    """The per-op loop commits every create row (store.added); only the
    trailing count raises. UNLIKE the other sites, this arm degrades to
    the loop's own ``staged`` tally (not 0) — the fallback the shipped
    copy renders. Success is real; the four writes persisted."""
    from sb.domain.setup import role_templates as rt

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_stage_seams(monkeypatch)
    _break_count(monkeypatch)
    rt._SELECTED["99:42"] = "community-hierarchy"

    reply = run(_resolve("setup.role_template_stage")(_req()))

    assert reply.outcome == SUCCESS
    assert len(store.added) == 4
    # pending degraded to the committed `staged` count (4), NOT to 0.
    assert reply.user_message == (
        "✅ Staged **4** new role(s) from **Community hierarchy** for "
        "Final review. Pending operations: **4**. Nothing is created "
        "until you apply.")


# =======================================================================================
# cog_routing._stage_cog_routing L637 — count raises ⇒ SUCCESS, pending 0
# =======================================================================================


def test_cog_routing_count_failure_still_stages_and_answers_success(
        monkeypatch):
    """``_stage_cog_routing`` commits one ``set_cog_routing`` row through
    the real store; the trailing count raises and soft-fails to **0**.
    The routing policy IS staged — the count swallow cannot mask it."""
    from sb.domain.setup import cog_routing

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_stage_seams(monkeypatch)
    _break_count(monkeypatch)

    reply = run(cog_routing._stage_cog_routing(
        _req(), scope_kind="guild", scope_id=None, scope_name="server",
        cog_name="games", enabled=False))

    assert reply.outcome == SUCCESS
    assert len(store.added) == 1
    assert store.added[0][1].op_kind == "set_cog_routing"
    assert reply.user_message.endswith("Pending operations: **0**.")
    assert reply.user_message.startswith("✅ Staged for Final review:")


# =======================================================================================
# cleanup._stage_cleanup_policy L619 — count raises ⇒ SUCCESS, pending 0
# =======================================================================================


def test_cleanup_count_failure_still_stages_and_answers_success(monkeypatch):
    """``_stage_cleanup_policy`` commits one cleanup-policy row; the
    trailing count raises and soft-fails to **0**. The policy IS staged —
    success is real."""
    from sb.domain.setup import cleanup

    store = _FakeStore()
    _patch_store(monkeypatch, store)
    _patch_stage_seams(monkeypatch)
    _break_count(monkeypatch)

    reply = run(cleanup._stage_cleanup_policy(
        _req(), scope_kind="guild", scope_id=None, scope_name="server",
        level="Standard"))

    assert reply.outcome == SUCCESS
    assert len(store.added) == 1
    assert reply.user_message.endswith("Pending operations: **0**.")
    assert reply.user_message.startswith("✅ Staged for Final review:")


# =======================================================================================
# cog_routing / cleanup — the WRITE swallow is a SEPARATE fail-CLOSED try
# (the other half of the boundary: a stage failure never reports SUCCESS)
# =======================================================================================


def test_cog_routing_stage_write_failure_is_a_blocked_refusal(monkeypatch):
    """The paired proof: when the WRITE (``stage_custom``) raises, the
    handler surfaces the shipped BLOCKED refusal — the write swallow is a
    distinct fail-CLOSED try, never confused with the count degrader."""
    from sb.domain.setup import cog_routing, section_card

    _patch_stage_seams(monkeypatch)

    async def boom(guild_id, slug, op):
        raise RuntimeError("draft store unavailable")

    monkeypatch.setattr(section_card, "stage_custom", boom)

    reply = run(cog_routing._stage_cog_routing(
        _req(), scope_kind="guild", scope_id=None, scope_name="server",
        cog_name="games", enabled=False))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Could not stage the routing policy — see logs.")


def test_cleanup_stage_write_failure_is_a_blocked_refusal(monkeypatch):
    """Cleanup's twin: a ``stage_custom`` failure fails CLOSED (BLOCKED),
    proving the write and the count reads live in separate try arms."""
    from sb.domain.setup import cleanup, section_card

    _patch_stage_seams(monkeypatch)

    async def boom(guild_id, slug, op):
        raise RuntimeError("draft store unavailable")

    monkeypatch.setattr(section_card, "stage_custom", boom)

    reply = run(cleanup._stage_cleanup_policy(
        _req(), scope_kind="guild", scope_id=None, scope_name="server",
        level="Standard"))

    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Could not stage the cleanup policy — see logs.")


# =======================================================================================
# final_review.complete_delete L926 — the count is a GUARD: failure fails CLOSED
# =======================================================================================


def test_complete_delete_count_failure_fails_closed_not_open(monkeypatch):
    """The destructive-delete GUARD contrast: here the staged-ops count is
    NOT a display feed — a failed read must BLOCK the channel delete, never
    proceed on a degraded 0. Pins the asymmetry that keeps a delete from
    firing over an unreadable draft."""
    from sb.domain.setup import store as setup_store
    from sb.domain.setup import wizard

    monkeypatch.setattr(wizard, "can_apply_setup", _Gate(True))

    async def complete_session(guild_id):
        return {"setup_status": "complete", "setup_channel_id": 12345}

    monkeypatch.setattr(setup_store, "get_session_row", complete_session)

    async def boom(guild_id):
        raise RuntimeError("count read failed")

    monkeypatch.setattr(wizard, "staged_ops_count", boom)

    reply = run(_resolve("setup.complete_delete")(_req()))

    assert reply.outcome == BLOCKED
    # shipped count-failed guard copy, verbatim (never a silent delete).
    assert reply.user_message == (
        "⚠️ Couldn't read the staged-ops count — see logs.  Re-run Final "
        "Review or try again later.")


# =======================================================================================
# the pure-render soft-fails — panels L717 / final_review L669
# read-only cards degrade to 0 / empty and NEVER propagate the read failure
# =======================================================================================


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


def test_sections_hub_render_survives_a_count_read_failure(monkeypatch):
    """``_render_sections_hub`` reads ``staged_ops_count`` for the pending
    line only. A failed read degrades to 0 and the card still renders — a
    display read may never break the hub."""
    from sb.domain.setup import panels, store, wizard

    async def no_session(guild_id):
        return None

    async def boom(guild_id):
        raise RuntimeError("count read failed")

    monkeypatch.setattr(store, "get_session_row", no_session)
    monkeypatch.setattr(wizard, "staged_ops_count", boom)

    rendered = run(panels._render_sections_hub(
        panels.sections_hub_spec(), _ctx()))

    # it returned (no propagation) — a real rendered panel with components.
    assert rendered is not None
    assert hasattr(rendered, "components")


def test_final_review_render_survives_a_staged_ops_read_failure(monkeypatch):
    """``_render_final_review`` reads the staged ops for the embed +
    Apply-button gate. A failed read degrades to empty (ops=[]) — the card
    renders the empty state and drops Apply, never propagating."""
    from sb.domain.setup import final_review

    async def boom(guild_id):
        raise RuntimeError("staged-ops read failed")

    monkeypatch.setattr(final_review, "_staged_ops", boom)

    rendered = run(final_review._render_final_review(
        final_review.final_review_spec(), _ctx()))

    assert rendered is not None
    # the empty-state render drops the Apply button (ops degraded to []).
    assert all(getattr(c, "custom_id", "") != "setup_final_review:apply"
               for c in rendered.components)
