"""Band 4 (karma) — the INV-K grant leg's rejection ladder + one-txn
write set, the policy read model, and the react-to-thank core."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    yield
    ksettings.clear_for_tests()


def _clock(epoch: int):
    return lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def _ctx(params: dict, *, uid: int = 42, gid: int = 1,
         epoch: int = 1_000_000):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params, clock=_clock(epoch))


class FakeKarmaStore:
    def __init__(self, *, recent: int = 0, given_today: int = 0):
        self.recent = recent
        self.given_today = given_today
        self.credits: list[tuple] = []
        self.given: list[int] = []
        self.audit: list[tuple] = []
        self.total = 0

    def install(self, monkeypatch):
        async def recent_grant_count(guild_id, from_user, to_user, since,
                                     conn=None):
            return self.recent

        async def grants_given_since(guild_id, from_user, since, conn=None):
            return self.given_today

        async def credit_karma(conn, *, to_user, guild_id, amount):
            self.total += amount
            self.credits.append((to_user, amount))
            return self.total

        async def increment_given(conn, *, from_user, guild_id):
            self.given.append(from_user)

        async def insert_karma_audit(conn, *, guild_id, from_user, to_user,
                                     delta, source, reason):
            self.audit.append((from_user, to_user, delta, source, reason))
            return f"m{len(self.audit)}"

        from sb.domain.karma import store as store_mod

        for name, fn in list(locals().items()):
            if callable(fn) and hasattr(store_mod, name):
                monkeypatch.setattr(store_mod, name, fn)
        return self


def _policy(monkeypatch, **overrides):
    from sb.domain.karma import policy as policy_mod

    p = policy_mod.KarmaPolicy(**overrides)

    async def load_policy(guild_id):
        return p

    monkeypatch.setattr(policy_mod, "load_policy", load_policy)
    return p


# --- the rejection ladder (nothing written on a block) -----------------------------------

def test_give_rejects_self_and_missing_target(monkeypatch):
    from sb.domain.karma import ops

    fake = FakeKarmaStore().install(monkeypatch)
    _policy(monkeypatch)
    with pytest.raises(ops.SelfKarmaError):
        run(ops._record_give(None, _ctx({"target_id": 42})))
    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError):
        run(ops._record_give(None, _ctx({})))
    assert not fake.credits and not fake.audit


def test_give_rejects_disabled_cooldown_and_cap(monkeypatch):
    from sb.domain.karma import ops

    fake = FakeKarmaStore().install(monkeypatch)
    _policy(monkeypatch, enabled=False)
    with pytest.raises(ops.KarmaDisabledError):
        run(ops._record_give(None, _ctx({"target_id": 7})))

    fake = FakeKarmaStore(recent=1).install(monkeypatch)
    _policy(monkeypatch)
    with pytest.raises(ops.KarmaCooldownError):
        run(ops._record_give(None, _ctx({"target_id": 7})))

    fake = FakeKarmaStore(given_today=10).install(monkeypatch)
    _policy(monkeypatch)
    with pytest.raises(ops.KarmaDailyCapError):
        run(ops._record_give(None, _ctx({"target_id": 7})))
    assert not fake.credits and not fake.audit


def test_give_writes_credit_given_and_audit(monkeypatch):
    from sb.domain.karma import ops

    fake = FakeKarmaStore().install(monkeypatch)
    _policy(monkeypatch)
    ctx = _ctx({"argv": ("<@7>", "for", "the", "help"), "source": "command"})
    out = run(ops._record_give(None, ctx))
    assert fake.credits == [(7, 1)]
    assert fake.given == [42]
    assert fake.audit == [(42, 7, 1, "command", "for the help")]
    assert out.after["new_total"] == 1
    payload = ops._granted_payload(ctx, None)
    assert payload == {"guild_id": 1, "from_user": 42, "to_user": 7,
                       "delta": 1, "new_total": 1, "source": "command"}


def test_zero_cooldown_skips_the_recent_read(monkeypatch):
    from sb.domain.karma import ops

    calls = []

    fake = FakeKarmaStore().install(monkeypatch)

    async def recent(*a, **k):
        calls.append(a)
        return 0

    from sb.domain.karma import store as store_mod

    monkeypatch.setattr(store_mod, "recent_grant_count", recent)
    _policy(monkeypatch, cooldown_seconds=0)
    run(ops._record_give(None, _ctx({"target_id": 7})))
    assert not calls and fake.credits == [(7, 1)]


# --- policy defaults ------------------------------------------------------------------------

def test_load_policy_defaults_when_undeclared():
    from sb.domain.karma.policy import KarmaPolicy, load_policy

    policy = run(load_policy(1))
    assert policy == KarmaPolicy()
    assert policy.enabled is True and policy.cooldown_seconds == 3600
    assert policy.daily_cap == 10 and policy.reaction_emoji == ""


def test_manifest_defaults_match_policy_constants():
    """The shipped no-drift invariant: SettingSpec defaults == the policy
    constants (karma_config precedent, pinned)."""
    from sb.domain.karma import policy
    from sb.manifest.karma import _SETTINGS

    by_name = {s.name: s for s in _SETTINGS}
    assert by_name["enabled"].default is policy.DEFAULT_ENABLED
    assert by_name["cooldown_seconds"].default == policy.DEFAULT_COOLDOWN_SECONDS
    assert by_name["daily_cap"].default == policy.DEFAULT_DAILY_CAP
    assert by_name["reaction_emoji"].default == policy.DEFAULT_REACTION_EMOJI


# --- react-to-thank ---------------------------------------------------------------------------

def test_handle_reaction_gates_before_any_write(monkeypatch):
    from sb.domain.karma import service

    ran = []

    async def fake_run(ref, ctx):
        ran.append(ctx.params)
        return SimpleNamespace(outcome="success", after={})

    from sb.kernel.workflow import engine

    monkeypatch.setattr(engine, "run", fake_run)

    _policy(monkeypatch, reaction_emoji="")     # feature OFF
    assert run(service.handle_reaction(guild_id=1, reactor_id=5,
                                       author_id=7, emoji="✨")) is None
    _policy(monkeypatch, reaction_emoji="✨")
    assert run(service.handle_reaction(guild_id=1, reactor_id=5,
                                       author_id=7, emoji="👍")) is None
    assert run(service.handle_reaction(guild_id=1, reactor_id=5,
                                       author_id=5, emoji="✨")) is None
    assert not ran

    out = run(service.handle_reaction(guild_id=1, reactor_id=5,
                                      author_id=7, emoji="✨"))
    assert out is not None
    assert ran and ran[0]["source"] == "reaction"


def test_karma_card_text_field_set():
    from sb.domain.karma.service import KarmaRecord, karma_card_text

    text = karma_card_text(7, KarmaRecord(points=12, received_count=12,
                                          given_count=3, rank=2))
    assert "**12** ✨" in text and "#2" in text
    assert "received **12**" in text and "given **3**" in text
    unranked = karma_card_text(7, KarmaRecord(0, 0, 0, None))
    assert "unranked" in unranked


def test_inv_k_spec_shape():
    from sb.domain.karma.invariants import karma_reconciliation_spec
    from sb.spec.invariants import InvariantKind, Severity

    spec = karma_reconciliation_spec()
    assert spec.kind is InvariantKind.RECONCILIATION
    assert spec.severity is Severity.QUARANTINE_ONLY
    assert spec.bears_value is True and spec.tolerance == 0
    assert spec.stores == ("karma", "karma_audit_log")
