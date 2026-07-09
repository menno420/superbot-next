"""The CUT-1 composition root (sb/app/main.py) — cheap wiring facts, no
network, no DB: the module is import-safe without runtime deps (guarded-
import discipline), the subscribe roster names real ``subscribe(bus)``
obligations, the escrow-recovery roster matches the domain constants, and
the drain step terminates on an emptied outbox."""

from __future__ import annotations

import asyncio
import importlib

from sb.app import main as app_main


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


class _RecordingBus:
    def __init__(self) -> None:
        self.subscriptions: list[str] = []

    def on(self, event_name: str, handler) -> None:
        self.subscriptions.append(event_name)


class TestSubscribeRoster:
    def test_every_roster_module_exposes_subscribe(self):
        for module_path in app_main.SUBSCRIBE_ROSTER:
            module = importlib.import_module(module_path)
            assert callable(getattr(module, "subscribe", None)), module_path

    def test_arm_subscribe_roster_arms_every_module(self):
        bus = _RecordingBus()
        armed = app_main.arm_subscribe_roster(bus)
        assert armed == app_main.SUBSCRIBE_ROSTER
        # every fan-out module that bus.on-subscribes did so on THIS bus
        # (role.service holds the bus by reference instead — no on() call).
        assert "xp.level_up" in bus.subscriptions
        assert "economy.balance_changed" in bus.subscriptions
        assert "moderation.action_taken" in bus.subscriptions


class TestEscrowRecoveryRoster:
    def test_roster_matches_the_domain_constants(self):
        from sb.domain.blackjack import ops as blackjack_ops
        from sb.domain.rps import ops as rps_ops

        assert blackjack_ops.PVP_ESCROW_SUBSYSTEM in app_main.ESCROW_RECOVERY_SUBSYSTEMS
        assert rps_ops.PVP_ESCROW_SUBSYSTEM in app_main.ESCROW_RECOVERY_SUBSYSTEMS


class TestSnapshot:
    def test_committed_snapshot_loads(self):
        snapshot = app_main.committed_snapshot()
        assert snapshot.get("stable_hash")
        assert snapshot.get("subsystems")


class TestDrainOutbox:
    def test_drain_returns_zero_when_ticks_empty_the_outbox(self, monkeypatch):
        from sb.kernel.db import pool

        pending = {"n": 2}

        async def fake_fetchone(query, params=(), *, conn=None):
            return dict(pending)

        class _Supervisor:
            def __init__(self) -> None:
                self.ticks = 0

            async def tick_once(self):
                self.ticks += 1
                pending["n"] = max(0, pending["n"] - 1)
                return []

        monkeypatch.setattr(pool, "fetchone", fake_fetchone)
        supervisor = _Supervisor()
        left = run(app_main._drain_outbox(supervisor, grace_s=5.0))
        assert left == 0
        assert supervisor.ticks == 2


class TestGatewayAdapter:
    def test_import_is_guarded(self):
        from sb.adapters.discord import gateway

        if gateway.DISCORD_AVAILABLE:
            assert callable(gateway.build_intents)
        else:
            import pytest

            with pytest.raises(RuntimeError):
                gateway.build_intents(object())
