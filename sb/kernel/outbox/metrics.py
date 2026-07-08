"""The four outbox MetricSpecs (K4, frozen L0 spec 08 §2/§3.2).

Homed here per spec 08's file map (not in sb/spec/observability.METRICS —
that tuple is the verbatim shipped-46 harvest). The composition root builds
the registry with METRICS + OUTBOX_METRICS; tools/check_metric_cardinality
validates both tuples.

`outbox_claims_total` high while `outbox_delivered_total` is flat and
`outbox_pending_age_seconds` grows = the relay-health alert shape (a
crash-looping relay never dead-letters a healthy event — finding 6).
"""

from __future__ import annotations

from sb.spec.observability import MetricKind, MetricSpec

__all__ = ["OUTBOX_METRICS"]

OUTBOX_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(
        name="outbox_pending_age_seconds",
        kind=MetricKind.GAUGE,
        doc="Age in seconds of the oldest PENDING event_outbox row (0 when none).",
        owner_subsystem="outbox",
    ),
    MetricSpec(
        name="outbox_delivered_total",
        kind=MetricKind.COUNTER,
        doc="Outbox rows the relay delivered (publish-accepted) to the bus.",
        owner_subsystem="outbox",
    ),
    MetricSpec(
        name="outbox_dead_letter_total",
        kind=MetricKind.COUNTER,
        doc="Outbox rows dead-lettered after MAX_ATTEMPTS bus-level delivery failures.",
        owner_subsystem="outbox",
    ),
    MetricSpec(
        name="outbox_claims_total",
        kind=MetricKind.COUNTER,
        doc="Outbox row leases taken by relay claim cycles (crash-loop signal; "
            "does not gate dead-lettering).",
        owner_subsystem="outbox",
    ),
)
