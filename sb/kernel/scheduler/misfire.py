"""``apply_misfire`` — PURE (K9/S10, frozen L0 spec 09 §3.7).

The coalesce/fire_all/skip decision + the recurring next-slot advance.
One-shots are policy-exempt: an overdue one-shot always fires exactly once
(it cannot re-arm forward). The cron parser is a bounded deferral (spec 09
§9): croniter when installed, else arming/advancing a Cron task raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sb.kernel.db.scheduler import DueTimer
from sb.spec.scheduler import MisfirePolicy

try:  # pragma: no cover — croniter is an optional pinned dep (spec 09 §9)
    from croniter import croniter
except ImportError:
    croniter = None

__all__ = ["MisfireDecision", "apply_misfire", "fire_epoch", "next_slot"]


@dataclass(frozen=True)
class MisfireDecision:
    fire_epochs: tuple[int, ...]      # epochs to fire NOW, each its own once() key
    next_fire_at: datetime | None     # advance the recurring slot here; None ⇒ one-shot delete
    truncated: bool = False           # FIRE_ALL exceeded max_catchup — operator finding


def fire_epoch(fire_at: datetime) -> int:
    """Deterministic — two instances (or a boot re-fire) collide on the
    same once() key and exactly one fires."""
    return int(fire_at.timestamp())


def next_slot(timer: DueTimer, *, after: datetime) -> datetime:
    """interval ⇒ smallest fire_at + k*interval > after; cron ⇒ croniter;
    condition ⇒ fire_at + poll cadence (carried in interval_seconds)."""
    if timer.interval_seconds:
        base = timer.fire_at
        step = timedelta(seconds=timer.interval_seconds)
        k = max(int((after - base) / step) + 1, 1)
        candidate = base + step * k
        while candidate <= after:  # guard integer-division edge
            candidate += step
        return candidate
    if timer.cron_expr:
        if croniter is None:
            raise RuntimeError(
                "cron trigger requires the pinned croniter parser "
                "(spec 09 §9 bounded deferral) — not installed")
        return croniter(timer.cron_expr, after).get_next(datetime)
    raise ValueError(f"timer {timer.task_key!r} is recurring but carries "
                     f"neither interval_seconds nor cron_expr")


def apply_misfire(timer: DueTimer, now: datetime) -> MisfireDecision:
    # one-shot: always fire once when overdue; misfire/catch_up do not apply.
    if not timer.recurring:
        return MisfireDecision(fire_epochs=(fire_epoch(timer.fire_at),),
                               next_fire_at=None)

    grace = timedelta(seconds=timer.grace_s)
    if timer.fire_at + grace >= now:
        # on time (within grace): one fire, advance from the slot.
        return MisfireDecision(
            fire_epochs=(fire_epoch(timer.fire_at),),
            next_fire_at=next_slot(timer, after=timer.fire_at))

    # overdue beyond grace.
    policy = MisfirePolicy(timer.misfire_policy)
    if not timer.catch_up or policy is MisfirePolicy.SKIP:
        return MisfireDecision(fire_epochs=(),
                               next_fire_at=next_slot(timer, after=now))
    if policy is MisfirePolicy.COALESCE:
        return MisfireDecision(fire_epochs=(fire_epoch(timer.fire_at),),
                               next_fire_at=next_slot(timer, after=now))
    # FIRE_ALL: enumerate missed slots, bounded by max_catchup.
    epochs: list[int] = []
    slot = timer.fire_at
    missed = 0
    truncated = False
    while slot <= now:
        missed += 1
        if len(epochs) < max(timer.max_catchup, 1):
            epochs.append(fire_epoch(slot))
        else:
            truncated = True
        if timer.interval_seconds:
            slot = slot + timedelta(seconds=timer.interval_seconds)
        else:
            slot = next_slot(timer, after=slot)
    if truncated:
        nfa = next_slot(timer, after=now)
    else:
        last = datetime.fromtimestamp(epochs[-1], tz=timer.fire_at.tzinfo)
        nfa = next_slot(timer, after=last)
    return MisfireDecision(fire_epochs=tuple(epochs), next_fire_at=nfa,
                           truncated=truncated)
