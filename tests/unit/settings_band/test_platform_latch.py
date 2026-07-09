"""ORDER 004 item 4 — the S15 platform-latch persist rides the K7 lane.

`_state_write`'s raw `upsert_setting` bypassed the sole-writer/audit lane
(the four-reviewer audit's finding); `settings.platform_latch` is its
audited home. These tests pin: the op registers with the audit verb and no
advisory emit, the leg fences on the `platform.*` prefix (no raw-KV write
path through the system lane either), and `_state_write` dispatches the op
with a system actor instead of touching the table itself.
"""

from __future__ import annotations

import asyncio

import pytest


def test_platform_latch_op_registers_on_the_k7_lane():
    from sb.domain.settings.ops import register_ops
    from sb.kernel.workflow.registry import REGISTRY

    register_ops()
    spec = REGISTRY.resolve_op_kind("settings.platform_latch")
    assert spec.domain == "settings"
    assert spec.audit_verb == "platform_latch_set"
    assert spec.idempotency.value == "natural_key"
    assert spec.emits == ()          # kernel marker, not operator config
    assert len(spec.legs) == 1 and spec.legs[0].kind.value == "db"


def test_platform_latch_leg_fences_on_the_platform_prefix():
    from sb.domain.settings import ops
    from sb.kernel.workflow.context import WorkflowContext

    ctx = WorkflowContext(actor=object(), guild_id=0, request_id="r1",
                          params={"key": "economy.daily_amount", "value": "9"})
    with pytest.raises(ValueError, match="platform"):
        asyncio.run(ops._write_platform_latch(None, ctx))


def test_platform_latch_leg_writes_guild_zero(monkeypatch):
    from sb.domain.settings import ops
    from sb.kernel.workflow.context import WorkflowContext

    seen = {}

    async def fake_upsert(conn, *, guild_id, key, value):
        seen.update(guild_id=guild_id, key=key, value=value)
        return "old"

    monkeypatch.setattr(ops.db_settings, "upsert_setting", fake_upsert)
    ctx = WorkflowContext(actor=object(), guild_id=1234, request_id="r2",
                          params={"key": "platform.degrade_state", "value": "none"})
    outcome = asyncio.run(ops._write_platform_latch(object(), ctx))
    assert seen == {"guild_id": 0, "key": "platform.degrade_state",
                    "value": "none"}
    assert outcome.before == {"key": "platform.degrade_state", "value": "old"}
    assert outcome.after == {"key": "platform.degrade_state", "value": "none"}


def test_state_write_dispatches_the_op_with_a_system_actor(monkeypatch):
    from sb.domain.settings import service
    from sb.kernel.workflow import engine

    calls = {}

    async def fake_run(target, ctx, **kw):
        calls["op_key"] = getattr(target, "op_key", target)
        calls["actor_type"] = getattr(ctx.actor, "actor_type", None)
        calls["params"] = dict(ctx.params)
        calls["guild_id"] = ctx.guild_id
        from sb.kernel.workflow.result import WorkflowResult
        from sb.spec.outcomes import SUCCESS

        return WorkflowResult(mutation_id="m", guild_id=0, domain="settings",
                              operation="settings.platform_latch",
                              outcome=SUCCESS, reversibility="reversible",
                              lane=target.lane)

    monkeypatch.setattr(engine, "run", fake_run)

    async def drive():
        service._state_write("platform.guildcap.75", "fired")
        await asyncio.sleep(0)           # let the fire-and-forget task run
        await asyncio.sleep(0)

    asyncio.run(drive())
    assert service._state_read("platform.guildcap.75") == "fired"
    assert calls["op_key"] == "settings.platform_latch"
    assert calls["actor_type"] == "system"
    assert calls["guild_id"] == 0
    assert calls["params"] == {"key": "platform.guildcap.75", "value": "fired"}


def test_state_write_swallows_a_failed_persist(monkeypatch, caplog):
    """Best-effort BY DESIGN: a lost persist re-fires the notice at the next
    boot warm-up — the sync caller must never see the failure."""
    from sb.domain.settings import service
    from sb.kernel.workflow import engine

    async def boom(target, ctx, **kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(engine, "run", boom)

    async def drive():
        service._state_write("platform.degrade_state", "prefix")
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(drive())                 # must not raise
    assert service._state_read("platform.degrade_state") == "prefix"
