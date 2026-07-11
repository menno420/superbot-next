"""Games substrate K7 lanes (band 6) — the GC/recovery sweep row op, the
privacy-erasure bodies for the two substrate stores, and the SHARED
game_xp / balance emit builders every game op reuses.

Emit conventions (all games ride these):

* ``games.balance_payload_N`` — reads the Nth entry of
  ``ctx.params["_balance_changes"]`` (a list of (user_id, delta,
  new_balance, reason) tuples stamped by the leg); returns None when the
  entry does not exist — the D-0036 conditional-emission rider skips it,
  so ops declare the maximum emit fan-out and the leg decides at runtime.
* ``games.game_xp_awarded_payload`` / ``games.game_xp_levelup_payload`` —
  read ``ctx.params["_gxp"]`` (a GameXpAward stamped by the leg); the
  level_up builder returns None on a non-boundary award.
"""

from __future__ import annotations

from sb.domain.games import store, wager
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["register_ops"]


# --- the GC / recovery sweep lane ----------------------------------------------------


@workflow("games.record_gc_sweep_row")
async def _record_gc_sweep_row(conn, ctx: WorkflowContext) -> LegOutcome:
    """Refund a stranded row's staked ``bet`` (ledger-audited) and delete
    the row PRECISELY by id — one txn (the shipped GC refund convention;
    a raced fresh game at the same natural key is untouched).

    Row-consumption guard (the same wallet-race class as F-001/F-002,
    caught in review — the GC driver's ``store.list_stale``/``list_active``
    scan is an UNLOCKED snapshot, so a row can legitimately be settled by
    its own player between that scan and this leg's turn): delete FIRST,
    by id, and credit ONLY when the delete actually removed a row. A bare
    ``DELETE ... WHERE id=$1`` already takes the row's lock for the life of
    this txn — a concurrent player settle that deletes the SAME row first
    makes this delete affect zero rows, so the refund is skipped instead of
    double-paying on top of the player's own settle. Reading the refund
    amount from the ctx-supplied (possibly stale) snapshot stays safe: a
    live blackjack/rps bet never changes after deal, only reachable *while
    the row still exists* — exactly the case this guard already requires."""
    row = dict(ctx.params["row"])
    reason = str(ctx.params.get("reason") or "games:gc_refund")
    state = dict(row.get("state") or {})
    bet = state.get(wager.STAKE_KEY)
    deleted = await store.delete_checkpoint_by_id(conn, row_id=int(row["id"]))
    changes: list[tuple[int, int, int, str]] = []
    if deleted and isinstance(bet, int) and bet > 0:
        balance = await wager.credit_in_txn(
            conn, guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]), amount=bet, reason=reason,
            actor_id=int(row["user_id"]))
        changes.append((int(row["user_id"]), bet, balance, reason))
    ctx.params["_balance_changes"] = changes
    return LegOutcome(
        step=StepResult(int(row["user_id"]), "gc_sweep", True),
        before={"state": state},
        after={"deleted": deleted, "refunded": bet if changes else 0},
    )


# --- privacy-erasure bodies (store-declared refs; flag-18 discipline) -----------------


@workflow("games.discard_subject_sessions")
async def _discard_subject_sessions(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_game_state(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "discard_subject_sessions", True),
                      before={}, after={"rows": rows})


@workflow("games.erase_subject_game_xp")
async def _erase_subject_game_xp(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_game_xp(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_game_xp", True),
                      before={}, after={"rows": rows})


# --- shared emit builders --------------------------------------------------------------


def _balance_builder(index: int):
    def _build(ctx: WorkflowContext, result) -> dict | None:
        changes = list(ctx.params.get("_balance_changes") or ())
        if index >= len(changes):
            return None                      # conditional emission (D-0036)
        uid, delta, new_balance, reason = changes[index]
        return {"guild_id": int(ctx.guild_id or 0), "user_id": int(uid),
                "delta": int(delta), "new_balance": int(new_balance),
                "reason": str(reason)}
    return _build


_balance_payload_0 = workflow("games.balance_payload_0")(_balance_builder(0))
_balance_payload_1 = workflow("games.balance_payload_1")(_balance_builder(1))


@workflow("games.game_xp_awarded_payload")
def _gxp_awarded_payload(ctx: WorkflowContext, result) -> dict | None:
    award = ctx.params.get("_gxp")
    if award is None or getattr(award, "amount", 0) <= 0:
        return None
    return {"guild_id": int(ctx.guild_id or 0),
            "user_id": int(getattr(ctx.actor, "user_id", 0) or 0),
            "game": award.game, "action": award.action,
            "delta": int(award.amount), "new_game_xp": int(award.new_game_xp),
            "new_total_xp": int(award.new_total_xp)}


@workflow("games.game_xp_levelup_payload")
def _gxp_levelup_payload(ctx: WorkflowContext, result) -> dict | None:
    award = ctx.params.get("_gxp")
    if award is None or not getattr(award, "leveled_up", False):
        return None                          # non-boundary award: no emit
    return {"guild_id": int(ctx.guild_id or 0),
            "user_id": int(getattr(ctx.actor, "user_id", 0) or 0),
            "game": award.game, "new_level": int(award.new_level)}


# --- op specs ----------------------------------------------------------------------------

GC_SWEEP_ROW = CompoundOpSpec(
    op_key="games.gc_sweep_row", domain="games", lane=WorkflowLane.DOMAIN,
    # No command/panel routes at this op — fired only by the session_gc
    # sweep under SYSTEM_ACTOR (the xp.repair precedent: tier lane floor).
    authority_ref="user",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("games.record_gc_sweep_row"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="game_session_swept", emits=())

_OPS = (GC_SWEEP_ROW,)

_REF_TABLE = (
    ("games.record_gc_sweep_row", _record_gc_sweep_row),
    ("games.discard_subject_sessions", _discard_subject_sessions),
    ("games.erase_subject_game_xp", _erase_subject_game_xp),
    ("games.balance_payload_0", _balance_payload_0),
    ("games.balance_payload_1", _balance_payload_1),
    ("games.game_xp_awarded_payload", _gxp_awarded_payload),
    ("games.game_xp_levelup_payload", _gxp_levelup_payload),
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
