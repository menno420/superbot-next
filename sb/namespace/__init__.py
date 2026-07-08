"""``sb/namespace`` — the K1 namespace registry (frozen L0 spec 03).

A **stdlib-only leaf** (design-spec §1.1): `validate`, `ReservationIndex`,
`check_trigger` import neither `sb/spec` nor manifests — they consume the
snapshot dict + committed JSON files (pure data). One pure oracle
(`validate(snapshot) -> NamespaceReport`) serves CI, `git merge-tree`
re-validation, and boot leg-A, so CI-green <=> boot-green by construction
(the #763 false-green class, closed).
"""

from sb.namespace.index import ReservationIndex
from sb.namespace.kinds import CommandScope, NamespaceKind, Origin, Surface, namespace_id, normalize
from sb.namespace.records import (
    CapViolation,
    Collision,
    FormatError,
    NamespaceReport,
    ReservationHit,
    ReservationRecord,
)
from sb.namespace.triggers import TriggerAvailability, check_trigger
from sb.namespace.validate import validate

__all__ = [
    "CapViolation",
    "Collision",
    "CommandScope",
    "FormatError",
    "NamespaceKind",
    "NamespaceReport",
    "Origin",
    "ReservationHit",
    "ReservationIndex",
    "ReservationRecord",
    "Surface",
    "TriggerAvailability",
    "check_trigger",
    "namespace_id",
    "normalize",
    "validate",
]
