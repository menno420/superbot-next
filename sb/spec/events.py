"""Event grammar: `DeliveryClass` (canonical home) + `EventSpec.delivery` (K4).

Built to frozen L0 spec 08 (event-outbox) §3.1. This module is the CANONICAL
home of `DeliveryClass` — K7's `EventEmitSpec.delivery` imports THIS enum
(spec 08 §12.1, the RC-3 `Lane` lesson: one enum or they drift). RC-17: no
local K7 copy is ever minted.

`EventSpec` carries the design-spec §2.8 frozen fields + the ONE new field
`delivery` (default `BEST_EFFORT` — zero behavior change for the 30+
observability-only events; membership of the `AT_LEAST_ONCE` set is
owner-gated, spec 08 §13 OD-1). `delivery` and `audited` are orthogonal:
`audited=True` = "this event IS an audit-row carrier"; `delivery` = "how
durably is it delivered". The fully-durable audit path is
`EventSpec(audited=True, delivery=AT_LEAST_ONCE)` — the `audit.action_recorded`
canary (no `AuditEventSpec` subclass; spec 08 §3.1 dropped it).

The `delivery_declared` compile fence lives in `tools/manifest_compile.py`
(P6 — additive to manifest-validate, spec 08 §3.1).

`KNOWN_EVENTS` is the name -> EventSpec registry the enqueue name-guard and
the relay read. It is populated by the manifest build (each subsystem's
`events` facet) on top of the kernel seed below. Stdlib-only leaf.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from sb.spec.roles import register_field_roles


class DeliveryClass(enum.Enum):
    """CANONICAL home (spec 08 §3.1/§12.1; K7 imports this — RC-17)."""

    BEST_EFFORT = "best_effort"      # post-commit bus.emit; a drop is a log line (shipped default)
    AT_LEAST_ONCE = "at_least_once"  # event_outbox row INSIDE the txn; relay delivers post-commit


@dataclass(frozen=True)
class FieldSpec:
    """One payload field of an event's declared schema (design-spec §2.8).

    `payload_schema` evolves ADDITIVE-ONLY (the manifest superset rule) —
    the invariant the outbox's re-emit-as-stored posture relies on
    (spec 08 §5.1/§9 deferral 3).
    """

    name: str            # [S] payload kwarg name, verbatim
    type: str = "str"    # [S] JSON-native type token: str|int|bool|float|dict|list|datetime|uuid
    required: bool = True  # [S] enqueue checks key-presence for required fields


@dataclass(frozen=True)
class EventSpec:
    """Design-spec §2.8 frozen fields + `delivery` (spec 08 §3.1)."""

    name: str                                       # [S] legacy name verbatim, KNOWN_EVENTS-checked
    payload_schema: tuple[FieldSpec, ...] = ()      # [S] superset of current kwargs
    owner_subsystem: str = ""                       # [S]
    expected_subscribers: tuple = ()                # [S] HandlerRef tuple
    observability_only: bool = False                # [S]
    audited: bool = False                           # [S] carries an emit_audit_action fan-out (orthogonal to delivery)
    redaction_ref: str | None = None                # [S] redaction-profile key (grammar finalized strand-3)
    delivery: DeliveryClass = DeliveryClass.BEST_EFFORT  # [S] NEW — completes the vocab §④/§⑤ skeleton


register_field_roles(
    "FieldSpec",
    name="S", type="S", required="S",
)
register_field_roles(
    "EventSpec",
    name="S", payload_schema="S", owner_subsystem="S", expected_subscribers="S",
    observability_only="S", audited="S", redaction_ref="S", delivery="S",
)


# ---------------------------------------------------------------------------
# KNOWN_EVENTS — the name -> EventSpec registry (spec 08 §3.3): the same
# registry the shipped events_catalogue._check_catalogue read, rebuilt as a
# populated mapping. The manifest build registers every subsystem's events
# facet here; the kernel seed below exists from import.
# ---------------------------------------------------------------------------

KNOWN_EVENTS: dict[str, EventSpec] = {}


class EventRedefined(Exception):
    """Two EventSpecs claimed the same event name (mirror of RefRedefined)."""


def register_event_specs(specs: tuple[EventSpec, ...] | list[EventSpec]) -> None:
    """Register EventSpecs into KNOWN_EVENTS; a re-registration with a
    DIFFERENT spec raises EventRedefined; identical re-registration is a
    no-op (module re-import discipline, matching sb.spec.roles)."""
    for spec in specs:
        existing = KNOWN_EVENTS.get(spec.name)
        if existing is not None and existing != spec:
            raise EventRedefined(
                f"event {spec.name!r} already registered with a different spec")
        KNOWN_EVENTS[spec.name] = spec


def clear_event_registry() -> None:
    """Test seam (mirrors refs.clear_ref_table): reset to the kernel seed."""
    KNOWN_EVENTS.clear()
    register_event_specs(_KERNEL_EVENTS)


# ---------------------------------------------------------------------------
# Kernel seed — the durable-audit canary (spec 08 §1/§11 item 5).
# ---------------------------------------------------------------------------

EVT_AUDIT_ACTION_RECORDED = "audit.action_recorded"

#: The 11-field frozen audit payload (shared-vocab §③.2; shipped
#: audit_events.py:52). occurred_at rides the bus as an ISO string
#: (audit_events.py:87 .isoformat(); the subscriber types it str).
AUDIT_ACTION_RECORDED = EventSpec(
    name=EVT_AUDIT_ACTION_RECORDED,
    payload_schema=(
        FieldSpec("mutation_id"),
        FieldSpec("subsystem"),
        FieldSpec("mutation_type"),
        FieldSpec("target"),
        FieldSpec("scope"),
        FieldSpec("guild_id", type="int", required=False),
        FieldSpec("prev_value", required=False),
        FieldSpec("new_value", required=False),
        FieldSpec("actor_id", type="int", required=False),
        FieldSpec("actor_type"),
        FieldSpec("occurred_at", type="datetime"),
    ),
    owner_subsystem="audit",
    audited=True,
    delivery=DeliveryClass.AT_LEAST_ONCE,   # the canary opts in from birth
)

_KERNEL_EVENTS: tuple[EventSpec, ...] = (AUDIT_ACTION_RECORDED,)

register_event_specs(_KERNEL_EVENTS)
