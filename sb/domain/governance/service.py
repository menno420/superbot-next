"""Governance service (band 5) — snapshot/diff (snapshot.py), health
(health.py), the version-upgrade hook (writes.py tail), the audited write
wrappers (pipeline call surface: K7 run + post-commit cache maintenance),
and THE PORT FILLS this band owes the kernel:

* ``sb.kernel.authority.resolve.install_capability_override_reader`` —
  the shipped ``governance.execution.get_capability_override`` semantics
  (S7 note: "the governance/settings bands install real readers");
* ``sb.kernel.authority.resolve.install_role_binding_reader`` — R-16:
  binding name -> the guild's configured role-id set, read over the
  band-1 subsystem_bindings store;
* ``sb.kernel.interaction.resolve.install_visibility_reader`` — K8's
  (guild_id, subsystem) gate. DEVIATION (D-0039): the K8 seam carries no
  member/channel context, so the reader answers "is the subsystem
  enabled at GUILD scope" (overrides + dependency rules, tier-agnostic —
  tier gating is the authority engine's job in the compiled
  architecture, CommandSpec.audience_tier).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sb.domain.governance import cache as gcache
from sb.domain.governance import execution, registry, store
from sb.domain.governance.cleanup import resolve_cleanup_policy
from sb.domain.governance.models import (
    GovernanceContext,
    GovernanceDiff,
    GovernanceHealthReport,
    GovernanceSnapshot,
    PolicySource,
    ResolutionTrace,
    SubsystemState,
)
from sb.domain.governance.resolver import (
    apply_dependency_rules,
    get_visible_subsystems,
    resolve_visibility,
)

logger = logging.getLogger("sb.domain.governance")

__all__ = [
    "ScopeCheck",
    "SubsystemResolution",
    "build_governance_snapshot",
    "check_governance_version",
    "diff_governance_snapshots",
    "install_authority_ports",
    "remove_cleanup_policy_for_scope",
    "resolve_subsystem_state",
    "run_governance_healthcheck",
    "set_capability_override",
    "set_cleanup_policy_for_scope",
    "set_subsystem_visibility",
    "subsystem_enabled",
]


# --- audited write wrappers (the shipped module-level pipeline surface) --------

async def _run_op(op, ctx) -> object:
    from sb.kernel.workflow import engine

    result = await engine.run(op, ctx)
    if getattr(result, "outcome", None) == "success":
        gcache.invalidate_guild_cache(int(ctx.guild_id or 0))
    return result


async def set_subsystem_visibility(ctx, *, scope_type: str, scope_id: int,
                                   subsystem: str,
                                   enabled: bool | None) -> object:
    """K7-run + post-commit cache invalidation (pipeline steps 4-6).
    ``ctx`` is a WorkflowContext (actor carries the authority)."""
    from sb.domain.governance.ops import SET_VISIBILITY

    ctx.params.update({"scope_type": scope_type, "scope_id": scope_id,
                       "subsystem": subsystem, "enabled": enabled})
    return await _run_op(SET_VISIBILITY, ctx)


async def set_cleanup_policy_for_scope(ctx, *, scope_type: str, scope_id: int,
                                       delete_invalid_commands: bool = True,
                                       delete_failed_commands: bool = True,
                                       delete_after_seconds: int = 5) -> object:
    from sb.domain.governance.ops import SET_CLEANUP

    ctx.params.update({
        "scope_type": scope_type, "scope_id": scope_id,
        "delete_invalid_commands": delete_invalid_commands,
        "delete_failed_commands": delete_failed_commands,
        "delete_after_seconds": delete_after_seconds})
    return await _run_op(SET_CLEANUP, ctx)


async def remove_cleanup_policy_for_scope(ctx, *, scope_type: str,
                                          scope_id: int) -> object:
    from sb.domain.governance.ops import REMOVE_CLEANUP

    ctx.params.update({"scope_type": scope_type, "scope_id": scope_id})
    return await _run_op(REMOVE_CLEANUP, ctx)


async def set_capability_override(ctx, *, capability: str,
                                  allowed: bool | None) -> object:
    from sb.domain.governance.ops import SET_CAPABILITY_OVERRIDE

    ctx.params.update({"capability": capability, "allowed": allowed})
    result = await _run_op(SET_CAPABILITY_OVERRIDE, ctx)
    if getattr(result, "outcome", None) == "success":
        execution.note_override_written(
            int(ctx.guild_id or 0), capability, allowed)
    return result


# --- snapshot + diff (snapshot.py verbatim) --------------------------------------

async def _resolve_all_capabilities(ctx: GovernanceContext) -> dict[str, bool]:
    visible = await get_visible_subsystems(ctx)
    return {cap: (subsystem in visible)
            for cap, subsystem in registry.CAPABILITY_TO_SUBSYSTEM.items()}


async def build_governance_snapshot(ctx: GovernanceContext) -> GovernanceSnapshot:
    """Complete governance state for a context (dashboards, /why, AI)."""
    vis = await resolve_visibility(ctx)
    cleanup = await resolve_cleanup_policy(ctx)
    cap_map = await _resolve_all_capabilities(ctx)

    all_names = set(registry.SUBSYSTEM_META.keys())
    denied = all_names - vis.visible_subsystems
    dep_blocks: dict[str, list[str]] = {}
    for name, trace in vis.traces.items():
        if trace.dependency_blocks:
            dep_blocks[name] = trace.dependency_blocks

    return GovernanceSnapshot(
        visible_subsystems=vis.visible_subsystems,
        denied_subsystems=denied,
        dependency_blocks=dep_blocks,
        cleanup_policy=cleanup,
        member_tier=vis.member_tier,
        scope_provenance=vis.resolved_from,
        capability_map=cap_map,
        registry_version=registry.REGISTRY_VERSION,
        registry_schema_version=registry.REGISTRY_SCHEMA_VERSION,
    )


def diff_governance_snapshots(before: GovernanceSnapshot,
                              after: GovernanceSnapshot) -> GovernanceDiff:
    added = after.visible_subsystems - before.visible_subsystems
    removed = before.visible_subsystems - after.visible_subsystems

    changed_sources: dict[str, tuple[str, str]] = {}
    for name in set(before.scope_provenance) | set(after.scope_provenance):
        old_src = before.scope_provenance.get(name)
        new_src = after.scope_provenance.get(name)
        if old_src != new_src:
            changed_sources[name] = (
                old_src.value if old_src else "none",
                new_src.value if new_src else "none")

    cap_changes: dict[str, tuple[bool, bool]] = {}
    for cap in set(before.capability_map) | set(after.capability_map):
        old_val = before.capability_map.get(cap, False)
        new_val = after.capability_map.get(cap, False)
        if old_val != new_val:
            cap_changes[cap] = (old_val, new_val)

    cleanup_changed = (before.cleanup_policy.to_dict()
                       != after.cleanup_policy.to_dict())
    return GovernanceDiff(
        added_visible=added, removed_visible=removed,
        changed_sources=changed_sources, capability_changes=cap_changes,
        cleanup_changed=cleanup_changed)


# --- health + version (health.py / writes.py tail) ---------------------------------

async def run_governance_healthcheck(guild_id: int) -> GovernanceHealthReport:
    """Orphan overrides, stale versions, invalid configs (shipped)."""
    known = set(registry.SUBSYSTEM_META.keys())
    rows = await store.get_all_visibility_for_guild(guild_id)
    orphans = [
        {"scope_type": r["scope_type"], "scope_id": r["scope_id"],
         "subsystem": r["subsystem"]}
        for r in rows if r["subsystem"] not in known
    ]
    stored = await _read_governance_version(guild_id)
    stale = [guild_id] if stored < registry.REGISTRY_VERSION else []
    summary = (f"{len(orphans)} orphan override(s), "
               f"{len(stale)} stale version guild(s)")
    return GovernanceHealthReport(
        orphan_overrides=orphans, stale_version_guilds=stale,
        invalid_cleanup_configs=[], summary=summary)


async def _read_governance_version(guild_id: int) -> int:
    try:
        from sb.kernel.settings import resolve

        stored = await resolve(guild_id, "governance", "governance_version")
        return int(stored or 0)
    except Exception:  # noqa: BLE001 — undeclared/unreadable = version 0
        return 0


async def check_governance_version(ctx) -> None:
    """Upgrade hook (shipped check_governance_version): prune orphan
    overrides for de-registered subsystems, then stamp the registry
    version through the band-1 settings lane (§4.1 — the write goes
    through settings.set_scalar, never a raw KV write)."""
    guild_id = int(ctx.guild_id or 0)
    stored = await _read_governance_version(guild_id)
    if stored >= registry.REGISTRY_VERSION:
        return
    logger.info("governance upgrade guild=%d from v%d to v%d",
                guild_id, stored, registry.REGISTRY_VERSION)
    known = set(registry.SUBSYSTEM_META.keys())
    rows = await store.get_all_visibility_for_guild(guild_id)
    orphans = [r for r in rows if r["subsystem"] not in known]
    if orphans:
        from sb.kernel.db.pool import transaction

        logger.warning("governance upgrade: removing %d orphan override(s) "
                       "for guild=%d", len(orphans), guild_id)
        async with transaction() as conn:
            for o in orphans:
                await store.delete_visibility_row(
                    conn, guild_id=guild_id, scope_type=o["scope_type"],
                    scope_id=o["scope_id"], subsystem=o["subsystem"])
    from sb.domain.settings.ops import SET_SCALAR
    from sb.kernel.workflow import engine

    ctx.params.update({"subsystem": "governance",
                       "name": "governance_version",
                       "value": str(registry.REGISTRY_VERSION)})
    await engine.run(SET_SCALAR, ctx)
    gcache.invalidate_guild_cache(guild_id)


# --- K8 visibility gate (tier-agnostic guild-scope read; D-0039) --------------------

async def subsystem_enabled(guild_id: int, subsystem: str) -> bool:
    """Is *subsystem* enabled at guild scope (overrides + dependency
    rules)? Unknown subsystems are ENABLED (fail-open — the compiled
    manifests own existence; governance only gates registered rows)."""
    if subsystem not in registry.SUBSYSTEM_META:
        return True
    ctx = GovernanceContext(guild_id=guild_id)
    chain = [("guild", guild_id)]
    scope_data = await store.fetch_visibility_for_chain(guild_id, chain)
    states: dict[str, SubsystemState] = {}
    traces: dict = {}
    resolved_from: dict[str, PolicySource] = {}
    for name in registry.SUBSYSTEM_META:
        row = scope_data.get(("guild", guild_id), {})
        val = row.get(name)
        states[name] = (SubsystemState.DISABLED if val is False
                        else SubsystemState.ENABLED)
        resolved_from[name] = (PolicySource.GUILD_OVERRIDE if val is not None
                               else PolicySource.REGISTRY_DEFAULT)
    apply_dependency_rules(states, traces, resolved_from)
    return states.get(subsystem) == SubsystemState.ENABLED


# --- the explorer's diagnostic read seam (settings.access, curation rows 82-87) ------

@dataclass(frozen=True)
class ScopeCheck:
    """One scope the resolver walked for a subsystem (most-specific first).

    ``has_row`` = a ``subsystem_visibility`` row exists at this scope;
    ``value`` is its stored tri-state (True/False; an explicit ``None``
    row means "inherit from the next scope up" — shipped semantics);
    ``matched`` marks the ONE row that decided the state."""

    scope_type: str
    scope_id: int
    has_row: bool
    value: bool | None
    matched: bool


@dataclass(frozen=True)
class SubsystemResolution:
    """One subsystem's resolved access state WITH provenance — the
    ``settings.access`` explorer's diagnostic READ (never a write).

    The pending copy named this seam ``governance.resolve_subsystem_state``;
    the resolve chain it reports is the one the resolver actually
    implements for subsystem access: scope-chain visibility rows
    (thread > channel > category > guild, ``subsystem_visibility``) →
    registry default, with hard-dependency propagation on top. The K7
    settings-KV lane (per-guild → global → declared default) is a
    DIFFERENT resolve chain for scalar settings and never gates
    subsystem access, so it does not appear here (honest provenance:
    visibility row vs registry default)."""

    subsystem: str
    known: bool                            # registered in SUBSYSTEM_META?
    state: SubsystemState
    source: PolicySource
    checks: tuple[ScopeCheck, ...]         # the chain walked, in order
    dependency_blocks: tuple[str, ...]
    visibility_tier: str


async def resolve_subsystem_state(
    guild_id: int, subsystem: str, *,
    channel_id: int | None = None, category_id: int | None = None,
    thread_id: int | None = None,
) -> SubsystemResolution:
    """Resolve ONE subsystem's access state for a scope selection and say
    WHERE it came from (which override row, or the registry default).

    Tier-agnostic like ``subsystem_enabled`` (D-0039 — member-tier gating
    is the authority engine's job); unknown subsystems are ENABLED
    (fail-open, ``known=False``) exactly like the dispatch gate. Reads the
    same store + walks the same chain as ``resolve_visibility``, so the
    diagnostic can never drift from the gate."""
    from sb.domain.governance.resolver import (
        _resolve_single_subsystem,
        build_scope_chain,
    )

    meta = registry.SUBSYSTEM_META.get(subsystem)
    if meta is None:
        return SubsystemResolution(
            subsystem=subsystem, known=False,
            state=SubsystemState.ENABLED,
            source=PolicySource.REGISTRY_DEFAULT,
            checks=(), dependency_blocks=(), visibility_tier="")

    ctx = GovernanceContext(
        guild_id=guild_id, channel_id=channel_id,
        category_id=category_id, thread_id=thread_id)
    chain = build_scope_chain(ctx)
    scope_data = await store.fetch_visibility_for_chain(guild_id, chain)

    # resolve EVERY subsystem so dependency propagation sees real states.
    states: dict[str, SubsystemState] = {}
    traces: dict = {}
    resolved_from: dict[str, PolicySource] = {}
    for name in registry.SUBSYSTEM_META:
        override_val, source, checked = _resolve_single_subsystem(
            name, chain, scope_data)
        final = (SubsystemState.DISABLED if override_val is False
                 else SubsystemState.ENABLED)
        states[name] = final
        traces[name] = ResolutionTrace(
            subsystem=name, checked_scopes=list(checked),
            matched_scope=source if override_val is not None else None,
            dependency_blocks=[], final_state=final)
        resolved_from[name] = (source if override_val is not None
                               else PolicySource.REGISTRY_DEFAULT)
    apply_dependency_rules(states, traces, resolved_from)

    checks: list[ScopeCheck] = []
    matched = False
    for scope_type, scope_id in chain:
        row = scope_data.get((scope_type, scope_id), {})
        has_row = subsystem in row
        value = row.get(subsystem)
        is_match = not matched and has_row and value is not None
        if is_match:
            matched = True
        checks.append(ScopeCheck(scope_type=scope_type, scope_id=scope_id,
                                 has_row=has_row, value=value,
                                 matched=is_match))

    return SubsystemResolution(
        subsystem=subsystem, known=True, state=states[subsystem],
        source=resolved_from[subsystem], checks=tuple(checks),
        dependency_blocks=tuple(traces[subsystem].dependency_blocks),
        visibility_tier=str(meta.get("visibility_tier", "")))


# --- port fills ----------------------------------------------------------------------

async def _role_binding_reader(guild_id: int,
                               binding_name: str) -> frozenset[int] | None:
    """R-16: binding name ('subsystem.name') -> configured role-id set via
    the band-1 subsystem_bindings store; None when unconfigured."""
    from sb.kernel.db import settings as db_settings

    subsystem, _, name = binding_name.partition(".")
    if not subsystem or not name:
        return None
    try:
        rows = await db_settings.get_bindings(guild_id, subsystem, name)
    except Exception:  # noqa: BLE001 — a failed read = unconfigured
        return None
    ids = frozenset(int(r) for r in rows if r is not None)
    return ids or None


def install_authority_ports() -> None:
    """Fill the S7/S9 waiting read ports with the real governance reads.
    Called at manifest import (idempotent) + by the composition root."""
    from sb.kernel.authority.resolve import (
        install_capability_override_reader,
        install_role_binding_reader,
    )
    from sb.kernel.interaction.resolve import install_visibility_reader

    install_capability_override_reader(execution.get_capability_override)
    install_role_binding_reader(_role_binding_reader)

    async def _visibility(guild_id: int, subsystem: str) -> bool:
        return await subsystem_enabled(guild_id, subsystem)

    install_visibility_reader(_visibility)


# --- guild teardown -------------------------------------------------------------------

async def teardown_guild(guild_id: int) -> None:
    """The governance half of guild teardown — the shipped ordering:
    capability overrides (execution layer) then visibility cache then the
    DB rows (audit log preserved)."""
    execution.forget_guild_capabilities(guild_id)
    gcache.forget_guild(guild_id)
    gcache.invalidate_guild_cache(guild_id)
    await store.delete_guild_governance_rows(guild_id)
