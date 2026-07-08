"""S10: apply_draft — sequenced per-op run(), stop-on-first-failure,
CAS terminal status, fail-closed confirmation gate (spec 06 §3.5)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from sb.kernel.draft import apply as apply_mod
from sb.kernel.draft.apply import apply_draft
from sb.kernel.draft.preview import DraftConfirmationSpec, DraftPreview
from sb.kernel.draft.registry import OpKindBinding, OpKindRegistry
from sb.spec.draft import (
    ConfirmChallenge,
    ConfirmationResponse,
    Draft,
    DraftOperation,
    DraftStatus,
    OwnerScope,
    Producer,
)
from sb.spec.outcomes import DECLINED, PARTIAL, SUCCESS
from sb.spec.refs import WorkflowRef

from tests.unit.draft.test_preview_accept import _decision

run = asyncio.run
NOW = datetime(2026, 7, 8, tzinfo=timezone.utc)


class FakeStore:
    def __init__(self, reaper_wins=False):
        self.status_writes = []
        self.reaper_wins = reaper_wins
        self.current = DraftStatus.OPEN

    async def set_status(self, draft_id, status, *, expect=None):
        if (self.reaper_wins and status is DraftStatus.APPLIED
                and expect is DraftStatus.APPLYING):
            self.current = DraftStatus.PARTIAL
            return False
        self.status_writes.append((status, expect))
        self.current = status
        return True

    async def load(self, draft_id):
        return Draft(draft_id=draft_id, producer=Producer.HUMAN_SETUP,
                     owner_scope=OwnerScope(guild_id=42, actor_id=7),
                     status=self.current, operations=(), created_at=NOW,
                     updated_at=NOW, correlation_id=draft_id)


class FakeResult:
    def __init__(self, outcome, user_message=None):
        self.outcome = outcome
        self.user_message = user_message
        self.mutation_id = "m"


class FakeEngine:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.contexts = []

    async def run(self, ref, ctx):
        self.contexts.append((ref, ctx))
        return FakeResult(self.outcomes.pop(0))


def make_draft(n_ops=2, producer=Producer.HUMAN_SETUP):
    ops = tuple(DraftOperation(
        op_seq=i + 1, op_kind="set_setting", subsystem="logging",
        authority_ref="settings.manage", payload={"i": i}, label=f"op{i}",
        dedup_token=f"d1:{i + 1}") for i in range(n_ops))
    return Draft(draft_id="d1", producer=producer,
                 owner_scope=OwnerScope(guild_id=42, actor_id=7),
                 status=DraftStatus.PREVIEWED, operations=ops,
                 created_at=NOW, updated_at=NOW, correlation_id="d1")


def make_preview(requires=True):
    return DraftPreview(
        draft_id="d1", preview_hash="h", allowed=True, op_previews=(),
        aggregate_reversibility="reversible", warnings=(),
        requires_confirmation=requires,
        confirmation=DraftConfirmationSpec(
            reversibility="reversible", challenge=ConfirmChallenge.BUTTON),
        blocking=())


def registry_with():
    reg = OpKindRegistry()
    reg.register(OpKindBinding(op_kind="set_setting",
                               workflow_ref=WorkflowRef("settings.set"),
                               payload_schema=()))
    return reg


def apply_kwargs(engine, store):
    return dict(actor=object(), store=store, registry=registry_with(),
                clock=lambda: NOW)


def test_full_success_applies_and_cas_flips_applied(monkeypatch):
    engine = FakeEngine([SUCCESS, SUCCESS])
    monkeypatch.setattr(apply_mod, "workflow_engine", engine)
    store = FakeStore()
    result = run(apply_draft(make_draft(), _decision(True, ""), make_preview(),
                             ConfirmationResponse(ConfirmChallenge.BUTTON),
                             **apply_kwargs(engine, store)))
    assert result.outcome == SUCCESS
    assert result.applied == (1, 2) and not result.failed
    assert (DraftStatus.APPLIED, DraftStatus.APPLYING) in store.status_writes
    # correlation + dedup token threaded into every op ctx.
    for _, ctx in engine.contexts:
        assert ctx.correlation_id == "d1"
        assert ctx.params["_draft_dedup_token"].startswith("d1:")
        assert ctx.confirmed is True


def test_mid_fail_stops_partial_and_skips_rest(monkeypatch):
    engine = FakeEngine([SUCCESS, "blocked", SUCCESS])
    monkeypatch.setattr(apply_mod, "workflow_engine", engine)
    store = FakeStore()
    result = run(apply_draft(make_draft(3), _decision(True, ""), make_preview(),
                             ConfirmationResponse(ConfirmChallenge.BUTTON),
                             **apply_kwargs(engine, store)))
    assert result.outcome == PARTIAL
    assert result.applied == (1,) and result.failed == (2,) and result.skipped == (3,)
    assert store.current is DraftStatus.PARTIAL


def test_unverified_confirmation_declines_with_no_writes(monkeypatch):
    engine = FakeEngine([SUCCESS])
    monkeypatch.setattr(apply_mod, "workflow_engine", engine)
    store = FakeStore()
    result = run(apply_draft(make_draft(1), _decision(True, ""), make_preview(),
                             None, **apply_kwargs(engine, store)))
    assert result.outcome == DECLINED
    assert store.status_writes == [] and engine.contexts == []


def test_denied_decision_declines_with_no_writes(monkeypatch):
    engine = FakeEngine([])
    monkeypatch.setattr(apply_mod, "workflow_engine", engine)
    store = FakeStore()
    result = run(apply_draft(make_draft(1), _decision(False, "x"), make_preview(),
                             ConfirmationResponse(ConfirmChallenge.BUTTON),
                             **apply_kwargs(engine, store)))
    assert result.outcome == DECLINED and store.status_writes == []


def test_reaper_race_honors_partial_never_clobbers(monkeypatch):
    engine = FakeEngine([SUCCESS])
    monkeypatch.setattr(apply_mod, "workflow_engine", engine)
    store = FakeStore(reaper_wins=True)
    result = run(apply_draft(make_draft(1), _decision(True, ""),
                             make_preview(requires=False), None,
                             **apply_kwargs(engine, store)))
    assert result.outcome == PARTIAL          # the reaper's verdict is honored
