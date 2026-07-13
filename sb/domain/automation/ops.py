"""The automation mutation lane — the K7 ``automation.add_rule`` compound
op (the K9 ``add_automation_rule`` apply lane; ORACLE
disbot/services/automation_mutation.AutomationMutationPipeline
.create_rule:118-220 + services/setup_operations.py:958-971 preset
expansion + :1387-1415 dispatcher arm @ f969b95).

The staged K9 payload carries ONLY ``template_slug`` (the preset_select
adapter's shape) — the DB leg resolves the slug against the carried
template catalogue (templates.py, the three preset-referenced slugs
verbatim), takes the rule name from the slug (the oracle preset
expansion: ``automation_rule_name=payload["template_slug"]``), and
inserts the rule DISABLED with the template's default trigger/action
configs. An unknown slug is REFUSED (fail-closed — the preview's
unknown-template warning class, now enforced at apply). ``scheduled_time``
is blocked at the service boundary with the oracle's copy verbatim
(``UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS`` — the cron parser never
shipped).

Divergences, ledgered: the ONE central audit row is engine-minted
(oracle: subsystem="automation", mutation_type="create_rule",
new_value=f"{trigger}->{action}" — carried in ``after``); the oracle's
advisory ``automation.rule_changed`` event is NOT emitted — its only
subscriber is the un-ported runtime consumer (the scheduler/executor
subsystem, the module's NAMED SUCCESSOR — see sb/domain/automation/
__init__.py), and a consumer-less durable event would be noise.
"""

from __future__ import annotations

import logging

from sb.domain.automation import store, templates
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

__all__ = ["UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS", "ensure_ops_refs",
           "register_ops"]

logger = logging.getLogger("sb.domain.automation")

#: known at the schema level but blocked for new rule installation until
#: cron parsing ships (oracle automation_registry.py:121, verbatim).
UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS: frozenset[str] = frozenset(
    {"scheduled_time"})


def _verr(message: str):
    """Copy-only ValidatorError (the D-0060/D-0061 refusal-copy posture)."""
    from sb.kernel.interaction.errors import ValidatorError

    return ValidatorError("", message)


@workflow("automation.record_add_rule")
async def _record_add_rule(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    slug = str(ctx.params.get("template_slug", "") or "").strip()
    template = templates.get_template(slug)
    if template is None:
        # fail-closed on an unknown slug (the preview warning class,
        # enforced at apply — preset_select.preview_warnings' wording).
        raise _verr(f"Unknown automation template slug `{slug}`.")
    if template.trigger_kind in UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS:
        # oracle copy, verbatim (automation_mutation.create_rule step 1).
        raise _verr(
            f"trigger_kind {template.trigger_kind!r} is known but not "
            f"installable yet; {template.trigger_kind} requires the "
            "cron-parser implementation before new rules can be created.")
    rule_id = await store.insert_rule(
        conn, guild_id=gid, name=template.slug,
        trigger_kind=template.trigger_kind, action_kind=template.action_kind,
        trigger_config=dict(template.default_trigger_config),
        action_config=dict(template.default_action_config),
        schedule=None, timezone="UTC",
        created_by=int(getattr(ctx.actor, "user_id", 0) or 0) or None)
    ctx.params["_rule_id"] = rule_id
    return LegOutcome(
        step=StepResult(rule_id, "add_rule", True),
        before=None,        # create path — no prior row (oracle prev=None)
        after={"rule": f"rule:{template.slug}", "enabled": False,
               "value": f"{template.trigger_kind}->{template.action_kind}"})


# --- privacy erasure body -------------------------------------------------------

@workflow("automation.tombstone_rule_creator")
async def _tombstone_rule_creator(conn, ctx: WorkflowContext) -> LegOutcome:
    """automation_rules erasure (S11 class 12 TOMBSTONE): scrub the
    subject's created_by pointer, keep the rule rows."""
    subject = int(ctx.params["subject_user_id"])
    rows = await store.tombstone_rule_creator(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "tombstone_rule_creator", True),
                      before={}, after={"rows": rows})


# --- the op spec ----------------------------------------------------------------

#: the K9 ``add_automation_rule`` apply lane: the oracle
#: AutomationMutationPipeline.create_rule as ONE K7 op. NATURAL_KEY —
#: ``UNIQUE (guild_id, name)`` IS the natural key: a duplicate insert
#: refuses instead of duplicating (rules are named per guild; the oracle
#: references them by name). Rules insert DISABLED (DDL DEFAULT FALSE —
#: "created disabled", the oracle final_review phase list).
#: ``domain``/``audit_verb`` carry the shipped audit vocabulary verbatim
#: (oracle emit_audit_action: subsystem="automation",
#: mutation_type="create_rule"). authority_ref="" = the ADMIN floor (the
#: setup apply gate's owner/admin class).
ADD_RULE = CompoundOpSpec(
    op_key="automation.add_rule", domain="automation",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("automation.record_add_rule"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="create_rule", emits=())

_OPS = (ADD_RULE,)

_REF_TABLE = (
    ("automation.record_add_rule", _record_add_rule),
    ("automation.tombstone_rule_creator", _tombstone_rule_creator),
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
