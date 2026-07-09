"""GOVERNANCE subsystem manifest (band 5) — the platform-control engine
(disbot/governance/ @7f7628e1): subsystem visibility scope-chain, cleanup
policies, the capability revoke overlay, templates, and the governance
audit trail. NO commands/panels of its own — the shipped write surfaces
live in the channel/setup panels (band 2 declared them); this manifest
owns the stores, the compat-frozen event names, and the settings slice
(sb/domain/settings/keys.py `governance` module: governance_version +
the two tier-grant role pointers).

Importing this manifest FILLS the S7/S9 kernel waiting ports
(capability-override reader, R-16 role-binding reader, K8 visibility
reader) via service.install_authority_ports().
"""

from __future__ import annotations

from sb.domain.governance.ops import (
    EVT_CACHE_INVALIDATED,
    EVT_CLEANUP_CHANGED,
    EVT_EXECUTION_ALLOWED,
    EVT_EXECUTION_DENIED,
    EVT_VISIBILITY_CHANGED,
    register_ops,
)
from sb.domain.governance.service import install_authority_ports
from sb.domain.governance.store import (
    CAPABILITY_OVERRIDES_STORE,
    CLEANUP_POLICIES_STORE,
    GOVERNANCE_AUDIT_STORE,
    GOVERNANCE_TEMPLATES_STORE,
    SUBSYSTEM_VISIBILITY_STORE,
)
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.settings import SettingSpec

_MUTATION_FIELDS = (
    FieldSpec("guild_id", "int"),
    FieldSpec("scope_type", "str"),
    FieldSpec("scope_id", "int"),
    FieldSpec("mutation_id", "str"),
    FieldSpec("occurred_at", "str"),
    FieldSpec("actor_id", "int"),
)

VISIBILITY_CHANGED_EVENT = EventSpec(
    name=EVT_VISIBILITY_CHANGED,
    payload_schema=_MUTATION_FIELDS + (
        FieldSpec("subsystem", "str"),
        FieldSpec("enabled", "bool", required=False),
    ),
    owner_subsystem="governance",
    delivery=DeliveryClass.BEST_EFFORT,
)

CLEANUP_CHANGED_EVENT = EventSpec(
    name=EVT_CLEANUP_CHANGED,
    payload_schema=_MUTATION_FIELDS,
    owner_subsystem="governance",
    delivery=DeliveryClass.BEST_EFFORT,
)

CACHE_INVALIDATED_EVENT = EventSpec(
    name=EVT_CACHE_INVALIDATED,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("mutation_id", "str"),
        FieldSpec("occurred_at", "str"),
    ),
    owner_subsystem="governance",
    delivery=DeliveryClass.BEST_EFFORT,
)

_EXECUTION_FIELDS = (
    FieldSpec("guild_id", "int"),
    FieldSpec("capability", "str"),
    FieldSpec("subsystem", "str"),
)

EXECUTION_DENIED_EVENT = EventSpec(
    name=EVT_EXECUTION_DENIED,
    payload_schema=_EXECUTION_FIELDS + (
        FieldSpec("denied_by", "str", required=False),),
    owner_subsystem="governance",
    delivery=DeliveryClass.BEST_EFFORT,
)

EXECUTION_ALLOWED_EVENT = EventSpec(
    name=EVT_EXECUTION_ALLOWED,
    payload_schema=_EXECUTION_FIELDS + (
        FieldSpec("bypass", "bool", required=False),
        FieldSpec("denied_by", "str", required=False),
    ),
    owner_subsystem="governance",
    delivery=DeliveryClass.BEST_EFFORT,
)

_EVENTS = (VISIBILITY_CHANGED_EVENT, CLEANUP_CHANGED_EVENT,
           CACHE_INVALIDATED_EVENT, EXECUTION_DENIED_EVENT,
           EXECUTION_ALLOWED_EVENT)

_SETTINGS = (
    SettingSpec(name="governance_version", value_type=int, default=0,
                settings_key="governance_version",
                hint="Internal registry-version stamp — the upgrade hook "
                     "prunes orphan overrides when the registry moves. "
                     "Managed by the platform, not operator-facing."),
    SettingSpec(name="trusted_tier_role_id", value_type=int, default=0,
                settings_key="trusted_tier_role_id",
                hint="Role granting the `trusted` visibility tier "
                     "(ISSUE-015). Holders see trusted-tier surfaces "
                     "without any Discord permission. 0 = unset."),
    SettingSpec(name="moderator_tier_role_id", value_type=int, default=0,
                settings_key="moderator_tier_role_id",
                hint="Role granting the `moderator` tier (ADR-008 — "
                     "capability-native moderation authority without the "
                     "matching Discord permissions). 0 = unset."),
)

MANIFEST = SubsystemManifest(
    key="governance",
    version=1,
    commands=(),
    panels=(),
    settings=_SETTINGS,
    stores=(SUBSYSTEM_VISIBILITY_STORE, CLEANUP_POLICIES_STORE,
            GOVERNANCE_AUDIT_STORE, CAPABILITY_OVERRIDES_STORE,
            GOVERNANCE_TEMPLATES_STORE),
    events=_EVENTS,
    capabilities=(),
)

register_ops()
register_event_specs(_EVENTS)
install_authority_ports()


def _ensure_refs() -> None:
    from sb.domain.governance import ops as _ops
    from sb.domain.governance import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    register_ops()
    register_event_specs(_EVENTS)
    install_authority_ports()


ENSURE_REFS = _ensure_refs
