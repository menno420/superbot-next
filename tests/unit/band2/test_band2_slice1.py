"""Band 2 slice 1 (moderation + logging) — seam-level unit legs."""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def _clean_settings_registry():
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    yield
    ksettings.clear_for_tests()


def _register_declarations():
    import sb.manifest.moderation as m_mod
    import sb.manifest.server_logging as m_log
    from sb.kernel.settings import register_manifest_settings

    for mod in (m_mod, m_log):
        try:
            register_manifest_settings(mod.MANIFEST)
        except ValueError as exc:
            if "already declared" not in str(exc):
                raise


def test_moderation_policy_defaults_are_shipped_values():
    from sb.domain.moderation.service import load_policy

    _register_declarations()
    policy = asyncio.run(load_policy(1))
    assert policy.warn_threshold == 3
    assert policy.warn_timeout_minutes == 10
    assert policy.warn_escalation_action == "timeout"
    assert policy.require_reason is False
    assert policy.max_timeout_minutes == 40320
    assert policy.public_log_actions == "none"


def test_require_reason_blocks_before_side_effects():
    from sb.domain.moderation.service import (
        ModerationPolicy,
        ReasonRequiredError,
        resolve_reason,
    )

    policy = ModerationPolicy(require_reason=True)
    with pytest.raises(ReasonRequiredError):
        resolve_reason("", policy, action="warn")
    # timeout is exempt (its reason carries the duration — shipped rule)
    assert resolve_reason("", policy, action="timeout") == "No reason provided"


def test_parse_target_and_reason_prefix_form():
    from sb.domain.moderation.service import parse_target_and_reason

    target, reason = parse_target_and_reason(
        {"argv": ("<@900000000000000103>", "parity", "test")})
    assert target == 900000000000000103
    assert reason == "parity test"
    with pytest.raises(ValueError):
        parse_target_and_reason({"argv": ("not-a-mention",)})


def test_warn_escalation_ladder(monkeypatch):
    """Threshold reached => escalation recorded + count reset IN the leg
    (shipped WarnOutcome semantics), decision threaded to the EFFECT leg."""
    from types import SimpleNamespace

    from sb.domain.moderation import ops, store
    from sb.kernel.workflow.context import WorkflowContext

    _register_declarations()
    rows: list[tuple] = []
    counts = {"n": 2}

    async def fake_add_warning(conn, *, user_id, guild_id):
        counts["n"] += 1
        return counts["n"]

    async def fake_clear(conn, *, user_id, guild_id):
        counts["n"] = 0

    async def fake_log(conn, *, guild_id, action, target_id, moderator_id,
                       reason, at=None):
        rows.append((action, target_id, reason))

    monkeypatch.setattr(store, "add_warning", fake_add_warning)
    monkeypatch.setattr(store, "clear_warnings", fake_clear)
    monkeypatch.setattr(store, "log_mod_action", fake_log)

    ctx = WorkflowContext(
        actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
        request_id="r1", confirmed=False,
        params={"argv": ("<@900000000000000103>", "spam")})
    outcome = asyncio.run(ops._record_warn(None, ctx))
    assert outcome.after["escalated"] == "timeout"   # 3rd warn hits threshold
    assert counts["n"] == 0                          # ladder resets the count
    assert [r[0] for r in rows] == ["warn", "timeout"]
    assert ctx.params["_escalation"] == "timeout"
    assert ctx.params["_target_id"] == 900000000000000103


def test_op_reversibility_rollup_and_kick_confirmation():
    from sb.domain.moderation.ops import KICK, register_ops
    from sb.kernel.workflow.registry import REGISTRY
    from sb.spec.refs import WorkflowRef

    register_ops()                    # REGISTRY stamps the derived rollup

    def rev(key: str) -> str:
        return REGISTRY.resolve(WorkflowRef(key)).reversibility

    assert rev("moderation.warn") == "reversible"
    assert rev("moderation.ban") == "compensatable"
    assert rev("moderation.kick") == "irreversible"
    assert KICK.confirmation is not None            # the frozen §2.7 fence
    assert rev("moderation.clearwarnings") == "reversible"


def test_logging_config_defaults_and_degrade():
    from sb.domain.server_logging.service import load_config

    _register_declarations()
    config = asyncio.run(load_config(1))
    assert config.enabled is False                  # OFF_UNTIL_OPT_IN
    assert config.routing == "combined"
    assert set(config.category_enabled) == {
        "messages", "members", "roles", "moderation", "channels",
        "server", "voice"}
    assert not any(config.category_enabled.values())


def test_moderation_fanout_routes_to_bound_channel(monkeypatch):
    from sb.domain.server_logging import service
    from sb.kernel.events_bus import EventBus
    from sb.kernel.interaction import egress

    service.reset_counters_for_tests()
    sent: list[tuple] = []

    class FakeEmitter:
        async def send(self, channel_id, content, *, guild_id):
            sent.append((channel_id, content.body, content.trust))
            return egress.EmitResult(sent=True, message_id=1)

    egress.install_channel_emitter(FakeEmitter())

    async def fake_config(guild_id):
        return service.LoggingConfig(
            enabled=True, category_enabled={"moderation": True})

    async def fake_bound(guild_id, name):
        return 555 if name == "mod" else None

    monkeypatch.setattr(service, "load_config", fake_config)
    monkeypatch.setattr(service, "bound_channel", fake_bound)

    bus = EventBus()
    service.subscribe(bus)
    delivered = asyncio.run(bus.emit(
        "moderation.action_taken", guild_id=1, action="warn",
        target_id=2, actor_id=3, reason="spam"))
    assert delivered == 1
    assert sent and sent[0][0] == 555
    assert "warn" in sent[0][1]
    assert service.counters().get("sent_total") == 1
    egress.reset_channel_emitter_for_tests()


def test_fanout_disabled_counts_skip(monkeypatch):
    from sb.domain.server_logging import service
    from sb.kernel.events_bus import EventBus

    service.reset_counters_for_tests()
    _register_declarations()          # defaults: disabled
    bus = EventBus()
    service.subscribe(bus)
    asyncio.run(bus.emit("moderation.action_taken", guild_id=1,
                         action="ban", target_id=2, actor_id=3, reason=""))
    assert service.counters().get("skipped_disabled") == 1


def test_band2_ai_task_claims():
    from sb.domain.moderation.ai_tasks import register_ai_tasks as reg_mod
    from sb.domain.server_logging.ai_tasks import register_ai_tasks as reg_log
    from sb.kernel.ai import tasks

    tasks.clear_tasks_for_tests()
    try:
        reg_mod()
        reg_log()
        assert tasks.get_task("moderation.assist") is not None
        assert tasks.get_task("logs.triage") is not None
    finally:
        tasks.clear_tasks_for_tests()


def test_qualified_name_and_group_field():
    from sb.spec.commands import CommandKind, CommandSpec

    spec = CommandSpec(name="status", kind=CommandKind.PREFIX, group="logging")
    assert spec.qualified_name == "logging status"
    bare = CommandSpec(name="warn", kind=CommandKind.PREFIX)
    assert bare.qualified_name == "warn"
