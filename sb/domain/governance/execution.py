"""Governance execution resolution (band 5) — disbot/governance/execution.py
ported headlessly: capability execution independent of visibility
(ISSUE-008), the TTL-bounded per-guild override cache (DEBT-001), the
fail-closed unknown-capability rule (ARCH-005), and the audited
internal/AI bypass (DEBT-002).

``get_capability_override`` doubles as THE body behind the S7 authority
port ``install_capability_override_reader`` (service.install_authority_ports
wires it) — the settings/binding/provisioning authority resolver honours a
per-guild revoke without owning a second DB read, exactly as shipped.
"""

from __future__ import annotations

import logging
import time

from sb.domain.governance import registry, store
from sb.domain.governance.models import (
    ExecutionResult,
    ExecutionTrace,
    GovernanceContext,
)
from sb.domain.governance.resolver import resolve_visibility

logger = logging.getLogger("sb.domain.governance")

__all__ = [
    "forget_guild_capabilities",
    "get_capability_override",
    "reset_overrides_for_tests",
    "resolve_execution",
]

# (guild_id, capability) -> bool; TTL-bounded staleness (shipped 600s).
_capability_execution_overrides: dict[tuple[int, str], bool] = {}
_loaded_guilds: set[int] = set()
_loaded_guilds_at: dict[int, float] = {}
_OVERRIDE_TTL: float = 600.0


async def _load_capability_overrides(guild_id: int) -> None:
    """Deterministic reload: prior entries cleared before the fresh row
    set inserts, so stale rows cannot survive a refresh (shipped)."""
    stale = [k for k in _capability_execution_overrides if k[0] == guild_id]
    for k in stale:
        _capability_execution_overrides.pop(k, None)
    try:
        rows = await store.fetch_capability_overrides(guild_id)
        for capability, allowed in rows.items():
            _capability_execution_overrides[(guild_id, capability)] = allowed
    except Exception as exc:  # noqa: BLE001 — read failure = no overrides
        logger.debug("capability_execution_overrides unavailable: %s", exc)
    _loaded_guilds_at[guild_id] = time.monotonic()


def _check_capability_override(guild_id: int, capability: str) -> bool | None:
    return _capability_execution_overrides.get((guild_id, capability))


def _overrides_stale(guild_id: int) -> bool:
    loaded_at = _loaded_guilds_at.get(guild_id)
    if loaded_at is None:
        return True
    return (time.monotonic() - loaded_at) > _OVERRIDE_TTL


async def get_capability_override(guild_id: int, capability: str) -> bool | None:
    """Public read of a per-guild capability execution override (True /
    False / None = no row); refreshes when stale."""
    if _overrides_stale(guild_id):
        await _load_capability_overrides(guild_id)
    return _check_capability_override(guild_id, capability)


def forget_guild_capabilities(guild_id: int) -> None:
    """Clear all capability override state for a guild (guild teardown;
    deliberately NOT called from cache.forget_guild — no backward import,
    the teardown coordinator orders both calls)."""
    _loaded_guilds.discard(guild_id)
    _loaded_guilds_at.pop(guild_id, None)
    stale = [k for k in _capability_execution_overrides if k[0] == guild_id]
    for k in stale:
        _capability_execution_overrides.pop(k, None)


def note_override_written(guild_id: int, capability: str,
                          allowed: bool | None) -> None:
    """Post-commit cache write-through (the K7 override op calls this so
    the TTL cache never serves the pre-write value for up to 10 minutes)."""
    if allowed is None:
        _capability_execution_overrides.pop((guild_id, capability), None)
    else:
        _capability_execution_overrides[(guild_id, capability)] = allowed


def reset_overrides_for_tests() -> None:
    _capability_execution_overrides.clear()
    _loaded_guilds.clear()
    _loaded_guilds_at.clear()


async def _audit_internal_bypass(
    ctx: GovernanceContext, capability: str, subsystem_name: str,
) -> None:
    """Durable audit row for an internal/AI-triggered bypass (DEBT-002).
    Best-effort: an audit failure must not block the execution."""
    try:
        from sb.kernel.db.pool import transaction

        async with transaction() as conn:
            await store.insert_governance_audit(
                conn, guild_id=ctx.guild_id,
                actor_id=int(ctx.user_id or 0), action="execution_bypass",
                scope_type=None, scope_id=None, subsystem=subsystem_name,
                old_value=None,
                new_value={
                    "capability": capability,
                    "subsystem": subsystem_name,
                    "reason": "internal_or_ai_invocation",
                    "visibility_check_skipped": True,
                })
    except Exception as exc:  # noqa: BLE001 — bypass already decided
        logger.warning(
            "internal bypass audit write failed (capability=%r guild=%d): %s",
            capability, ctx.guild_id, exc)


async def resolve_execution(
    ctx: GovernanceContext, capability: str, check_visibility: bool = True,
) -> ExecutionResult:
    """May this capability execute in this context?

    Explicit overrides always win; unknown capabilities fail CLOSED;
    check_visibility=False (internal/AI) skips the visibility gate but
    writes the durable bypass audit row.
    """
    if ctx.guild_id not in _loaded_guilds or _overrides_stale(ctx.guild_id):
        await _load_capability_overrides(ctx.guild_id)
        _loaded_guilds.add(ctx.guild_id)

    subsystem_name = registry.CAPABILITY_TO_SUBSYSTEM.get(capability)
    if not subsystem_name:
        logger.warning(
            "resolve_execution: unknown capability %r — denying (fail-closed)",
            capability)
        return ExecutionResult(
            allowed=False,
            reason="Unknown capability — denied (fail-closed)",
            trace=ExecutionTrace(
                capability=capability, checked_scopes=[], matched_scope=None,
                denied_by="unknown_capability", final_result=False))

    explicit_override = _check_capability_override(ctx.guild_id, capability)
    if explicit_override is not None:
        allowed = explicit_override
        denied_by = "capability_override" if not allowed else None
        return ExecutionResult(
            allowed=allowed, reason=denied_by, resolved_scope="override",
            matched_capability=capability if allowed else None,
            trace=ExecutionTrace(
                capability=capability, checked_scopes=[],
                matched_scope="override", denied_by=denied_by,
                final_result=allowed))

    if not check_visibility:
        logger.info(
            "resolve_execution: internal bypass capability=%r subsystem=%r "
            "guild=%d", capability, subsystem_name, ctx.guild_id)
        await _audit_internal_bypass(ctx, capability, subsystem_name)
        return ExecutionResult(
            allowed=True,
            reason="Internal/AI-triggered — visibility gate skipped",
            resolved_scope=None, matched_capability=capability,
            trace=ExecutionTrace(
                capability=capability, checked_scopes=[], matched_scope=None,
                denied_by=None, final_result=True))

    vis = await resolve_visibility(ctx)
    allowed = subsystem_name in vis.visible_subsystems
    trace_obj = vis.traces.get(subsystem_name)
    denied_by = (trace_obj.final_state.value
                 if trace_obj and not allowed else None)
    return ExecutionResult(
        allowed=allowed, reason=denied_by,
        resolved_scope=(trace_obj.matched_scope.value
                        if trace_obj and trace_obj.matched_scope else None),
        matched_capability=capability if allowed else None,
        trace=ExecutionTrace(
            capability=capability,
            checked_scopes=trace_obj.checked_scopes if trace_obj else [],
            matched_scope=(trace_obj.matched_scope.value
                           if trace_obj and trace_obj.matched_scope else None),
            denied_by=denied_by, final_result=allowed))
