"""S10: the pure misfire decision (frozen L0 spec 09 §3.7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sb.kernel.db.scheduler import DueTimer
from sb.kernel.scheduler.misfire import apply_misfire, fire_epoch, next_slot

T0 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def timer(**kw) -> DueTimer:
    defaults = dict(
        task_id="t1", task_key="gc:sweep", guild_id=None,
        trigger_kind="interval", fire_at=T0, payload={}, payload_version=1,
        recurring=True, misfire_policy="coalesce", catch_up=True, grace_s=0,
        max_catchup=1, interval_seconds=600, cron_expr=None, error_policy="log")
    defaults.update(kw)
    return DueTimer(**defaults)


def test_one_shot_always_fires_once_even_overdue_with_skip():
    t = timer(recurring=False, misfire_policy="skip", catch_up=False)
    d = apply_misfire(t, T0 + timedelta(hours=5))
    assert d.fire_epochs == (fire_epoch(T0),)
    assert d.next_fire_at is None       # delete after fire


def test_on_time_within_grace_fires_and_advances_from_slot():
    t = timer(grace_s=30)
    d = apply_misfire(t, T0 + timedelta(seconds=20))
    assert d.fire_epochs == (fire_epoch(T0),)
    assert d.next_fire_at == T0 + timedelta(seconds=600)


def test_coalesce_overdue_one_fire_advance_past_now():
    t = timer()
    now = T0 + timedelta(seconds=3000)   # 5 slots missed
    d = apply_misfire(t, now)
    assert d.fire_epochs == (fire_epoch(T0),)   # ONE fire
    assert d.next_fire_at > now


def test_skip_and_no_catch_up_drop_missed_and_rearm_forward():
    now = T0 + timedelta(seconds=3000)
    for t in (timer(misfire_policy="skip"), timer(catch_up=False)):
        d = apply_misfire(t, now)
        assert d.fire_epochs == ()
        assert d.next_fire_at > now


def test_fire_all_bounded_by_max_catchup_with_truncation_flag():
    t = timer(misfire_policy="fire_all", max_catchup=3)
    now = T0 + timedelta(seconds=6000)   # 11 slots due
    d = apply_misfire(t, now)
    assert len(d.fire_epochs) == 3
    assert d.truncated
    assert d.next_fire_at > now

    t2 = timer(misfire_policy="fire_all", max_catchup=10)
    now2 = T0 + timedelta(seconds=1250)  # slots at 0, 600, 1200 due
    d2 = apply_misfire(t2, now2)
    assert len(d2.fire_epochs) == 3
    assert not d2.truncated


def test_next_slot_interval_strictly_after():
    t = timer()
    assert next_slot(t, after=T0) == T0 + timedelta(seconds=600)
    assert next_slot(t, after=T0 + timedelta(seconds=599)) == T0 + timedelta(seconds=600)
    assert next_slot(t, after=T0 + timedelta(seconds=600)) == T0 + timedelta(seconds=1200)


def test_cron_without_parser_raises():
    t = timer(interval_seconds=None, cron_expr="0 4 * * *")
    try:
        import croniter  # noqa: F401
        pytest.skip("croniter installed — parser path live")
    except ImportError:
        pass
    with pytest.raises(RuntimeError, match="croniter"):
        next_slot(t, after=T0)
