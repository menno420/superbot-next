"""The compound-ops slice 2 (FINAL): the staged ``set_cog_routing`` /
``add_automation_rule`` rows APPLY through the K9→K7 lane instead of
failing closed (sb/domain/server_management/ops.py ``routing.set_policy``
· sb/domain/automation/ops.py ``automation.add_rule``), plus the routing
resolver port (sb/domain/server_management/routing.is_cog_enabled).

Runs the REAL K7 engine over the tests/unit/workflow FakeConn pattern
(the slice-1 test_compound_create_ops harness, widened for the
command_routing_policy / automation_rules SQL) — the assertions pin the
ORACLE semantics: read-old → upsert → audit with the REAL prev_value
(command_routing.set_policy:88), the resolver precedence chain channel →
category → guild → default-TRUE with no cache (is_cog_enabled:57-85),
rules insert DISABLED with the template's configs
(automation_mutation.create_rule + migration 032 DEFAULT FALSE), unknown
template slugs refused, and ``scheduled_time`` blocked
(UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS)."""

from __future__ import annotations

import asyncio
import contextlib
import json

import pytest

from sb.spec.outcomes import SUCCESS
from tests.unit.workflow.conftest import Actor, FakeConn

run = asyncio.run

_GUILD = 99


# --- the widened fake conn (routing + automation SQL) -----------------------------


def _coalesce(scope_id):
    return -1 if scope_id is None else int(scope_id)


class _Conn(FakeConn):
    def __init__(self) -> None:
        super().__init__()
        # (scope_type, COALESCE(scope_id,-1), cog_name) -> row
        self.routing: dict[tuple, dict] = {}
        self.rules: dict[int, dict] = {}     # id -> row
        self._rule_seq = 0
        self.fail_routing = False

    async def fetchrow(self, query: str, *params):
        if query.startswith("SELECT enabled, actor_id, updated_at "
                            "FROM command_routing_policy"):
            _gid, scope_type, scope_id, cog_name = params
            row = self.routing.get((scope_type, _coalesce(scope_id),
                                    cog_name))
            return dict(row) if row else None
        if query.startswith("INSERT INTO automation_rules"):
            (gid, name, trigger_kind, trigger_config, action_kind,
             action_config, schedule, timezone, created_by) = params
            if any(r["guild_id"] == gid and r["name"] == name
                   for r in self.rules.values()):
                raise RuntimeError(
                    "duplicate key value violates unique constraint "
                    '"automation_rules_guild_id_name_key"')
            self._rule_seq += 1
            self.rules[self._rule_seq] = {
                "id": self._rule_seq, "guild_id": gid, "name": name,
                "enabled": False,           # DDL DEFAULT FALSE
                "trigger_kind": trigger_kind,
                "trigger_config": json.loads(trigger_config),
                "action_kind": action_kind,
                "action_config": json.loads(action_config),
                "schedule": schedule, "timezone": timezone,
                "created_by": created_by}
            return {"id": self._rule_seq}
        return await super().fetchrow(query, *params)

    async def execute(self, query: str, *params):
        if query.startswith("INSERT INTO command_routing_policy"):
            if self.fail_routing:
                raise RuntimeError("db refused the routing upsert")
            _gid, scope_type, scope_id, cog_name, enabled, actor_id = params
            self.routing[(scope_type, _coalesce(scope_id), cog_name)] = {
                "enabled": enabled, "actor_id": actor_id,
                "updated_at": None}
            return "INSERT 1"
        return await super().execute(query, *params)


# --- fixtures ----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _armed(monkeypatch):
    """Re-arm every ref/spec the lane needs (other suites legitimately
    clear the global tables), install the fake txn, and point the
    resolver's bare reads at the same fake table."""
    import sb.manifest.automation as mautomation
    import sb.manifest.server_management as msm
    from sb.domain.server_management import routing
    from sb.domain.setup import cog_routing, preset_select
    from sb.kernel.db import pool

    msm.ENSURE_REFS()
    mautomation.ENSURE_REFS()
    cog_routing._register_set_cog_routing_op_kind()
    preset_select._register_add_automation_rule_op_kind()

    conn = _Conn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        snap = conn.snapshot()
        extra = (dict(conn.routing), dict(conn.rules), conn._rule_seq)
        try:
            yield conn
        except Exception:
            conn.restore(snap)   # rollback semantics
            conn.routing, conn.rules, conn._rule_seq = (
                dict(extra[0]), dict(extra[1]), extra[2])
            raise

    fake_conn = conn

    async def fake_fetchone(query, params=(), *, conn=None):
        del conn
        return await fake_conn.fetchrow(query, *params)

    monkeypatch.setattr(pool, "transaction", fake_transaction)
    # the resolver's conn-less reads (is_cog_enabled) ride the module-
    # bound fetchone — point it at the same fake table.
    monkeypatch.setattr(routing, "fetchone", fake_fetchone)
    yield conn


@pytest.fixture()
def conn(_armed):
    return _armed


def _ctx(params, *, request_id="req-1", correlation_id=None):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=Actor(), guild_id=_GUILD, request_id=request_id,
        confirmed=True, params=dict(params), correlation_id=correlation_id)


def _run(op_key, params, **kw):
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    return run(engine.run(WorkflowRef(op_key), _ctx(params, **kw)))


def _routing_payload(*, scope_kind="channel", scope_id=42,
                     scope_name="general", cog_name="games", enabled=False):
    """The REAL staged payload (cog_routing._routing_op) — the apply lane
    reads it back unchanged, the module's design promise."""
    from sb.domain.setup.cog_routing import _routing_op

    return dict(_routing_op(scope_kind=scope_kind, scope_id=scope_id,
                            scope_name=scope_name, cog_name=cog_name,
                            enabled=enabled).payload)


# ====================================================================================
# the K9 bindings resolve (the staged rows are draftable + applyable)
# ====================================================================================


def test_set_cog_routing_op_kind_binds_the_k7_op():
    from sb.kernel.draft.registry import OP_KINDS
    from sb.kernel.workflow.registry import REGISTRY

    binding = OP_KINDS.get("set_cog_routing")
    assert binding is not None
    assert binding.workflow_ref.name == "routing.set_policy"
    assert binding.is_resource_create is False
    # the staged payload carries every declared field…
    declared = {f.name for f in binding.payload_schema}
    assert declared <= set(_routing_payload())
    # …and the bound workflow resolves to a registered CompoundOpSpec.
    spec = REGISTRY.resolve(binding.workflow_ref)
    assert [leg.leg_id for leg in spec.legs] == ["record"]
    assert spec.audit_verb == "set_cog_routing"
    assert spec.domain == "cog_routing"


def test_add_automation_rule_op_kind_binds_the_k7_op():
    from sb.kernel.draft.registry import OP_KINDS
    from sb.kernel.workflow.registry import REGISTRY

    binding = OP_KINDS.get("add_automation_rule")
    assert binding is not None
    assert binding.workflow_ref.name == "automation.add_rule"
    declared = {f.name for f in binding.payload_schema}
    assert declared == {"template_slug"}
    spec = REGISTRY.resolve(binding.workflow_ref)
    assert [leg.leg_id for leg in spec.legs] == ["record"]
    assert spec.audit_verb == "create_rule"
    assert spec.domain == "automation"


def test_template_catalogue_matches_the_preview_slug_set():
    """The preview's unknown-template warning validates against the SAME
    three slugs the apply seam carries — no preset can preview clean and
    then fail on an unknown slug."""
    from sb.domain.automation.templates import TEMPLATES
    from sb.domain.setup.preset_select import _KNOWN_TEMPLATE_SLUGS

    assert {t.slug for t in TEMPLATES} == set(_KNOWN_TEMPLATE_SLUGS)


# ====================================================================================
# routing.set_policy: read-old → upsert → audit with the REAL prev_value
# ====================================================================================


def test_set_policy_upserts_and_audits_null_prev(conn):
    result = _run("routing.set_policy", _routing_payload(enabled=False),
                  correlation_id="11111111-1111-1111-1111-111111111111")
    assert result.outcome == SUCCESS
    assert conn.routing[("channel", 42, "games")]["enabled"] is False
    # actor_id preserved for audit joins (oracle 036 comment).
    assert conn.routing[("channel", 42, "games")]["actor_id"] == 1
    (row,) = conn.audit_rows.values()
    assert row["subsystem"] == "cog_routing"
    assert row["mutation_type"] == "set_cog_routing"
    # no prior row — the REAL prev_value is null (the default-true chain).
    assert '"enabled": null' in row["prev_value"]
    assert '"enabled": "disabled"' in row["new_value"]
    # the oracle audit target string rides the rollup.
    assert "channel:42:games" in row["new_value"]


def test_set_policy_second_write_carries_the_real_prev(conn):
    assert _run("routing.set_policy",
                _routing_payload(enabled=False)).outcome == SUCCESS
    result = _run("routing.set_policy", _routing_payload(enabled=True),
                  request_id="req-2")
    assert result.outcome == SUCCESS
    # replace-on-conflict: still ONE row, flag flipped.
    assert conn.routing[("channel", 42, "games")]["enabled"] is True
    assert any(
        '"enabled": "disabled"' in (row["prev_value"] or "")
        and '"enabled": "enabled"' in row["new_value"]
        for row in conn.audit_rows.values())


def test_set_policy_guild_scope_forces_null_scope_id(conn):
    payload = _routing_payload(scope_kind="guild", scope_id=None,
                               scope_name="guild", cog_name="economy",
                               enabled=False)
    assert _run("routing.set_policy", payload).outcome == SUCCESS
    # COALESCE(-1) — the guild-scope slot (oracle unique-index posture).
    assert conn.routing[("guild", -1, "economy")]["enabled"] is False


def test_set_policy_refuses_bad_scope_and_missing_target(conn):
    bad_scope = _routing_payload()
    bad_scope["scope_type"] = "thread"     # threads inherit — no own scope
    assert _run("routing.set_policy", bad_scope).outcome != SUCCESS
    no_target = _routing_payload()
    no_target["scope_id"] = None
    assert _run("routing.set_policy", no_target,
                request_id="req-2").outcome != SUCCESS
    assert conn.routing == {}


def test_set_policy_missing_enabled_defaults_true(conn):
    """_coerce_routing_enabled: a drafting bug never silently disables a
    cog (oracle setup_operations.py:1517-1533)."""
    payload = _routing_payload()
    del payload["enabled"]
    assert _run("routing.set_policy", payload).outcome == SUCCESS
    assert conn.routing[("channel", 42, "games")]["enabled"] is True


# ====================================================================================
# the resolver: channel → category → guild → default-TRUE, first row wins
# ====================================================================================


def _enabled(**kw):
    from sb.domain.server_management import routing

    return run(routing.is_cog_enabled(
        guild_id=_GUILD, cog_name=kw.pop("cog_name", "games"),
        channel_id=kw.pop("channel_id", None),
        category_id=kw.pop("category_id", None)))


def test_resolver_default_true_on_a_fresh_guild(conn):
    assert _enabled(channel_id=42, category_id=7) is True


def test_resolver_guild_row_restricts_everywhere(conn):
    assert _run("routing.set_policy", _routing_payload(
        scope_kind="guild", scope_id=None, scope_name="guild",
        enabled=False)).outcome == SUCCESS
    assert _enabled() is False
    assert _enabled(channel_id=42, category_id=7) is False


def test_resolver_category_beats_guild(conn):
    for i, payload in enumerate((
            _routing_payload(scope_kind="guild", scope_id=None,
                             scope_name="guild", enabled=False),
            _routing_payload(scope_kind="category", scope_id=7,
                             scope_name="games-cat", enabled=True))):
        assert _run("routing.set_policy", payload,
                    request_id=f"req-{i}").outcome == SUCCESS
    assert _enabled(category_id=7) is True         # category row wins
    assert _enabled(category_id=8) is False        # falls through to guild
    assert _enabled() is False


def test_resolver_channel_beats_category_and_guild(conn):
    for i, payload in enumerate((
            _routing_payload(scope_kind="guild", scope_id=None,
                             scope_name="guild", enabled=True),
            _routing_payload(scope_kind="category", scope_id=7,
                             scope_name="games-cat", enabled=True),
            _routing_payload(scope_kind="channel", scope_id=42,
                             scope_name="general", enabled=False))):
        assert _run("routing.set_policy", payload,
                    request_id=f"req-{i}").outcome == SUCCESS
    # the channel row wins over BOTH enabled outer scopes.
    assert _enabled(channel_id=42, category_id=7) is False
    # a different channel falls through to the category row.
    assert _enabled(channel_id=43, category_id=7) is True


def test_resolver_scopes_are_per_cog(conn):
    assert _run("routing.set_policy", _routing_payload(
        scope_kind="channel", scope_id=42, scope_name="general",
        cog_name="games", enabled=False)).outcome == SUCCESS
    assert _enabled(cog_name="games", channel_id=42) is False
    assert _enabled(cog_name="economy", channel_id=42) is True


# ====================================================================================
# automation.add_rule: template slug → DISABLED rule row
# ====================================================================================


def test_add_rule_inserts_disabled_with_the_template_config(conn):
    result = _run("automation.add_rule",
                  {"template_slug": "welcome-message"},
                  correlation_id="22222222-2222-2222-2222-222222222222")
    assert result.outcome == SUCCESS
    (rule,) = conn.rules.values()
    assert rule["guild_id"] == _GUILD
    assert rule["name"] == "welcome-message"     # oracle: name = slug
    assert rule["enabled"] is False              # created disabled
    assert rule["trigger_kind"] == "member_join"
    assert rule["action_kind"] == "send_message"
    assert rule["trigger_config"] == {}
    assert rule["action_config"] == {
        "channel_id": 0, "template": "Welcome, {{member}}! 👋"}
    assert rule["schedule"] is None and rule["timezone"] == "UTC"
    assert rule["created_by"] == 1
    (row,) = conn.audit_rows.values()
    assert row["subsystem"] == "automation"
    assert row["mutation_type"] == "create_rule"
    assert row["prev_value"] is None             # create path
    assert "member_join->send_message" in row["new_value"]


def test_add_rule_every_shipped_template_applies(conn):
    from sb.domain.automation.templates import TEMPLATES

    for i, template in enumerate(TEMPLATES):
        result = _run("automation.add_rule",
                      {"template_slug": template.slug},
                      request_id=f"req-{i}")
        assert result.outcome == SUCCESS, template.slug
    rows = {r["name"]: r for r in conn.rules.values()}
    assert set(rows) == {"welcome-message", "new-member-role",
                         "notify-staff-on-join"}
    assert all(r["enabled"] is False for r in rows.values())
    assert rows["new-member-role"]["action_kind"] == "assign_role"
    assert rows["new-member-role"]["action_config"] == {"role_id": 0}
    assert rows["notify-staff-on-join"]["action_config"]["template"] == (
        "🆕 {{member}} joined the server.")


def test_add_rule_unknown_slug_is_refused(conn):
    result = _run("automation.add_rule", {"template_slug": "nope"})
    assert result.outcome != SUCCESS
    assert conn.rules == {}
    # the refusal carries the copy (the raise-site sentence, D-0060).
    assert "Unknown automation template slug `nope`." in str(
        result.user_message or "")


def test_add_rule_blocks_scheduled_time(conn, monkeypatch):
    """UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS (oracle
    automation_registry.py:121): scheduled_time is known but not
    installable until the cron parser ships — the fence holds even for a
    future template that carries it."""
    from sb.domain.automation import ops as aops
    from sb.domain.automation.templates import AutomationTemplate

    cron = AutomationTemplate(
        slug="cron-thing", display_name="Cron", description="",
        trigger_kind="scheduled_time", action_kind="send_message")
    monkeypatch.setattr(aops.templates, "get_template",
                        lambda slug: cron if slug == "cron-thing" else None)
    result = _run("automation.add_rule", {"template_slug": "cron-thing"})
    assert result.outcome != SUCCESS
    assert conn.rules == {}
    assert "not installable yet" in str(result.user_message or "")


def test_add_rule_duplicate_name_refuses_not_duplicates(conn):
    """UNIQUE (guild_id, name) IS the natural key: a re-staged duplicate
    refuses instead of minting a second row (oracle: operators reference
    rules by name within a guild)."""
    assert _run("automation.add_rule",
                {"template_slug": "new-member-role"}).outcome == SUCCESS
    result = _run("automation.add_rule",
                  {"template_slug": "new-member-role"},
                  request_id="req-2")
    assert result.outcome != SUCCESS
    assert len(conn.rules) == 1
