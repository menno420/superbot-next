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


register_field_roles(
    "StoreSpec",
    table="S", sole_writer="S", retention="S", checkpoint_class="S",
    invariant_tag="S", reader_domains="S", payload_version="S", bears_value="S",
    version_policy="S", active_rows_ref="S", retire_ref="S", upcast_ref="S",
    compensation_ref="S",
)
