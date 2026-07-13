"""Band 5 (role) — feasibility verdicts, the time/XP planners, the
classified apply loop, reaction-role runtime semantics, temp-grant
sweep, the K7 legs, and the band-4 waiting-port fill."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

run = asyncio.run
UTC = dt.timezone.utc


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.role import service

    service.reset_role_ports_for_tests()
    yield
    service.reset_role_ports_for_tests()


def _role(rid, name, position=1, managed=False, guild_id=999):
    return SimpleNamespace(id=rid, name=name, position=position,
                           managed=managed,
                           guild=SimpleNamespace(id=guild_id))


def _member(mid, roles=(), joined_days_ago=0, bot=False, display=None):
    return SimpleNamespace(
        id=mid, roles=list(roles), bot=bot,
        display_name=display or f"m{mid}",
        joined_at=dt.datetime.now(tz=UTC) - dt.timedelta(days=joined_days_ago))


def _guild(roles=(), members=(), me=None, gid=999):
    return SimpleNamespace(id=gid, roles=list(roles), members=list(members),
                           me=me)


def _me(manage_roles=True, top_position=100):
    return SimpleNamespace(
        guild_permissions=SimpleNamespace(manage_roles=manage_roles),
        top_role=SimpleNamespace(position=top_position, id=1))


class FakeActions:
    def __init__(self, fail=None):
        self.added: list[tuple] = []
        self.removed: list[tuple] = []
        self.fail = fail

    async def add_role(self, guild_id, member_id, role_id, *, reason):
        if self.fail:
            raise self.fail
        self.added.append((guild_id, member_id, role_id))

    async def remove_role(self, guild_id, member_id, role_id, *, reason):
        if self.fail:
            raise self.fail
        self.removed.append((guild_id, member_id, role_id))


# --- feasibility -----------------------------------------------------------------

def test_feasibility_precedence():
    from sb.domain.role import feasibility as f

    guild = SimpleNamespace(id=42)
    everyone = SimpleNamespace(id=42, name="@everyone", position=0,
                               managed=False, guild=guild)
    assert f.evaluate_role(everyone).code == f.EVERYONE
    managed = _role(2, "Bot", managed=True)
    assert f.evaluate_role(managed).code == f.MANAGED
    high = _role(3, "High", position=200)
    assert f.evaluate_role(high, bot_member=_me()).code == f.ABOVE_BOT
    # position TIE resolves by id (Discord tiebreak)
    tie = _role(5, "Tie", position=100)
    assert f.evaluate_role(tie, bot_member=_me()).code == f.ABOVE_BOT
    ok = _role(4, "Low", position=1)
    assert f.evaluate_role(ok, bot_member=_me()).ok
    assert f.evaluate_role(
        ok, bot_member=_me(manage_roles=False)).code == \
        f.BOT_MISSING_MANAGE_ROLES


# --- time automation planner --------------------------------------------------------

def _thresholds():
    from sb.domain.role.automation import RoleThreshold

    return (RoleThreshold("Bronze", 10), RoleThreshold("Silver", 30))


def test_compute_assignments_promotes_and_removes_lower():
    from sb.domain.role.automation import compute_assignments

    bronze, silver = _role(1, "Bronze"), _role(2, "Silver")
    m = _member(7, roles=[bronze], joined_days_ago=40)
    plans = compute_assignments(_guild([bronze, silver], [m]), _thresholds())
    assert len(plans) == 1
    assert plans[0].add_role_name == "Silver"
    assert plans[0].remove_role_names == ("Bronze",)


def test_compute_assignments_stack_exempt_bot_and_demotion_guard():
    from sb.domain.role.automation import compute_assignments

    bronze, silver = _role(1, "Bronze"), _role(2, "Silver")
    guild_roles = [bronze, silver]
    # keep_previous_tier keeps Bronze
    m = _member(7, roles=[bronze], joined_days_ago=40)
    plans = compute_assignments(_guild(guild_roles, [m]), _thresholds(),
                                keep_previous_tier=True)
    assert plans[0].remove_role_ids == ()
    # exempt member skipped
    exempt_role = _role(9, "Exempt")
    m2 = _member(8, roles=[exempt_role], joined_days_ago=40)
    assert compute_assignments(_guild(guild_roles + [exempt_role], [m2]),
                               _thresholds(),
                               exempt_role_ids=frozenset({9})) == ()
    # bots skipped
    m3 = _member(9, joined_days_ago=40, bot=True)
    assert compute_assignments(_guild(guild_roles, [m3]), _thresholds()) == ()
    # never demote: holder of Silver at 15 days (target would be Bronze)
    m4 = _member(10, roles=[silver], joined_days_ago=15)
    assert compute_assignments(_guild(guild_roles, [m4]), _thresholds()) == ()
    # below every tier: the shipped planner DOES strip progression roles
    m5 = _member(11, roles=[silver], joined_days_ago=5)
    plans = compute_assignments(_guild(guild_roles, [m5]), _thresholds())
    assert plans[0].remove_role_names == ("Silver",)
    assert plans[0].add_role_id is None


def test_threshold_id_first_resolution_survives_rename():
    from sb.domain.role.automation import RoleThreshold, compute_assignments

    renamed = _role(1, "Bronze Renamed")
    m = _member(7, joined_days_ago=15)
    plans = compute_assignments(
        _guild([renamed], [m]),
        (RoleThreshold("Bronze", 10, role_id=1),))
    assert plans and plans[0].add_role_id == 1


def test_explain_and_preflight():
    from sb.domain.role.automation import check_preflight, explain_assignment_for

    bronze, silver = _role(1, "Bronze"), _role(2, "Silver", position=200)
    m = _member(7, joined_days_ago=12)
    plan = explain_assignment_for(_guild([bronze, silver], [m], me=_me()),
                                  m, _thresholds())
    assert plan is not None and plan.add_role_name == "Bronze"

    result = check_preflight(_guild([bronze, silver], me=_me()),
                             _thresholds())
    assert not result.ok and "Silver" in result.hierarchy_blockers
    from sb.domain.role.automation import RoleThreshold

    result2 = check_preflight(_guild([bronze], me=_me()),
                              (RoleThreshold("Gone", 5),))
    assert "Gone" in result2.missing_roles


def test_apply_dry_run_classified_failures_and_audit(monkeypatch):
    from sb.domain.role import automation, service

    bronze = _role(1, "Bronze")
    m = _member(7, joined_days_ago=15)
    guild = _guild([bronze], [m], me=_me())
    plans = automation.compute_assignments(guild, _thresholds()[:1])

    # dry run mutates nothing
    res = run(automation.apply(guild, plans, dry_run=True))
    assert res.skipped == len(plans) and res.succeeded == 0

    # missing manage_roles => whole batch classified, no port calls
    res = run(automation.apply(
        _guild([bronze], [m], me=_me(manage_roles=False)), plans))
    assert res.failed == len(plans)
    assert res.failure_counts() == {"bot_missing_manage_roles": len(plans)}
    assert "missing Manage Roles" in automation.summarize_failures(res)

    # success path + audit fact on the installed bus
    actions = FakeActions()
    service.install_role_actions(actions)
    facts = []

    class Bus:
        async def emit(self, name, **payload):
            facts.append((name, payload["mutation_type"]))

    service.subscribe(Bus())
    res = run(automation.apply(guild, plans, actor_id=1))
    assert res.succeeded == len(plans) and actions.added
    assert facts and facts[0][0] == "audit.action_recorded"

    # classified mutate failure (name-based, discord absent)
    class Forbidden(Exception):
        pass

    service.install_role_actions(FakeActions(fail=Forbidden("403")))
    res = run(automation.apply(guild, plans))
    assert res.failure_counts() == {"forbidden": len(plans)}


# --- xp level-role planning + the waiting-port fill -----------------------------------

def _xp_roles():
    return [{"role_name": "Lv5", "role_id": 1, "level_required": 5},
            {"role_name": "Lv10", "role_id": 2, "level_required": 10}]


def test_plan_level_roles_stack_and_single():
    from sb.domain.role.xp_sync import plan_level_role_assignments

    lv5, lv10 = _role(1, "Lv5"), _role(2, "Lv10")
    guild = _guild([lv5, lv10])
    m = _member(7, roles=[lv5])
    stacked = plan_level_role_assignments(
        guild, m, 10, stack=True, exempt_xp_ids=frozenset(),
        xp_roles=_xp_roles(), reason="r")
    assert [p.add_role_id for p in stacked] == [2]

    single = plan_level_role_assignments(
        guild, m, 10, stack=False, exempt_xp_ids=frozenset(),
        xp_roles=_xp_roles(), reason="r")
    assert len(single) == 1
    assert single[0].add_role_id == 2 and single[0].remove_role_ids == (1,)

    assert plan_level_role_assignments(
        guild, m, 10, stack=True, exempt_xp_ids=frozenset({1}),
        xp_roles=_xp_roles(), reason="r") == []


def test_level_role_granter_fills_xp_port(monkeypatch):
    import sb.manifest.role  # noqa: F401 — import-time fill
    from sb.domain.role import service, store
    from sb.domain.xp.service import _role_granter as installed

    assert installed is service._level_role_granter

    # no guild view -> honest no-op
    run(service._level_role_granter(1, 7, 10))

    # with a guild view + thresholds -> plans applied through the port
    lv5 = _role(1, "Lv5")
    m = _member(7, roles=[])
    guild = _guild([lv5], [m], me=_me())

    async def gsource(gid):
        return guild

    service.install_guild_source(gsource)
    actions = FakeActions()
    service.install_role_actions(actions)

    async def thresholds(gid, conn=None):
        return [{"role_name": "Lv5", "role_id": 1, "days_required": 0,
                 "level_required": 5, "xp_auto_assign": True,
                 "display_name": None}]

    async def exemptions(gid, conn=None):
        return []

    monkeypatch.setattr(store, "get_thresholds", thresholds)
    monkeypatch.setattr(store, "get_exemptions", exemptions)

    import sb.kernel.settings as ksettings

    async def no_setting(gid, sub, name):
        raise LookupError("undeclared in this test")

    monkeypatch.setattr(ksettings, "resolve", no_setting)
    run(service._level_role_granter(999, 7, 6))
    assert actions.added == [(999, 7, 1)]


# --- reaction-role runtime --------------------------------------------------------------

def _install_reaction_env(monkeypatch, *, binding=5, mode="normal",
                          siblings=()):
    from sb.domain.role import service, store

    async def get_binding(gid, mid, emoji, conn=None):
        return binding

    async def get_mode(gid, mid, conn=None):
        return mode

    async def get_siblings(gid, mid, conn=None):
        return [{"emoji": "x", "role_id": rid} for rid in siblings]

    monkeypatch.setattr(store, "get_reaction_binding", get_binding)
    monkeypatch.setattr(store, "get_message_mode", get_mode)
    monkeypatch.setattr(store, "sibling_reaction_bindings", get_siblings)

    async def enabled(gid):
        return True

    monkeypatch.setattr(service, "reaction_roles_enabled", enabled)
    actions = FakeActions()
    service.install_role_actions(actions)
    return actions


def test_reaction_add_modes(monkeypatch):
    from sb.domain.role import service

    actions = _install_reaction_env(monkeypatch)
    assert run(service.handle_reaction_add(1, 2, "😀", 7)) == "added"
    assert actions.added == [(1, 7, 5)]

    # unique mode swaps held siblings
    actions = _install_reaction_env(monkeypatch, mode="unique",
                                    siblings=(5, 9))
    out = run(service.handle_reaction_add(
        1, 2, "😀", 7, member_role_ids=frozenset({9})))
    assert out == "unique_swap"
    assert actions.removed == [(1, 7, 9)] and actions.added == [(1, 7, 5)]

    # verify mode: no grant on ADD, grant on REMOVE
    actions = _install_reaction_env(monkeypatch, mode="verify")
    assert run(service.handle_reaction_add(1, 2, "😀", 7)) is None
    assert run(service.handle_reaction_remove(1, 2, "😀", 7)) == "verified"
    assert actions.added == [(1, 7, 5)]

    # bots ignored; unbound emoji ignored
    assert run(service.handle_reaction_add(1, 2, "😀", 7, is_bot=True)) is None
    actions = _install_reaction_env(monkeypatch, binding=None)
    assert run(service.handle_reaction_add(1, 2, "😀", 7)) is None


# --- temp grants -----------------------------------------------------------------------

def test_sweep_defers_without_port_and_keeps_on_forbidden(monkeypatch):
    from sb.domain.role import service, store

    now = dt.datetime.now(tz=UTC)

    async def expired(_now, conn=None):
        return [{"grant_id": 1, "guild_id": 1, "member_id": 7, "role_id": 5}]

    monkeypatch.setattr(store, "list_expired_grants", expired)
    # no actions port installed -> deferred, nothing resolved
    assert run(service.sweep_expired(now)) == 0

    class Forbidden(Exception):
        pass

    service.install_role_actions(FakeActions(fail=Forbidden("hierarchy")))
    assert run(service.sweep_expired(now)) == 0  # kept to retry


def test_grants_expiry_task_declared():
    import sb.manifest.role  # noqa: F401
    from sb.kernel.scheduler.due_queue import declared_tasks

    names = {t.name for t in declared_tasks()}
    assert "role:grants_expiry" in names


# --- K7 legs ------------------------------------------------------------------------------

def _ctx(params, *, uid=42, gid=1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(1_000_000, tz=UTC))


class FakeRoleStore:
    def __init__(self):
        self.thresholds: list = []
        self.exemptions: list = []
        self.binds: list = []
        self.modes: list = []
        self.menus: list = []
        self.grants: list = []

    def install(self, monkeypatch):
        from sb.domain.role import store as store_mod

        async def upsert_threshold(conn, **kw):
            self.thresholds.append(kw)

        async def delete_threshold(conn, *, guild_id, role_name):
            return True

        async def get_thresholds(guild_id, conn=None):
            return list(self.thresholds)

        async def get_exemptions(gid, conn=None):
            return []

        async def set_exemption_row(conn, **kw):
            self.exemptions.append(kw)

        async def clear_exemption_row(conn, **kw):
            self.exemptions.append(("cleared", kw))
            return True

        async def bind_reaction(conn, **kw):
            self.binds.append(kw)

        async def insert_menu(conn, **kw):
            self.menus.append(kw)
            return 11

        async def replace_menu_options(conn, *, menu_id, options):
            self.menus.append(("options", menu_id, len(options)))

        async def upsert_grant(conn, **kw):
            self.grants.append(kw)

        async def delete_grant(conn, *, grant_id):
            self.grants.append(("deleted", grant_id))
            return True

        for name, fn in list(locals().items()):
            if callable(fn) and hasattr(store_mod, name):
                monkeypatch.setattr(store_mod, name, fn)
        return self


def test_threshold_and_exemption_legs(monkeypatch):
    from sb.domain.role import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeRoleStore().install(monkeypatch)
    out = run(ops._record_set_threshold(None, _ctx(
        {"role_name": "Bronze", "days_required": 10})))
    assert fake.thresholds[0]["role_name"] == "Bronze"
    assert out.after["days_required"] == 10
    with pytest.raises(ValidatorError):
        run(ops._record_set_threshold(None, _ctx({"role_name": ""})))

    run(ops._record_set_exemption(None, _ctx(
        {"role_id": 5, "exempt_xp": True, "exempt_time": False})))
    assert fake.exemptions[0]["exempt_xp"] is True
    # neither flag -> row cleared, not stored (shipped)
    run(ops._record_set_exemption(None, _ctx(
        {"role_id": 5, "exempt_xp": False, "exempt_time": False})))
    assert fake.exemptions[1][0] == "cleared"


def test_reaction_and_menu_legs(monkeypatch):
    from sb.domain.role import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeRoleStore().install(monkeypatch)
    run(ops._record_bind_reaction(None, _ctx(
        {"message_id": 123, "emoji": "😀", "role_id": 5})))
    assert fake.binds[0]["message_id"] == 123
    with pytest.raises(ValidatorError):
        run(ops._record_bind_reaction(None, _ctx({"message_id": 123})))

    out = run(ops._record_create_menu(None, _ctx(
        {"channel_id": 9, "options": [{"role_id": 5}], "style": "dropdown"})))
    assert out.after["menu_id"] == 11
    with pytest.raises(ValidatorError):   # no options
        run(ops._record_create_menu(None, _ctx({"channel_id": 9})))
    with pytest.raises(ValidatorError):   # bad style
        run(ops._record_create_menu(None, _ctx(
            {"channel_id": 9, "options": [{"role_id": 5}],
             "style": "carousel"})))


def test_grant_and_expire_legs(monkeypatch):
    from sb.domain.role import ops, service

    fake = FakeRoleStore().install(monkeypatch)
    expires = dt.datetime.now(tz=UTC).isoformat()
    run(ops._record_grant_temp(None, _ctx(
        {"member_id": 7, "role_id": 5, "expires_at_iso": expires})))
    assert fake.grants[0]["member_id"] == 7

    actions = FakeActions()
    service.install_role_actions(actions)
    run(ops._apply_grant_temp(None, _ctx({"member_id": 7, "role_id": 5})))
    assert actions.added == [(1, 7, 5)]

    out = run(ops._record_expire_temp(None, _ctx(
        {"grant_id": 3, "member_id": 7, "role_id": 5, "did_remove": True})))
    assert ("deleted", 3) in fake.grants and out.after["removed"] is True


def test_erasure_body(monkeypatch):
    from sb.domain.role import ops
    from sb.domain.role import store as store_mod

    async def erase(conn, *, user_id):
        return 2

    monkeypatch.setattr(store_mod, "erase_subject_grants", erase)
    out = run(ops._erase_subject_grants(None, _ctx({"subject_user_id": 7})))
    assert out.after["rows"] == 2


# --- the live-drive fix lane (testing-report 2026-07-09, band-5 row: 3 live bugs) --


class FakeReq:
    def __init__(self, argv=(), invoked="", gid=1, uid=42):
        self.args = {"argv": tuple(argv), "invoked_with": invoked}
        self.guild_id = gid
        self.request_id = "r1"
        self.confirmed = False
        self.actor = SimpleNamespace(user_id=uid, actor_type="user")


def test_pending_terminals_registered_at_module_import():
    """Live bug 1 (ledger row 7): the live root imports the handlers module
    and dispatches — it never calls ENSURE_REFS when zero plugins are
    admitted, so the four polite pending terminals must register at IMPORT
    (declaring IS reserving), not only inside ensure_handler_refs()."""
    import importlib
    import sys

    from sb.spec.refs import HandlerRef, clear_ref_table, is_registered

    # clear_ref_table PURGES sb.manifest.* from sys.modules — snapshot the
    # imported set so the teardown can restore it for the rest of the suite
    manifest_names = [n for n in sys.modules if n.startswith("sb.manifest.")]
    clear_ref_table()
    sys.modules.pop("sb.domain.role.handlers", None)
    try:
        importlib.import_module("sb.domain.role.handlers")
        for name in ("role.create_form_submit", "role.roleinfo_pending",
                     "role.assignroles_pending", "role.debug_pending",
                     "role.time_roles_view", "role.setrole"):
            assert is_registered(HandlerRef(name)), name
    finally:
        # re-import + re-arm the purged manifests (the compiler P1 posture:
        # domain modules stay cached so ENSURE_REFS restores their refs)
        for n in manifest_names:
            mod = importlib.import_module(n)
            hook = getattr(mod, "ENSURE_REFS", None)
            if callable(hook):
                hook()


def _fake_engine_run(monkeypatch, leg):
    """engine.run stand-in that runs the REAL leg and rolls its LegOutcome
    up EXACTLY like the engine does (_rollup keys after by the step's
    target_name — there is no \"record\" key; live bug 2's root cause)."""
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.result import WorkflowResult

    async def fake_run(target, ctx):
        out = await leg(None, ctx)
        before, after = engine._rollup([out])
        return WorkflowResult(
            mutation_id="m1", guild_id=int(ctx.guild_id or 0), domain="role",
            operation=str(getattr(target, "op_key", target)),
            outcome="success", reversibility="reversible",
            steps=(out.step,), before=before, after=after)

    monkeypatch.setattr(engine, "run", fake_run)


def test_setrole_ack_speaks_the_written_tier(monkeypatch):
    """Live bug 2: the ack read result.after["record"] (nonexistent) and
    said "✅ **None** auto-assigns at None day(s)." over a CORRECT write.
    Copy pinned to the oracle (disbot/cogs/role_cog.py:534 /
    parity/goldens/_unmapped/sweep_setrole.json)."""
    from sb.domain.role import handlers, ops
    from sb.spec.refs import HandlerRef, resolve

    FakeRoleStore().install(monkeypatch)
    _fake_engine_run(monkeypatch, ops._record_set_threshold)
    handlers.ensure_handler_refs()
    setrole = resolve(HandlerRef("role.setrole"))
    out = run(setrole(FakeReq(argv=("3", "test"))))
    assert out.outcome == "success"
    assert out.user_message == \
        "✅ Role **test** will be assigned after **3** day(s)."


def test_unsetrole_ack_is_unconditional(monkeypatch):
    """The shipped unsetrole has NO miss branch (role_cog.unsetrole:
    `match = next((...), role_name)` falls back to the RAW name, the
    DELETE runs unconditionally, and the ack always speaks the removed
    byte — goldens/role/sweep_unsetrole pins the success ack over an
    absent row). The band-5 "No such tier was configured." miss copy was
    a port invention, retired at the role-family re-home (oracle-wins,
    the D-0065 flip-review posture)."""
    from sb.domain.role import handlers, ops
    from sb.domain.role import store as store_mod
    from sb.spec.refs import HandlerRef, resolve

    FakeRoleStore().install(monkeypatch)
    _fake_engine_run(monkeypatch, ops._record_remove_threshold)
    handlers.ensure_handler_refs()
    unsetrole = resolve(HandlerRef("role.unsetrole"))
    out = run(unsetrole(FakeReq(argv=("test",))))
    assert out.user_message == \
        "✅ Removed **test** from time-based assignment."

    async def delete_threshold_miss(conn, *, guild_id, role_name):
        return False

    monkeypatch.setattr(store_mod, "delete_threshold", delete_threshold_miss)
    out = run(unsetrole(FakeReq(argv=("ghost",))))
    # shipped: the fallback name rides the SAME unconditional ack
    assert out.user_message == \
        "✅ Removed **ghost** from time-based assignment."


def test_removereactrole_ack_is_unconditional(monkeypatch):
    """The shipped removereactrole runs a bare DELETE and always speaks
    the removed byte (role_cog.py:705 — no existence branch;
    goldens/role/sweep_removereactrole pins the success ack over an
    absent row). The band-5 "That binding did not exist." miss copy was
    a port invention, retired at the role-family re-home (oracle-wins)."""
    from sb.domain.role import handlers, ops
    from sb.domain.role import store as store_mod
    from sb.spec.refs import HandlerRef, resolve

    async def unbind_reaction(conn, *, guild_id, message_id, emoji):
        return True

    monkeypatch.setattr(store_mod, "unbind_reaction", unbind_reaction)
    _fake_engine_run(monkeypatch, ops._record_unbind_reaction)
    handlers.ensure_handler_refs()
    unbind = resolve(HandlerRef("role.reactroles_unbind"))
    out = run(unbind(FakeReq(argv=("123", "😀"))))
    assert out.user_message == \
        "✅ Reaction role for 😀 on that message removed."

    async def unbind_reaction_miss(conn, *, guild_id, message_id, emoji):
        return False

    monkeypatch.setattr(store_mod, "unbind_reaction", unbind_reaction_miss)
    out = run(unbind(FakeReq(argv=("123", "😀"))))
    assert out.user_message == \
        "✅ Reaction role for 😀 on that message removed."


def test_temprole_failure_copy_never_leaks_the_result_repr(monkeypatch):
    """Live bug 3: a non-success grant raised
    RuntimeError(f"... {result!r}") and the handler sent "⚠️ {exc}" — the
    raw WorkflowResult repr in the channel. The live outcome was an honest
    PARTIAL (GuildRoleActions not installed); the copy must be honest user
    copy, the diagnostics stay in the log (no oracle surface for the
    unarmed port — the oracle always had Discord; ledger-pinned)."""
    from sb.domain.role import handlers
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.result import StepResult, WorkflowResult
    from sb.spec.refs import HandlerRef, resolve

    async def fake_run(target, ctx):
        return WorkflowResult(
            mutation_id="m1", guild_id=1, domain="role",
            operation="role.grant_temp_role", outcome="partial",
            reversibility="reversible",
            steps=(StepResult(7, "record_grant_temp", True),
                   StepResult(0, "apply", False,
                              "GuildRoleActions not installed — the "
                              "composition root must install the discord "
                              "adapter's implementation")))

    monkeypatch.setattr(engine, "run", fake_run)
    handlers.ensure_handler_refs()
    temprole = resolve(HandlerRef("role.temprole"))
    out = run(temprole(FakeReq(argv=("<@7>", "2h", "<@&5>"))))
    assert out.outcome == "blocked"
    assert "WorkflowResult" not in out.user_message
    assert "mutation_id" not in out.user_message
    assert out.user_message == (
        "⚠️ The temporary role was not granted — the Discord role update "
        "did not complete, so nothing was kept.")


def test_role_manifest_in_snapshot():
    import json

    snap = json.load(open("manifest.snapshot.json"))
    role = snap["subsystems"]["role"]
    names = {c["name"] for c in role["commands"]}
    assert {"roles", "setrole", "unsetrole", "reactroles", "temprole",
            "temproles", "listreactroles"} <= names
    assert len(role["stores"]) == 8
