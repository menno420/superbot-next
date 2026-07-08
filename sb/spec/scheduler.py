"""The durability-extended ``ManagedTaskSpec`` (K9/S10 — frozen L0 spec 09
§3.1, completing design-spec §2.8's empty durability half, T2-6) + the A-13 /
R-17 riders.

- The base 5 fields (name/trigger/handler/error_policy/metrics_labels) are
  design-spec §2.8 verbatim; the NEW durability/misfire/catch-up fields are
  spec 09's gap-close.
- NO ``idempotency`` field (spec 09 §12 #2 — the leaf inversion is retired):
  every durable fire is unconditionally guarded by the scheduler's
  deterministic ``once()`` (dedup_token = task_id:fire_epoch); the fired
  workflow's own posture lives on its ``CompoundOpSpec`` (K7).
- **R-17**: ``ConditionTrigger`` — the condition-poll trigger kind the live
  substrate uses (channel_inactive / setup_readiness_below / binding_missing)
  that mapped to nothing frozen.
- **A-13**: ``QuietHours`` (per-user timezone + delivery-window; skip-vs-defer
  pinned against MisfirePolicy: DEFER pushes the fire to the window end,
  SKIP drops the occurrence) and ``AutomationEligibility`` (the provisional
  P-5 manifest field grammar; category B ``ACTION`` is structurally reserved
  but FENCED OFF until the pricing session rules — see
  sb/kernel/scheduler/user_automation.py).

Stdlib-only leaf apart from sb.spec.refs + sb.spec.roles — imports NO kernel
module.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Union

from sb.spec.refs import HandlerRef, WorkflowRef
from sb.spec.roles import register_field_roles

__all__ = [
    "AutomationEligibility",
    "ConditionTrigger",
    "Cron",
    "ErrorPolicy",
    "EventTrigger",
    "Interval",
    "ManagedTaskSpec",
    "MisfirePolicy",
    "OneShot",
    "QuietHours",
    "QuietHoursPolicy",
    "TaskDurability",
    "TaskScope",
    "Trigger",
    "TriggerKind",
]


class TaskDurability(str, enum.Enum):
    IN_MEMORY = "in_memory"   # supervised task only; lost on restart (declared, never implicitly lossy)
    DURABLE = "durable"       # persisted in sb_due_queue; survives merge=deploy; boot-reconciled


class MisfirePolicy(str, enum.Enum):
    """Governs RECURRING timers only — an overdue one-shot always fires once."""

    COALESCE = "coalesce"     # N missed fires while down -> ONE fire on boot (A#7 default)
    FIRE_ALL = "fire_all"     # replay every missed interval, bounded by max_catchup
    SKIP = "skip"             # drop all missed; re-arm forward only


class TriggerKind(str, enum.Enum):
    INTERVAL = "interval"
    CRON = "cron"
    ONE_SHOT = "one_shot"
    EVENT = "event"           # bus-armed, NOT polled (out of the due-queue)
    CONDITION = "condition"   # R-17: condition-poll (evaluated each tick via a registered predicate)


class TaskScope(str, enum.Enum):
    GLOBAL = "global"
    GUILD = "guild"           # reclaimed on guild-leave (C-8 / T2-8)


class ErrorPolicy(str, enum.Enum):
    """design-spec §2.8 verbatim."""

    LOG = "log"
    DISABLE_AFTER_N = "disable_after_n"
    ESCALATE_FINDING = "escalate_finding"


@dataclass(frozen=True)
class Interval:
    seconds: int              # [S] persisted as interval_seconds


@dataclass(frozen=True)
class Cron:
    expr: str                 # [S] 5-field; the parser is a bounded impl detail (spec 09 §9)


@dataclass(frozen=True)
class OneShot:
    """fire_at is a runtime arm-time argument, not [S]."""


@dataclass(frozen=True)
class EventTrigger:
    event: str                # [S] bus event name — armed by the K4 bus, never the due-queue


@dataclass(frozen=True)
class ConditionTrigger:
    """R-17 — the condition-poll carrier. `condition` names a REGISTERED
    predicate ref (two-form PredicateRef grammar); `poll_interval_s` is the
    evaluation cadence (the timer re-arms forward each poll; the handler
    fires only when the predicate holds). The three live kinds this carries:
    channel_inactive / setup_readiness_below / binding_missing."""

    condition: str            # [S] PredicateRef string form
    poll_interval_s: int      # [S] evaluation cadence


Trigger = Union[Interval, Cron, OneShot, EventTrigger, ConditionTrigger]


class QuietHoursPolicy(str, enum.Enum):
    """A-13 skip-vs-defer, pinned: DEFER pushes an in-window fire to the
    window END (one fire, late); SKIP drops the occurrence (re-arm forward).
    Interacts with MisfirePolicy downstream of the misfire decision — quiet
    hours filter the epochs the misfire step already selected."""

    DEFER = "defer"
    SKIP = "skip"


@dataclass(frozen=True)
class QuietHours:
    """A-13 — the delivery-window carrier (the one live scheduler behavior
    with no frozen carrier). Hours are 0-23 in `tz`; a window may wrap
    midnight (start > end)."""

    start_hour: int           # [S] window start (inclusive) — fires suppressed from here
    end_hour: int             # [S] window end (exclusive) — fires resume here
    tz: str = "UTC"           # [S] IANA zone name (per-user timezone)
    policy: QuietHoursPolicy = QuietHoursPolicy.DEFER  # [S]


class AutomationEligibility(str, enum.Enum):
    """A-13 — the provisional-P-5 manifest field grammar (ratify_when =
    second ported consumer). Category B (`ACTION`) is structurally reserved
    but compile-fenced OFF pending the pricing session (Q-0243)."""

    NONE = "none"
    NOTIFY_ONLY = "notify_only"
    ACTION = "action"


@dataclass(frozen=True)
class ManagedTaskSpec:
    """EXTENDS design-spec §2.8 — the base 5 fields are unchanged."""

    name: str                                     # [S] "<subsystem>:<purpose>" — namespace kind task_prefix
    trigger: Trigger                              # [S]
    handler: WorkflowRef | HandlerRef             # [S] MUST be WorkflowRef if the fire mutates (fence)
    error_policy: ErrorPolicy = ErrorPolicy.LOG   # [S]
    metrics_labels: tuple[str, ...] = ()          # [S]
    # ---- NEW durability fields (T2-6) ----
    durability: TaskDurability = TaskDurability.IN_MEMORY  # [S]
    misfire_policy: MisfirePolicy = MisfirePolicy.COALESCE  # [S] (A#7 default)
    catch_up: bool = True                         # [S] recurring only
    grace_s: int = 0                              # [S]
    scope: TaskScope = TaskScope.GLOBAL           # [S]
    max_catchup: int = 1                          # [S] FIRE_ALL replay cap
    # ---- A-13 rider ----
    quiet_hours: QuietHours | None = None         # [S] delivery window; None = always deliverable

    @property
    def trigger_kind(self) -> TriggerKind:
        return {
            Interval: TriggerKind.INTERVAL, Cron: TriggerKind.CRON,
            OneShot: TriggerKind.ONE_SHOT, EventTrigger: TriggerKind.EVENT,
            ConditionTrigger: TriggerKind.CONDITION,
        }[type(self.trigger)]


register_field_roles("Interval", seconds="S")
register_field_roles("Cron", expr="S")
register_field_roles("EventTrigger", event="S")
register_field_roles("ConditionTrigger", condition="S", poll_interval_s="S")
register_field_roles("QuietHours", start_hour="S", end_hour="S", tz="S", policy="S")
register_field_roles(
    "ManagedTaskSpec",
    name="S", trigger="S", handler="S", error_policy="S", metrics_labels="S",
    durability="S", misfire_policy="S", catch_up="S", grace_s="S", scope="S",
    max_catchup="S", quiet_hours="S",
)
