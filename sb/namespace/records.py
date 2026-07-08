"""Reservation / violation records (frozen L0 spec 03 §3.2). Stdlib-only leaf."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sb.namespace.kinds import CommandScope, NamespaceKind, Origin

if TYPE_CHECKING:  # leaf-internal forward ref only
    from sb.namespace.index import ReservationIndex


@dataclass(frozen=True)
class ReservationRecord:
    kind: NamespaceKind
    value: str                      # normalized
    scope: CommandScope | None
    origin: Origin
    owner: str | None               # owning subsystem key (manifest/legacy); None for tombstone/ban
    spec_id: str | None             # declaring spec id — provenance + TargetRef assembly
    source: str                     # "subsystem@file:line" | "legacy_reservations.json" | "Q-0NNN"
    renamed_to: str | None = None   # tombstone successor -> the helpful "renamed to X" error
    reason: str | None = None       # tombstone/ban reason


ReservationHit = ReservationRecord


@dataclass(frozen=True)
class Collision:
    kind: NamespaceKind
    value: str
    scope: CommandScope | None      # LOAD-BEARING (spec 03 §4.2 seam note — 01's Collision adds it)
    claimant_a: str                 # "subsystem@file:line" of each claimant
    claimant_b: str
    detail: str | None = None       # e.g. "reserved_tombstone (renamed to X)" | "banned_name"


@dataclass(frozen=True)
class CapViolation:
    cap: str                        # "top_level_100" | "sub_25" | "nest_1"
    #   (reserved, dormant: "user_context_5" | "message_context_5" — spec 03 §3.5)
    locus: str                      # "" (global) | the group path that overflows
    count: int
    limit: int
    members: tuple[str, ...]        # overflowing names, sorted (deterministic)


@dataclass(frozen=True)
class FormatError:
    kind: NamespaceKind
    value: str
    detail: str                     # "capability_not_3_part" | "reserved_prefix_misuse" | ...


@dataclass(frozen=True)
class NamespaceReport:
    ok: bool
    collisions: tuple[Collision, ...]
    cap_violations: tuple[CapViolation, ...]
    format_errors: tuple[FormatError, ...]
    index: "ReservationIndex"       # built once here, REUSED at boot (the shared-oracle guarantee)
