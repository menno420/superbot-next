"""The routing mutation lane — the K7 ``routing.set_policy`` compound op
(the K9 ``set_cog_routing`` apply lane; ORACLE
disbot/services/command_routing.set_policy:88-146 +
services/setup_operations._apply_set_cog_routing:1559-1625 @ f969b95).

The oracle's canonical routing write is read-old → upsert → audit with
the REAL previous value ("no caller can write silently or lose the
previous state"); here the same shape rides the K7 discipline: the DB
leg reads the old row into ``LegOutcome.before`` (the engine's central
audit row carries it as ``prev_value``), performs the ON CONFLICT
upsert, and reports the new flag in ``after``. Divergences, ledgered:
the audit ``target`` is the op_key (the engine's fixed column) — the
oracle's ``{scope_type}:{scope_id|'guild'}:{cog_name}`` target string
rides ``after["target"]`` instead; the mutation_id is engine-minted.

Validation is the oracle dispatcher arm verbatim: ``scope_type`` ∈
{guild, category, channel} (``_ROUTING_SCOPE_TYPES``), a non-empty
``cog_name``, a non-guild scope requires ``scope_id`` (guild scope
forces it NULL), and the enabled flag defaults TRUE "so a drafting bug
doesn't silently disable a cog" (``_coerce_routing_enabled``).

NO dispatch-time command enforcement is declared here — the oracle has
none (routing is consulted by the access projection + the setup
dispatcher's change-plan read only; see routing.py's module ledger).
"""

from __future__ import annotations

import logging

from sb.domain.server_management import routing as store
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

__all__ = ["ensure_ops_refs", "register_ops"]

logger = logging.getLogger("sb.domain.server_management")


def _verr(message: str):
    """Copy-only ValidatorError — the raise-site sentence IS the user
    copy (the D-0060/D-0061 refusal-copy posture, the role-ops twin)."""
    from sb.kernel.interaction.errors import ValidatorError

    return ValidatorError("", message)


def _enabled_label(enabled: bool | None) -> str | None:
    """The oracle audit value vocabulary (command_routing._enabled_label,
    verbatim): "enabled" / "disabled" / None (no prior row)."""
    if enabled is None:
        return None
    return "enabled" if enabled else "disabled"


@workflow("routing.record_set_policy")
async def _record_set_policy(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    scope_type = str(ctx.params.get("scope_type", "") or "")
    if scope_type not in store.KNOWN_SCOPES:
        # oracle _apply_set_cog_routing's scope guard.
        raise _verr(f"Unknown routing scope `{scope_type}`.")
    cog_name = str(ctx.params.get("cog_name", "") or "").strip()
    if not cog_name:
        # oracle guard: value = non-empty cog name.
        raise _verr("A cog name is required.")
    raw_scope_id = ctx.params.get("scope_id")
    if scope_type == "guild":
        scope_id = None          # guild scope forces scope_id=None (oracle)
    else:
        if raw_scope_id is None:
            raise _verr(
                f"A {scope_type} id is required for {scope_type}-scope "
                "routing.")
        scope_id = int(raw_scope_id)
    # _coerce_routing_enabled: defaults True so a drafting bug doesn't
    # silently disable a cog (oracle setup_operations.py:1517-1533).
    raw_enabled = ctx.params.get("enabled")
    if isinstance(raw_enabled, str):
        enabled = raw_enabled.strip().lower() != "false"
    else:
        enabled = True if raw_enabled is None else bool(raw_enabled)
    # read-old → upsert: the REAL prev_value (oracle set_policy:88).
    old_row = await store.get_policy(gid, scope_type, scope_id, cog_name,
                                     conn=conn)
    old_enabled = bool(old_row["enabled"]) if old_row is not None else None
    await store.upsert_policy(
        conn, guild_id=gid, scope_type=scope_type, scope_id=scope_id,
        cog_name=cog_name, enabled=enabled,
        actor_id=int(getattr(ctx.actor, "user_id", 0) or 0) or None)
    # the oracle audit target string rides `after` (module docstring).
    target = (f"{scope_type}:"
              f"{scope_id if scope_id is not None else 'guild'}:{cog_name}")
    return LegOutcome(
        step=StepResult(gid, "set_policy", True),
        before={"enabled": _enabled_label(old_enabled)},
        after={"enabled": _enabled_label(enabled), "target": target})


# --- privacy erasure body -------------------------------------------------------

@workflow("routing.tombstone_policy_actor")
async def _tombstone_policy_actor(conn, ctx: WorkflowContext) -> LegOutcome:
    """command_routing_policy erasure (S11 class 12 TOMBSTONE — the
    governance tombstone_subject_audit twin): scrub the subject's
    actor_id pointer in place, keep the policy rows."""
    subject = int(ctx.params["subject_user_id"])
    rows = await store.tombstone_policy_actor(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "tombstone_policy_actor", True),
                      before={}, after={"rows": rows})


# --- the op spec ----------------------------------------------------------------

#: the K9 ``set_cog_routing`` apply lane: the oracle command_routing
#: .set_policy as ONE K7 op. NATURAL_KEY — the write is an ON CONFLICT
#: upsert keyed on (guild, scope_type, COALESCE(scope_id,-1), cog_name),
#: intrinsically once (the §2.2 posture for keyed config writes).
#: ``domain``/``audit_verb`` carry the shipped audit vocabulary verbatim
#: (oracle emit_audit_action: subsystem="cog_routing",
#: mutation_type="set_cog_routing"). authority_ref="" = the ADMIN floor
#: (the setup apply gate's owner/admin class — same as the settings ops
#: the staged drafts already ride).
SET_POLICY = CompoundOpSpec(
    op_key="routing.set_policy", domain="cog_routing",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("routing.record_set_policy"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="set_cog_routing", emits=())

_OPS = (SET_POLICY,)

_REF_TABLE = (
    ("routing.record_set_policy", _record_set_policy),
    ("routing.tombstone_policy_actor", _tombstone_policy_actor),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; engine resolves via REGISTRY
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
    register_ops()
