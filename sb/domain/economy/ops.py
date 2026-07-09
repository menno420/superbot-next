"""The economy mutation lane (band 3) — K7 CompoundOpSpecs over the shipped
CRIT-9 semantics: EVERY coin movement is one audited DB leg (balance write +
economy_audit_log ledger row in the SAME txn — the aggregate and the ledger
can never commit apart, INV-F's runtime half) and one
`economy.balance_changed` emission AFTER commit (the shipped
transfer/workflow precedent, verbatim event name + payload keys).

Authority: user-tier ops declare `authority_ref="user"` (TIER lane — these
are member-facing loops, never the ADMIN floor).

The daily tier draw is the shipped weighted random — the ONE randomness
point, injectable for tests/replay (`set_rng_for_tests`).
"""

from __future__ import annotations

import random
import re

from sb.domain.economy import catalogue, service, store
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["EVT_BALANCE_CHANGED", "register_ops", "set_rng_for_tests"]

#: shipped event name, verbatim (services/economy_service.py:57)
EVT_BALANCE_CHANGED = "economy.balance_changed"

_MENTION = re.compile(r"^<@!?(\d{15,20})>$")

_rng: random.Random = random.Random()


def set_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def _actor_id(ctx: WorkflowContext) -> int:
    actor = getattr(ctx, "actor", None)
    return int(getattr(actor, "user_id", 0) or 0)


def _now(ctx: WorkflowContext) -> int:
    return int(ctx.clock().timestamp())


# --- DB legs -----------------------------------------------------------------------

@workflow("economy.record_daily")
async def _record_daily(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    now = _now(ctx)
    row = await store.ensure_and_get_economy(conn, user_id=uid, guild_id=gid)
    last, streak = int(row["last_daily"]), int(row["daily_streak"])

    on_cd, secs = service.check_cooldown(last, catalogue.DAILY_COOLDOWN, now=now)
    if on_cd:
        raise service.CooldownActiveError(
            f"⏰ Already claimed today! Come back in "
            f"**{service.format_remaining(secs)}**.")

    if last > 0 and now - last > catalogue.DAILY_COOLDOWN * 2:
        streak = 0                      # shipped: a missed window resets
    streak += 1

    amount, tier_label, tier_emoji = catalogue.pick_daily(streak, _rng)
    new_count = int(row["daily_count"]) + 1
    new_bal = await store.credit_coins(conn, user_id=uid, guild_id=gid,
                                       amount=amount)
    await store.insert_economy_audit(conn, guild_id=gid, user_id=uid,
                                     actor_id=uid, delta=amount,
                                     new_balance=new_bal, reason="daily")
    await store.set_daily_claim(conn, user_id=uid, guild_id=gid,
                                last_daily=now, daily_streak=streak,
                                daily_count=new_count)

    ctx.params["_subject_id"] = uid
    ctx.params["_delta"] = amount
    ctx.params["_new_balance"] = new_bal
    ctx.params["_reason"] = "daily"
    return LegOutcome(
        step=StepResult(uid, "daily", True),
        before={"coins": new_bal - amount, "streak": streak - 1},
        after={"coins": new_bal, "streak": streak, "tier": tier_label,
               "tier_emoji": tier_emoji, "amount": amount,
               "claims": new_count},
    )


def _job_from(ctx: WorkflowContext) -> str:
    job = str(ctx.params.get("job", "") or "")
    if not job:
        # component select (panel-action slice): the COMPONENT adapter
        # carries the chosen option as args["values"] — same audited op,
        # third arg spelling.
        values = tuple(ctx.params.get("values", ()) or ())
        job = str(values[0]) if values else ""
    if not job:
        argv = tuple(ctx.params.get("argv", ()) or ())
        job = str(argv[0]) if argv else ""
    return job.lower().strip()


@workflow("economy.record_work")
async def _record_work(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.kernel.interaction.errors import ValidatorError

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    now = _now(ctx)
    job = _job_from(ctx)
    if job not in catalogue.JOBS:
        raise ValidatorError(
            f"❌ Unknown job {job!r} — see `!joblist` for jobs you can work.")

    row = await store.ensure_and_get_economy(conn, user_id=uid, guild_id=gid)
    on_cd, secs = service.check_cooldown(int(row["last_worked"]),
                                         catalogue.WORK_COOLDOWN, now=now)
    if on_cd:
        raise service.CooldownActiveError(
            f"⏰ You're tired! Rest for "
            f"**{service.format_remaining(secs)}** more.")

    eligible = await service.available_jobs(uid, gid)
    if job not in eligible:
        raise ValidatorError(
            "❌ You don't meet that job's requirements yet — earn XP or buy "
            "the required items from `!shop`.")

    times = await store.get_job_times(uid, gid, job, conn=conn)
    pay = catalogue.job_pay(job, times)
    new_times = await store.increment_job(conn, user_id=uid, guild_id=gid,
                                          job_name=job)
    new_bal = await store.credit_coins(conn, user_id=uid, guild_id=gid,
                                       amount=pay)
    await store.insert_economy_audit(conn, guild_id=gid, user_id=uid,
                                     actor_id=uid, delta=pay,
                                     new_balance=new_bal,
                                     reason=f"work:{job}")
    await store.set_last_worked(conn, user_id=uid, guild_id=gid, ts=now)

    ctx.params["_subject_id"] = uid
    ctx.params["_delta"] = pay
    ctx.params["_new_balance"] = new_bal
    ctx.params["_reason"] = f"work:{job}"
    ctx.params["_xp_gain"] = catalogue.JOBS[job]["xp"]
    ctx.params["_job"] = job
    ctx.params["_now"] = now
    return LegOutcome(
        step=StepResult(uid, "work", True),
        before={"coins": new_bal - pay, "times_worked": new_times - 1},
        after={"coins": new_bal, "times_worked": new_times, "job": job,
               "pay": pay, "mastery_bonus_pct": min(times, 100)},
    )


@workflow("economy.record_pay")
async def _record_pay(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.kernel.interaction.errors import ValidatorError

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    target = ctx.params.get("target_id") or ctx.params.get("member")
    amount = ctx.params.get("amount")
    argv = tuple(ctx.params.get("argv", ()) or ())
    if target is None and argv:
        match = _MENTION.match(str(argv[0]))
        if match:
            target = int(match.group(1))
        if amount is None and len(argv) > 1 and str(argv[1]).lstrip("-").isdigit():
            amount = int(argv[1])
    if target is None or amount is None:
        raise ValidatorError("Usage: `!pay @user <amount>`")
    target = int(str(target).strip("<@!>"))
    amount = int(amount)
    if target == uid:
        raise ValidatorError("❌ You can't pay yourself.")
    if amount <= 0:
        raise ValidatorError("❌ Amount must be positive.")

    new_from = await store.try_debit_coins(conn, user_id=uid, guild_id=gid,
                                           amount=amount)
    if new_from is None:
        coins = await store.get_coins(uid, gid, conn=conn)
        raise service.InsufficientFundsError(
            f"❌ Not enough coins — you have **{coins:,}** 🪙, "
            f"tried to send **{amount:,}** 🪙.")
    new_to = await store.credit_coins(conn, user_id=target, guild_id=gid,
                                      amount=amount)
    await store.insert_economy_audit(conn, guild_id=gid, user_id=uid,
                                     actor_id=uid, delta=-amount,
                                     new_balance=new_from, reason="gift")
    await store.insert_economy_audit(conn, guild_id=gid, user_id=target,
                                     actor_id=uid, delta=amount,
                                     new_balance=new_to, reason="gift")

    ctx.params["_from_id"] = uid
    ctx.params["_to_id"] = target
    ctx.params["_amount"] = amount
    ctx.params["_from_balance"] = new_from
    ctx.params["_to_balance"] = new_to
    return LegOutcome(
        step=StepResult(target, "pay", True),
        before={"from": new_from + amount, "to": new_to - amount},
        after={"from": new_from, "to": new_to, "amount": amount},
    )


def _item_from(ctx: WorkflowContext) -> str:
    item = str(ctx.params.get("item", "") or "")
    if not item:
        # component select (panel-action slice): args["values"] spelling.
        values = tuple(ctx.params.get("values", ()) or ())
        item = str(values[0]) if values else ""
    if not item:
        argv = tuple(ctx.params.get("argv", ()) or ())
        item = " ".join(str(a) for a in argv) if argv else ""
    return item.lower().strip()


@workflow("economy.record_buy")
async def _record_buy(conn, ctx: WorkflowContext) -> LegOutcome:
    """Shop purchase — the shipped Q-0071 workflow verbatim: conditional
    unique grant FIRST (authoritative ownership check), audited debit second;
    an unaffordable debit raises and rolls the grant back with it."""
    from sb.kernel.interaction.errors import ValidatorError

    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    item = _item_from(ctx)
    if item not in catalogue.SHOP_ITEMS:
        raise ValidatorError(
            f"❌ Unknown shop item {item!r} — see `!shop` for the catalogue.")
    price = int(catalogue.SHOP_ITEMS[item]["price"])

    granted = await store.try_grant_unique_item(conn, user_id=uid,
                                                guild_id=gid, item_name=item)
    if not granted:
        raise service.AlreadyOwnedError(f"You already own a **{item}**!")
    new_bal = await store.try_debit_coins(conn, user_id=uid, guild_id=gid,
                                          amount=price)
    if new_bal is None:
        coins = await store.get_coins(uid, gid, conn=conn)
        raise service.InsufficientFundsError(
            f"❌ Need **{price:,}** 🪙 — you only have **{coins:,}** 🪙.")
    await store.insert_economy_audit(conn, guild_id=gid, user_id=uid,
                                     actor_id=uid, delta=-price,
                                     new_balance=new_bal,
                                     reason=f"shop:{item}")

    ctx.params["_subject_id"] = uid
    ctx.params["_delta"] = -price
    ctx.params["_new_balance"] = new_bal
    ctx.params["_reason"] = f"shop:{item}"
    return LegOutcome(
        step=StepResult(uid, "buy", True),
        before={"coins": new_bal + price, "owned": False},
        after={"coins": new_bal, "owned": True, "item": item, "price": price},
    )


# --- EFFECT legs -------------------------------------------------------------------

@workflow("economy.award_work_xp")
async def _award_work_xp(conn, ctx: WorkflowContext) -> LegOutcome:
    """The band-4 XP boundary: award through the installed port (shipped
    xp_service.award signature); no port yet => xp_pending, never a fake."""
    awarder = service.active_xp_awarder()
    result = await awarder(
        guild_id=int(ctx.guild_id or 0), user_id=_actor_id(ctx),
        amount=int(ctx.params.get("_xp_gain", 0) or 0),
        source=f"work:{ctx.params.get('_job', '')}",
        now=int(ctx.params.get("_now", 0) or 0))
    pending = result is None and not service.xp_installed()
    return LegOutcome(
        step=StepResult(_actor_id(ctx), "award_work_xp", True),
        before={},
        after={"xp_pending": pending,
               "xp_awarded": (None if result is None
                              else dict(result))},
    )


# --- privacy erasure bodies (the store-declared refs; flag-18 discipline) -----------

def _erasure_body(name: str, row_fn_name: str):
    @workflow(name)
    async def _body(conn, ctx: WorkflowContext) -> LegOutcome:
        subject = int(ctx.params["subject_user_id"])
        rows = await getattr(store, row_fn_name)(conn, user_id=subject)
        return LegOutcome(step=StepResult(0, name.rsplit(".", 1)[-1], True),
                          before={}, after={"rows": rows})
    return _body


_erase_balances = _erasure_body("economy.erase_subject_balances",
                                "erase_subject_balances")
_tombstone_audit = _erasure_body("economy.tombstone_subject_audit",
                                 "tombstone_subject_audit")
_erase_track = _erasure_body("economy.erase_subject_track",
                             "erase_subject_track")
_erase_jobs = _erasure_body("economy.erase_subject_jobs",
                            "erase_subject_jobs")
_erase_inventory = _erasure_body("economy.erase_subject_inventory",
                                 "erase_subject_inventory")


# --- event payload builders (shipped payload keys, verbatim) ------------------------

@workflow("economy.balance_payload")
def _balance_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_subject_id", 0) or 0),
        "delta": int(ctx.params.get("_delta", 0) or 0),
        "new_balance": int(ctx.params.get("_new_balance", 0) or 0),
        "reason": str(ctx.params.get("_reason", "") or ""),
    }


@workflow("economy.pay_payload_from")
def _pay_payload_from(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_from_id", 0) or 0),
        "delta": -int(ctx.params.get("_amount", 0) or 0),
        "new_balance": int(ctx.params.get("_from_balance", 0) or 0),
        "reason": "gift",
    }


@workflow("economy.pay_payload_to")
def _pay_payload_to(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_to_id", 0) or 0),
        "delta": int(ctx.params.get("_amount", 0) or 0),
        "new_balance": int(ctx.params.get("_to_balance", 0) or 0),
        "reason": "gift",
    }


_BALANCE_EMIT = (EventEmitSpec(EVT_BALANCE_CHANGED,
                               WorkflowRef("economy.balance_payload"),
                               DeliveryClass.BEST_EFFORT),)
_PAY_EMITS = (
    EventEmitSpec(EVT_BALANCE_CHANGED, WorkflowRef("economy.pay_payload_from"),
                  DeliveryClass.BEST_EFFORT),
    EventEmitSpec(EVT_BALANCE_CHANGED, WorkflowRef("economy.pay_payload_to"),
                  DeliveryClass.BEST_EFFORT),
)


def _op(op_key: str, verb: str, legs: tuple[LegSpec, ...], *,
        emits: tuple[EventEmitSpec, ...]) -> CompoundOpSpec:
    """All band-3 econ loops are NATURAL_KEY: the cooldown anchors ride
    row-locked conditional writes and the unique-grant / conditional-debit
    statements decide-and-write in one statement (shipped race closures)."""
    return CompoundOpSpec(
        op_key=op_key, domain="economy", lane=WorkflowLane.DOMAIN,
        authority_ref="user",             # member-facing (TIER lane)
        legs=legs,
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=emits)


DAILY = _op("economy.daily", "daily_claimed",
            (LegSpec("record", LegKind.DB,
                     WorkflowRef("economy.record_daily"), "reversible"),),
            emits=_BALANCE_EMIT)
WORK = _op("economy.work", "work_completed",
           (LegSpec("record", LegKind.DB,
                    WorkflowRef("economy.record_work"), "reversible"),
            LegSpec("award_xp", LegKind.EFFECT,
                    WorkflowRef("economy.award_work_xp"), "reversible",
                    optional=True)),
           emits=_BALANCE_EMIT)
PAY = _op("economy.pay", "coins_transferred",
          (LegSpec("record", LegKind.DB,
                   WorkflowRef("economy.record_pay"), "reversible"),),
          emits=_PAY_EMITS)
BUY = _op("economy.buy", "item_purchased",
          (LegSpec("record", LegKind.DB,
                   WorkflowRef("economy.record_buy"), "reversible"),),
          emits=_BALANCE_EMIT)

_OPS = (DAILY, WORK, PAY, BUY)

_REF_TABLE = (
    ("economy.record_daily", _record_daily),
    ("economy.record_work", _record_work),
    ("economy.record_pay", _record_pay),
    ("economy.record_buy", _record_buy),
    ("economy.award_work_xp", _award_work_xp),
    ("economy.erase_subject_balances", _erase_balances),
    ("economy.tombstone_subject_audit", _tombstone_audit),
    ("economy.erase_subject_track", _erase_track),
    ("economy.erase_subject_jobs", _erase_jobs),
    ("economy.erase_subject_inventory", _erase_inventory),
    ("economy.balance_payload", _balance_payload),
    ("economy.pay_payload_from", _pay_payload_from),
    ("economy.pay_payload_to", _pay_payload_to),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    """Refs-table twins of the REGISTRY op keys (the band-2 convention) —
    P2 resolves WorkflowRef command routes against the refs table."""
    from sb.spec.refs import is_registered, workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered, workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
