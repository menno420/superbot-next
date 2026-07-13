"""The compound-ops slice: the staged ``create_channel`` /
``create_managed_role`` rows APPLY through the K9→K7 lane instead of
failing closed (sb/domain/setup/ops.py ``setup.ensure_channel`` ·
sb/domain/role/ops.py ``role.create_managed_role``).

Runs the REAL K7 engine over the tests/unit/workflow FakeConn pattern
(widened for the binding/threshold SQL the nested ``settings.bind`` /
``role.set_threshold`` runs issue) with fake channel/role ports — the
assertions pin the ORACLE semantics: name-based reuse (guild_resources.
ensure_channel), bind failure never undoes the channel
(resource_provisioning ``binding_failed``), apply-time unconditional
role create (role_lifecycle_service._apply_one), and the best-effort
tier fold (_apply_template_role_tiers)."""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from sb.spec.outcomes import DISCORD_FAILED, PARTIAL, SUCCESS
from tests.unit.workflow.conftest import Actor, FakeConn

run = asyncio.run

_GUILD = 99


# --- the widened fake conn (binding + threshold SQL) -----------------------------------


class _Conn(FakeConn):
    def __init__(self) -> None:
        super().__init__()
        self.bindings: dict[tuple, dict] = {}   # (gid, sub, name) -> row
        self.binding_audits: list[tuple] = []
        self.thresholds: list[tuple] = []
        self.fail_binding = False
        self.fail_thresholds = False

    async def fetchrow(self, query: str, *params):
        if query.startswith("SELECT target_id, status FROM subsystem_bindings"):
            row = self.bindings.get(tuple(params[:3]))
            return dict(row) if row else None
        return await super().fetchrow(query, *params)

    async def execute(self, query: str, *params):
        if query.startswith("INSERT INTO subsystem_bindings"):
            if self.fail_binding:
                raise RuntimeError("db refused the binding upsert")
            gid, sub, name, kind, resource_id = params
            self.bindings[(gid, sub, name)] = {
                "target_id": resource_id, "status": "bound", "kind": kind}
            return "INSERT 1"
        if query.startswith("INSERT INTO binding_audit_log"):
            self.binding_audits.append(params)
            return "INSERT 1"
        if query.startswith("INSERT INTO role_thresholds"):
            if self.fail_thresholds:
                raise RuntimeError("db refused the threshold upsert")
            self.thresholds.append(params)
            return "INSERT 1"
        return await super().execute(query, *params)


# --- fake ports -------------------------------------------------------------------------


class _Directory:
    def __init__(self, snapshots=()):
        self.snapshots = tuple(snapshots)

    async def list_channels(self, guild_id):
        return self.snapshots

    async def get_channel(self, guild_id, channel_id):  # pragma: no cover
        return None

    async def list_roles(self, guild_id):  # pragma: no cover
        return ()


class _ChannelActions:
    def __init__(self, *, new_id=555, fail=None):
        self.new_id = new_id
        self.fail = fail
        self.created: list[dict] = []
        self.deleted: list[int] = []

    async def create_text_channel(self, guild_id, *, name, overwrites,
                                  parent_id, reason):
        if self.fail is not None:
            raise self.fail
        self.created.append({"guild_id": guild_id, "name": name})
        return self.new_id

    async def delete_channel(self, channel_id, *, reason):
        self.deleted.append(int(channel_id))


class _Provisioning:
    def __init__(self, *, new_id=777, fail=None):
        self.new_id = new_id
        self.fail = fail
        self.created: list[dict] = []
        self.deleted: list[int] = []

    async def create_guild_role(self, guild_id, *, name, color, reason,
                                hoist=False, mentionable=False):
        if self.fail is not None:
            raise self.fail
        self.created.append({"guild_id": guild_id, "name": name,
                             "color": color, "hoist": hoist,
                             "mentionable": mentionable, "reason": reason})
        return self.new_id

    async def delete_role(self, guild_id, role_id, *, reason):
        self.deleted.append(int(role_id))


class _Bus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit(self, name, **payload):
        self.events.append((name, dict(payload)))


# --- fixtures -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _armed(monkeypatch):
    """Re-arm every ref/spec the lane needs (other suites legitimately
    clear the global tables) and install the fake txn + ports."""
    import sb.manifest.role as mrole
    import sb.manifest.settings as msettings
    import sb.manifest.setup as msetup
    from sb.domain.channel import service as channel_service
    from sb.domain.role import service as role_service
    from sb.kernel.db import pool

    msettings.ENSURE_REFS()
    mrole.ENSURE_REFS()
    msetup.ENSURE_REFS()

    conn = _Conn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        snap = conn.snapshot()
        extra = (dict(conn.bindings), list(conn.binding_audits),
                 list(conn.thresholds))
        try:
            yield conn
        except Exception:
            conn.restore(snap)   # rollback semantics
            conn.bindings, conn.binding_audits, conn.thresholds = (
                dict(extra[0]), list(extra[1]), list(extra[2]))
            raise

    monkeypatch.setattr(pool, "transaction", fake_transaction)
    yield conn
    channel_service.reset_channel_ports_for_tests()
    role_service.reset_role_ports_for_tests()


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


def _install_channel_ports(*, snapshots=(), actions=None, bus=None):
    from sb.domain.channel import service as channel_service

    actions = actions or _ChannelActions()
    channel_service.install_channel_directory(_Directory(snapshots))
    channel_service.install_channel_actions(actions)
    if bus is not None:
        channel_service.subscribe(bus)
    return actions


def _install_role_ports(*, provisioning=None, bus=None):
    from sb.domain.role import service as role_service

    provisioning = provisioning or _Provisioning()
    role_service.install_role_provisioning(provisioning)
    if bus is not None:
        role_service.subscribe(bus)
    return provisioning


_CHANNEL_PAYLOAD = {
    "subsystem": "logging", "name": "audit_channel", "kind": "channel",
    "resource_name": "bot-logs", "resource_mode": "create",
}

_ROLE_PAYLOAD = {
    "name": "role:regular", "resource_name": "Regular",
    "resource_mode": "create",
    "role_template": {"color": "#1ABC9C", "hoist": True,
                      "mentionable": False, "time_days": 7,
                      "xp_level": None, "purpose": "",
                      "template_slug": "time-progression"},
}


# =========================================================================================
# the K9 bindings resolve (the staged rows are draftable + applyable)
# =========================================================================================


def test_create_channel_op_kind_binds_the_k7_op():
    from sb.domain.setup import logging_presets as lp
    from sb.kernel.draft.registry import OP_KINDS
    from sb.kernel.workflow.registry import REGISTRY

    binding = OP_KINDS.get("create_channel")
    assert binding is not None
    assert binding.workflow_ref.name == "setup.ensure_channel"
    assert binding.is_resource_create is True
    declared = {f.name for f in binding.payload_schema}
    assert declared == {"subsystem", "name", "kind", "resource_name"}
    # the staged payload (_build_create_op) carries every declared field…
    op = lp._build_create_op(lp._LOGGING_BINDINGS[0],
                             resource_name="superbot-logs",
                             preset_key="single")
    assert declared <= set(op.payload)
    # …and the bound workflow resolves to a registered CompoundOpSpec.
    spec = REGISTRY.resolve(binding.workflow_ref)
    assert [leg.leg_id for leg in spec.legs] == ["ensure", "bind"]


def test_create_managed_role_workflow_resolves():
    from sb.kernel.draft.registry import OP_KINDS
    from sb.kernel.workflow.registry import REGISTRY

    binding = OP_KINDS.get("create_managed_role")
    assert binding is not None
    spec = REGISTRY.resolve(binding.workflow_ref)
    assert [leg.leg_id for leg in spec.legs] == ["create", "tier"]
    # NONE_JUSTIFIED, per the oracle's apply-time-unconditional posture.
    assert spec.idempotency_justification


# =========================================================================================
# ensure-channel: create → bind → audit
# =========================================================================================


def test_ensure_channel_creates_binds_and_audits(conn):
    bus = _Bus()
    actions = _install_channel_ports(bus=bus)
    result = _run("setup.ensure_channel", _CHANNEL_PAYLOAD,
                  correlation_id="11111111-1111-1111-1111-111111111111")
    assert result.outcome == SUCCESS
    # ONE create through the port, with the staged resource_name.
    assert actions.created == [{"guild_id": _GUILD, "name": "bot-logs"}]
    # the slot bind landed through settings.bind (row + binding audit).
    assert conn.bindings[(_GUILD, "logging", "audit_channel")] == {
        "target_id": 555, "status": "bound", "kind": "channel"}
    assert len(conn.binding_audits) == 1
    # the K7 central audit rows: the op's own + the nested bind's.
    verbs = {r["mutation_type"] for r in conn.audit_rows.values()}
    assert {"setup.channel_provisioned", "binding_set"} <= verbs
    # the shipped lifecycle advisory rode the bus for the real create.
    names = [n for n, _p in bus.events]
    assert "channel.lifecycle_changed" in names
    # both legs reported.
    assert [(s.target_name, s.ok) for s in result.steps] == [
        ("ensure_channel", True), ("bind_channel", True)]


def test_ensure_channel_reuses_by_name(conn):
    from sb.domain.channel.service import ChannelSnapshot

    bus = _Bus()
    actions = _install_channel_ports(
        snapshots=(ChannelSnapshot(channel_id=42, name="bot-logs",
                                   kind="text"),),
        bus=bus)
    result = _run("setup.ensure_channel", _CHANNEL_PAYLOAD)
    assert result.outcome == SUCCESS
    # the oracle ensure_channel reuse: a name+kind match is returned
    # unchanged — NO create call, the existing id binds to the slot.
    assert actions.created == []
    assert conn.bindings[(_GUILD, "logging", "audit_channel")][
        "target_id"] == 42
    # nothing was created ⇒ no lifecycle advisory.
    assert [n for n, _p in bus.events
            if n == "channel.lifecycle_changed"] == []


def test_ensure_channel_bind_failure_keeps_the_channel(conn):
    """The oracle ``binding_failed`` outcome: the op folds non-SUCCESS
    but the created channel is NEVER rolled back (resource_provisioning
    .py:52-55) — the compensator only guards the create leg itself."""
    actions = _install_channel_ports()
    conn.fail_binding = True
    result = _run("setup.ensure_channel", _CHANNEL_PAYLOAD)
    assert result.outcome == PARTIAL
    # the channel was created…
    assert len(actions.created) == 1
    # …and deliberately NOT deleted (no compensation on bind failure).
    assert actions.deleted == []
    assert [(s.target_name, s.ok) for s in result.steps] == [
        ("ensure_channel", True), ("bind", False)]


def test_ensure_channel_create_refusal_is_honest(conn):
    """A port refusal (permission denied / uninstalled) folds the op
    non-SUCCESS with NO binding write and NO withdrawal — the oracle's
    ``discord_failed`` audit class."""
    actions = _install_channel_ports(
        actions=_ChannelActions(fail=RuntimeError("403 Forbidden")))
    result = _run("setup.ensure_channel", _CHANNEL_PAYLOAD)
    assert result.outcome == DISCORD_FAILED
    assert conn.bindings == {}
    assert actions.deleted == []


# =========================================================================================
# create-managed-role: unconditional create + best-effort tier fold
# =========================================================================================


def test_create_managed_role_applies_spec_and_folds_tier(conn):
    bus = _Bus()
    provisioning = _install_role_ports(bus=bus)
    result = _run("role.create_managed_role", _ROLE_PAYLOAD,
                  correlation_id="22222222-2222-2222-2222-222222222222")
    assert result.outcome == SUCCESS
    # the cosmetic spec rode the port: parsed hex colour + hoist, and
    # the oracle's create reason vocabulary.
    assert provisioning.created == [{
        "guild_id": _GUILD, "name": "Regular", "color": 0x1ABC9C,
        "hoist": True, "mentionable": False,
        "reason": "setup role template (time-progression)"}]
    # the tier fold reached the audited threshold seam (full-row upsert:
    # guild, role_name, days, level, xp_auto, role_id, display_name).
    assert conn.thresholds == [(_GUILD, "Regular", 7, None, False, 777,
                                "Regular")]
    # central audit rows: the create op's + the nested threshold op's.
    verbs = {r["mutation_type"] for r in conn.audit_rows.values()}
    assert {"role_create", "role_threshold_set"} <= verbs
    # the shipped lifecycle advisory.
    assert [n for n, _p in bus.events if n == "role.lifecycle_changed"]


def test_create_managed_role_tier_failure_never_undoes_the_role(conn):
    """The oracle best-effort companion: 'a failed tier never undoes the
    already-created role' — the op stays SUCCESS and no delete runs."""
    provisioning = _install_role_ports()
    conn.fail_thresholds = True
    result = _run("role.create_managed_role", _ROLE_PAYLOAD)
    assert result.outcome == SUCCESS
    assert len(provisioning.created) == 1
    assert provisioning.deleted == []
    assert conn.thresholds == []
    # the tier leg reports ok (best-effort) — the miss lives in the log.
    assert [(s.target_name, s.ok) for s in result.steps] == [
        ("create_managed_role", True), ("template_tier", True)]


def test_create_managed_role_permission_denied_is_honest(conn):
    provisioning = _install_role_ports(
        provisioning=_Provisioning(
            fail=RuntimeError("403 Forbidden: Missing Permissions")))
    result = _run("role.create_managed_role", _ROLE_PAYLOAD)
    assert result.outcome != SUCCESS
    assert conn.thresholds == []
    assert provisioning.deleted == []


def test_create_managed_role_without_a_tier_skips_the_fold(conn):
    provisioning = _install_role_ports()
    payload = dict(_ROLE_PAYLOAD)
    payload["role_template"] = {"color": None, "hoist": False,
                                "mentionable": True, "time_days": None,
                                "xp_level": None, "purpose": "",
                                "template_slug": "support-server"}
    result = _run("role.create_managed_role", payload)
    assert result.outcome == SUCCESS
    assert provisioning.created[0]["color"] == 0
    assert provisioning.created[0]["mentionable"] is True
    assert conn.thresholds == []


def test_create_managed_role_xp_tier_folds_the_xp_row(conn):
    _install_role_ports()
    payload = dict(_ROLE_PAYLOAD)
    payload["resource_name"] = "Level 5"
    payload["role_template"] = {"color": "#2ECC71", "hoist": False,
                                "mentionable": False, "time_days": None,
                                "xp_level": 5, "purpose": "",
                                "template_slug": "xp-progression"}
    result = _run("role.create_managed_role", payload)
    assert result.outcome == SUCCESS
    # the XP half of the full-row fold: level + xp_auto_assign True.
    assert conn.thresholds == [(_GUILD, "Level 5", 0, 5, True, 777,
                                "Level 5")]
