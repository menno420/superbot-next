"""The version-extended `StoreSpec` + versioned-state policy grammar (leaf).

Built verbatim to frozen L0 spec 09 (scheduler-state) §3.2. Authored at S5
because spec 08 §5.1 declares the `event_outbox` StoreSpec against THIS
grammar; the load-time primitives (`sb/kernel/versioning/resolve.py`,
`compile.py` — the `version_policy_declared` fence) land at S10 with the
due-queue leg, per the build order.

Base 6 fields = design-spec §2.8 StoreSpec, unchanged. The NEW payload-version
fields close T2-7 (the "cog decides resume/refund+clear" class): a
value-bearing store can never declare DROP (`value_bearing_store_cannot_drop`),
and REJECT_AND_PRESERVE + bears_value mandates a `compensation_ref` whose
ordered DB legs refund THEN retire atomically (spec 09 §3.3 row 3).

Stdlib-only leaf apart from sb.spec.refs (ref dataclasses) + sb.spec.roles.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Mapping

from sb.spec.refs import EngineRef, HandlerRef, ProviderRef, WorkflowRef
from sb.spec.roles import register_field_roles


class CheckpointClass(str, enum.Enum):
    """design-spec §5.1 verbatim."""

    LEDGER = "ledger"
    AGGREGATE = "aggregate"
    SESSION = "session"


class VersionPolicy(str, enum.Enum):
    UPCAST = "upcast"                            # run upcast_ref chain, then RESUME
    REJECT_AND_PRESERVE = "reject_and_preserve"  # no resume; compensate first iff value-bearing
    DROP = "drop"                                # clear the row (ONLY legal when bears_value=False)


class ForwardMapKind(str, enum.Enum):
    """S14 (spec 13 §2.4b) — how the CUT-2 forward importer maps this store
    OLD→NEW; the invertibility input of the `rollback_class` derivation.
    Grounded in existing signals, never a fresh judgment: NAME_STABLE = the
    §5.2 name-stable set; RENAME = a pure-bijection alias-map entry;
    COLLAPSE = session-state→checkpoint / merging map; NEW_ONLY = no
    old-schema source; DROP = a store_retirements.yml entry (SF-g)."""

    NAME_STABLE = "name_stable"   # invertible
    RENAME = "rename"             # invertible (pure column/table rename)
    COLLAPSE = "collapse"         # NOT invertible (merges/aggregates old rows)
    NEW_ONLY = "new_only"         # NOT invertible (no old-schema home)
    DROP = "drop"                 # NOT invertible (retired at migration)


INVERTIBLE_MAP_KINDS = (ForwardMapKind.NAME_STABLE, ForwardMapKind.RENAME)


class RollbackClass(str, enum.Enum):
    """S14 (spec 13 §2.4b) — the disposition of this store's
    post-`cutover_flip_ts` writes on rollback. DERIVED by
    `derive_rollback_class`, never hand-set — except the owner's
    REPLAY_INTENT narrowing override (`StoreSpec.replay_intent`)."""

    REVERSE_IMPORTABLE = "reverse_importable"  # invertible AND bears_value
    DECLARED_LOSS = "declared_loss"            # non-invertible OR not value-bearing
    REPLAY_INTENT = "replay_intent"            # owner narrowing of a REVERSE_IMPORTABLE store


class DataClass(str, enum.Enum):
    """S11 (spec 10 §2.A class 12) — the PII discriminator
    `check_data_lifecycle` keys on."""

    NONE = "none"              # no personal data (config, presets, non-personal counters)
    MEMBER_ID = "member_id"    # keyed on a Discord numeric id only (pseudonymous)
    MEMBER_PII = "member_pii"  # display name / username / message text / avatar


class CacheScope(str, enum.Enum):
    """S11 — a member-data cache MUST be GUILD-scoped (closes the B#34/X-3
    cross-guild cache bleed by construction)."""

    GUILD = "guild"
    GLOBAL = "global"


@dataclass(frozen=True)
class VersionedRow:
    """The NORMALIZED row shape `resolve_versioned_load` reads (S10) —
    heterogeneous stores register an `active_rows_ref` reader that maps
    their rows to this one shape (spec 09 §3.2)."""

    row_id: str                   # the store's PK value (stringified)
    version: int                  # the payload's persisted schema version
    payload: Mapping[str, Any]    # the versioned payload blob (JSONB -> dict)
    guild_id: int | None          # for the compensation authority + the once() key


@dataclass(frozen=True)
class StoreSpec:
    """EXTENDS design-spec §2.8 — the base 6 fields are unchanged (spec 09 §3.2)."""

    table: str                                        # [S]
    sole_writer: HandlerRef | EngineRef               # [S] INV-style sole-writer
    retention: str                                    # [S]
    checkpoint_class: CheckpointClass                 # [S]
    invariant_tag: str                                # [S] INV-F/G/K — drives the fences
    reader_domains: tuple[str, ...] = ()              # [S] read-only projections, never writers
    # ---- NEW payload-version fields (T2-7) ----
    payload_version: int = 1                          # [S] CURRENT schema version of the payload
    bears_value: bool = False                         # [S] True => money/audit-bearing payload
    version_policy: VersionPolicy = VersionPolicy.REJECT_AND_PRESERVE  # [S] non-destructive default
    active_rows_ref: ProviderRef | None = None        # [S] REQUIRED iff swept by run_recovery
    retire_ref: WorkflowRef | None = None             # [S] REQUIRED iff DROP or (REJECT & not bears_value)
    upcast_ref: WorkflowRef | None = None             # [S] REQUIRED iff UPCAST
    compensation_ref: WorkflowRef | None = None       # [S] REQUIRED iff REJECT & bears_value
    # ---- S11 privacy/retention/erasure fields (spec 10 §2.A class 12;
    #      the §2.8 field set is ADDITIVE, not closed — spec 10 §8.2) ----
    data_class: DataClass = DataClass.NONE            # [S]
    erasure_ref: WorkflowRef | None = None            # [S] REQUIRED iff data_class != NONE (AUDITED K7 hook)
    is_cache: bool = False                            # [S] marks a cache store (drives cache_scope)
    cache_scope: CacheScope | None = None             # [S] REQUIRED iff is_cache
    # ---- S14 rollback-disposition fields (spec 13 §2.4b; additive) ----
    forward_map_kind: ForwardMapKind | None = None    # [S] OLD→NEW mapping kind; None only if
    #     derivable (SESSION ⇒ COLLAPSE / a store_retirements.yml DROP) — else fence-red
    replay_intent: bool = False                       # [O] OWNER override: narrows an otherwise
    #     REVERSE_IMPORTABLE store to a human-reviewed replay list (never widens)


register_field_roles(
    "StoreSpec",
    table="S", sole_writer="S", retention="S", checkpoint_class="S",
    invariant_tag="S", reader_domains="S", payload_version="S", bears_value="S",
    version_policy="S", active_rows_ref="S", retire_ref="S", upcast_ref="S",
    compensation_ref="S", data_class="S", erasure_ref="S", is_cache="S",
    cache_scope="S", forward_map_kind="S", replay_intent="O",
)


# --- the rollback_class derivation (S14, spec 13 §2.4b — mechanical) -------------

class RollbackUnresolved(ValueError):
    """SEMANTIC_VIOLATION("rollback_class_unresolved") — the store declares
    no forward_map_kind and none is derivable (spec 13 §2.5 fence)."""


def resolve_forward_map_kind(spec: StoreSpec, *,
                             retired_tables: frozenset[str] = frozenset(),
                             ) -> ForwardMapKind | None:
    """Declared kind, else the two derivable short-circuits: SESSION ⇒
    COLLAPSE (§5.1 session-state→checkpoints) and a store_retirements.yml
    entry ⇒ DROP (SF-g). NO silent absence-of-source ⇒ NEW_ONLY fallback:
    until the CUT-2 forward-importer alias map exists, a store must DECLARE
    NEW_ONLY — a silent default would misclass a renamed value store as
    unrecoverable (D-0017)."""
    if spec.checkpoint_class is CheckpointClass.SESSION:
        return ForwardMapKind.COLLAPSE  # the collapse short-circuit ALWAYS wins
    if spec.forward_map_kind is not None:
        return spec.forward_map_kind
    if spec.table in retired_tables:
        return ForwardMapKind.DROP
    return None


def derive_rollback_class(spec: StoreSpec, *,
                          retired_tables: frozenset[str] = frozenset(),
                          ) -> RollbackClass:
    """The §2.4b derivation table. Raises RollbackUnresolved when the store
    cannot resolve — the `rollback_class_resolved` fence input."""
    kind = resolve_forward_map_kind(spec, retired_tables=retired_tables)
    if kind is None:
        raise RollbackUnresolved(
            f"{spec.table}: rollback_class_unresolved — declare "
            f"forward_map_kind (or retire via store_retirements.yml)")
    if kind not in INVERTIBLE_MAP_KINDS:
        return RollbackClass.DECLARED_LOSS   # structurally cannot round-trip (T-5)
    if not spec.bears_value:
        return RollbackClass.DECLARED_LOSS   # declared-loss by POSTURE (Q3-B), not capability
    if spec.replay_intent:
        return RollbackClass.REPLAY_INTENT   # the ONE hand-set narrowing
    return RollbackClass.REVERSE_IMPORTABLE


# --- the store registry (S11) ---------------------------------------------------
# The machine-walkable StoreSpec inventory the class-12 erasure executor and
# check_data_lifecycle enumerate (spec 10 §2.A: "no member-data store exists
# OUTSIDE this walk"). Kernel store constants register at module import; the
# port bands' manifest `stores` facets register at compile.

_STORE_REGISTRY: dict[str, StoreSpec] = {}


def register_store(spec: StoreSpec) -> StoreSpec:
    prior = _STORE_REGISTRY.get(spec.table)
    if prior is not None and prior != spec:
        raise ValueError(f"store {spec.table!r} registered twice with differing specs")
    _STORE_REGISTRY[spec.table] = spec
    return spec


def registered_stores() -> tuple[StoreSpec, ...]:
    return tuple(_STORE_REGISTRY[k] for k in sorted(_STORE_REGISTRY))


def clear_store_registry_for_tests() -> None:
    _STORE_REGISTRY.clear()
