"""S11: class-11/12/13 mechanics — cost fence, data-lifecycle fence,
erasure executor + export twin, egress port defaults, AST fence."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field

import pytest

from sb.kernel.interaction.egress import (
    OutboundContent,
    TrustLevel,
    active_channel_emitter,
    install_channel_emitter,
    neutralize_untrusted,
    reset_channel_emitter_for_tests,
)
from sb.kernel.privacy import erasure as er
from sb.spec.cost import CostPosture, check_command_cost_posture
from sb.spec.refs import HandlerRef, WorkflowRef
from sb.spec.versioning import (
    CacheScope,
    CheckpointClass,
    DataClass,
    StoreSpec,
    clear_store_registry_for_tests,
    register_store,
    registered_stores,
)

run = asyncio.run


# --- class 11: cost posture -----------------------------------------------------

@dataclass
class Cmd:
    name: str = "ai_image"
    effect: str = "external"
    cost_posture: object = CostPosture.FREE
    quota_ref: str = ""


def test_external_free_is_red_fail_closed_is_the_honest_interim():
    assert check_command_cost_posture(Cmd())                      # FREE + external ⇒ red
    assert not check_command_cost_posture(Cmd(cost_posture=CostPosture.FAIL_CLOSED))
    assert not check_command_cost_posture(
        Cmd(cost_posture=CostPosture.BUDGET_CAP, quota_ref="media.spend"))


def test_quota_posture_requires_counter_and_inert_ref_is_red():
    assert check_command_cost_posture(Cmd(cost_posture=CostPosture.PER_GUILD_QUOTA))
    assert check_command_cost_posture(
        Cmd(cost_posture=CostPosture.FREE, effect="read", quota_ref="dangling"))
    assert not check_command_cost_posture(Cmd(effect="read"))     # plain read: clean


# --- class 12: data lifecycle ----------------------------------------------------

def make_store(**kw) -> StoreSpec:
    defaults = dict(table="xp_events", sole_writer=WorkflowRef("xp.write"),
                    retention="365d", checkpoint_class=CheckpointClass.LEDGER,
                    invariant_tag="INV-G")
    defaults.update(kw)
    return StoreSpec(**defaults)


def test_check_data_lifecycle_rules():
    from tools.check_data_lifecycle import check
    member = make_store(data_class=DataClass.MEMBER_ID)
    assert any("erasure_ref" in p for p in check([member]))       # (a) hook required
    assert any("retention" in p for p in check([make_store(
        data_class=DataClass.MEMBER_PII, retention="",
        erasure_ref=WorkflowRef("xp.erase"))]))
    assert any("WorkflowRef" in p for p in check([make_store(
        data_class=DataClass.MEMBER_ID, erasure_ref=HandlerRef("xp.erase"))]))  # (c)
    assert any("cache_scope" in p for p in check([make_store(is_cache=True)]))  # (b)
    assert any("GUILD" in p for p in check([make_store(
        data_class=DataClass.MEMBER_PII, erasure_ref=WorkflowRef("xp.erase"),
        is_cache=True, cache_scope=CacheScope.GLOBAL)]))          # member cache ⇒ guild
    assert check([make_store(data_class=DataClass.MEMBER_ID,
                             erasure_ref=WorkflowRef("xp.erase"))]) == []


def test_kernel_stores_registered_and_clean():
    import sb.kernel.db.draft  # noqa: F401
    import sb.kernel.db.idempotency  # noqa: F401
    import sb.kernel.db.scheduler  # noqa: F401
    import sb.kernel.outbox.store  # noqa: F401
    import sb.kernel.workflow.audit  # noqa: F401
    tables = {s.table for s in registered_stores()}
    assert {"event_outbox", "audit_log", "idempotency_keys",
            "sb_due_queue", "sb_drafts"} <= tables
    from tools.check_data_lifecycle import check
    assert check(registered_stores()) == []


# --- the erasure executor + export twin -------------------------------------------

class FakeIdem:
    def __init__(self):
        self.keys = {}

    async def once(self, key, *, conn):
        if key.render() in self.keys:
            return False
        self.keys[key.render()] = None
        return True

    async def record_outcome(self, key, outcome, *, result_ref=None, conn):
        self.keys[key.render()] = outcome

    async def read_outcome(self, key, *, conn):
        return None


@dataclass
class FakeResult:
    outcome: str = "success"
    mutation_id: str = "m1"
    after: dict = field(default_factory=dict)


@pytest.fixture
def erasure_env(monkeypatch):
    clear_store_registry_for_tests()
    idem = FakeIdem()
    ran = []
    results: dict[str, object] = {}

    class FakeEngine:
        @staticmethod
        async def run_ref(ref, ctx, *, conn=None):
            ran.append(ref.name)
            out = results.get(ref.name, FakeResult())
            if isinstance(out, Exception):
                raise out
            return out

    @contextlib.asynccontextmanager
    async def fake_tx():
        yield object()

    monkeypatch.setattr(er, "transaction", fake_tx)
    monkeypatch.setattr(er, "once", idem.once)
    monkeypatch.setattr(er, "record_outcome", idem.record_outcome)
    monkeypatch.setattr(er, "read_outcome", idem.read_outcome)
    monkeypatch.setattr(er, "workflow_engine", FakeEngine)
    er.reset_export_readers_for_tests()
    yield idem, ran, results
    clear_store_registry_for_tests()
    er.reset_export_readers_for_tests()


def _register_two_stores():
    register_store(make_store(
        table="xp_events", data_class=DataClass.MEMBER_ID,
        erasure_ref=WorkflowRef("xp.tombstone"), bears_value=True,
        compensation_ref=WorkflowRef("xp.comp")))
    register_store(make_store(
        table="greet_cache", checkpoint_class=CheckpointClass.SESSION,
        data_class=DataClass.MEMBER_PII, erasure_ref=WorkflowRef("greet.erase"),
        is_cache=True, cache_scope=CacheScope.GUILD,
        active_rows_ref=None))
    register_store(make_store(table="config_presets"))   # NONE — outside the walk


def test_run_erasure_walks_every_member_store_and_proves_complete(erasure_env):
    idem, ran, results = erasure_env
    _register_two_stores()
    results["xp.tombstone"] = FakeResult(
        after={"disposition": "tombstoned", "rows_affected": 12})
    results["greet.erase"] = FakeResult(
        after={"disposition": "erased", "rows_affected": 3})
    result = run(er.run_erasure(er.ErasureTrigger.GUILD_LEAVE, guild_id=42,
                                subject_id=None, actor=object()))
    assert result.complete
    assert {leg.store for leg in result.legs} == {"xp_events", "greet_cache"}
    dispositions = {leg.store: leg.disposition for leg in result.legs}
    assert dispositions["xp_events"] is er.ErasureDisposition.TOMBSTONED
    assert dispositions["greet_cache"] is er.ErasureDisposition.ERASED
    assert len(idem.keys) == 2
    # idempotent replay: no second workflow run, still complete.
    result2 = run(er.run_erasure(er.ErasureTrigger.GUILD_LEAVE, guild_id=42,
                                 subject_id=None, actor=object()))
    assert result2.complete and ran.count("xp.tombstone") == 1


def test_run_erasure_failed_leg_is_resumable_partial(erasure_env):
    idem, ran, results = erasure_env
    _register_two_stores()
    results["greet.erase"] = RuntimeError("db down")
    result = run(er.run_erasure(er.ErasureTrigger.SUBJECT_REQUEST, guild_id=42,
                                subject_id=7, actor=object()))
    assert not result.complete
    assert result.unreached == ("greet_cache",)
    # the fix lands; the re-fire resumes ONLY the unreached store.
    results["greet.erase"] = FakeResult(after={"disposition": "erased",
                                               "rows_affected": 1})
    result2 = run(er.run_erasure(er.ErasureTrigger.SUBJECT_REQUEST, guild_id=42,
                                 subject_id=7, actor=object()))
    assert result2.complete
    assert ran.count("xp.tombstone") == 1     # once()-skipped on resume


def test_run_export_read_only_twin_cross_guild(erasure_env):
    _, ran, _ = erasure_env
    _register_two_stores()

    async def xp_reader(store, guild_id, subject_id):
        return ({"guild": guild_id, "subject": subject_id, "xp": 5},)
    er.install_export_reader("xp_events", xp_reader)
    result = run(er.run_export(subject_id=7, guild_ids=(42, 43)))
    assert not result.complete                       # greet_cache has no reader yet
    assert result.unreached == ("greet_cache",)
    assert len(result.rows["xp_events"]) == 2        # account-level: both guilds
    assert ran == []                                 # zero writes — read-only twin


# --- class 13: the egress port -----------------------------------------------------

def test_outbound_content_default_deny_and_neutralization():
    content = OutboundContent(body="@everyone **hi**")
    assert content.trust is TrustLevel.UNTRUSTED     # the default IS the safety
    neutralized = neutralize_untrusted(content.body)
    assert "@everyone" not in neutralized            # zero-width break
    assert "\\*\\*" in neutralized                   # markdown escaped


def test_channel_emitter_not_installed_is_loud():
    reset_channel_emitter_for_tests()
    with pytest.raises(RuntimeError, match="not installed"):
        run(active_channel_emitter().send(
            1, OutboundContent(body="x"), guild_id=42))

    class Fake:
        async def send(self, channel_id, content, *, guild_id):
            return (channel_id, content.trust, guild_id)
    install_channel_emitter(Fake())
    try:
        out = run(active_channel_emitter().send(
            5, OutboundContent(body="x"), guild_id=42))
        assert out == (5, TrustLevel.UNTRUSTED, 42)
    finally:
        reset_channel_emitter_for_tests()


def test_egress_ast_fence_clean_and_catches_a_rogue_send(tmp_path):
    import tools.check_egress as fence
    assert fence.check() == []                       # the tree is clean at S11

    rogue = fence.SB / "kernel" / "_rogue_egress_probe.py"
    rogue.write_text(
        "async def bad(channel, member):\n"
        "    await channel.send('@everyone hi')\n"
        "    await member.add_roles(role)\n")
    try:
        problems = fence.check()
        assert any(".send" in p for p in problems)
        assert any(".add_roles" in p for p in problems)   # the A-5 widening
    finally:
        rogue.unlink()
