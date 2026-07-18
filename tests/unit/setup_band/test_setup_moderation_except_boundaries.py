"""Characterization of the FOUR `except Exception` swallows in
`sb/domain/setup/moderation.py` (prod-readiness backlog item C1 — the
setup-band except-density audit).

The sibling `test_settings_write_flows.py` drives the moderation happy
paths and the gate refusal; NONE of its cases exercise the except arm.
This suite pins what each swallow DOES when the guarded op RAISES, so a
future edit to any boundary reds visibly. It changes NO product
behavior — additive, DB-free (the K7/K9 write seams and the two
read-current-state imports are monkeypatched at their module
functions), mirroring the settings-write suite's harness.

Boundaries pinned (line numbers at the born-red HEAD):

* `_stage_setting` L224 — `section_card.stage_custom` raises ⇒
  `Reply(BLOCKED, "Could not stage the moderation setting — see logs.")`
  (**fail-CLOSED**: the write error is surfaced as a refusal, never a
  staged success).
* `_stage_setting` L232 — `wizard.staged_ops_count` raises ⇒ still
  `SUCCESS`, `pending` degrades to **0** (the stage already committed;
  the count is display-only — informational fail-soft).
* `read_current_state` L172 — `load_policy` raises ⇒ the three policy
  values degrade to `None`.
* `read_current_state` L181 — settings `resolve` raises ⇒
  `moderator_role_id` degrades to `None`.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_state():
    import sb.manifest.governance as mgov
    import sb.manifest.moderation as mmod
    import sb.manifest.setup as m
    from sb.domain.setup import channels, cleanup, preset_select, wizard
    from sb.domain.setup import wizard_nav
    from sb.kernel import settings as ksettings

    m.ENSURE_REFS()
    for manifest in (mmod.MANIFEST, mgov.MANIFEST):
        try:
            ksettings.register_manifest_settings(manifest)
        except ValueError:
            pass    # already declared by an earlier test
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    cleanup.reset_cleanup_state_for_tests()
    yield
    wizard.reset_wizard_state_for_tests()
    wizard_nav.reset_wizard_nav_state_for_tests()
    preset_select.reset_preset_state_for_tests()
    channels.reset_channels_state_for_tests()
    cleanup.reset_cleanup_state_for_tests()


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
    def __init__(self, drafts=()):
        self.drafts = list(drafts)
        self.added: list = []

    async def list_open(self, scope):
        return tuple(self.drafts)

    async def create(self, *, producer, owner_scope):
        draft = SimpleNamespace(draft_id="d-new", operations=())
        self.drafts.append(draft)
        return draft

    async def add(self, draft_id, op):
        self.added.append((draft_id, op))


def _patch_store(monkeypatch, store):
    from sb.kernel.draft import store as draft_store_module

    monkeypatch.setattr(draft_store_module, "DraftStore", lambda: store)


def _patch_write_seams(monkeypatch, *, pending=1):
    """Gate open + K7 engine no-op + count + refresh — the shared
    staging-path harness (settings-write suite twin)."""
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
# _stage_setting L224 — stage_custom raises ⇒ fail-CLOSED BLOCKED refusal
# =======================================================================================


def test_stage_write_failure_is_a_blocked_refusal_not_a_staged_success(
        monkeypatch):
    """When the K9 append (`section_card.stage_custom`) raises, the pick
    surfaces the shipped BLOCKED refusal copy — it does NOT report the
    setting as staged. This is the fail-CLOSED boundary: a write error
    can never masquerade as a Final-review-bound success."""
    from sb.domain.setup import section_card

    _patch_write_seams(monkeypatch)

    async def boom(guild_id, slug, op):
        raise RuntimeError("draft store unavailable")

    monkeypatch.setattr(section_card, "stage_custom", boom)

    reply = run(_resolve("setup.moderation_dm_pick")(
        _req(args={"values": ["true"]})))

    assert reply.outcome == BLOCKED
    # shipped copy, verbatim (moderation._stage_setting).
    assert reply.user_message == (
        "Could not stage the moderation setting — see logs.")


def test_stage_write_failure_short_circuits_before_the_count(monkeypatch):
    """The refusal returns before `staged_ops_count` is consulted — the
    count swallow is downstream of a committed stage, never reached on
    the write-failure arm."""
    from sb.domain.setup import section_card, wizard

    _patch_write_seams(monkeypatch)

    async def boom(guild_id, slug, op):
        raise RuntimeError("draft store unavailable")

    monkeypatch.setattr(section_card, "stage_custom", boom)

    counted: list[int] = []

    async def spy_count(guild_id):
        counted.append(int(guild_id))
        return 7

    monkeypatch.setattr(wizard, "staged_ops_count", spy_count)

    reply = run(_resolve("setup.moderation_reason_pick")(
        _req(args={"values": ["false"]})))

    assert reply.outcome == BLOCKED
    assert counted == []    # never counted after a failed stage


# =======================================================================================
# _stage_setting L232 — staged_ops_count raises ⇒ SUCCESS, pending degrades to 0
# =======================================================================================


def test_count_read_failure_still_answers_success_with_zero_pending(
        monkeypatch):
    """The stage already committed (the real `_FakeStore` recorded the
    op); only the display count read raises. The pick still answers
    SUCCESS and the pending count soft-fails to 0 — informational
    degradation, not a refusal."""
    from sb.domain.setup import wizard

    _patch_write_seams(monkeypatch)
    store = _FakeStore([SimpleNamespace(draft_id="d-1", operations=())])
    _patch_store(monkeypatch, store)

    async def boom_count(guild_id):
        raise RuntimeError("count read failed")

    monkeypatch.setattr(wizard, "staged_ops_count", boom_count)

    reply = run(_resolve("setup.moderation_dm_pick")(
        _req(args={"values": ["true"]})))

    assert reply.outcome == SUCCESS
    # the write did land — the count swallow rides strictly AFTER it.
    assert len(store.added) == 1
    # shipped confirmation shape, pending degraded to 0.
    assert reply.user_message == (
        "✅ Staged for Final review: `moderation.dm_on_action = True`.  "
        "Pending operations: **0**.")


# =======================================================================================
# read_current_state L172 / L181 — the two informational read swallows
# =======================================================================================


def test_read_current_state_degrades_policy_values_when_load_policy_raises(
        monkeypatch):
    """`load_policy` raising degrades the three policy-sourced values to
    None; the snapshot is informational and must never block the
    render. The moderator-role read is independent and still runs."""
    import sb.kernel.settings as ksettings
    from sb.domain.moderation import service as mod_service
    from sb.domain.setup.moderation import read_current_state

    async def boom_policy(guild_id):
        raise RuntimeError("policy backend down")

    async def ok_resolve(guild_id, subsystem, name):
        return None     # no moderator role configured

    monkeypatch.setattr(mod_service, "load_policy", boom_policy)
    monkeypatch.setattr(ksettings, "resolve", ok_resolve)

    dm_on, require_reason, escalation, role_id = run(read_current_state(99))

    assert dm_on is None
    assert require_reason is None
    assert escalation is None
    assert role_id is None


def test_read_current_state_degrades_role_when_resolve_raises(monkeypatch):
    """The moderator-role `resolve` raising degrades ONLY
    `moderator_role_id` to None; the three policy values still read off
    the (working) load_policy."""
    import sb.kernel.settings as ksettings
    from sb.domain.moderation import service as mod_service
    from sb.domain.setup.moderation import read_current_state

    async def ok_policy(guild_id):
        return SimpleNamespace(dm_on_action=True, require_reason=False,
                               warn_escalation_action="kick")

    async def boom_resolve(guild_id, subsystem, name):
        raise RuntimeError("settings read failed")

    monkeypatch.setattr(mod_service, "load_policy", ok_policy)
    monkeypatch.setattr(ksettings, "resolve", boom_resolve)

    dm_on, require_reason, escalation, role_id = run(read_current_state(99))

    assert dm_on is True
    assert require_reason is False
    assert escalation == "kick"
    assert role_id is None
