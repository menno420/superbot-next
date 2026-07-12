"""Band 4 (XP) — level math, the audited award/reset/import legs, the
conditional level_up emission (the D-0036 kernel widening), and the
FILLED band-3 economy waiting ports."""

from __future__ import annotations

import asyncio
import datetime as dt
import random
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.economy.service import reset_economy_ports_for_tests
    from sb.domain.xp.service import reset_xp_ports_for_tests
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    reset_economy_ports_for_tests()
    reset_xp_ports_for_tests()
    yield
    ksettings.clear_for_tests()
    reset_economy_ports_for_tests()
    reset_xp_ports_for_tests()


def _clock(epoch: int):
    return lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def _ctx(params: dict, *, uid: int = 42, gid: int = 1,
         epoch: int = 1_000_000):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params, clock=_clock(epoch))


# --- level math (shipped verbatim) ----------------------------------------------------

def test_level_curve_is_shipped_math():
    from sb.domain.xp.levels import level_progress, total_xp_for_level, xp_for_level

    assert xp_for_level(0) == 100
    assert xp_for_level(1) == 155
    assert xp_for_level(5) == 475
    assert level_progress(0) == (0, 0, 100)
    assert level_progress(100) == (1, 0, 155)
    assert level_progress(99) == (0, 99, 100)
    for lv in (0, 1, 3, 10):
        total = total_xp_for_level(lv)
        assert level_progress(total) == (lv, 0, xp_for_level(lv))


# --- fake store harness ----------------------------------------------------------------

class FakeXpStore:
    def __init__(self, rows: dict | None = None):
        # (user, guild) -> {"xp": int, "level": int, "messages": int, "last_xp": int}
        self.rows = dict(rows or {})

    def install(self, monkeypatch):
        from sb.domain.xp.levels import level_progress

        async def get_xp(user_id, guild_id, conn=None):
            row = self.rows.get((user_id, guild_id))
            if row is None:
                return {"user_id": user_id, "guild_id": guild_id, "xp": 0,
                        "level": 0, "messages": 0, "last_xp": 0}
            return dict(row, user_id=user_id, guild_id=guild_id)

        async def add_xp(conn, *, user_id, guild_id, amount, now):
            row = self.rows.setdefault((user_id, guild_id),
                                       {"xp": 0, "level": 0, "messages": 0,
                                        "last_xp": 0})
            row["xp"] += amount
            row["messages"] += 1
            row["last_xp"] = now
            new_level, _, _ = level_progress(row["xp"])
            leveled = new_level > row["level"]
            if leveled:
                row["level"] = new_level
            return row["xp"], row["level"], leveled

        async def set_imported_xp(conn, *, user_id, guild_id, xp, level, now):
            row = self.rows.get((user_id, guild_id))
            if row is None or xp > row["xp"]:
                old = row["xp"] if row else -1
                self.rows[(user_id, guild_id)] = {
                    "xp": max(xp, row["xp"] if row else 0), "level": level,
                    "messages": row["messages"] if row else 0,
                    "last_xp": row["last_xp"] if row else now}
                return xp, level, xp > old
            return row["xp"], row["level"], False

        async def delete_xp(conn, *, user_id, guild_id):
            return 1 if self.rows.pop((user_id, guild_id), None) else 0

        from sb.domain.xp import store as store_mod

        for name, fn in list(locals().items()):
            if callable(fn) and hasattr(store_mod, name):
                monkeypatch.setattr(store_mod, name, fn)
        return self


# --- the award leg -----------------------------------------------------------------------

def test_award_leg_levels_up_and_stamps_params(monkeypatch):
    from sb.domain.xp import ops

    fake = FakeXpStore({(7, 1): {"xp": 95, "level": 0, "messages": 3,
                                 "last_xp": 0}}).install(monkeypatch)
    ctx = _ctx({"target_id": 7, "amount": 10, "source": "chat"})
    out = run(ops._record_award(None, ctx))
    assert out.after["new_xp"] == 105 and out.after["new_level"] == 1
    assert out.after["leveled_up"] is True
    assert ctx.params["_leveled_up"] is True
    assert fake.rows[(7, 1)]["level"] == 1

    # non-boundary award: leveled_up False
    ctx2 = _ctx({"target_id": 7, "amount": 5, "source": "chat"})
    out2 = run(ops._record_award(None, ctx2))
    assert out2.after["leveled_up"] is False


def test_award_leg_refuses_non_positive(monkeypatch):
    from sb.domain.xp import ops
    from sb.kernel.interaction.errors import ValidatorError

    FakeXpStore().install(monkeypatch)
    with pytest.raises(ValidatorError):
        run(ops._record_award(None, _ctx({"target_id": 7, "amount": 0})))
    with pytest.raises(ValidatorError):
        run(ops._record_award(None, _ctx({"target_id": 7, "amount": "nope"})))


def test_award_argv_parse_is_positional(monkeypatch):
    """`!givexp <member> <amount>` — argv[0] is the member slot, argv[1]
    the amount (the shipped MemberConverter/int positional binding)."""
    from sb.domain.xp import ops

    snowflake = 900000000000000103

    # mention + amount (the golden-pinned lane stays byte-identical)
    fake = FakeXpStore().install(monkeypatch)
    out = run(ops._record_award(
        None, _ctx({"argv": (f"<@{snowflake}>", "3")})))
    assert out.after["delta"] == 3
    assert fake.rows[(snowflake, 1)]["xp"] == 3

    # bare ID + amount (the golden-unpinned defect lane)
    fake2 = FakeXpStore().install(monkeypatch)
    out2 = run(ops._record_award(
        None, _ctx({"argv": (str(snowflake), "12")})))
    assert out2.after["delta"] == 12
    assert fake2.rows[(snowflake, 1)]["xp"] == 12

    # nickname-mention form <@!id>
    fake3 = FakeXpStore().install(monkeypatch)
    out3 = run(ops._record_award(
        None, _ctx({"argv": (f"<@!{snowflake}>", "7")})))
    assert out3.after["delta"] == 7
    assert fake3.rows[(snowflake, 1)]["xp"] == 7


def test_award_bare_id_never_becomes_the_amount(monkeypatch):
    """REGRESSION: the first-digit-token scan awarded the snowflake ITSELF
    (~9e17 XP) on `!givexp <bare_user_id> <amount>`."""
    from sb.domain.xp import ops

    snowflake = 900000000000000103
    fake = FakeXpStore().install(monkeypatch)
    out = run(ops._record_award(
        None, _ctx({"argv": (str(snowflake), "5")})))
    assert out.after["delta"] == 5          # not 900000000000000103
    assert out.after["new_xp"] == 5
    assert fake.rows[(snowflake, 1)]["xp"] == 5
    # and the target is the snowflake, not the amount
    assert (5, 1) not in fake.rows


def test_award_argv_failure_copy(monkeypatch):
    from sb.domain.xp import ops
    from sb.kernel.interaction.errors import ValidatorError

    FakeXpStore().install(monkeypatch)

    # unknown-member name leg: the shipped MemberConverter raised
    # MemberNotFound and bot1.py's BadArgument arm sent this copy.
    with pytest.raises(ValidatorError) as exc:
        run(ops._record_award(None, _ctx({"argv": ("somename", "5")})))
    assert exc.value.user_copy == '⚠️ Bad argument: Member "somename" not found.'

    # garbage amount at argv[1]
    with pytest.raises(ValidatorError) as exc2:
        run(ops._record_award(None, _ctx({"argv": ("<@7>", "lots")})))
    assert exc2.value.user_copy == "❌ Amount must be a whole number of XP."

    # amount-only (one arg): no amount slot at argv[1] — amount copy, and
    # the lone digit token must NOT be double-read as the amount
    with pytest.raises(ValidatorError) as exc3:
        run(ops._record_award(None, _ctx({"argv": ("42",)})))
    assert exc3.value.user_copy == "❌ Amount must be a whole number of XP."


def test_reset_argv_parse_is_positional(monkeypatch):
    """`!resetxp <bare_id>` resolves argv[0]; an unresolvable name never
    silently falls back to the actor (the shipped converter raised)."""
    from sb.domain.xp import ops
    from sb.kernel.interaction.errors import ValidatorError

    snowflake = 900000000000000103
    fake = FakeXpStore({(snowflake, 1): {"xp": 50, "level": 0,
                                         "messages": 1, "last_xp": 0}}
                       ).install(monkeypatch)
    out = run(ops._record_reset(None, _ctx({"argv": (str(snowflake),)})))
    assert out.after["rows_removed"] == 1
    assert (snowflake, 1) not in fake.rows

    with pytest.raises(ValidatorError) as exc:
        run(ops._record_reset(None, _ctx({"argv": ("somename",)})))
    assert exc.value.user_copy == '⚠️ Bad argument: Member "somename" not found.'


def test_levelup_payload_is_conditional():
    from sb.domain.xp import ops

    ctx = _ctx({"_subject_id": 7, "_new_level": 2, "_leveled_up": True,
                "_source": "chat"})
    payload = ops._levelup_payload(ctx, None)
    assert payload == {"guild_id": 1, "user_id": 7, "new_level": 2,
                       "source": "chat"}
    ctx.params["_leveled_up"] = False
    assert ops._levelup_payload(ctx, None) is None


def test_enqueue_all_skips_none_payload():
    """The D-0036 kernel widening: a None payload builder output skips
    that emit; the other emits' positions are unchanged."""
    from sb.kernel.outbox.enqueue import enqueue_all
    from sb.spec.events import DeliveryClass

    class Emit:
        def __init__(self, name, builder):
            self.event = name
            self.payload_builder = builder
            self.delivery = DeliveryClass.BEST_EFFORT

    emits = (Emit("xp.awarded", lambda ctx, r: {"user_id": 7}),
             Emit("xp.level_up", lambda ctx, r: None))
    batch = run(enqueue_all(emits, SimpleNamespace(guild_id=1, op_key="xp.award"),
                            SimpleNamespace(mutation_id="m1", dedup_key=None,
                                            op_key="xp.award"),
                            conn=None))
    assert [name for name, _ in batch._events] == ["xp.awarded"]


# --- reset + import legs -------------------------------------------------------------------

def test_reset_leg_deletes_row(monkeypatch):
    from sb.domain.xp import ops

    fake = FakeXpStore({(7, 1): {"xp": 500, "level": 2, "messages": 9,
                                 "last_xp": 0}}).install(monkeypatch)
    out = run(ops._record_reset(None, _ctx({"target_id": 7})))
    assert out.after["rows_removed"] == 1
    assert (7, 1) not in fake.rows


def test_import_leg_is_raise_only_and_max_reduced(monkeypatch):
    from sb.domain.xp import ops
    from sb.domain.xp.levels import total_xp_for_level

    fake = FakeXpStore({(7, 1): {"xp": 10_000, "level": 7, "messages": 1,
                                 "last_xp": 0}}).install(monkeypatch)
    ctx = _ctx({"records": ((7, 3), (7, 5), (8, 2)),
                "source": "import:arcane"})
    out = run(ops._record_import(None, ctx))
    assert out.after["users"] == 2
    assert out.after["raised"] == 1                       # only user 8
    assert fake.rows[(7, 1)]["xp"] == 10_000              # never lowered
    assert fake.rows[(8, 1)]["xp"] == total_xp_for_level(2)


def test_migrate_parsing_arcane_and_reduce():
    from sb.domain.xp.migrate import (
        DEFAULT_FORMAT,
        get_format,
        parse_level_message,
        reduce_max_levels,
    )

    fmt = get_format(DEFAULT_FORMAT)
    parsed = parse_level_message("@Nicely has reached level 3. GG!",
                                 mention_ids=(555,), fmt=fmt)
    assert parsed.level == 3 and parsed.user_id == 555
    named = parse_level_message("Nicely has reached level **4**. GG!",
                                fmt=fmt)
    assert named.level == 4 and named.name == "Nicely"
    assert parse_level_message("hello there", fmt=fmt) is None
    assert reduce_max_levels([(1, 2), (1, 5), (2, 3), (1, 4)]) == {1: 5, 2: 3}


# --- the chat hot path ------------------------------------------------------------------------

def test_chat_award_respects_cooldown_and_gate(monkeypatch):
    from sb.domain.xp import service

    FakeXpStore({(7, 1): {"xp": 0, "level": 0, "messages": 1,
                          "last_xp": 999_990}}).install(monkeypatch)
    # cooldown (default 60s) still running at epoch 1_000_000
    assert run(service.handle_chat_message(7, 1, now=1_000_000)) is None

    # gate denies
    async def deny(user_id, guild_id):
        return False

    FakeXpStore().install(monkeypatch)
    service.install_participation_gate(deny)
    assert run(service.handle_chat_message(7, 1, now=1_000_000)) is None


def test_chat_award_runs_the_op(monkeypatch):
    from sb.domain.xp import service

    FakeXpStore().install(monkeypatch)
    service.set_rng_for_tests(random.Random(3))
    calls = {}

    async def fake_run_award(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(outcome="success", after={})

    monkeypatch.setattr(service, "_run_award", fake_run_award)
    result = run(service.handle_chat_message(7, 1, now=1_000_000))
    assert result is not None
    assert calls["source"] == "chat" and 15 <= calls["amount"] <= 25


# --- the FILLED band-3 waiting ports ----------------------------------------------------------

def test_manifest_import_fills_economy_ports(monkeypatch):
    import sb.manifest.xp  # noqa: F401 — import runs install_economy_ports()
    from sb.domain.economy import service as economy_service
    from sb.domain.xp.service import install_economy_ports

    install_economy_ports()          # idempotent re-arm (fixture reset it)
    assert economy_service.xp_installed() is True

    FakeXpStore({(7, 1): {"xp": 0, "level": 4, "messages": 1,
                          "last_xp": 0}}).install(monkeypatch)
    level = run(economy_service.active_level_reader()(7, 1))
    assert level == 4


def test_xp_awarder_returns_award_dict(monkeypatch):
    from sb.domain.economy import service as economy_service
    from sb.domain.xp import service
    from sb.spec.outcomes import SUCCESS

    service.install_economy_ports()

    async def fake_run_award(**kwargs):
        return SimpleNamespace(outcome=SUCCESS,
                               after={"award": {"new_xp": 110, "new_level": 1,
                                                "leveled_up": True,
                                                "delta": 10,
                                                "source": kwargs["source"]}})

    monkeypatch.setattr(service, "_run_award", fake_run_award)
    awarder = economy_service.active_xp_awarder()
    out = run(awarder(guild_id=1, user_id=7, amount=10,
                      source="work:janitor", now=1_000_000))
    assert out == {"new_xp": 110, "new_level": 1, "leveled_up": True,
                   "delta": 10, "source": "work:janitor"}

    # zero-amount jobs award nothing (never a fake)
    assert run(awarder(guild_id=1, user_id=7, amount=0,
                       source="work:x", now=0)) is None


# --- fan-out + INV-G --------------------------------------------------------------------------

def test_levelup_fanout_routes_to_bound_channel(monkeypatch):
    from sb.domain.xp import service
    from sb.kernel.interaction import egress

    sent = []

    class FakeEmitter:
        async def send(self, channel_id, content, *, guild_id=None):
            sent.append((channel_id, content.body, guild_id))

    async def bound(guild_id):
        return 999

    monkeypatch.setattr(service, "bound_announce_channel", bound)
    monkeypatch.setattr(egress, "active_channel_emitter",
                        lambda: FakeEmitter())
    run(service._route_level_up(guild_id=1, user_id=7, new_level=3,
                                source="chat"))
    assert sent and sent[0][0] == 999 and "Level 3" in sent[0][1]


def test_inv_g_spec_shape():
    from sb.domain.xp.invariants import xp_level_consistency_spec
    from sb.spec.invariants import InvariantKind, Severity

    spec = xp_level_consistency_spec()
    assert spec.kind is InvariantKind.ROW_PREDICATE
    assert spec.severity is Severity.REPAIRABLE
    assert spec.repair_ref is not None and spec.bears_value is True
    assert spec.stores == ("xp",)
