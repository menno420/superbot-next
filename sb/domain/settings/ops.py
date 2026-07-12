"""The settings mutation lane (band 1) — K7 CompoundOpSpecs over the
shipped `SettingsMutationPipeline` semantics (disbot
services/settings_mutation.py): coerce → validate → capability → DB write +
audit in ONE transaction → advisory ``settings.changed`` AFTER commit
(best-effort), verbatim as lane structure.

Design-spec §4.1: settings NEVER writes — these ops (four operator lanes +
the S15 `settings.platform_latch` system lane) are the only write paths to
the `settings` / `subsystem_bindings` tables (sole_writer
EngineRef("settings.store"); the leg helpers live in sb/kernel/db/settings).

Authority: op-level `authority_ref=""` = the ADMIN floor — the shipped v1
policy ("every capability resolves to the administrator tier"); per-spec
`capability_required` narrowing rides the governance band's capability
resolver when it ports (D-0025). Coercion/validation runs in
service.coerce_value BEFORE the op is invoked (the resolver/panel edit path)
AND the DB leg re-checks declaredness — an undeclared key is refused.

Idempotency: NATURAL_KEY — the upsert/delete is intrinsically once
(ON CONFLICT / keyed DELETE), the §2.2 posture for keyed config writes.
"""

from __future__ import annotations

from sb.kernel.db import settings as db_settings
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

__all__ = [
    "EVT_BINDINGS_CHANGED",
    "EVT_SETTINGS_CHANGED",
    "SET_SCALAR",
    "CLEAR_SCALAR",
    "BIND",
    "UNBIND",
    "PLATFORM_LATCH",
    "register_ops",
]

#: shipped event name, verbatim (services/settings_mutation.py:63)
EVT_SETTINGS_CHANGED = "settings.changed"

#: shipped event name, verbatim (services/binding_mutation.py
#: EVT_BINDING_CHANGED — the binding lane's own advisory;
#: goldens/economy/sweep_setlogchannel pins the payload bytes)
EVT_BINDINGS_CHANGED = "bindings.changed"


def _declared_or_refuse(key: str) -> None:
    """§4.1 seam authority: a write against an undeclared persisted key is
    refused (declared = some registered SettingDeclaration maps to it)."""
    from sb.kernel import settings as ksettings

    for decl in ksettings.iter_declarations():
        if ksettings.persisted_key(decl.subsystem, decl.name) == key:
            return
    raise ValueError(f"setting key {key!r} is not declared (no raw-KV writes)")


@workflow("settings.write_scalar")
async def _write_scalar(conn, ctx: WorkflowContext) -> LegOutcome:
    key = str(ctx.params["key"])
    value = str(ctx.params["value"])
    _declared_or_refuse(key)
    prior = await db_settings.upsert_setting(
        conn, guild_id=int(ctx.params.get("scope_guild_id", ctx.guild_id or 0)),
        key=key, value=value)
    return LegOutcome(
        step=StepResult(0, "write_scalar", True),
        before={"key": key, "value": prior},
        after={"key": key, "value": value},
    )


@workflow("settings.erase_scalar")
async def _erase_scalar(conn, ctx: WorkflowContext) -> LegOutcome:
    key = str(ctx.params["key"])
    prior = await db_settings.delete_setting(
        conn, guild_id=int(ctx.params.get("scope_guild_id", ctx.guild_id or 0)),
        key=key)
    return LegOutcome(
        step=StepResult(0, "erase_scalar", True),
        before={"key": key, "value": prior},
        after={"key": key, "value": None},
    )


def _stash_binding_change(ctx: WorkflowContext, *, mutation_id: str,
                          old_status: str, old_target_id: int | None,
                          new_status: str,
                          new_target_id: int | None) -> None:
    """The ctx.params side-channel (the karma/economy `_underscore`
    precedent — ctx.params is the SAME dict the caller passed): the
    bindings.changed payload builder reads these after the leg txn."""
    params = ctx.params
    if isinstance(params, dict):
        params["_binding_mutation_id"] = mutation_id
        params["_binding_old_status"] = old_status
        params["_binding_old_target_id"] = old_target_id
        params["_binding_new_status"] = new_status
        params["_binding_new_target_id"] = new_target_id


@workflow("settings.write_binding")
async def _write_binding(conn, ctx: WorkflowContext) -> LegOutcome:
    """The shipped BindingMutationPipeline.set_binding DB leg (oracle
    services/binding_mutation.py): upsert the binding row to 'bound',
    then append the binding_audit_log row IN the same txn (write-then-
    audit ordering; goldens/economy/sweep_setlogchannel pins both rows'
    bytes). The bindings.changed advisory rides the op's BEST_EFFORT
    emit — after commit, the shipped posture."""
    import uuid

    guild_id = int(ctx.guild_id or 0)
    subsystem = str(ctx.params["subsystem"])
    name = str(ctx.params["name"])
    target_id = int(ctx.params["resource_id"])
    prior = await db_settings.upsert_binding(
        conn, guild_id=guild_id, subsystem=subsystem, name=name,
        kind=str(ctx.params["kind"]), resource_id=target_id,
    )
    old_target = None if prior is None else prior["target_id"]
    # absent row = 'unresolved' — the shipped vocabulary for never-bound.
    old_status = "unresolved" if prior is None else str(prior["status"])
    mutation_id = str(uuid.uuid4())
    await db_settings.insert_binding_audit(
        conn, mutation_id=mutation_id, guild_id=guild_id,
        subsystem=subsystem, binding_name=name,
        actor_type=str(getattr(ctx.actor, "actor_type", "") or "user"),
        actor_id=int(getattr(ctx.actor, "user_id", 0) or 0),
        action="set", old_target_id=old_target, new_target_id=target_id,
        old_status=old_status, new_status="bound",
    )
    _stash_binding_change(ctx, mutation_id=mutation_id,
                          old_status=old_status, old_target_id=old_target,
                          new_status="bound", new_target_id=target_id)
    return LegOutcome(
        step=StepResult(0, "write_binding", True),
        before={"resource_id": old_target},
        after={"resource_id": target_id},
    )


@workflow("settings.erase_binding")
async def _erase_binding(conn, ctx: WorkflowContext) -> LegOutcome:
    """The shipped clear_binding DB leg — keyed DELETE + the 'clear'
    audit row in the same txn (no golden pins the clear bytes; the
    semantics mirror the oracle 022 action vocabulary)."""
    import uuid

    guild_id = int(ctx.guild_id or 0)
    subsystem = str(ctx.params["subsystem"])
    name = str(ctx.params["name"])
    removed = await db_settings.delete_binding(
        conn, guild_id=guild_id, subsystem=subsystem, name=name,
    )
    old_target = None if removed is None else removed["target_id"]
    old_status = "unresolved" if removed is None else str(removed["status"])
    mutation_id = str(uuid.uuid4())
    await db_settings.insert_binding_audit(
        conn, mutation_id=mutation_id, guild_id=guild_id,
        subsystem=subsystem, binding_name=name,
        actor_type=str(getattr(ctx.actor, "actor_type", "") or "user"),
        actor_id=int(getattr(ctx.actor, "user_id", 0) or 0),
        action="clear", old_target_id=old_target, new_target_id=None,
        old_status=old_status, new_status="unresolved",
    )
    _stash_binding_change(ctx, mutation_id=mutation_id,
                          old_status=old_status, old_target_id=old_target,
                          new_status="unresolved", new_target_id=None)
    return LegOutcome(
        step=StepResult(0, "erase_binding", True),
        before={"bound_rows_removed": 0 if removed is None else 1},
        after={"resource_id": None},
    )


@workflow("settings.write_platform_latch")
async def _write_platform_latch(conn, ctx: WorkflowContext) -> LegOutcome:
    """The S15 durable-latch write (ORDER 004 item 4 — K7 sole-writer
    alignment): `platform.*` rows are kernel-owned one-way markers, NOT
    SettingDeclarations (declaring them would surface kernel latches as
    operator-editable settings), so this leg fences on the prefix instead
    of `_declared_or_refuse` — still no raw-KV write path."""
    key = str(ctx.params["key"])
    if not key.startswith("platform."):
        raise ValueError(
            f"platform_latch writes only `platform.*` keys, got {key!r}")
    value = str(ctx.params["value"])
    prior = await db_settings.upsert_setting(conn, guild_id=0, key=key,
                                             value=value)
    return LegOutcome(
        step=StepResult(0, "write_platform_latch", True),
        before={"key": key, "value": prior},
        after={"key": key, "value": value},
    )


# --- privacy erasure body ---------------------------------------------------------

@workflow("settings.tombstone_binding_audit")
async def _tombstone_binding_audit(conn, ctx: WorkflowContext) -> LegOutcome:
    """binding_audit_log erasure (S11 class 12 TOMBSTONE — the governance
    tombstone_subject_audit twin): scrub the subject's actor_id in place,
    keep the forensic skeleton."""
    subject = int(ctx.params["subject_user_id"])
    rows = await db_settings.tombstone_binding_audit_actor(
        conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "tombstone_binding_audit", True),
                      before={}, after={"rows": rows})


@workflow("settings.changed_payload")
def _changed_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "key": str(ctx.params.get("key", ctx.params.get("name", ""))),
        "subsystem": str(ctx.params.get("subsystem", "")),
    }


@workflow("settings.binding_changed_payload")
def _binding_changed_payload(ctx: WorkflowContext, result) -> dict:
    """The shipped bindings.changed payload, verbatim shape —
    goldens/economy/sweep_setlogchannel pins every key (the leg stashed
    the values on the ctx.params side-channel)."""
    return {
        "guild_id": int(ctx.guild_id or 0),
        "subsystem": str(ctx.params.get("subsystem", "")),
        "binding_name": str(ctx.params.get("name", "")),
        "mutation_id": str(ctx.params.get("_binding_mutation_id", "")),
        "old_status": ctx.params.get("_binding_old_status"),
        "new_status": ctx.params.get("_binding_new_status"),
        "old_target_id": ctx.params.get("_binding_old_target_id"),
        "new_target_id": ctx.params.get("_binding_new_target_id"),
        "occurred_at": ctx.clock().isoformat(),
    }


_EMITS = (EventEmitSpec(EVT_SETTINGS_CHANGED,
                        WorkflowRef("settings.changed_payload"),
                        DeliveryClass.BEST_EFFORT),)

#: the binding lane's own advisory (the shipped BindingMutationPipeline
#: emitted bindings.changed, never settings.changed — the previous
#: settings.changed emit on BIND/UNBIND was a port-side invention the
#: sweep_setlogchannel golden reds).
_BINDING_EMITS = (EventEmitSpec(EVT_BINDINGS_CHANGED,
                                WorkflowRef("settings.binding_changed_payload"),
                                DeliveryClass.BEST_EFFORT),)

SET_SCALAR = CompoundOpSpec(
    op_key="settings.set_scalar",
    domain="settings",
    lane=WorkflowLane.SCALAR,
    authority_ref="",                     # ADMIN floor (shipped v1 policy)
    legs=(LegSpec("write", LegKind.DB, WorkflowRef("settings.write_scalar"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY,
    dedup_key=None,
    audit_verb="setting_set",
    emits=_EMITS,
)

CLEAR_SCALAR = CompoundOpSpec(
    op_key="settings.clear_scalar",
    domain="settings",
    lane=WorkflowLane.SCALAR,
    authority_ref="",
    legs=(LegSpec("erase", LegKind.DB, WorkflowRef("settings.erase_scalar"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY,
    dedup_key=None,
    audit_verb="setting_cleared",
    emits=_EMITS,
)

BIND = CompoundOpSpec(
    op_key="settings.bind",
    domain="settings",
    lane=WorkflowLane.BINDING,
    authority_ref="",
    legs=(LegSpec("write", LegKind.DB, WorkflowRef("settings.write_binding"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY,
    dedup_key=None,
    audit_verb="binding_set",
    emits=_BINDING_EMITS,
)

UNBIND = CompoundOpSpec(
    op_key="settings.unbind",
    domain="settings",
    lane=WorkflowLane.BINDING,
    authority_ref="",
    legs=(LegSpec("erase", LegKind.DB, WorkflowRef("settings.erase_binding"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY,
    dedup_key=None,
    audit_verb="binding_cleared",
    emits=_BINDING_EMITS,
)

PLATFORM_LATCH = CompoundOpSpec(
    op_key="settings.platform_latch",
    domain="settings",
    lane=WorkflowLane.SCALAR,
    authority_ref="",                     # system actor rides the K6 step-1 bypass
    legs=(LegSpec("write", LegKind.DB,
                  WorkflowRef("settings.write_platform_latch"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY,
    dedup_key=None,
    audit_verb="platform_latch_set",
    emits=(),                             # kernel marker, not operator config —
                                          # no advisory settings.changed
)

_OPS = (SET_SCALAR, CLEAR_SCALAR, BIND, UNBIND, PLATFORM_LATCH)


def register_ops() -> None:
    """Register the four ops (idempotent — REGISTRY tolerates identical
    re-registration; called from the manifest module at compile/import)."""
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise


def ensure_ops_refs() -> None:
    """Idempotent re-arm of the leg-handler/payload WorkflowRefs."""
    from sb.spec.refs import is_registered, workflow as _workflow

    for name, fn in (
        ("settings.write_scalar", _write_scalar),
        ("settings.erase_scalar", _erase_scalar),
        ("settings.write_binding", _write_binding),
        ("settings.erase_binding", _erase_binding),
        ("settings.write_platform_latch", _write_platform_latch),
        ("settings.tombstone_binding_audit", _tombstone_binding_audit),
        ("settings.changed_payload", _changed_payload),
        ("settings.binding_changed_payload", _binding_changed_payload),
    ):
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
