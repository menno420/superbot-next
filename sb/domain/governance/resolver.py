"""Governance scope-chain traversal + visibility resolution (band 5) —
disbot/governance/resolver.py + dependency.py ported headlessly.

Tier resolution deviations from shipped (ledgered, D-0039):

* the base tier arrives ON the context (adapters compute
  ``ActorRef.member_tier`` fresh per interaction — RC-12); the shipped
  declared-tier read path (Q-0045 option b) is IDENTICAL because in the
  compiled architecture every caller is a declared-tier caller;
* the platform-owner elevation reads ``sb.kernel.authority.owner``
  (config.is_platform_owner's compiled home);
* the configured trusted/moderator role grants (ISSUE-015 / ADR-008)
  read the governance settings slice through the K7 settings resolve
  seam — a failed read degrades to no-grant (fail-toward-lower-tier,
  shipped verbatim).
"""

from __future__ import annotations

import logging

from sb.domain.governance import cache as gcache
from sb.domain.governance import registry, store
from sb.domain.governance.models import (
    SCOPE_PARENT,
    GovernanceContext,
    PolicySource,
    ResolutionTrace,
    SubsystemState,
    VisibilityResult,
)
from sb.spec.authority import TIERS, is_tier_sufficient

logger = logging.getLogger("sb.domain.governance")

__all__ = [
    "get_visible_subsystems",
    "resolve_member_tier",
    "resolve_visibility",
]

_SCOPE_TO_SOURCE: dict[str, PolicySource] = {
    "thread": PolicySource.THREAD_OVERRIDE,
    "channel": PolicySource.CHANNEL_OVERRIDE,
    "category": PolicySource.CATEGORY_OVERRIDE,
    "guild": PolicySource.GUILD_OVERRIDE,
    "role": PolicySource.ROLE_OVERRIDE,
}


def build_scope_chain(ctx: GovernanceContext) -> list[tuple[str, int]]:
    """Ordered most-specific -> least-specific scope list; the ONLY place
    that knows the traversal order (shipped verbatim)."""
    scope_id_map: dict[str, int | None] = {
        "thread": ctx.thread_id,
        "channel": ctx.channel_id,
        "category": ctx.category_id,
        "guild": ctx.guild_id,
    }
    chain: list[tuple[str, int]] = []
    scope: str | None = "thread"
    while scope is not None:
        sid = scope_id_map.get(scope)
        if sid is not None:
            chain.append((scope, sid))
        scope = SCOPE_PARENT.get(scope)
    return chain


def _resolve_single_subsystem(
    subsystem: str,
    chain: list[tuple[str, int]],
    scope_data: dict[tuple[str, int], dict[str, bool | None]],
) -> tuple[bool | None, PolicySource, list[str]]:
    """Walk the scope chain for one subsystem (shipped verbatim —
    explicit NULL = inherit from the next scope)."""
    checked: list[str] = []
    for scope_type, scope_id in chain:
        scope_map = scope_data.get((scope_type, scope_id), {})
        checked.append(scope_type)
        if subsystem in scope_map:
            val = scope_map[subsystem]
            if val is None:
                continue
            return val, _SCOPE_TO_SOURCE[scope_type], checked
    return None, PolicySource.INHERITED_DEFAULT, checked


# --- tier resolution ------------------------------------------------------------

async def _configured_role_grants_tier(
    guild_id: int, setting_name: str, role_ids: set[int],
) -> bool:
    """True when the configured role (governance settings slice) is one
    the member holds. A failed read NEVER grants (shipped: a configured
    role only ever ADDS standing)."""
    if not role_ids:
        return False
    try:
        from sb.kernel.settings import resolve

        value = await resolve(guild_id, "governance", setting_name)
    except Exception:  # noqa: BLE001 — a failed read must never grant a tier
        return False
    if value in (None, "", 0, "0"):
        return False
    try:
        role_id = int(value)
    except (TypeError, ValueError):
        return False
    return role_id in role_ids


async def resolve_member_tier(ctx: GovernanceContext) -> str:
    """The member's effective visibility tier (shipped _resolve_member_tier).

    Order: declared tier (verbatim, unknown value ignored with warning) →
    platform-owner elevation → configured moderator/trusted role grants
    (raise-only; higher wins; never demote).
    """
    if ctx.member_tier is not None:
        if ctx.member_tier in TIERS:
            return ctx.member_tier
        logger.warning(
            "governance: ignoring unknown declared member_tier %r (guild %s)",
            ctx.member_tier, ctx.guild_id)

    if ctx.user_id is None:
        return "user"

    try:
        from sb.kernel.authority.owner import is_platform_owner

        if is_platform_owner(int(ctx.user_id)):
            return "owner"
    except Exception:  # noqa: BLE001 — owner elevation is raise-only
        pass

    tier = "user"
    if ctx.role_ids:
        if not is_tier_sufficient(tier, "moderator") and \
                await _configured_role_grants_tier(
                    ctx.guild_id, "moderator_tier_role_id", ctx.role_ids):
            tier = "moderator"
        if not is_tier_sufficient(tier, "trusted") and \
                await _configured_role_grants_tier(
                    ctx.guild_id, "trusted_tier_role_id", ctx.role_ids):
            tier = "trusted"
    return tier


# --- dependency propagation (dependency.py verbatim) ------------------------------

def apply_dependency_rules(
    states: dict[str, SubsystemState],
    traces: dict[str, ResolutionTrace],
    resolved_from: dict[str, PolicySource],
) -> None:
    """Propagate hard dependency blocking in topological order (soft
    dependencies are NOT propagated — UI hint only, shipped)."""
    for subsystem in registry.dependency_order():
        if subsystem not in states:
            continue
        meta = registry.SUBSYSTEM_META.get(subsystem)
        if not meta:
            continue
        blocking = [
            dep for dep in meta["dependencies"]
            if states.get(dep) in (SubsystemState.DISABLED,
                                   SubsystemState.BLOCKED_DEPENDENCY)
        ]
        if blocking and states[subsystem] == SubsystemState.ENABLED:
            states[subsystem] = SubsystemState.BLOCKED_DEPENDENCY
            resolved_from[subsystem] = PolicySource.DEPENDENCY_BLOCK
            if subsystem in traces:
                traces[subsystem].dependency_blocks.extend(blocking)
                traces[subsystem].final_state = SubsystemState.BLOCKED_DEPENDENCY
                traces[subsystem].matched_scope = PolicySource.DEPENDENCY_BLOCK


# --- visibility resolution ---------------------------------------------------------

def _static_trace(name: str, state: SubsystemState) -> ResolutionTrace:
    return ResolutionTrace(
        subsystem=name, checked_scopes=[],
        matched_scope=PolicySource.REGISTRY_DEFAULT,
        dependency_blocks=[], final_state=state)


async def _resolve_visibility_overrides(
    ctx: GovernanceContext, tier_accessible: set[str],
) -> tuple[dict[str, SubsystemState], dict[str, ResolutionTrace],
           dict[str, PolicySource]]:
    chain = build_scope_chain(ctx)
    scope_data = await store.fetch_visibility_for_chain(ctx.guild_id, chain)

    states: dict[str, SubsystemState] = {}
    traces: dict[str, ResolutionTrace] = {}
    resolved_from: dict[str, PolicySource] = {}

    for name in registry.SUBSYSTEM_META:
        if name not in tier_accessible:
            states[name] = SubsystemState.DISABLED
            traces[name] = _static_trace(name, SubsystemState.DISABLED)
            resolved_from[name] = PolicySource.REGISTRY_DEFAULT
            continue
        if name in gcache._FAILED_SUBSYSTEMS:
            states[name] = SubsystemState.INTERNAL
            traces[name] = _static_trace(name, SubsystemState.INTERNAL)
            resolved_from[name] = PolicySource.REGISTRY_DEFAULT
            continue

        override_val, source, checked = _resolve_single_subsystem(
            name, chain, scope_data)
        if override_val is False:
            final = SubsystemState.DISABLED
        elif override_val is True:
            final = SubsystemState.ENABLED
        else:
            final = SubsystemState.ENABLED
            source = PolicySource.REGISTRY_DEFAULT

        states[name] = final
        traces[name] = ResolutionTrace(
            subsystem=name, checked_scopes=checked,
            matched_scope=source if override_val is not None else None,
            dependency_blocks=[], final_state=final)
        resolved_from[name] = source

    return states, traces, resolved_from


async def resolve_visibility(ctx: GovernanceContext) -> VisibilityResult:
    """Which subsystems are visible to this member in this context —
    thread > channel > category > guild > registry default; dependency
    rules after scope resolution; results version/tier/thread cached."""
    tier = await resolve_member_tier(ctx)

    role_ids = frozenset(ctx.role_ids) if ctx.role_ids else frozenset()
    cache_key = gcache._cache_key(
        ctx.guild_id, ctx.channel_id, tier, role_ids, thread_id=ctx.thread_id)

    async with gcache._CACHE_LOCK:
        cached = gcache._cache_get(cache_key)
        if cached is not None:
            return cached

    tier_accessible = set(registry.get_subsystems_for_tier(tier))
    states, traces, resolved_from = await _resolve_visibility_overrides(
        ctx, tier_accessible)
    apply_dependency_rules(states, traces, resolved_from)

    visible = {name for name, state in states.items()
               if state == SubsystemState.ENABLED}
    result = VisibilityResult(
        visible_subsystems=visible, member_tier=tier,
        resolved_from=resolved_from, traces=traces)

    async with gcache._CACHE_LOCK:
        gcache._cache_set(cache_key, result)
    return result


async def get_visible_subsystems(ctx: GovernanceContext) -> set[str]:
    result = await resolve_visibility(ctx)
    return result.visible_subsystems
