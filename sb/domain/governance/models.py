"""Governance models (band 5) — the shipped dataclasses/enums/scope
constants ported HEADLESSLY from disbot/governance/models.py +
scopes.py + utils/governance_exceptions.py @7f7628e1.

Deviation from shipped (ledgered, D-0039): ``GovernanceContext`` carries
no ``discord.Member`` — the compiled architecture computes tier/role_ids
at the adapter (RC-12 ActorRef.member_tier + A-12 role_ids) and passes
them in. The shipped ``member_tier`` declared-tier read path (Q-0045
option b) survives verbatim: when set it is preferred over everything,
so audience simulation (Help Preview) still works without a live member.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "SCOPE_PARENT",
    "SCOPE_PRIORITY",
    "VALID_CLEANUP_SCOPE_TYPES",
    "VALID_VISIBILITY_SCOPE_TYPES",
    "CapabilityNamespaceError",
    "CircularDependencyError",
    "CleanupPolicy",
    "ExecutionResult",
    "ExecutionTrace",
    "GovernanceContext",
    "GovernanceDiff",
    "GovernanceError",
    "GovernanceHealthReport",
    "GovernanceScope",
    "GovernanceSnapshot",
    "GovernanceUpgradeError",
    "PolicySource",
    "ResolutionTrace",
    "SubsystemEffectiveState",
    "SubsystemState",
    "UnauthorizedGovernanceWriteError",
    "VisibilityResult",
]

# --- scope resolution constants (models.py verbatim) -------------------------

SCOPE_PRIORITY: list[str] = ["thread", "channel", "category", "guild"]
SCOPE_PARENT: dict[str, str | None] = {
    "thread": "channel",
    "channel": "category",
    "category": "guild",
    "guild": None,
}


class GovernanceScope(Enum):
    """Typed governance scope taxonomy (scopes.py verbatim — value strings
    match the historical governance scope strings / stored DB rows)."""

    GUILD = "guild"
    CATEGORY = "category"
    CHANNEL = "channel"
    THREAD = "thread"
    ROLE = "role"
    USER = "user"


LEGACY_SCOPE_TYPES: frozenset[str] = frozenset(s.value for s in GovernanceScope)

# RC-5: visibility accepts "thread"; cleanup does NOT (the shipped
# cleanup_policies non-thread CHECK constraint carries into 0016).
VALID_VISIBILITY_SCOPE_TYPES: frozenset[str] = frozenset(
    {"channel", "category", "guild", "thread"})
VALID_CLEANUP_SCOPE_TYPES: frozenset[str] = frozenset(
    {"channel", "category", "guild"})


# --- enums (models.py verbatim) ----------------------------------------------

class SubsystemState(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    INHERITED = "inherited"
    BLOCKED_DEPENDENCY = "blocked_dep"
    INTERNAL = "internal"
    EXPERIMENTAL_DISABLED = "exp_disabled"


class PolicySource(Enum):
    """Typed provenance for governance decisions (serialized to .value)."""

    REGISTRY_DEFAULT = "registry_default"
    INHERITED_DEFAULT = "inherited_default"
    FALLBACK_DEFAULT = "fallback_default"
    DEPENDENCY_BLOCK = "dependency_block"
    THREAD_OVERRIDE = "thread"
    CHANNEL_OVERRIDE = "channel"
    CATEGORY_OVERRIDE = "category"
    GUILD_OVERRIDE = "guild"
    ROLE_OVERRIDE = "role"


# --- exceptions (utils/governance_exceptions.py verbatim) --------------------

class GovernanceError(Exception):
    """Base class for all governance-layer errors."""


class RegistryValidationError(GovernanceError):
    """Registry integrity check failed during startup validation."""


class CircularDependencyError(RegistryValidationError):
    def __init__(self, node: str, neighbour: str) -> None:
        super().__init__(
            f"Circular dependency detected: '{node}' → '{neighbour}'")
        self.node = node
        self.neighbour = neighbour


class CapabilityNamespaceError(RegistryValidationError):
    """Capability does not follow {subsystem}.{resource}.{action}, or uses a
    reserved namespace prefix (_internal, system, governance)."""


class GovernanceUpgradeError(GovernanceError):
    """Governance schema version upgrade failed."""


class UnauthorizedGovernanceWriteError(GovernanceError):
    """Caller lacks the authority tier required to mutate governance state."""


# --- context + results --------------------------------------------------------

@dataclass
class GovernanceContext:
    """Context for governance resolution — HEADLESS (ids + declared facts).

    ``member_tier`` = the declared-tier read path (Q-0045 option b): the
    resolver prefers it verbatim (adapters set it from ActorRef; simulated
    callers set it for audience previews). ``user_id`` lets the resolver
    apply the platform-owner elevation; ``role_ids`` feeds the configured
    trusted/moderator role grants and role-fingerprinted cache keys.
    """

    guild_id: int
    channel_id: int | None = None
    category_id: int | None = None
    thread_id: int | None = None
    user_id: int | None = None
    role_ids: set[int] = field(default_factory=set)
    member_tier: str | None = None


@dataclass
class ResolutionTrace:
    subsystem: str
    checked_scopes: list[str]
    matched_scope: PolicySource | None
    dependency_blocks: list[str]
    final_state: SubsystemState
    request_id: str | None = None

    def to_dict(self) -> dict:
        d = {
            "subsystem": self.subsystem,
            "checked_scopes": sorted(self.checked_scopes),
            "matched_scope": self.matched_scope.value if self.matched_scope else None,
            "dependency_blocks": sorted(self.dependency_blocks),
            "final_state": self.final_state.value,
        }
        if self.request_id is not None:
            d["request_id"] = self.request_id
        return d


@dataclass
class VisibilityResult:
    visible_subsystems: set[str]
    member_tier: str
    resolved_from: dict[str, PolicySource]
    traces: dict[str, ResolutionTrace]

    def to_dict(self) -> dict:
        return {
            "visible_subsystems": sorted(self.visible_subsystems),
            "member_tier": self.member_tier,
            "resolved_from": {
                k: v.value for k, v in sorted(self.resolved_from.items())},
            "traces": {k: v.to_dict() for k, v in sorted(self.traces.items())},
        }


@dataclass
class ExecutionTrace:
    capability: str
    checked_scopes: list[str]
    matched_scope: str | None
    denied_by: str | None
    final_result: bool

    def to_dict(self) -> dict:
        return {
            "capability": self.capability,
            "checked_scopes": sorted(self.checked_scopes),
            "matched_scope": self.matched_scope,
            "denied_by": self.denied_by,
            "final_result": self.final_result,
        }


@dataclass
class ExecutionResult:
    allowed: bool
    reason: str | None = None
    resolved_scope: str | None = None
    matched_capability: str | None = None
    trace: ExecutionTrace | None = None


@dataclass
class CleanupPolicy:
    delete_message: bool
    delete_after_seconds: int
    send_feedback: bool
    resolved_from: PolicySource

    def to_dict(self) -> dict:
        return {
            "delete_message": self.delete_message,
            "delete_after_seconds": self.delete_after_seconds,
            "send_feedback": self.send_feedback,
            "resolved_from": self.resolved_from.value,
        }


@dataclass
class SubsystemEffectiveState:
    """Complete resolved state for one subsystem in one context.
    Powers /why, per-subsystem diagnostics, AI explanations."""

    name: str
    state: SubsystemState
    visibility_source: PolicySource
    execution_allowed: bool
    execution_source: PolicySource
    dependency_blocks: list[str]
    cleanup_policy: CleanupPolicy
    trace: ResolutionTrace

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "visibility_source": self.visibility_source.value,
            "execution_allowed": self.execution_allowed,
            "execution_source": self.execution_source.value,
            "dependency_blocks": sorted(self.dependency_blocks),
            "cleanup_policy": self.cleanup_policy.to_dict(),
            "trace": self.trace.to_dict(),
        }


@dataclass
class GovernanceHealthReport:
    orphan_overrides: list[dict]
    stale_version_guilds: list[int]
    invalid_cleanup_configs: list[dict]
    summary: str


@dataclass
class GovernanceSnapshot:
    """Complete governance state for a context (dashboards, /why, AI)."""

    visible_subsystems: set[str]
    denied_subsystems: set[str]
    dependency_blocks: dict[str, list[str]]
    cleanup_policy: CleanupPolicy
    member_tier: str
    scope_provenance: dict[str, PolicySource]
    capability_map: dict[str, bool]
    registry_version: int
    registry_schema_version: int

    def to_dict(self) -> dict:
        return {
            "visible_subsystems": sorted(self.visible_subsystems),
            "denied_subsystems": sorted(self.denied_subsystems),
            "dependency_blocks": {
                k: sorted(v) for k, v in sorted(self.dependency_blocks.items())},
            "cleanup_policy": self.cleanup_policy.to_dict(),
            "member_tier": self.member_tier,
            "scope_provenance": {
                k: v.value for k, v in sorted(self.scope_provenance.items())},
            "capability_map": {k: v for k, v in sorted(self.capability_map.items())},
            "registry_version": self.registry_version,
            "registry_schema_version": self.registry_schema_version,
        }


@dataclass
class GovernanceDiff:
    """Difference between two GovernanceSnapshots."""

    added_visible: set[str]
    removed_visible: set[str]
    changed_sources: dict[str, tuple[str, str]]
    capability_changes: dict[str, tuple[bool, bool]]
    cleanup_changed: bool

    @property
    def is_empty(self) -> bool:
        return (
            not self.added_visible
            and not self.removed_visible
            and not self.changed_sources
            and not self.capability_changes
            and not self.cleanup_changed
        )

    def to_dict(self) -> dict:
        return {
            "added_visible": sorted(self.added_visible),
            "removed_visible": sorted(self.removed_visible),
            "changed_sources": {
                k: list(v) for k, v in sorted(self.changed_sources.items())},
            "capability_changes": {
                k: list(v) for k, v in sorted(self.capability_changes.items())},
            "cleanup_changed": self.cleanup_changed,
        }
