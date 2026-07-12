"""The treasury mutation lane (band 3) — the shipped RS02/Q-0071 semantics
as K7 CompoundOpSpecs: the pool-row write and the user coin leg (audited by
the economy ledger — `economy_audit_log` IS the money trail, treasury rows
are the domain-inventory leg) commit in ONE txn; `economy.balance_changed`
emits AFTER commit with the shipped `treasury:contribute` /
`treasury:disburse` reason tags verbatim.

Authority mirrors shipped exactly: contribute is member-facing (`user`
tier); disburse was `perms_or_owner(manage_guild=True)` — `staff` is THE
tier whose Discord permission bit is manage_guild
(sb/spec/authority.TIER_DISCORD_PERMISSION, ported verbatim).
"""

from __future__ import annotations

from sb.domain.economy import service as economy_service
from sb.domain.economy import store as economy_store
from sb.domain.treasury import store
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

__all__ = ["CONTRIBUTE_REASON", "DISBURSE_REASON", "register_ops"]

#: shipped audit/event reason tags, verbatim (services/treasury_service.py)
CONTRIBUTE_REASON = "treasury:contribute"
DISBURSE_REASON = "treasury:disburse"


def _actor_id(ctx: WorkflowContext) -> int:
    actor = getattr(ctx, "actor", None)
    return int(getattr(actor, "user_id", 0) or 0)


def _now(ctx: WorkflowContext) -> int:
    return int(ctx.clock().timestamp())


def _amount_from(ctx: WorkflowContext, *, slot: int = 0) -> int:
    """amount param > argv[slot] (the shipped positional amount slot).

    POSITIONAL, never a scan: the shipped commands were
    ``contribute(ctx, amount: int)`` — slot 0 — and ``grant(ctx, member:
    discord.Member, amount: int)`` — slot 1 (disbot/cogs/treasury_cog.py);
    discord.py bound each arg by POSITION. Scanning argv for the first
    digit token let a bare snowflake target double-read as the AMOUNT on
    `!treasury grant <bare_id> <amt>` (the #275 givexp misparse twin —
    the pool-balance check caught it loudly, but the parse was wrong)."""
    from sb.kernel.interaction.errors import ValidatorError

    amount = ctx.params.get("amount")
    if amount is None:
        argv = tuple(ctx.params.get("argv", ()) or ())
        if len(argv) > slot:
            amount = argv[slot]
    if amount is None:
        raise ValidatorError("amount", "➕ Give a number of coins.")
    try:
        # the Contribute modal submits a free-text field — the shipped
        # modal's non-numeric rejection, verbatim copy.
        amount = int(str(amount).strip())
    except ValueError:
        raise ValidatorError(
            "amount",
            f"❌ `{str(amount).strip()}` is not a whole number of coins.") from None
    if amount <= 0:
        raise ValidatorError("amount", "➕ Give a positive number of coins.")
    return amount


@workflow("treasury.record_contribute")
async def _record_contribute(conn, ctx: WorkflowContext) -> LegOutcome:
    """Debit the member, credit the pool — one txn; the debit audits itself
    on the economy ledger (the shipped debit_in_txn composition)."""
    uid, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    amount = _amount_from(ctx)
    now = _now(ctx)

    user_balance = await economy_store.try_debit_coins(
        conn, user_id=uid, guild_id=gid, amount=amount)
    if user_balance is None:
        balance = await economy_store.get_coins(uid, gid, conn=conn)
        raise economy_service.InsufficientFundsError(
            f"🏛️ Contributing **{amount}** 🪙 is more than your "
            f"**{balance}** 🪙.")
    await economy_store.insert_economy_audit(
        conn, guild_id=gid, user_id=uid, actor_id=uid, delta=-amount,
        new_balance=user_balance, reason=CONTRIBUTE_REASON)
    treasury_balance = await store.credit_treasury(
        conn, guild_id=gid, amount=amount, updated_at=now)

    ctx.params["_subject_id"] = uid
    ctx.params["_delta"] = -amount
    ctx.params["_new_balance"] = user_balance
    ctx.params["_reason"] = CONTRIBUTE_REASON
    return LegOutcome(
        step=StepResult(uid, "contribute", True),
        before={"treasury": treasury_balance - amount,
                "user": user_balance + amount},
        after={"treasury": treasury_balance, "user": user_balance,
               "amount": amount},
        payload={"treasury_balance": treasury_balance,
                 "user_balance": user_balance},
        user_message=(f"🏛️ Contributed **{amount:,}** 🪙 — the treasury now "
                      f"holds **{treasury_balance:,}** 🪙 (your balance: "
                      f"**{user_balance:,}** 🪙)."),
    )


@workflow("treasury.record_disburse")
async def _record_disburse(conn, ctx: WorkflowContext) -> LegOutcome:
    """Debit the pool (conditional — never overdraws), credit the target;
    the manager stays attributable as actor_id on the target's ledger row
    (shipped verbatim)."""
    from sb.kernel.interaction.errors import ValidatorError

    actor, gid = _actor_id(ctx), int(ctx.guild_id or 0)
    target = ctx.params.get("target_id") or ctx.params.get("member")
    if target is None:
        # POSITIONAL, argv[0] only — the shipped signature was
        # ``grant(ctx, member: discord.Member, amount: int)``
        # (disbot/cogs/treasury_cog.py): MemberConverter bound the FIRST
        # arg (mention or bare ID), never a later token.
        argv = tuple(ctx.params.get("argv", ()) or ())
        if argv:
            token = str(argv[0])
            stripped = token.strip("<@!>")
            if stripped.isdigit():
                target = stripped
            else:
                # bot1.py on_command_error BadArgument arm over
                # commands.MemberNotFound, byte-for-byte (treasury_cog
                # has no local error handler).
                raise ValidatorError(
                    "member",
                    f'⚠️ Bad argument: Member "{token}" not found.')
    if target is None:
        raise ValidatorError("member", "Usage: `!treasury grant @member <amount>`")
    target = int(str(target).strip("<@!>"))
    amount = _amount_from(ctx, slot=1)   # argv[1] is the amount slot
    now = _now(ctx)

    new_treasury = await store.try_debit_treasury(
        conn, guild_id=gid, amount=amount, updated_at=now)
    if new_treasury is None:
        available = await store.get_treasury(gid, conn=conn)
        raise ValidatorError(
            "amount",
            f"🏛️ The treasury only holds **{available}** 🪙 — not enough "
            f"to disburse **{amount}** 🪙.")
    user_balance = await economy_store.credit_coins(
        conn, user_id=target, guild_id=gid, amount=amount)
    await economy_store.insert_economy_audit(
        conn, guild_id=gid, user_id=target, actor_id=actor, delta=amount,
        new_balance=user_balance, reason=DISBURSE_REASON)

    ctx.params["_subject_id"] = target
    ctx.params["_delta"] = amount
    ctx.params["_new_balance"] = user_balance
    ctx.params["_reason"] = DISBURSE_REASON
    return LegOutcome(
        step=StepResult(target, "disburse", True),
        before={"treasury": new_treasury + amount,
                "user": user_balance - amount},
        after={"treasury": new_treasury, "user": user_balance,
               "amount": amount},
        payload={"treasury_balance": new_treasury,
                 "user_balance": user_balance},
        user_message=(f"🏛️ Disbursed **{amount:,}** 🪙 to <@{target}> — the "
                      f"treasury now holds **{new_treasury:,}** 🪙."),
    )


@workflow("treasury.balance_payload")
def _balance_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_subject_id", 0) or 0),
        "delta": int(ctx.params.get("_delta", 0) or 0),
        "new_balance": int(ctx.params.get("_new_balance", 0) or 0),
        "reason": str(ctx.params.get("_reason", "") or ""),
    }


_EMITS = (EventEmitSpec("economy.balance_changed",
                        WorkflowRef("treasury.balance_payload"),
                        DeliveryClass.BEST_EFFORT),)


def _op(op_key: str, verb: str, ref: str, authority: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="treasury", lane=WorkflowLane.DOMAIN,
        authority_ref=authority,
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=_EMITS)


CONTRIBUTE = _op("treasury.contribute", "treasury_contributed",
                 "treasury.record_contribute", "user")
DISBURSE = _op("treasury.disburse", "treasury_disbursed",
               "treasury.record_disburse", "staff")   # shipped manage_guild

_OPS = (CONTRIBUTE, DISBURSE)

_REF_TABLE = (
    ("treasury.record_contribute", _record_contribute),
    ("treasury.record_disburse", _record_disburse),
    ("treasury.balance_payload", _balance_payload),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
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
