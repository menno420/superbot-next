"""The XP mutation lane (band 4) — K7 CompoundOpSpecs over the shipped
xp_service semantics (INV-G: one audited seam for every XP mutation).

Events carry the shipped names + payload keys VERBATIM:
  xp.awarded  (guild_id, user_id, delta, new_xp, new_level, source)
  xp.level_up (guild_id, user_id, new_level, source)
  xp.reset    (guild_id, user_id, actor_id, source)

``xp.level_up`` is CONDITIONAL — the payload builder returns ``None``
on a non-boundary award and the K7 emit loop SKIPS a None payload (the
additive kernel widening this band armed; D-0036). The import op emits
NOTHING by design (shipped: a bulk migration never spams the announce
channel and an absolute set has no per-message delta).
"""

from __future__ import annotations

from sb.domain.xp import store
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
from sb.spec.confirmation import Challenge, ConfirmationSpec
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, workflow

__all__ = [
    "EVT_LEVEL_UP",
    "EVT_XP_AWARDED",
    "EVT_XP_RESET",
    "register_ops",
]

#: shipped event names, verbatim (services/xp_service.py:38-40)
EVT_XP_AWARDED = "xp.awarded"
EVT_LEVEL_UP = "xp.level_up"
EVT_XP_RESET = "xp.reset"


def _actor_id(ctx: WorkflowContext) -> int:
    actor = getattr(ctx, "actor", None)
    return int(getattr(actor, "user_id", 0) or 0)


def _now(ctx: WorkflowContext) -> int:
    explicit = ctx.params.get("now")
    if explicit:
        return int(explicit)
    return int(ctx.clock().timestamp())


def _target_from(ctx: WorkflowContext) -> int:
    """target_id param > modal `user` field > argv mention > the actor."""
    target = ctx.params.get("target_id") or ctx.params.get("user")
    if target is None:
        argv = tuple(ctx.params.get("argv", ()) or ())
        for token in argv:
            stripped = str(token).strip("<@!>")
            if stripped.isdigit():
                target = stripped
                break
    if target is None:
        return _actor_id(ctx)
    return int(str(target).strip("<@!>"))


def _amount_from(ctx: WorkflowContext) -> int:
    from sb.kernel.interaction.errors import ValidatorError

    raw = ctx.params.get("amount")
    if raw is None:
        argv = tuple(ctx.params.get("argv", ()) or ())
        for token in argv:
            if str(token).lstrip("-").isdigit():
                raw = token
                break
    try:
        amount = int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValidatorError("❌ Amount must be a whole number of XP.")
    return amount


# --- DB legs -----------------------------------------------------------------------

@workflow("xp.record_award")
async def _record_award(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.kernel.interaction.errors import ValidatorError

    gid = int(ctx.guild_id or 0)
    target = _target_from(ctx)
    amount = _amount_from(ctx)
    if amount <= 0:
        raise ValidatorError("❌ Amount must be positive.")
    source = str(ctx.params.get("source", "") or "admin:givexp")
    now = _now(ctx)

    new_xp, new_level, leveled_up = await store.add_xp(
        conn, user_id=target, guild_id=gid, amount=amount, now=now)

    ctx.params["_subject_id"] = target
    ctx.params["_delta"] = amount
    ctx.params["_new_xp"] = new_xp
    ctx.params["_new_level"] = new_level
    ctx.params["_leveled_up"] = leveled_up
    ctx.params["_source"] = source
    return LegOutcome(
        step=StepResult(target, "award", True),
        before={"xp": new_xp - amount},
        after={"new_xp": new_xp, "new_level": new_level,
               "leveled_up": leveled_up, "delta": amount, "source": source},
    )


@workflow("xp.record_reset")
async def _record_reset(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    target = _target_from(ctx)
    source = str(ctx.params.get("source", "") or "admin:resetxp")
    removed = await store.delete_xp(conn, user_id=target, guild_id=gid)

    ctx.params["_subject_id"] = target
    ctx.params["_source"] = source
    return LegOutcome(
        step=StepResult(target, "reset", True),
        before={"had_row": removed > 0},
        after={"rows_removed": removed, "source": source},
    )


@workflow("xp.record_import")
async def _record_import(conn, ctx: WorkflowContext) -> LegOutcome:
    """Raise-only batch import (shipped import_level over a ScanPlan's
    records) — max-reduced per user, idempotent re-runs, NO events."""
    from sb.domain.xp.levels import total_xp_for_level
    from sb.domain.xp.migrate import reduce_max_levels
    from sb.kernel.interaction.errors import ValidatorError

    gid = int(ctx.guild_id or 0)
    raw = tuple(ctx.params.get("records", ()) or ())
    if not raw:
        raise ValidatorError("❌ Nothing to import — no (user, level) records.")
    source = str(ctx.params.get("source", "") or "import:generic")
    now = _now(ctx)

    best = reduce_max_levels((int(u), int(lv)) for u, lv in raw)
    raised = 0
    for user_id, level in sorted(best.items()):
        if level < 0:
            raise ValidatorError(f"❌ Level must be >= 0, got {level}.")
        _, _, did_raise = await store.set_imported_xp(
            conn, user_id=user_id, guild_id=gid,
            xp=total_xp_for_level(level), level=level, now=now)
        if did_raise:
            raised += 1

    return LegOutcome(
        step=StepResult(_actor_id(ctx), "import", True),
        before={},
        after={"users": len(best), "raised": raised, "source": source},
    )


# --- the INV-G repair leg (sweep-invoked; pure DB, atomic_db_only) --------------------

@workflow("xp.record_repair_level")
async def _record_repair_level(conn, ctx: WorkflowContext) -> LegOutcome:
    """Deterministic level re-derivation for a flagged row: level :=
    level_progress(xp).level (the xp column IS the ground truth; the
    monotonic-advance race is the only shipped drift source)."""
    from sb.domain.xp.levels import level_progress
    from sb.kernel.db.pool import execute, fetchone
    from sb.kernel.interaction.errors import ValidatorError

    violation = dict(ctx.params.get("violation", {}) or {})
    row_id = str(violation.get("row_id", "") or "")
    try:
        user_id, guild_id = (int(part) for part in row_id.split(":", 1))
    except ValueError:
        raise ValidatorError(f"❌ Unparseable xp violation row_id {row_id!r}.")
    row = await fetchone(
        "SELECT xp, level FROM xp WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    if row is None:
        return LegOutcome(step=StepResult(user_id, "repair_level", True),
                          before={}, after={"repaired": False,
                                            "reason": "row_gone"})
    derived, _, _ = level_progress(int(row["xp"]))
    await execute(
        "UPDATE xp SET level=$3 WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id, derived), conn=conn)
    return LegOutcome(
        step=StepResult(user_id, "repair_level", True),
        before={"level": int(row["level"])},
        after={"repaired": True, "level": derived})


# --- privacy erasure body ------------------------------------------------------------

@workflow("xp.erase_subject_xp")
async def _erase_subject_xp(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_xp(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_xp", True),
                      before={}, after={"rows": rows})


# --- event payload builders (shipped payload keys, verbatim) --------------------------

@workflow("xp.awarded_payload")
def _awarded_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_subject_id", 0) or 0),
        "delta": int(ctx.params.get("_delta", 0) or 0),
        "new_xp": int(ctx.params.get("_new_xp", 0) or 0),
        "new_level": int(ctx.params.get("_new_level", 0) or 0),
        "source": str(ctx.params.get("_source", "") or ""),
    }


@workflow("xp.levelup_payload")
def _levelup_payload(ctx: WorkflowContext, result) -> dict | None:
    """CONDITIONAL: None on a non-boundary award => the emit is skipped
    (the D-0036 kernel widening)."""
    if not ctx.params.get("_leveled_up"):
        return None
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_subject_id", 0) or 0),
        "new_level": int(ctx.params.get("_new_level", 0) or 0),
        "source": str(ctx.params.get("_source", "") or ""),
    }


@workflow("xp.reset_payload")
def _reset_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "user_id": int(ctx.params.get("_subject_id", 0) or 0),
        "actor_id": _actor_id(ctx),
        "source": str(ctx.params.get("_source", "") or ""),
    }


_AWARD_EMITS = (
    EventEmitSpec(EVT_XP_AWARDED, WorkflowRef("xp.awarded_payload"),
                  DeliveryClass.BEST_EFFORT),   # OD-1 v1 default; ALO rides the ruling
    EventEmitSpec(EVT_LEVEL_UP, WorkflowRef("xp.levelup_payload"),
                  DeliveryClass.BEST_EFFORT),
)
_RESET_EMITS = (
    EventEmitSpec(EVT_XP_RESET, WorkflowRef("xp.reset_payload"),
                  DeliveryClass.BEST_EFFORT),
)


def _op(op_key: str, verb: str, leg_ref: str, *,
        emits: tuple[EventEmitSpec, ...] = (),
        leg_reversibility: str = "reversible",
        confirmation: ConfirmationSpec | None = None) -> CompoundOpSpec:
    """NATURAL_KEY: the upsert/raise-only/delete statements decide-and-
    write in one statement (the shipped race closures)."""
    return CompoundOpSpec(
        op_key=op_key, domain="xp", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      leg_reversibility),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=emits, confirmation=confirmation)


AWARD = _op("xp.award", "xp_awarded", "xp.record_award", emits=_AWARD_EMITS)
RESET = _op("xp.reset", "xp_reset", "xp.record_reset", emits=_RESET_EMITS,
            leg_reversibility="irreversible",
            confirmation=ConfirmationSpec(reversibility="irreversible",
                                          challenge=Challenge.TYPED_PHRASE))
IMPORT = _op("xp.import_levels", "xp_imported", "xp.record_import")
REPAIR = _op("xp.repair_level_consistency", "xp_level_repaired",
             "xp.record_repair_level")

_OPS = (AWARD, RESET, IMPORT, REPAIR)

_REF_TABLE = (
    ("xp.record_award", _record_award),
    ("xp.record_reset", _record_reset),
    ("xp.record_import", _record_import),
    ("xp.record_repair_level", _record_repair_level),
    ("xp.erase_subject_xp", _erase_subject_xp),
    ("xp.awarded_payload", _awarded_payload),
    ("xp.levelup_payload", _levelup_payload),
    ("xp.reset_payload", _reset_payload),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

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
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
