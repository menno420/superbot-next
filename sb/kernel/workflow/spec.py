"""The K7 declared shapes (frozen L0 spec 07 §3.1). Every field [S] unless
tagged. `DeliveryClass` is IMPORTED from `sb.spec.events` (canonical home,
RC-17 — never a local copy) and `ConfirmationSpec` from `sb.spec.confirmation`
(a K1/K2 manifest leaf, not a K7 type).

These types are registered into the `WorkflowRegistry` (not carried on
`SubsystemManifest` facets), so the K2 pipeline sees them only through the
`WorkflowRef` strings on routable specs; the K7 fences (`compile.py`) run at
registration + CI over the registry.

Q-D24 (ships-until-ruled option A): `session_transition: bool` names the
multi-actor session-concurrency posture — a session-transition op MUST declare
`IdempotencyPosture.NATURAL_KEY` (FOR UPDATE / state_version compare-and-swap
row-consumption), fence-enforced.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sb.spec.confirmation import ConfirmationSpec
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, resolve
from sb.spec.roles import register_field_roles

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.workflow.context import WorkflowContext

__all__ = [
    "CompoundOpSpec",
    "DedupKeySpec",
    "EmptyResultSpec",
    "EventEmitSpec",
    "IdempotencyPosture",
    "LegAuditSpec",
    "LegKind",
    "LegSpec",
    "WorkflowLane",
]


class LegKind(enum.Enum):
    DB = "db"          # inside the single db.transaction() conn; atomic rollback
    EFFECT = "effect"  # AFTER commit; external/Discord/event; never rolled back


class WorkflowLane(enum.Enum):
    """The WorkflowResult.lane tag (design-spec §2.7)."""

    SCALAR = "scalar"
    BINDING = "binding"
    RESOURCE = "resource"
    GOVERNANCE = "governance"
    LIFECYCLE = "lifecycle"
    DOMAIN = "domain"


class IdempotencyPosture(enum.Enum):
    """T2-21 — the MANDATED per-op declaration (spec 07 §3.1)."""

    DURABLE_ONCE = "durable_once"      # once()+record_outcome (K3); REQUIRES dedup_key
    NATURAL_KEY = "natural_key"        # intrinsically once (ON CONFLICT / FOR UPDATE)
    SINGLE_FLIGHT = "single_flight"    # in-process lock; REQUIRES single_flight_scope
    NONE_JUSTIFIED = "none"            # REQUIRES idempotency_justification


@dataclass(frozen=True)
class DedupKeySpec:
    """EITHER a registered token handler(ctx)->str (WorkflowRef form) OR a
    tuple of ctx.params names joined by ":" (natural-key form, e.g.
    ("user_id", "interaction_id") — the actor-encoded shape, spec 07 §6)."""

    source: "WorkflowRef | tuple[str, ...]"    # [S]

    def render(self, ctx: "WorkflowContext") -> str:
        if isinstance(self.source, WorkflowRef):
            return str(resolve(self.source)(ctx))
        # KeyError iff a named param is absent — the posture fence asserts
        # every named token is a declared op input (spec 07 §3.6).
        return ":".join(str(ctx.params[name]) for name in self.source)


@dataclass(frozen=True)
class LegAuditSpec:
    """OPTIONAL per-leg enrichment folded into the ONE central row — never a
    second row (spec 07 §3.4)."""

    audit_target_kind: str                     # [S] "balance" | "coop" | "inventory" | ...
    verb: str                                  # [S] leg verb (detail only)


@dataclass(frozen=True)
class EventEmitSpec:
    event: str                                 # [S] frozen legacy event name
    payload_builder: WorkflowRef               # [S] handler(ctx, result) -> dict
    delivery: DeliveryClass                    # [S] the IMPORTED enum (RC-17)


@dataclass(frozen=True)
class EmptyResultSpec:
    """The "nothing to do" no-op — predicate evaluated BEFORE the txn opens
    (farm-collect: settled.eggs <= 0)."""

    predicate: WorkflowRef                     # [S] handler(ctx) -> bool
    user_message: str                          # [S] the no-op copy


@dataclass(frozen=True)
class LegSpec:
    leg_id: str                                # [S] unique within the op
    kind: LegKind                              # [S]
    handler: WorkflowRef                       # [S] registered LegHandler
    reversibility: str                         # [S] REVERSIBLE|COMPENSATABLE|IRREVERSIBLE (per-leg author declaration)
    compensator: WorkflowRef | None = None     # [S] REQUIRED iff kind==EFFECT and COMPENSATABLE
    audit: LegAuditSpec | None = None          # [S]
    optional: bool = False                     # [S] failed optional leg => PARTIAL, never BLOCKED


@dataclass(frozen=True)
class CompoundOpSpec:
    # --- required (no default) ---
    op_key: str                                # [S] namespace-reserved workflow key; the once() namespace
    domain: str                                # [S] audit subsystem
    lane: WorkflowLane                         # [S]
    authority_ref: str                         # [S] resolved as leg-0 (K6)
    legs: tuple[LegSpec, ...]                  # [S] ordered; DB legs in-txn first, EFFECT after commit
    idempotency: IdempotencyPosture            # [S] T2-21
    dedup_key: DedupKeySpec | None             # [S] REQUIRED iff DURABLE_ONCE (else None)
    audit_verb: str                            # [S] mutation_type for the ONE central row
    # --- optional / conditionally required (fence-enforced, spec 07 §3.6) ---
    idempotency_justification: str | None = None  # [S] REQUIRED iff NONE_JUSTIFIED; else None
    single_flight_scope: str | None = None     # [S] REQUIRED iff SINGLE_FLIGHT; the lock key
    confirmation: ConfirmationSpec | None = None   # [S] presence-keyed backstop (§3.3 step 2)
    emits: tuple[EventEmitSpec, ...] = ()      # [S] post-commit / in-txn events
    empty_result: EmptyResultSpec | None = None    # [S]
    session_transition: bool = False           # [S] Q-D24: multi-actor session transition => NATURAL_KEY (fence)
    reversibility: str = ""                    # [derived — NOT [S]] max(leg reversibilities); the fence computes it; author never sets it


# Registered self-documenting (P5 discipline). These types live in the
# WorkflowRegistry, NOT on manifest facets — so they enter the committed
# snapshot's field_roles only if a spec module imports this one (none does);
# the A-2 ledger tracks sb.spec grammar (ConfirmationSpec's entries live
# there). `CompoundOpSpec.reversibility` is engine-DERIVED — tagged O.
register_field_roles(
    "DedupKeySpec", source="S",
)
register_field_roles(
    "LegAuditSpec", audit_target_kind="S", verb="S",
)
register_field_roles(
    "EventEmitSpec", event="S", payload_builder="S", delivery="S",
)
register_field_roles(
    "EmptyResultSpec", predicate="S", user_message="S",
)
register_field_roles(
    "LegSpec",
    leg_id="S", kind="S", handler="S", reversibility="S", compensator="S",
    audit="S", optional="S",
)
register_field_roles(
    "CompoundOpSpec",
    op_key="S", domain="S", lane="S", authority_ref="S", legs="S",
    idempotency="S", dedup_key="S", audit_verb="S",
    idempotency_justification="S", single_flight_scope="S", confirmation="S",
    emits="S", empty_result="S", session_transition="S", reversibility="O",
)
