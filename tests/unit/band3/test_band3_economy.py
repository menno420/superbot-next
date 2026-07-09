"""Band 3 slice 1 (economy core) — seam-level unit legs."""

from __future__ import annotations

import asyncio
import datetime as dt
import random
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _clean_registries():
    from sb.domain.economy.service import reset_economy_ports_for_tests
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    reset_economy_ports_for_tests()
    yield
    ksettings.clear_for_tests()
    reset_economy_ports_for_tests()


def _clock(epoch: int):
    return lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def _ctx(params: dict, *, uid: int = 42, gid: int = 1, epoch: int = 1_000_000):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=False, params=params, clock=_clock(epoch))


# --- catalogue (the coupled item namespace) ----------------------------------------

def test_item_namespace_is_coupled():
    from sb.domain.economy.catalogue import (
        ITEM_CATALOGUE,
        JOBS,
        SHOP_ITEMS,
        assert_item_namespace,
    )

    assert_item_namespace()          # every shop/job item resolves
    assert set(SHOP_ITEMS) <= set(ITEM_CATALOGUE)
    assert len(JOBS) == 12 and len(SHOP_ITEMS) == 3


def test_daily_weights_and_pick_are_shipped_math():
    from sb.domain.economy.catalogue import DAILY_TIERS, daily_weights, pick_daily

    assert daily_weights(0) == [45.0, 25.0, 15.0, 8.0, 5.0, 2.0]
    boosted = daily_weights(60)
    assert boosted[0] < 45.0 and sum(boosted) == pytest.approx(100.0)
    amount, label, emoji = pick_daily(1, random.Random(7))
    tier = next(t for t in DAILY_TIERS if t[0] == label)
    assert tier[2] <= amount <= tier[3] and emoji == tier[1]


def test_job_pay_mastery_cap():
    from sb.domain.economy.catalogue import job_pay

    assert job_pay("janitor", 0) == 50
    assert job_pay("janitor", 50) == 75
    assert job_pay("janitor", 250) == 100      # +100% cap


# --- fake store harness -------------------------------------------------------------

class FakeEconomyStore:
    def __init__(self, coins: int = 0, track: dict | None = None):
        self.coins = {42: coins}
        self.track = dict(track or {})
        self.audit: list[tuple] = []
        self.jobs: dict[str, int] = {}
        self.inventory: dict[int, dict[str, int]] = {42: {}}

    def install(self, monkeypatch):
        from sb.domain.economy import store

        async def ensure_and_get_economy(conn, *, user_id, guild_id):
            base = {"user_id": user_id, "guild_id": guild_id, "last_daily": 0,
                    "daily_streak": 0, "daily_count": 0, "last_worked": 0}
            base.update(self.track)
            return base

        async def credit_coins(conn, *, user_id, guild_id, amount):
            self.coins[user_id] = max(0, self.coins.get(user_id, 0) + amount)
            return self.coins[user_id]

        async def try_debit_coins(conn, *, user_id, guild_id, amount):
            if self.coins.get(user_id, 0) < amount:
                return None
            self.coins[user_id] -= amount
            return self.coins[user_id]

        async def get_coins(user_id, guild_id, conn=None):
            return self.coins.get(user_id, 0)

        async def insert_economy_audit(conn, *, guild_id, user_id, actor_id,
                                       delta, new_balance, reason):
            self.audit.append((user_id, delta, new_balance, reason))
            return f"m{len(self.audit)}"

        async def set_daily_claim(conn, *, user_id, guild_id, last_daily,
                                  daily_streak, daily_count):
            self.track.update(last_daily=last_daily, daily_streak=daily_streak,
                              daily_count=daily_count)

        async def set_last_worked(conn, *, user_id, guild_id, ts):
            self.track["last_worked"] = ts

        async def get_job_times(user_id, guild_id, job_name, conn=None):
            return self.jobs.get(job_name, 0)

        async def increment_job(conn, *, user_id, guild_id, job_name):
            self.jobs[job_name] = self.jobs.get(job_name, 0) + 1
            return self.jobs[job_name]

        async def get_inventory(user_id, guild_id, conn=None):
            return dict(self.inventory.get(user_id, {}))

        async def try_grant_unique_item(conn, *, user_id, guild_id, item_name):
            inv = self.inventory.setdefault(user_id, {})
            if inv.get(item_name, 0) > 0:
                return False
            inv[item_name] = 1
            return True

        from sb.domain.economy import store as store_mod

        for name, fn in locals().items():
            if callable(fn) and not name.startswith(("self", "monkeypatch")):
                if hasattr(store_mod, name):
                    monkeypatch.setattr(store_mod, name, fn)
        return self


# --- the daily loop -----------------------------------------------------------------

def test_daily_claim_credits_audits_and_advances_streak(monkeypatch):
    from sb.domain.economy import ops

    fake = FakeEconomyStore(coins=100,
                            track={"last_daily": 0, "daily_streak": 0,
                                   "daily_count": 0}).install(monkeypatch)
    ops.set_rng_for_tests(random.Random(7))
    ctx = _ctx({})
    out = asyncio.run(ops._record_daily(None, ctx))
    assert out.after["streak"] == 1 and out.after["claims"] == 1
    assert fake.audit and fake.audit[0][3] == "daily"
    assert fake.track["daily_streak"] == 1
    assert ctx.params["_reason"] == "daily"
    assert ctx.params["_new_balance"] == fake.coins[42]


def test_daily_cooldown_blocks_and_missed_window_resets(monkeypatch):
    from sb.domain.economy import ops
    from sb.domain.economy.service import CooldownActiveError

    now = 1_000_000
    fake = FakeEconomyStore(coins=0, track={"last_daily": now - 100,
                                            "daily_streak": 5,
                                            "daily_count": 5})
    fake.install(monkeypatch)
    with pytest.raises(CooldownActiveError):
        asyncio.run(ops._record_daily(None, _ctx({}, epoch=now)))

    # a >2x window gap resets the streak to 1 (shipped rule)
    fake2 = FakeEconomyStore(coins=0, track={"last_daily": now - 86400 * 3,
                                             "daily_streak": 9,
                                             "daily_count": 9})
    fake2.install(monkeypatch)
    ops.set_rng_for_tests(random.Random(3))
    out = asyncio.run(ops._record_daily(None, _ctx({}, epoch=now)))
    assert out.after["streak"] == 1


# --- the work loop -------------------------------------------------------------------

def test_work_pays_with_mastery_and_flags_xp_pending(monkeypatch):
    from sb.domain.economy import ops

    fake = FakeEconomyStore(coins=0).install(monkeypatch)
    fake.jobs["janitor"] = 10                       # +10% mastery
    ctx = _ctx({"job": "janitor"})
    out = asyncio.run(ops._record_work(None, ctx))
    assert out.after["pay"] == 55                   # 50 * 1.10
    assert fake.audit[0][3] == "work:janitor"
    assert fake.track["last_worked"] == 1_000_000
    assert ctx.params["_xp_gain"] == 10

    effect = asyncio.run(ops._award_work_xp(None, ctx))
    assert effect.after["xp_pending"] is True       # band-4 port not installed


def test_work_refuses_unknown_and_ineligible_jobs(monkeypatch):
    from sb.domain.economy import ops
    from sb.kernel.interaction.errors import ValidatorError

    FakeEconomyStore(coins=0).install(monkeypatch)
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_work(None, _ctx({"job": "astronaut"})))
    # ceo needs level 50 + suit + car; default level reader answers 0
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_work(None, _ctx({"job": "ceo"})))


def test_work_xp_port_installs(monkeypatch):
    from sb.domain.economy import ops, service

    FakeEconomyStore(coins=0).install(monkeypatch)
    calls = []

    async def awarder(**kwargs):
        calls.append(kwargs)
        return {"new_level": 3, "leveled_up": True}

    service.install_xp_awarder(awarder)
    ctx = _ctx({"job": "janitor"})
    asyncio.run(ops._record_work(None, ctx))
    effect = asyncio.run(ops._award_work_xp(None, ctx))
    assert effect.after["xp_pending"] is False
    assert calls and calls[0]["source"] == "work:janitor"


# --- transfers -----------------------------------------------------------------------

def test_pay_moves_coins_with_two_ledger_rows(monkeypatch):
    from sb.domain.economy import ops

    fake = FakeEconomyStore(coins=500).install(monkeypatch)
    ctx = _ctx({"argv": ("<@900000000000000103>", "200")})
    out = asyncio.run(ops._record_pay(None, ctx))
    assert out.after == {"from": 300, "to": 200, "amount": 200}
    assert [(r[0], r[1]) for r in fake.audit] == [
        (42, -200), (900000000000000103, 200)]
    assert all(r[3] == "gift" for r in fake.audit)
    assert ctx.params["_from_balance"] == 300
    assert ctx.params["_to_balance"] == 200


def test_pay_refusals(monkeypatch):
    from sb.domain.economy import ops
    from sb.domain.economy.service import InsufficientFundsError
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeEconomyStore(coins=10).install(monkeypatch)
    with pytest.raises(InsufficientFundsError):
        asyncio.run(ops._record_pay(
            None, _ctx({"target_id": 7, "amount": 999})))
    assert not fake.audit                            # nothing written
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_pay(None, _ctx({"target_id": 42, "amount": 5})))
    with pytest.raises(ValidatorError):
        asyncio.run(ops._record_pay(None, _ctx({"argv": ()})))


# --- shop purchases ------------------------------------------------------------------

def test_buy_grants_then_debits_atomically(monkeypatch):
    from sb.domain.economy import ops
    from sb.domain.economy.service import AlreadyOwnedError, InsufficientFundsError

    fake = FakeEconomyStore(coins=10_000).install(monkeypatch)
    ctx = _ctx({"item": "car"})
    out = asyncio.run(ops._record_buy(None, ctx))
    assert out.after["owned"] is True and out.after["price"] == 5000
    assert fake.audit[0][3] == "shop:car"
    assert fake.coins[42] == 5000

    with pytest.raises(AlreadyOwnedError):
        asyncio.run(ops._record_buy(None, _ctx({"item": "car"})))

    poor = FakeEconomyStore(coins=100).install(monkeypatch)
    with pytest.raises(InsufficientFundsError):
        asyncio.run(ops._record_buy(None, _ctx({"item": "suit"})))
    assert not poor.audit                            # nothing ledgered


# --- op registration / fences --------------------------------------------------------

def test_ops_registered_with_natural_key_posture():
    from sb.domain.economy.ops import register_ops
    from sb.kernel.workflow.registry import REGISTRY
    from sb.kernel.workflow.spec import IdempotencyPosture
    from sb.spec.refs import WorkflowRef

    register_ops()
    for key in ("economy.daily", "economy.work", "economy.pay", "economy.buy"):
        spec = REGISTRY.resolve(WorkflowRef(key))
        assert spec.idempotency is IdempotencyPosture.NATURAL_KEY
        assert spec.authority_ref == "user"
        assert spec.emits                        # balance_changed declared
    work = REGISTRY.resolve(WorkflowRef("economy.work"))
    assert any(leg.optional for leg in work.legs)   # XP effect leg is optional


def test_pay_emits_two_balance_changed_events():
    from sb.domain.economy.ops import PAY, _pay_payload_from, _pay_payload_to

    assert len(PAY.emits) == 2
    ctx = _ctx({"_from_id": 1, "_to_id": 2, "_amount": 50,
                "_from_balance": 10, "_to_balance": 60})
    frm = _pay_payload_from(ctx, None)
    to = _pay_payload_to(ctx, None)
    assert frm["delta"] == -50 and to["delta"] == 50
    assert frm["reason"] == to["reason"] == "gift"


# --- rollback disposition / reverse importers ----------------------------------------

def test_value_stores_are_reverse_importable_and_covered():
    import sb.manifest.economy  # noqa: F401 — registers stores + importers
    from sb.domain.economy.store import (
        ECONOMY_AUDIT_STORE,
        ECONOMY_BALANCES_STORE,
        ECONOMY_TRACK_STORE,
        INVENTORY_STORE,
    )
    from sb.spec.versioning import RollbackClass, derive_rollback_class
    from tools.importer.reverse import reverse_importer_coverage

    assert derive_rollback_class(ECONOMY_AUDIT_STORE) is RollbackClass.REVERSE_IMPORTABLE
    assert derive_rollback_class(ECONOMY_BALANCES_STORE) is RollbackClass.REVERSE_IMPORTABLE
    assert derive_rollback_class(ECONOMY_TRACK_STORE) is RollbackClass.DECLARED_LOSS
    assert derive_rollback_class(INVENTORY_STORE) is RollbackClass.DECLARED_LOSS
    covered = reverse_importer_coverage()
    assert {"economy_audit_log", "economy_balances"} <= covered


# --- the INV-F reconciliation invariant ----------------------------------------------

def test_reconciliation_invariant_declares_and_flags_drift(monkeypatch):
    from sb.domain.economy import invariants as inv
    from sb.kernel.db import pool as pool_mod
    from sb.spec.refs import resolve

    spec = inv.declare_economy_invariants()
    assert spec.severity.value == "quarantine_only"   # Q-D13: never guessed

    async def fake_fetchall(sql, params=(), conn=None):
        return [{"user_id": 42, "coins": 700, "ledger_sum": 500},
                {"user_id": 43, "coins": 500, "ledger_sum": 500}]

    monkeypatch.setattr(pool_mod, "fetchall", fake_fetchall)
    check = resolve(spec.check_ref)
    violations = asyncio.run(check(spec, guild_id=1))
    assert len(violations) == 1
    assert violations[0].row_id == "42:1"
    assert "drift +200" in violations[0].detail


# --- the log fan-out ------------------------------------------------------------------

def test_fanout_routes_balance_changed_to_bound_channel(monkeypatch):
    from sb.domain.economy import service
    from sb.kernel.events_bus import EventBus
    from sb.kernel.interaction import egress

    sent: list[tuple] = []

    class FakeEmitter:
        async def send(self, channel_id, content, *, guild_id):
            sent.append((channel_id, content.body))
            return egress.EmitResult(sent=True, message_id=1)

    egress.install_channel_emitter(FakeEmitter())

    async def fake_bound(guild_id):
        return 777

    monkeypatch.setattr(service, "bound_log_channel", fake_bound)
    bus = EventBus()
    service.subscribe(bus)
    asyncio.run(bus.emit("economy.balance_changed", guild_id=1, user_id=42,
                         delta=150, new_balance=650, reason="work:janitor"))
    egress.reset_channel_emitter_for_tests()
    assert sent and sent[0][0] == 777
    assert "Work completed" in sent[0][1] and "+150" in sent[0][1]


# --- manifest / settings facets --------------------------------------------------------

def test_manifest_facets_validate():
    import sb.manifest.economy as m
    from sb.spec.settings import validate_settings_facets

    assert validate_settings_facets(m.MANIFEST) == []
    names = {c.name for c in m.MANIFEST.commands}
    assert names == {"economymenu", "economy", "daily", "work", "shop",
                     "balance", "pay", "setlogchannel", "joblist"}
    aliases = {a for c in m.MANIFEST.commands for a in c.aliases}
    assert aliases == {"bal", "wallet", "transfer", "jobs"}
    assert {s.table for s in m.MANIFEST.stores} == {
        "economy_balances", "economy_audit_log", "economy", "job_progress",
        "inventory"}


# --- D-0060: legs speak their acks; refusals render verbatim; replay seams ----------

def test_daily_leg_speaks_the_shipped_ack(monkeypatch):
    from sb.domain.economy import ops

    FakeEconomyStore(coins=0, track={"last_daily": 0, "daily_streak": 0,
                                     "daily_count": 0}).install(monkeypatch)
    ops.set_rng_for_tests(random.Random(7))
    out = asyncio.run(ops._record_daily(None, _ctx({})))
    assert out.user_message and out.user_message.startswith("🎁 Daily Reward")
    assert "Streak **1**" in out.user_message


def test_work_and_pay_and_buy_legs_speak(monkeypatch):
    from sb.domain.economy import ops

    fake = FakeEconomyStore(coins=500).install(monkeypatch)
    out = asyncio.run(ops._record_work(None, _ctx({"job": "janitor"})))
    assert out.user_message and "Worked as **Janitor**" in out.user_message

    out = asyncio.run(ops._record_pay(
        None, _ctx({"target_id": 77, "amount": 50})))
    assert out.user_message and "Sent **50** 🪙 to <@77>" in out.user_message

    fake.coins[42] = 10_000
    out = asyncio.run(ops._record_buy(None, _ctx({"item": "toolkit"})))
    assert out.user_message and "Bought **Toolkit**" in out.user_message


def test_daily_rng_defaults_to_the_seeded_global(monkeypatch):
    """Replay determinism (D-0060): with no injected rng the draw comes from
    the module-global `random` the parity harness seeds per case."""
    from sb.domain.economy import ops
    from sb.domain.economy.catalogue import pick_daily

    ops.set_rng_for_tests(None)
    FakeEconomyStore(coins=0, track={"last_daily": 0, "daily_streak": 0,
                                     "daily_count": 0}).install(monkeypatch)
    random.seed(42)
    expected_amount, expected_label, _ = pick_daily(1)
    random.seed(42)
    out = asyncio.run(ops._record_daily(None, _ctx({})))
    assert out.after["amount"] == expected_amount
    assert out.after["tier"] == expected_label


def test_domain_refusal_renders_its_copy_bare():
    """InsufficientFunds/Cooldown/AlreadyOwned carry raise-site copy the
    envelope renders VERBATIM — never the missing-argument boilerplate."""
    from sb.domain.economy.service import InsufficientFundsError
    from sb.kernel.interaction.errors import from_exception
    from sb.kernel.interaction.request import Surface

    exc = InsufficientFundsError("❌ Not enough coins — you have **0** 🪙.")
    env = from_exception(exc, surface=Surface.MAINTENANCE, target=None)
    assert env.user_message == "❌ Not enough coins — you have **0** 🪙."
    assert "Missing/invalid argument" not in env.user_message


def test_validator_error_param_form_keeps_the_usage_hint():
    from sb.kernel.interaction.errors import ValidatorError, from_exception
    from sb.kernel.interaction.request import Surface

    env = from_exception(ValidatorError("amount"),
                         surface=Surface.MAINTENANCE, target=None)
    assert "Missing/invalid argument: `amount`" in env.user_message


def test_system_clock_reads_the_pinnable_time_seam(monkeypatch):
    """SYSTEM_CLOCK must read time.time() (the one seam the parity harness
    pins) so default-clock legs replay against the logical clock."""
    import time as _time

    from sb.kernel.workflow.context import SYSTEM_CLOCK

    monkeypatch.setattr(_time, "time", lambda: 1_853_737_031.0)
    assert int(SYSTEM_CLOCK().timestamp()) == 1_853_737_031
