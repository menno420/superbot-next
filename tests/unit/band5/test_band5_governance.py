"""Band 5 (governance) — registry integrity, scope-chain visibility
resolution + cache, execution fail-closed + overrides, the K7 write legs,
cleanup fallback, the K8/K6 port fills, and the template surface."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.governance import cache as gcache
    from sb.domain.governance import execution

    gcache.reset_cache_for_tests()
    execution.reset_overrides_for_tests()
    yield
    gcache.reset_cache_for_tests()
    execution.reset_overrides_for_tests()


def _clock(epoch: int = 1_000_000):
    return lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def _ctx(params: dict, *, uid: int = 42, gid: int = 1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params, clock=_clock())


def _gctx(**kw):
    from sb.domain.governance.models import GovernanceContext

    kw.setdefault("guild_id", 1)
    return GovernanceContext(**kw)


# --- registry ------------------------------------------------------------------

def test_registry_valid_and_shapes():
    from sb.domain.governance import registry
    from sb.spec.authority import TIERS

    registry.validate_registry()
    assert len(registry.SUBSYSTEM_META) == 43
    assert registry.VISIBILITY_TIERS == tuple(TIERS)
    assert registry.CAPABILITY_TO_SUBSYSTEM["moderation.warn.apply"] == "moderation"
    order = registry.dependency_order()
    assert order.index("economy") < order.index("inventory")
    assert registry.is_reserved_capability("governance.x.y")
    # tier filter: 'user' tier never sees administrator-tier subsystems
    user_visible = set(registry.get_subsystems_for_tier("user"))
    assert "admin" not in user_visible and "economy" in user_visible
    assert "admin" in set(registry.get_subsystems_for_tier("administrator"))


def test_registry_version_stamps():
    from sb.domain.governance import registry

    assert registry.REGISTRY_VERSION == 1
    assert registry.REGISTRY_SCHEMA_VERSION == 2


# --- resolver ------------------------------------------------------------------

def _install_visibility(monkeypatch, rows):
    """rows: {(scope_type, scope_id): {subsystem: enabled}}"""
    from sb.domain.governance import store

    async def fetch(guild_id, chain, conn=None):
        return {(s, i): dict(rows.get((s, i), {})) for s, i in chain}

    monkeypatch.setattr(store, "fetch_visibility_for_chain", fetch)


def test_scope_chain_order():
    from sb.domain.governance.resolver import build_scope_chain

    chain = build_scope_chain(_gctx(guild_id=9, channel_id=2, category_id=3,
                                    thread_id=4))
    assert chain == [("thread", 4), ("channel", 2), ("category", 3),
                     ("guild", 9)]


def test_visibility_channel_override_beats_guild(monkeypatch):
    from sb.domain.governance.resolver import resolve_visibility

    _install_visibility(monkeypatch, {
        ("guild", 1): {"economy": True},
        ("channel", 5): {"economy": False},
    })
    res = run(resolve_visibility(_gctx(channel_id=5, member_tier="user")))
    assert "economy" not in res.visible_subsystems
    from sb.domain.governance.models import PolicySource

    assert res.resolved_from["economy"] is PolicySource.CHANNEL_OVERRIDE


def test_visibility_explicit_null_inherits(monkeypatch):
    from sb.domain.governance.resolver import resolve_visibility

    _install_visibility(monkeypatch, {
        ("channel", 5): {"economy": None},   # explicit inherit
        ("guild", 1): {"economy": False},
    })
    res = run(resolve_visibility(_gctx(channel_id=5, member_tier="user")))
    assert "economy" not in res.visible_subsystems


def test_dependency_block_propagates(monkeypatch):
    from sb.domain.governance.models import SubsystemState
    from sb.domain.governance.resolver import resolve_visibility

    _install_visibility(monkeypatch, {("guild", 1): {"economy": False}})
    res = run(resolve_visibility(_gctx(member_tier="user")))
    trace = res.traces["inventory"]
    assert trace.final_state is SubsystemState.BLOCKED_DEPENDENCY
    assert "economy" in trace.dependency_blocks
    assert "inventory" not in res.visible_subsystems


def test_tier_gate_and_declared_tier(monkeypatch):
    from sb.domain.governance.resolver import resolve_visibility

    _install_visibility(monkeypatch, {})
    user = run(resolve_visibility(_gctx(member_tier="user")))
    admin = run(resolve_visibility(_gctx(member_tier="administrator")))
    assert "admin" not in user.visible_subsystems
    assert "admin" in admin.visible_subsystems
    # unknown declared tier ignored -> falls to 'user'
    weird = run(resolve_visibility(_gctx(member_tier="galactic")))
    assert weird.member_tier == "user"


def test_visibility_cache_and_invalidation(monkeypatch):
    from sb.domain.governance import cache as gcache
    from sb.domain.governance import store
    from sb.domain.governance.resolver import resolve_visibility

    calls = []

    async def fetch(guild_id, chain, conn=None):
        calls.append(1)
        return {(s, i): {} for s, i in chain}

    monkeypatch.setattr(store, "fetch_visibility_for_chain", fetch)
    ctx = _gctx(member_tier="user")
    run(resolve_visibility(ctx))
    run(resolve_visibility(ctx))
    assert len(calls) == 1          # second call served from cache
    gcache.invalidate_guild_cache(1)
    run(resolve_visibility(ctx))
    assert len(calls) == 2          # version bump invalidated


def test_failed_subsystem_is_internal(monkeypatch):
    from sb.domain.governance import cache as gcache
    from sb.domain.governance.models import SubsystemState
    from sb.domain.governance.resolver import resolve_visibility

    gcache.register_failed_subsystems({"economy"})
    _install_visibility(monkeypatch, {})
    res = run(resolve_visibility(_gctx(member_tier="user")))
    assert res.traces["economy"].final_state is SubsystemState.INTERNAL
    assert "economy" not in res.visible_subsystems


def test_member_tier_owner_and_role_grants(monkeypatch):
    from sb.domain.governance import resolver
    from sb.kernel.authority import owner as owner_mod

    monkeypatch.setattr(owner_mod, "is_platform_owner", lambda uid: uid == 99)
    assert run(resolver.resolve_member_tier(_gctx(user_id=99))) == "owner"

    # configured moderator role grant via the settings seam
    import sb.kernel.settings as ksettings

    async def fake_resolve(guild_id, subsystem, name):
        return 555 if name == "moderator_tier_role_id" else 0

    monkeypatch.setattr(ksettings, "resolve", fake_resolve)
    tier = run(resolver.resolve_member_tier(
        _gctx(user_id=7, role_ids={555})))
    assert tier == "moderator"
    # failed read never grants
    async def broken(guild_id, subsystem, name):
        raise RuntimeError("db down")

    monkeypatch.setattr(ksettings, "resolve", broken)
    assert run(resolver.resolve_member_tier(
        _gctx(user_id=7, role_ids={555}))) == "user"


# --- execution -----------------------------------------------------------------

def test_execution_unknown_capability_fail_closed():
    from sb.domain.governance.execution import resolve_execution

    res = run(resolve_execution(_gctx(), "no.such.capability"))
    assert not res.allowed
    assert res.trace.denied_by == "unknown_capability"


def test_execution_override_wins(monkeypatch):
    from sb.domain.governance import execution, store

    async def fetch(guild_id, conn=None):
        return {"economy.shop.buy": False}

    monkeypatch.setattr(store, "fetch_capability_overrides", fetch)
    res = run(execution.resolve_execution(
        _gctx(member_tier="administrator"), "economy.shop.buy"))
    assert not res.allowed and res.resolved_scope == "override"
    # get_capability_override reads the same TTL cache
    assert run(execution.get_capability_override(1, "economy.shop.buy")) is False
    # write-through
    execution.note_override_written(1, "economy.shop.buy", None)
    assert run(execution.get_capability_override(1, "economy.shop.buy")) is None


def test_execution_bypass_audits(monkeypatch):
    from sb.domain.governance import execution, store

    async def fetch(guild_id, conn=None):
        return {}

    monkeypatch.setattr(store, "fetch_capability_overrides", fetch)
    audited = []

    async def fake_audit(ctx, capability, subsystem_name):
        audited.append((capability, subsystem_name))

    monkeypatch.setattr(execution, "_audit_internal_bypass", fake_audit)
    res = run(execution.resolve_execution(
        _gctx(), "economy.shop.buy", check_visibility=False))
    assert res.allowed and audited == [("economy.shop.buy", "economy")]


def test_execution_visibility_gate(monkeypatch):
    from sb.domain.governance import execution, store

    async def fetch(guild_id, conn=None):
        return {}

    monkeypatch.setattr(store, "fetch_capability_overrides", fetch)
    _install_visibility(monkeypatch, {("guild", 1): {"economy": False}})
    res = run(execution.resolve_execution(
        _gctx(member_tier="user"), "economy.shop.buy"))
    assert not res.allowed


# --- K7 legs --------------------------------------------------------------------

class FakeGovStore:
    def __init__(self):
        self.vis: list[tuple] = []
        self.cleanup: list[tuple] = []
        self.audit: list[tuple] = []
        self.caps: list[tuple] = []
        self.removed = True

    def install(self, monkeypatch):
        from sb.domain.governance import store as store_mod

        async def get_visibility_override(gid, st, si, sub, conn=None):
            return None

        async def upsert_visibility(conn, *, guild_id, scope_type, scope_id,
                                    subsystem, enabled):
            self.vis.append((guild_id, scope_type, scope_id, subsystem,
                             enabled))

        async def get_cleanup_policy(gid, st, si, conn=None):
            return None

        async def upsert_cleanup_policy(conn, *, guild_id, scope_type,
                                        scope_id, delete_invalid_commands,
                                        delete_failed_commands,
                                        delete_after_seconds):
            self.cleanup.append((scope_type, scope_id,
                                 delete_invalid_commands,
                                 delete_after_seconds))

        async def remove_cleanup_policy(conn, *, guild_id, scope_type,
                                        scope_id):
            return self.removed

        async def insert_governance_audit(conn, **kw):
            self.audit.append(kw)

        async def fetch_capability_overrides(gid, conn=None):
            return {}

        async def upsert_capability_override(conn, *, guild_id, capability,
                                             allowed):
            self.caps.append((guild_id, capability, allowed))

        for name, fn in list(locals().items()):
            if callable(fn) and hasattr(store_mod, name):
                monkeypatch.setattr(store_mod, name, fn)
        return self


def test_set_visibility_leg_writes_and_audits(monkeypatch):
    from sb.domain.governance import ops

    fake = FakeGovStore().install(monkeypatch)
    out = run(ops._record_set_visibility(None, _ctx(
        {"scope_type": "channel", "scope_id": 5, "subsystem": "economy",
         "enabled": False})))
    assert fake.vis == [(1, "channel", 5, "economy", False)]
    assert fake.audit[0]["action"] == "set_visibility"
    assert out.after["enabled"] is False


def test_set_visibility_leg_validates(monkeypatch):
    from sb.domain.governance import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeGovStore().install(monkeypatch)
    with pytest.raises(ValidatorError):
        run(ops._record_set_visibility(None, _ctx(
            {"scope_type": "role", "scope_id": 5, "subsystem": "economy",
             "enabled": True})))
    with pytest.raises(ValidatorError):
        run(ops._record_set_visibility(None, _ctx(
            {"scope_type": "guild", "scope_id": 1, "subsystem": "nope",
             "enabled": True})))
    assert not fake.vis and not fake.audit


def test_cleanup_legs(monkeypatch):
    from sb.domain.governance import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeGovStore().install(monkeypatch)
    run(ops._record_set_cleanup(None, _ctx(
        {"scope_type": "channel", "scope_id": 5,
         "delete_after_seconds": 10})))
    assert fake.cleanup == [("channel", 5, True, 10)]
    with pytest.raises(ValidatorError):   # RC-5: thread rejected pre-DB
        run(ops._record_set_cleanup(None, _ctx(
            {"scope_type": "thread", "scope_id": 5})))
    out = run(ops._record_remove_cleanup(None, _ctx(
        {"scope_type": "channel", "scope_id": 5})))
    assert out.after["removed"] is True


def test_capability_override_leg(monkeypatch):
    from sb.domain.governance import ops
    from sb.kernel.interaction.errors import ValidatorError

    fake = FakeGovStore().install(monkeypatch)
    run(ops._record_set_capability_override(None, _ctx(
        {"capability": "economy.shop.buy", "allowed": False})))
    assert fake.caps == [(1, "economy.shop.buy", False)]
    with pytest.raises(ValidatorError):
        run(ops._record_set_capability_override(None, _ctx(
            {"capability": "made.up.cap", "allowed": False})))


def test_tombstone_erasure_body(monkeypatch):
    from sb.domain.governance import ops
    from sb.domain.governance import store as store_mod

    scrubbed = []

    async def tomb(conn, *, user_id):
        scrubbed.append(user_id)
        return 3

    monkeypatch.setattr(store_mod, "tombstone_subject_governance_audit", tomb)
    out = run(ops._tombstone_subject_audit(None, _ctx(
        {"subject_user_id": 42})))
    assert scrubbed == [42] and out.after["rows"] == 3


# --- cleanup resolution ----------------------------------------------------------

def test_cleanup_policy_fallback_and_override(monkeypatch):
    from sb.domain.governance import store
    from sb.domain.governance.cleanup import resolve_cleanup_policy
    from sb.domain.governance.models import PolicySource

    async def none_policy(gid, st, si, conn=None):
        return None

    monkeypatch.setattr(store, "get_cleanup_policy", none_policy)
    pol = run(resolve_cleanup_policy(_gctx(channel_id=5)))
    assert pol.delete_message and pol.delete_after_seconds == 5
    assert pol.resolved_from is PolicySource.FALLBACK_DEFAULT

    async def chan_policy(gid, st, si, conn=None):
        if st == "channel":
            return {"delete_invalid_commands": False,
                    "delete_after_seconds": 30}
        return None

    monkeypatch.setattr(store, "get_cleanup_policy", chan_policy)
    pol = run(resolve_cleanup_policy(_gctx(channel_id=5)))
    assert not pol.delete_message and pol.delete_after_seconds == 30
    assert pol.resolved_from is PolicySource.CHANNEL_OVERRIDE


# --- service: subsystem_enabled + snapshot + ports --------------------------------

def test_subsystem_enabled_guild_scope(monkeypatch):
    from sb.domain.governance.service import subsystem_enabled

    _install_visibility(monkeypatch, {("guild", 1): {"economy": False}})
    assert not run(subsystem_enabled(1, "economy"))
    assert not run(subsystem_enabled(1, "inventory"))  # dependency block
    assert run(subsystem_enabled(1, "xp"))
    assert run(subsystem_enabled(1, "not_a_subsystem"))  # fail-open


def test_snapshot_and_diff(monkeypatch):
    from sb.domain.governance import store
    from sb.domain.governance.service import (
        build_governance_snapshot,
        diff_governance_snapshots,
    )

    _install_visibility(monkeypatch, {})

    async def none_policy(gid, st, si, conn=None):
        return None

    monkeypatch.setattr(store, "get_cleanup_policy", none_policy)
    before = run(build_governance_snapshot(_gctx(member_tier="user")))
    assert before.registry_version == 1
    assert before.capability_map["economy.shop.buy"] is True
    assert "admin" in before.denied_subsystems

    from sb.domain.governance import cache as gcache

    gcache.invalidate_guild_cache(1)
    _install_visibility(monkeypatch, {("guild", 1): {"economy": False}})
    after = run(build_governance_snapshot(_gctx(member_tier="user")))
    diff = diff_governance_snapshots(before, after)
    assert "economy" in diff.removed_visible
    assert diff.capability_changes["economy.shop.buy"] == (True, False)
    assert not diff.is_empty


def test_authority_ports_filled():
    """The manifest import fills the S7/S9 waiting ports with the real
    governance reads (the band-5 obligation)."""
    import importlib

    import sb.manifest.governance  # noqa: F401 — import-time fill
    from sb.domain.governance.execution import get_capability_override
    from sb.domain.governance.service import install_authority_ports

    authority_resolve = importlib.import_module("sb.kernel.authority.resolve")
    interaction_resolve = importlib.import_module(
        "sb.kernel.interaction.resolve")

    install_authority_ports()
    assert authority_resolve._override_reader is get_capability_override
    assert authority_resolve._role_binding_reader.__name__ == "_role_binding_reader"
    assert interaction_resolve._visibility_reader.__name__ == "_visibility"


def test_role_binding_reader(monkeypatch):
    from sb.domain.governance.service import _role_binding_reader
    from sb.kernel.db import settings as db_settings

    async def get_bindings(guild_id, subsystem, name, conn=None):
        assert (subsystem, name) == ("welcome", "entry_role")
        return (10, 20)

    monkeypatch.setattr(db_settings, "get_bindings", get_bindings)
    assert run(_role_binding_reader(1, "welcome.entry_role")) == frozenset({10, 20})
    assert run(_role_binding_reader(1, "malformed")) is None


# --- templates ---------------------------------------------------------------------

def test_template_export_and_apply(monkeypatch):
    from sb.domain.governance import service, store, templates

    async def all_vis(gid, conn=None):
        return [{"scope_type": "guild", "scope_id": gid, "subsystem": "economy",
                 "enabled": False}]

    async def all_cleanup(gid, conn=None):
        return [{"scope_type": "channel", "scope_id": 5,
                 "delete_invalid_commands": True,
                 "delete_failed_commands": True, "delete_after_seconds": 9}]

    monkeypatch.setattr(store, "get_all_visibility_for_guild", all_vis)
    monkeypatch.setattr(store, "get_all_cleanup_for_guild", all_cleanup)
    tpl = run(templates.export_template(1, name="t"))
    assert tpl.source_guild_id == 1 and len(tpl.visibility_overrides) == 1

    # round-trip through the dict codec
    tpl2 = templates.GovernanceTemplate.from_dict(tpl.to_dict())
    assert tpl2.visibility_overrides == tpl.visibility_overrides

    applied = []

    async def set_vis(ctx, **kw):
        applied.append(("vis", kw))

    async def set_cleanup(ctx, **kw):
        applied.append(("cleanup", kw))

    monkeypatch.setattr(service, "set_subsystem_visibility", set_vis)
    monkeypatch.setattr(service, "set_cleanup_policy_for_scope", set_cleanup)
    count = run(templates.apply_template(_ctx({}), tpl2))
    assert count == 2 and [a[0] for a in applied] == ["vis", "cleanup"]


# --- tiers + role templates ----------------------------------------------------------

def test_tier_metadata_and_order():
    from sb.domain.governance.tiers import (
        PermissionTier,
        all_tiers_ordered,
        metadata_for,
        tier_at_or_above,
        tier_index,
    )

    assert tier_index("moderator") == 3
    assert tier_at_or_above("administrator", PermissionTier.MODERATOR)
    assert not tier_at_or_above("user", "trusted")
    assert metadata_for(PermissionTier.PLATFORM_OWNER).tier_index == 6
    assert [t.value for t in all_tiers_ordered()][:6] == [
        "user", "trusted", "staff", "moderator", "administrator", "owner"]
    with pytest.raises(ValueError):
        tier_index("galactic")


def test_role_template_registry():
    from sb.domain.governance import role_templates as rt

    rt.reset_role_templates_for_tests()
    assert rt.get_template("Moderator") is rt.MODERATOR_TEMPLATE
    assert set(rt.all_collections()) == {
        "moderation_essentials", "administration_essentials",
        "trusted_user_tiers"}
    assert "manage_messages" in rt.MODERATOR_TEMPLATE.permissions


def test_governance_manifest_compiles_in_snapshot():
    import json

    snap = json.load(open("manifest.snapshot.json"))
    assert "governance" in snap["subsystems"]
    gov = snap["subsystems"]["governance"]
    assert {e["name"] for e in gov["events"]} == {
        "governance.visibility.changed", "governance.cleanup.changed",
        "governance.cache.invalidated", "governance.execution.denied",
        "governance.execution.allowed"}
