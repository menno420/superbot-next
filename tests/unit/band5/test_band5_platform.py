"""Band 5 (platform/control + proof_channel) — command-access reader
fill + lanes, teardown registry isolation, consistency promotion,
introspection privacy shapes, proof lock lanes + the reconcile sweep."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

run = asyncio.run
UTC = dt.timezone.utc


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.platform import command_access
    from sb.domain.proof_channel import service as proof_service

    command_access.reset_access_cache_for_tests()
    proof_service.reset_proof_ports_for_tests()
    yield
    command_access.reset_access_cache_for_tests()
    proof_service.reset_proof_ports_for_tests()


def _ctx(params, *, uid=42, gid=1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(1_000_000, tz=UTC))


# --- command access --------------------------------------------------------------

def test_access_snapshot_default_and_cache(monkeypatch):
    from sb.domain.platform import command_access as ca

    calls = []

    async def fetch(guild_id, conn=None):
        calls.append(1)
        from sb.kernel.authority.channel_access import CommandAccessSnapshot

        return CommandAccessSnapshot(mode="selected_channels",
                                     allowed_channels=frozenset({5}))

    monkeypatch.setattr(ca, "_fetch_snapshot", fetch)
    snap = run(ca.read_policy_snapshot(1))
    run(ca.read_policy_snapshot(1))
    assert len(calls) == 1 and snap.mode == "selected_channels"
    ca.forget_guild(1)
    run(ca.read_policy_snapshot(1))
    assert len(calls) == 2


def test_access_reader_port_filled():
    import importlib

    import sb.manifest.platform  # noqa: F401 — import-time fill

    interaction_resolve = importlib.import_module(
        "sb.kernel.interaction.resolve")
    assert interaction_resolve._policy_reader.__name__ == "_reader"


def test_access_mode_leg_validates_and_writes(monkeypatch):
    from sb.domain.platform import command_access as ca
    from sb.kernel.interaction.errors import ValidatorError

    writes = []

    async def execute(sql, args=(), conn=None):
        writes.append(sql.split()[0])

    async def fetchone(sql, args=(), conn=None):
        return None

    monkeypatch.setattr(ca, "execute", execute)
    monkeypatch.setattr(ca, "fetchone", fetchone)
    out = run(ca._record_set_access_mode(None, _ctx({"mode": "all_channels"})))
    assert out.after["mode"] == "all_channels" and "INSERT" in writes
    with pytest.raises(ValidatorError):
        run(ca._record_set_access_mode(None, _ctx({"mode": "lockdown"})))


def test_channel_role_sets_fold_into_snapshot(monkeypatch):
    """D3 M1: role rows fold into channel_role_sets keyed by channel."""
    from sb.domain.platform import command_access as ca

    async def fetchone(sql, args=(), conn=None):
        return {"mode": "all_channels"}

    async def fetchall(sql, args=(), conn=None):
        if "guild_command_access_channels" in sql and "role" not in sql:
            return [{"channel_id": 5}]
        if "guild_command_access_channel_roles" in sql:
            return [
                {"channel_id": 5, "role_id": 100},
                {"channel_id": 5, "role_id": 200},
                {"channel_id": 9, "role_id": 300},
            ]
        return []

    monkeypatch.setattr(ca, "fetchone", fetchone)
    monkeypatch.setattr(ca, "fetchall", fetchall)
    snap = run(ca._fetch_snapshot(1))
    assert snap.mode == "all_channels"
    assert snap.allowed_channels == frozenset({5})
    assert snap.channel_role_sets[5] == frozenset({100, 200})
    assert snap.channel_role_sets[9] == frozenset({300})
    # a channel with no role rows is absent (unconstrained), not empty-set.
    assert 42 not in snap.channel_role_sets


def test_channel_roles_leg_atomic_replace_and_writes(monkeypatch):
    """D3 M1: the leg clears then re-INSERTs this channel's role set and
    the op carries the command_access_channel_roles_set audit verb."""
    from sb.domain.platform import command_access as ca
    from sb.kernel.interaction.errors import ValidatorError

    writes = []

    async def execute(sql, args=(), conn=None):
        writes.append((sql.split()[0], args))

    async def fetchone(sql, args=(), conn=None):
        return {"mode": "all_channels"}   # policy row already present

    monkeypatch.setattr(ca, "execute", execute)
    monkeypatch.setattr(ca, "fetchone", fetchone)

    out = run(ca._record_set_channel_roles(
        None, _ctx({"channel_id": 5, "role_ids": (100, 200)})))
    assert out.after == {"channel_id": 5, "role_ids": [100, 200]}
    verbs = [w[0] for w in writes]
    # exactly one DELETE (the per-channel clear) then one INSERT per role.
    assert verbs == ["DELETE", "INSERT", "INSERT"]
    assert all(w[1][0] == 1 and w[1][1] == 5 for w in writes)   # gid, channel
    assert ca.SET_CHANNEL_ROLES.audit_verb == "command_access_channel_roles_set"

    # empty role set without allow_empty is refused (copy-only ValidatorError).
    with pytest.raises(ValidatorError):
        run(ca._record_set_channel_roles(None, _ctx({"channel_id": 5})))
    # a missing channel id is refused too.
    with pytest.raises(ValidatorError):
        run(ca._record_set_channel_roles(
            None, _ctx({"channel_id": 0, "role_ids": (1,)})))


# --- teardown registry -------------------------------------------------------------

def test_teardown_isolation_and_order():
    from sb.domain.platform import guild_teardown as gt

    gt.reset_teardowns_for_tests()
    ran = []

    async def ok_hook(gid):
        ran.append(("ok", gid))

    def boom(gid):
        raise RuntimeError("boom")

    gt.register_teardown("zz_test_ok", ok_hook)
    gt.register_teardown("zz_test_boom", boom)
    results = run(gt.teardown(7))
    assert results["zz_test_ok"] == "ok"
    assert results["zz_test_boom"] == "failed"     # isolated, never aborts
    assert ("ok", 7) in ran
    assert set(gt.registered_teardowns()) >= {
        "governance", "command_access", "role_family",
        "proof_channel_locks"}
    gt.reset_teardowns_for_tests()


# --- consistency ---------------------------------------------------------------------

def test_consistency_promotion_and_isolation():
    from sb.domain.platform import consistency as c

    c.reset_collectors_for_tests()

    async def clean():
        return c.SectionResult("t1", c.SectionStatus.CLEAN, "ok")

    async def info_fatal():
        return c.SectionResult("t2", c.SectionStatus.FATAL, "roadmap",
                               informational=True)

    async def raises():
        raise ValueError("broken collector")

    c._COLLECTORS.clear()
    c.register_collector("t1", clean)
    c.register_collector("t2", info_fatal)
    report = run(c.collect_report())
    # informational FATAL never promotes
    assert report.overall_status is c.SectionStatus.CLEAN
    c.register_collector("t3", raises)
    report = run(c.collect_report())
    assert report.overall_status is c.SectionStatus.FATAL
    assert len(c.iter_blocking_sections(report)) == 1
    assert c.get_last_report() is report
    c.reset_collectors_for_tests()


def test_builtin_collectors_run():
    from sb.domain.platform import consistency as c

    c.reset_collectors_for_tests()
    report = run(c.collect_report())
    kinds = {s.kind for s in report.sections}
    assert {"migrations", "manifests", "governance", "scheduler"} <= kinds
    mig = next(s for s in report.sections if s.kind == "migrations")
    assert mig.status is c.SectionStatus.CLEAN


# --- introspection + snapshot privacy ---------------------------------------------------

def test_introspection_shapes():
    from sb.domain.platform import introspection as i

    perms = SimpleNamespace(administrator=True, manage_guild=True,
                            manage_roles=False, manage_channels=False,
                            ban_members=False, kick_members=False,
                            manage_messages=False)
    role = SimpleNamespace(name="Admin", position=5, permissions=perms,
                           hoist=True, mentionable=False)
    guild = SimpleNamespace(
        name="G", description=None, owner=SimpleNamespace(display_name="O"),
        created_at=dt.datetime(2020, 1, 1), text_channels=[],
        voice_channels=[], categories=[],
        roles=[SimpleNamespace(name="@everyone", position=0), role],
        premium_tier=0, premium_subscription_count=0, owner_id=1,
        members=[SimpleNamespace(id=1, display_name="Owner", bot=False,
                                 guild_permissions=perms, roles=[role],
                                 joined_at=dt.datetime(2021, 1, 1))])
    ov = i.server_overview(guild)
    assert ov["counts"]["roles"] == 1 and "member_count" not in ov
    roles = i.list_roles(guild)
    assert roles["roles"][0]["privileges"] == "administrator"
    members = i.list_members(guild)
    assert members["members"][0]["permission_tier"] == "owner"
    found = i.lookup_member(guild, "own")
    assert found["found"] and found["matches"][0]["is_owner"]


def test_guild_snapshot_privacy_tokens():
    import dataclasses

    from sb.domain.platform import guild_snapshot as gs

    guild = SimpleNamespace(id=1, name="G", owner_id=2, me=None,
                            text_channels=[], voice_channels=[],
                            stage_channels=[], categories=[], roles=[])
    snap = run(gs.collect(guild))
    keys = set(dataclasses.asdict(snap))
    assert not (keys & gs.EXCLUDED_FIELD_TOKENS)
    assert gs.documented_field_names() == tuple(
        f.name for f in dataclasses.fields(gs.GuildSnapshot))


# --- K10 claims ---------------------------------------------------------------------------

def test_platform_task_claims():
    import sb.manifest.platform  # noqa: F401
    from sb.kernel.ai.tasks import registered_task_ids

    ids = set(registered_task_ids())
    assert {"platform.explain_status", "platform.explain_consistency",
            "code_context.explain"} <= ids


# --- proof channel --------------------------------------------------------------------------

class FakeChannelActions:
    def __init__(self, fail=None):
        self.locked: list = []
        self.unlocked: list = []
        self.fail = fail

    async def lock_channel_for_winner(self, gid, cid, winner):
        if self.fail:
            raise self.fail
        self.locked.append((gid, cid, winner))

    async def unlock_channel(self, gid, cid):
        if self.fail:
            raise self.fail
        self.unlocked.append((gid, cid))


def test_proof_lock_legs(monkeypatch):
    from sb.domain.proof_channel import ops, service, store
    from sb.kernel.interaction.errors import ValidatorError

    rows = []

    async def upsert_lock(conn, **kw):
        rows.append(kw)

    async def delete_lock(conn, *, guild_id, channel_id):
        rows.append(("deleted", guild_id, channel_id))
        return True

    async def get_lock(guild_id, channel_id, conn=None):
        return {"winner_id": 7,
                "unlock_at": dt.datetime(2026, 7, 10, tzinfo=dt.timezone.utc)}

    async def bound(gid):
        return 55

    monkeypatch.setattr(store, "upsert_lock", upsert_lock)
    monkeypatch.setattr(store, "delete_lock", delete_lock)
    monkeypatch.setattr(store, "get_lock", get_lock)
    monkeypatch.setattr(service, "bound_proof_channel", bound)

    # timed lock persists the deadline row (bug #8)
    out = run(ops._record_lock(None, _ctx(
        {"winner_id": 7, "duration_minutes": 30})))
    assert rows[0]["winner_id"] == 7 and out.after["channel_id"] == 55
    # manual lock writes no deadline row
    rows.clear()
    run(ops._record_lock(None, _ctx({"winner_id": 7})))
    assert rows == []
    with pytest.raises(ValidatorError):
        run(ops._record_lock(None, _ctx({})))

    actions = FakeChannelActions()
    service.install_channel_actions(actions)
    run(ops._apply_lock(None, _ctx({"channel_id": 55, "winner_id": 7})))
    assert actions.locked == [(1, 55, 7)]
    out = run(ops._record_unlock(None, _ctx({})))
    assert out.after["removed"] is True


def test_end_access_blocked_compensates(monkeypatch):
    """A Discord-refused unlock must not strand external state: record_unlock
    stashes the deleted deadline row, and the compensator re-inserts it so
    the sweep retries at the deadline (the DB never claims an unlock that
    never happened). Permanent grants have no row — the compensator no-ops."""
    from sb.domain.proof_channel import ops, service, store
    from sb.spec.refs import WorkflowRef

    deadline = dt.datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    restored: list[dict] = []
    deleted: list[tuple] = []

    async def get_lock(guild_id, channel_id, conn=None):
        return {"winner_id": 7, "unlock_at": deadline}

    async def delete_lock(conn, *, guild_id, channel_id):
        deleted.append((guild_id, channel_id))
        return True

    async def insert_lock_if_absent(conn, **kw):
        restored.append(kw)
        return True

    async def bound(gid):
        return 55

    monkeypatch.setattr(store, "get_lock", get_lock)
    monkeypatch.setattr(store, "delete_lock", delete_lock)
    monkeypatch.setattr(store, "insert_lock_if_absent", insert_lock_if_absent)
    monkeypatch.setattr(service, "bound_proof_channel", bound)

    # the DB leg stashes the compensation handle before deleting
    ctx = _ctx({})
    run(ops._record_unlock(None, ctx))
    assert deleted == [(1, 55)]
    assert ctx.params["_deleted_lock"] == {
        "winner_id": 7, "unlock_at": deadline.isoformat()}

    # the compensator re-inserts exactly what was deleted
    out = run(ops._compensate_unlock(None, ctx))
    assert restored == [{"guild_id": 1, "channel_id": 55,
                         "winner_id": 7, "unlock_at": deadline}]
    assert out.after["compensated"] == "unlock"

    # no stashed row (permanent grant) => no-op
    out2 = run(ops._compensate_unlock(None, _ctx({"channel_id": 55})))
    assert out2.after == {"compensated": "nothing"}
    assert len(restored) == 1

    # END_PRIZE declares the compensator on its EFFECT leg (fork E wiring)
    effect = [leg for leg in ops.END_PRIZE.legs if leg.leg_id == "apply"][0]
    assert effect.reversibility == "compensatable"
    assert effect.compensator == WorkflowRef("proof_channel.compensate_unlock")


def test_end_access_compensation_yields_to_concurrent_regrant(monkeypatch):
    """The compensator race (codex 4673572674): record_unlock's delete
    COMMITS before the unlock EFFECT runs, and grant_access is NATURAL_KEY
    (nothing serializes it against end_access) — so a re-grant can land a
    NEWER deadline row in the window before a refused unlock compensates.
    The compensation must be insert-only: the newer grant's row survives
    untouched, the stale stash is discarded. (Symmetric follow-up:
    GRANT_PRIZE's _compensate_lock plain-deletes — same class.)"""
    from sb.domain.proof_channel import ops, service, store

    old_deadline = dt.datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    new_deadline = dt.datetime(2026, 7, 11, 18, 0, tzinfo=UTC)
    # the table, keyed by the (guild_id, channel_id) natural key
    table: dict[tuple, dict] = {(1, 55): {"winner_id": 7,
                                          "unlock_at": old_deadline}}

    async def get_lock(guild_id, channel_id, conn=None):
        return table.get((guild_id, channel_id))

    async def delete_lock(conn, *, guild_id, channel_id):
        return table.pop((guild_id, channel_id), None) is not None

    async def insert_lock_if_absent(conn, *, guild_id, channel_id,
                                    winner_id, unlock_at):
        # ON CONFLICT (guild_id, channel_id) DO NOTHING semantics
        if (guild_id, channel_id) in table:
            return False
        table[(guild_id, channel_id)] = {"winner_id": winner_id,
                                         "unlock_at": unlock_at}
        return True

    async def bound(gid):
        return 55

    monkeypatch.setattr(store, "get_lock", get_lock)
    monkeypatch.setattr(store, "delete_lock", delete_lock)
    monkeypatch.setattr(store, "insert_lock_if_absent", insert_lock_if_absent)
    monkeypatch.setattr(service, "bound_proof_channel", bound)

    # 1. end_access's DB leg: stash + delete, committed with the txn
    ctx = _ctx({})
    run(ops._record_unlock(None, ctx))
    assert (1, 55) not in table
    assert ctx.params["_deleted_lock"] == {
        "winner_id": 7, "unlock_at": old_deadline.isoformat()}

    # 2. a concurrent grant_access lands a NEWER row in the window
    table[(1, 55)] = {"winner_id": 9, "unlock_at": new_deadline}

    # 3. apply_unlock refused => the compensator fires — and must yield
    out = run(ops._compensate_unlock(None, ctx))
    assert out.after["restored"] is False
    assert table[(1, 55)] == {"winner_id": 9, "unlock_at": new_deadline}

    # empty slot control: with no concurrent grant, the row IS restored
    del table[(1, 55)]
    out2 = run(ops._compensate_unlock(None, ctx))
    assert out2.after["restored"] is True
    assert table[(1, 55)] == {"winner_id": 7, "unlock_at": old_deadline}


def test_grant_access_compensation_yields_to_concurrent_regrant(monkeypatch):
    """The SYMMETRIC compensator race (codex 4673572674's named follow-up):
    record_lock's upsert COMMITS before apply_lock runs and grant_access is
    NATURAL_KEY, so a concurrent re-grant can own the (guild_id, channel_id)
    slot by the time a refused lock compensates. The compensation must be
    delete-if-match: only the exact row THIS grant wrote is withdrawn — a
    newer grant's row survives untouched."""
    from sb.domain.proof_channel import ops, service, store

    table: dict[tuple, dict] = {}

    async def upsert_lock(conn, *, guild_id, channel_id, winner_id, unlock_at):
        table[(guild_id, channel_id)] = {"winner_id": winner_id,
                                         "unlock_at": unlock_at}

    async def delete_lock_if_match(conn, *, guild_id, channel_id,
                                   winner_id, unlock_at):
        # DELETE ... WHERE guild+channel+winner_id+unlock_at match semantics
        row = table.get((guild_id, channel_id))
        if row == {"winner_id": winner_id, "unlock_at": unlock_at}:
            del table[(guild_id, channel_id)]
            return True
        return False

    async def bound(gid):
        return 55

    monkeypatch.setattr(store, "upsert_lock", upsert_lock)
    monkeypatch.setattr(store, "delete_lock_if_match", delete_lock_if_match)
    monkeypatch.setattr(service, "bound_proof_channel", bound)

    # 1. grant A's DB leg writes its timed row (committed with the txn)
    ctx = _ctx({"winner_id": 7, "duration_minutes": 30})
    run(ops._record_lock(None, ctx))
    row_a = dict(table[(1, 55)])

    # 2. a concurrent grant B upserts a NEWER row in the window
    new_deadline = dt.datetime(2026, 7, 11, 18, 0, tzinfo=UTC)
    table[(1, 55)] = {"winner_id": 9, "unlock_at": new_deadline}

    # 3. apply_lock refused => A's compensator fires — and must yield
    out = run(ops._compensate_lock(None, ctx))
    assert out.after["removed"] is False
    assert table[(1, 55)] == {"winner_id": 9, "unlock_at": new_deadline}

    # own-row control: with no concurrent grant, A withdraws its OWN row
    table[(1, 55)] = row_a
    out2 = run(ops._compensate_lock(None, ctx))
    assert out2.after["removed"] is True
    assert (1, 55) not in table


def test_grant_access_permanent_grant_compensates_nothing(monkeypatch):
    """The aggravator: a PERMANENT grant (minutes == 0) writes NO deadline
    row, yet the old compensator plain-deleted whatever timed row existed
    for the slot. It must no-op."""
    from sb.domain.proof_channel import ops, service, store

    deadline = dt.datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    table: dict[tuple, dict] = {(1, 55): {"winner_id": 7,
                                          "unlock_at": deadline}}
    deletes: list = []

    async def delete_lock_if_match(conn, **kw):
        deletes.append(kw)
        return False

    async def delete_lock(conn, **kw):
        deletes.append(kw)
        return True

    async def bound(gid):
        return 55

    monkeypatch.setattr(store, "delete_lock_if_match", delete_lock_if_match)
    monkeypatch.setattr(store, "delete_lock", delete_lock)
    monkeypatch.setattr(service, "bound_proof_channel", bound)

    # permanent grant: record_lock writes nothing (no duration)
    ctx = _ctx({"winner_id": 9})
    run(ops._record_lock(None, ctx))
    assert table == {(1, 55): {"winner_id": 7, "unlock_at": deadline}}

    out = run(ops._compensate_lock(None, ctx))
    assert out.after == {"compensated": "nothing"}
    assert deletes == []          # no delete of ANY kind was attempted
    assert table == {(1, 55): {"winner_id": 7, "unlock_at": deadline}}

    # GRANT_PRIZE still declares the compensator on its EFFECT leg
    from sb.spec.refs import WorkflowRef

    effect = [leg for leg in ops.GRANT_PRIZE.legs if leg.leg_id == "apply"][0]
    assert effect.compensator == WorkflowRef("proof_channel.compensate_lock")


def test_proof_reconcile_defers_without_port(monkeypatch):
    from sb.domain.proof_channel import service, store

    async def due(now, conn=None):
        return [{"guild_id": 1, "channel_id": 5, "winner_id": 7,
                 "unlock_at": now}]

    monkeypatch.setattr(store, "list_due_locks", due)
    assert run(service.reconcile_due_locks()) == 0   # port unarmed = honest


def test_proof_and_platform_manifests_in_snapshot():
    import json

    snap = json.load(open("manifest.snapshot.json"))
    assert "platform" in snap["subsystems"]
    pc = snap["subsystems"]["proof_channel"]
    assert {c["name"] for c in pc["commands"]} == {
        "+prize", "-prize", "prizestatus", "prizemenu", "timedprize"}
    from sb.kernel.scheduler.due_queue import declared_tasks

    import sb.manifest.proof_channel  # noqa: F401

    assert "proof:lock_reconcile" in {t.name for t in declared_tasks()}
