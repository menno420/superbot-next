"""Setup-lane channel-provisioning recovery (D-0077) — the create-channel
EFFECT leg's compensator class, defined AHEAD of the setup ops that will
reference it.

The D-0030 named successor slice armed the ChannelStateActions
create/delete surface (sb/domain/channel/service.py + the capture twin);
the setup/quicksetup flip lane declares the ops. The ruling
(docs/decisions.md D-0077): a setup-lane channel CREATE that runs as an
EFFECT leg AFTER a committed DB leg is compensated by DELETING the
created channel — id-guarded (only the exact channel id the create leg
stashed in ``ctx.params["_created_channel_id"]``), best-effort (a failed
delete degrades to an operator finding, never a raise), NotFound treated
as success (the port contract: already-gone IS the goal state — the
oracle's delete_setup_channel ``except discord.NotFound: return True``).
Oracle precedent for the class: disbot/services/ticket_mutation.py
compensates create-with-DB-follow-up by delete
(``await channel.delete(reason="Ticket row insert failed")``).

The oracle's own SETUP lane sequences the create BEFORE any DB write and
never rollback-deletes (its deletes are separate deliberate cleanup ops,
name-guarded) — an op that mirrors that sequencing (the Discord call
INSIDE the DB leg, the moderation.timeout posture) needs NO compensator.
This handler exists for the DB-first leg shape only; whenever the create
leg sits after a DB leg it MUST declare
``compensator=WorkflowRef("setup.compensate_create_channel")``.

The setup flip (this slice) declared the compound ops — and took the
D-0065 create-BEFORE-DB shape D-0077's contrast clause sanctioned: the
oracle's own sequencing (views/setup/essential_setup.py +
wizard.open_setup_workspace: resume READ → ensure_setup_channel → the
workspace channel.send → only then the session writes) runs the Discord
calls INSIDE the record leg, BEFORE the row upsert — a failed row write
aborts the txn and leaves channel + card standing, exactly like the
oracle (which never rollback-deleted its workspace). No session-write leg
therefore declares ``compensator=`` and the allowlist stays EMPTY; the
``setup.compensate_create_channel`` handler below stays the RULED class
for any FUTURE DB-first leg shape (D-0077's mandate binds the moment a
create leg sits after a committed DB leg).

The compound-ops slice landed the first WIRED consumer:
``setup.ensure_channel`` (the logging_presets ``create_channel`` named
successor — the oracle ResourceProvisioningPipeline's reachable core as
one K7 op: name-based reuse or create → slot bind → audit). Its create
EFFECT leg declares ``compensator=WorkflowRef("setup.compensate_create_
channel")`` per the COMPENSATABLE-EFFECT grammar fence — id-guarded on
the same ``_created_channel_id`` stash contract; the BIND leg carries NO
compensator by DESIGN (the oracle: "Binding failure does NOT roll back
the created Discord resource — it is audited as ``binding_failed``",
resource_provisioning.py:52-55)."""

from __future__ import annotations

import logging

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
from sb.spec.outcomes import SUCCESS
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["ensure_ops_refs", "register_ops"]

logger = logging.getLogger("sb.domain.setup")


@workflow("setup.compensate_create_channel")
async def _compensate_create_channel(conn, ctx: WorkflowContext) -> LegOutcome:
    """The create-channel compensator (fork E; conn=None): delete the
    channel the create leg minted, so Discord stops carrying a workspace
    the durable record refused. ID-GUARDED — only the exact id the leg
    stashed is touched (never a name lookup, never a session pointer:
    a stale pointer must not delete an operator's channel). BEST-EFFORT
    — a Discord-refused delete records an operator finding and the
    compensation still completes (the orphan channel is visible +
    harmless; the oracle's setup deletes are best-effort the same way).
    NotFound-as-success rides the ChannelStateActions.delete_channel
    port contract, not this handler."""
    del conn  # fork E runs compensators outside the txn
    cid = int(ctx.params.get("_created_channel_id", 0) or 0)
    if not cid:
        # the create leg never ran (or stashed nothing) — nothing to
        # withdraw; never guess at a channel to delete.
        return LegOutcome(
            step=StepResult(0, "compensate_create_channel", True),
            before={}, after={"compensated": "nothing"})
    from sb.domain.channel.service import active_actions

    deleted = True
    try:
        await active_actions().delete_channel(
            cid, reason="setup channel create compensated — a later leg failed")
    except Exception as exc:  # noqa: BLE001 — best-effort withdrawal
        deleted = False
        logger.warning("setup: compensating delete of channel %s failed: %s",
                       cid, exc)
        try:
            from sb.kernel.observability.findings import record_operator_finding

            record_operator_finding(
                source="workflow:setup.compensate_create_channel",
                severity="warning",
                summary=(f"compensating delete of created setup channel "
                         f"{cid} blocked — the channel is orphaned but "
                         f"harmless; delete it by hand or re-run setup"),
                detail="", correlation_id=None)
        except Exception:  # noqa: BLE001 — findings are observability only
            pass
    return LegOutcome(
        step=StepResult(0, "compensate_create_channel", True),
        before={}, after={"compensated": "create_channel",
                          "channel_id": cid, "deleted": deleted})


# --- the session-write legs (the flip's D-0065-shaped record legs) -----------------

@workflow("setup.record_session_started")
async def _record_session_started(conn, ctx: WorkflowContext) -> LegOutcome:
    """The ``/setup-hub`` entry's session mint — the shipped
    ``start_session`` upsert (status ``pending``, no workspace pointers;
    goldens/setup/sweep_slash_setup-hub pins the row)."""
    from sb.domain.setup import store

    guild_id = int(ctx.guild_id or 0)
    await store.upsert_session(
        conn, guild_id=guild_id,
        guild_name=str(ctx.params.get("guild_name", "")),
        owner_id=int(ctx.params.get("owner_id", 0) or 0),
        setup_status="pending", setup_channel_id=None,
        setup_message_id=None, current_step=None)
    return LegOutcome(
        step=StepResult(0, "record_session_started", True),
        before=None, after="pending")


@workflow("setup.record_workspace_open")
async def _record_workspace_open(conn, ctx: WorkflowContext) -> LegOutcome:
    """The ``/setup-advanced`` wizard entry — the ORACLE SEQUENCING
    verbatim (wizard.open_setup_workspace, the D-0077 contrast clause):
    ensure the private workspace (find = the gateway-cache name hit with
    ZERO wire calls; miss = ONE create_text_channel POST with the
    overwrite map at creation), post the depth-chooser anchor INTO it,
    and only then upsert the session row with the minted pointers
    (status ``in_progress``, ``current_step="depth"`` —
    goldens/setup/sweep_slash_setup-advanced pins row + card + reply).
    Create-BEFORE-DB: a failed row write aborts the txn and leaves
    channel + card standing (the oracle never rollback-deleted); NO
    compensator is declared, per D-0077's D-0065-shape clause."""
    from sb.domain.setup import service, store
    from sb.domain.setup.panels import HUB_PANEL_ID

    guild_id = int(ctx.guild_id or 0)
    invoker = int(getattr(ctx.actor, "user_id", 0) or 0)
    channel_id, created = await service.ensure_setup_channel(guild_id, invoker)
    if created:
        # the D-0077 stash contract — the id a (future) compensating
        # delete would be guarded on; unused by this D-0065-shaped op.
        ctx.params["_created_channel_id"] = int(channel_id)
    req = ctx.params.get("_workspace_request")
    message_id = None
    if req is not None:
        message_id = await service.post_panel_to_channel(
            HUB_PANEL_ID, req, channel_id)
    await store.upsert_session(
        conn, guild_id=guild_id,
        guild_name=str(ctx.params.get("guild_name", "")),
        owner_id=int(ctx.params.get("owner_id", 0) or 0),
        setup_status="in_progress", setup_channel_id=int(channel_id),
        setup_message_id=int(message_id) if message_id else None,
        current_step="depth")
    ctx.params["_workspace_channel_id"] = int(channel_id)
    ctx.params["_workspace_message_id"] = (int(message_id)
                                           if message_id else None)
    return LegOutcome(
        step=StepResult(0, "record_workspace_open", True),
        before=None, after="pending")


@workflow("setup.record_depth")
async def _record_depth(conn, ctx: WorkflowContext) -> LegOutcome:
    """The depth-chooser click's session write — the shipped
    ``setup_session.set_depth`` (views/setup/depth_panel.py ``_select``):
    a value-checked UPDATE keyed on the guild; no row is a silent no-op
    (the shipped semantics — the chooser also serves sessionless
    presentations)."""
    from sb.domain.setup import store

    depth = str(ctx.params.get("depth", "") or "") or None
    await store.set_depth(conn, guild_id=int(ctx.guild_id or 0), depth=depth)
    return LegOutcome(step=StepResult(0, "record_depth", True),
                      before=None, after=depth)


@workflow("setup.record_section_skip")
async def _record_section_skip(conn, ctx: WorkflowContext) -> LegOutcome:
    """The ``/setup-skip`` / ``/setup-unskip`` session write — the shipped
    ``mark_section_skipped`` / ``unmark_section_skipped`` set-semantics
    UPDATE pair (cogs/setup_cog.py ``_toggle_skip``)."""
    from sb.domain.setup import store

    slug = str(ctx.params["section"])
    skipped = bool(ctx.params.get("skipped", True))
    await store.set_section_skip(conn, guild_id=int(ctx.guild_id or 0),
                                 slug=slug, skipped=skipped)
    return LegOutcome(step=StepResult(0, "record_section_skip", True),
                      before=None, after={"section": slug, "skipped": skipped})


@workflow("setup.record_in_progress")
async def _record_in_progress(conn, ctx: WorkflowContext) -> LegOutcome:
    """The section-flows slice's step marker — the shipped
    ``setup_session.mark_in_progress`` (status → ``in_progress`` +
    ``current_step`` = the section's step marker; the oracle wrote it
    on every section-card open / staging lane). A bare keyed UPDATE —
    no session row is a silent no-op (the set_depth semantics)."""
    from sb.domain.setup import store

    step = ctx.params.get("step")
    step = str(step) if step is not None else None
    await store.mark_in_progress(conn, guild_id=int(ctx.guild_id or 0),
                                 step=step)
    return LegOutcome(step=StepResult(0, "record_in_progress", True),
                      before=None, after={"status": "in_progress",
                                          "step": step})


@workflow("setup.record_session_complete")
async def _record_session_complete(conn, ctx: WorkflowContext) -> LegOutcome:
    """The final-review apply lane's full-success session write — the
    shipped ``setup_session.mark_complete`` (status → ``complete``; the
    oracle emitted the ``setup.session.completed`` audit for exactly
    this transition)."""
    from sb.domain.setup import store

    await store.set_session_status(conn, guild_id=int(ctx.guild_id or 0),
                                   status="complete")
    return LegOutcome(step=StepResult(0, "record_session_complete", True),
                      before=None, after="complete")


@workflow("setup.record_essential_step")
async def _record_essential_step(conn, ctx: WorkflowContext) -> LegOutcome:
    """The essential flow's position write (the essential-steps slice —
    the oracle ``persist_progress``'s ``set_essential_step`` leg): a
    bare keyed UPDATE; no session row is a silent no-op (the shipped
    semantics — the ``!setup`` entry mints no row, goldens pin it)."""
    from sb.domain.setup import store

    step = int(ctx.params.get("step", 0) or 0)
    await store.set_essential_step(conn, guild_id=int(ctx.guild_id or 0),
                                   step=step)
    return LegOutcome(step=StepResult(0, "record_essential_step", True),
                      before=None, after=step)


@workflow("setup.record_essential_anchor_clear")
async def _record_essential_anchor_clear(conn,
                                         ctx: WorkflowContext) -> LegOutcome:
    """The essential flow's done-write (``persist_progress``'s
    ``clear_essential_anchor`` leg — the summary reached; the companion
    ``setup.mark_complete`` op carries the status flip)."""
    from sb.domain.setup import store

    await store.clear_essential_anchor(conn, guild_id=int(ctx.guild_id or 0))
    return LegOutcome(
        step=StepResult(0, "record_essential_anchor_clear", True),
        before=None, after="cleared")


@workflow("setup.record_workspace_pointer_clear")
async def _record_workspace_pointer_clear(conn,
                                          ctx: WorkflowContext) -> LegOutcome:
    """The setup-complete Delete-now lane's pointer nulls — the shipped
    post-cleanup ``set_setup_channel_id(None)`` +
    ``set_setup_message_id(None)`` pair (setup_channel.py), so the next
    ``/setup`` re-creates a fresh channel."""
    from sb.domain.setup import store

    await store.clear_workspace_pointers(conn, guild_id=int(ctx.guild_id or 0))
    return LegOutcome(
        step=StepResult(0, "record_workspace_pointer_clear", True),
        before=None, after="cleared")


# --- the ensure-channel legs (the K9 ``create_channel`` apply lane) -----------------

@workflow("setup.ensure_channel_resource")
async def _ensure_channel_resource(conn, ctx: WorkflowContext) -> LegOutcome:
    """The oracle ``ensure_channel`` reuse-vs-create semantics
    (core/runtime/guild_resources.py:124-156) over the D-0077 ports:
    resolve by name + text kind through the ChannelDirectory READ port
    (get-before-create is DOMAIN logic — the adapter always creates); a
    hit is returned UNCHANGED (the oracle: "overwrites are NOT
    reconciled"); a miss creates ONE text channel through the
    channel-state port and stashes ``_created_channel_id`` (the D-0077
    compensator guard) + ``_ensured_channel_id`` (the bind leg's input).
    A real create emits the shipped ``channel.lifecycle_changed``
    advisory (essential_steps._create_channel's companion); the AUDIT
    fact is the op's ONE K7 central row — engine-minted mutation_id, a
    ledgered divergence from the oracle's shared audit/lifecycle id
    pair. A directory read failure (headless — no cache installed)
    degrades to no-match, the same answer the oracle's empty gateway
    cache gives resolve_channel."""
    del conn  # EFFECT leg (post-commit)
    import uuid

    from sb.domain.channel import service as channel_service

    gid = int(ctx.guild_id or 0)
    name = str(ctx.params.get("resource_name", "") or "").strip()
    if not name:
        raise ValueError(
            "create_channel: requires resource_name (the channel name)")
    existing_id = None
    try:
        for snap in await channel_service.active_directory().list_channels(gid):
            if snap.name == name and snap.kind == "text":
                existing_id = int(snap.channel_id)
                break
    except Exception:  # noqa: BLE001 — headless/no directory ⇒ no match
        logger.debug("setup.ensure_channel: directory read failed",
                     exc_info=True)
    created = False
    if existing_id is not None:
        cid = existing_id
    else:
        actions = channel_service.active_actions()  # the D-0077 port binding
        cid = int(await actions.create_text_channel(
            gid, name=name, overwrites=(), parent_id=None, reason=None))
        created = True
        # the D-0077 stash contract — the id the compensating delete is
        # guarded on (never a name lookup).
        ctx.params["_created_channel_id"] = cid
        await channel_service.emit_channel_lifecycle(
            gid, mutation_id=str(uuid.uuid4()), operation="create",
            outcome="success", applied=[cid], failed=[])
    ctx.params["_ensured_channel_id"] = cid
    return LegOutcome(
        step=StepResult(cid, "ensure_channel", True),
        before={}, after={"channel_id": cid, "created": created,
                          "resource_name": name})


@workflow("setup.bind_ensured_channel")
async def _bind_ensured_channel(conn, ctx: WorkflowContext) -> LegOutcome:
    """Step 8 of the oracle provision contract
    (resource_provisioning.py:795-816): slot-bind the ensured channel
    through the audited K7 ``settings.bind`` op (the
    BindingMutationPipeline twin — essential_steps._bind's seam; binding
    row + binding_audit_log row in ONE txn). A bind failure RAISES so
    the op folds non-SUCCESS with the channel left standing — fork E
    records the operator finding and never runs the create leg's
    compensator (the oracle's ``binding_failed`` outcome: "Binding
    failure does NOT roll back the created Discord resource",
    resource_provisioning.py:52-55)."""
    del conn  # EFFECT leg (post-commit)
    from sb.kernel.workflow import engine

    cid = int(ctx.params.get("_ensured_channel_id", 0) or 0)
    if not cid:
        raise RuntimeError(
            "ensure_channel: the ensure leg minted no channel — nothing "
            "to bind")
    subsystem = str(ctx.params.get("subsystem", "") or "")
    name = str(ctx.params.get("name", "") or "")
    if not subsystem or not name:
        raise ValueError(
            "create_channel: requires subsystem + name (the binding slot)")
    bind_ctx = WorkflowContext(
        actor=ctx.actor, guild_id=int(ctx.guild_id or 0),
        request_id=f"{ctx.request_id}:bind", confirmed=True,
        params={"subsystem": subsystem, "name": name,
                "kind": str(ctx.params.get("kind", "channel") or "channel"),
                "resource_id": cid},
        correlation_id=ctx.correlation_id, test_mode=ctx.test_mode,
        clock=ctx.clock)
    result = await engine.run(WorkflowRef("settings.bind"), bind_ctx)
    if result.outcome != SUCCESS:
        raise RuntimeError(
            f"binding_failed: settings.bind {subsystem}.{name} → "
            f"{result.outcome}")
    return LegOutcome(
        step=StepResult(cid, "bind_channel", True),
        before={}, after={"subsystem": subsystem, "name": name,
                          "resource_id": cid})


# --- privacy erasure body (the store-declared ref; flag-18 discipline) --------------

@workflow("setup.erase_subject_session")
async def _erase_subject_session(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.setup import store

    subject = int(ctx.params["subject_user_id"])
    rows = await store.scrub_subject_session(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_session", True),
                      before={}, after={"scrubbed_rows": rows})


# --- the op specs -------------------------------------------------------------------

#: both entries mint/refresh ONE row keyed on the guild (ON CONFLICT
#: upsert) — intrinsically once (NATURAL_KEY). ``audit_verb`` carries the
#: shipped mutation vocabulary (services/setup_session.py
#: ``_emit_session_audit`` — ``mutation_type="setup.session.started"``,
#: ``new_value="pending"``).
START_SESSION = CompoundOpSpec(
    op_key="setup.start_session", domain="setup", lane=WorkflowLane.DOMAIN,
    authority_ref="",                 # ADMIN floor (the shipped owner/admin gate)
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_session_started"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.started")

OPEN_WORKSPACE = CompoundOpSpec(
    op_key="setup.open_workspace", domain="setup", lane=WorkflowLane.DOMAIN,
    authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_workspace_open"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.started")

#: the wizard-interior session writes (this slice). The oracle wrote both
#: through bare service functions with NO audit row (services/
#: setup_session.py emitted session audits only for started/completed/
#: dismissed); here the writes ride the K7 discipline, so each carries
#: the ONE central audit row the engine mandates — a ledgered divergence
#: (audit is additive; the DB shape stays the shipped UPDATE).
SET_DEPTH = CompoundOpSpec(
    op_key="setup.set_depth", domain="setup", lane=WorkflowLane.DOMAIN,
    authority_ref="",
    legs=(LegSpec("record", LegKind.DB, WorkflowRef("setup.record_depth"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.depth_set")

SET_SECTION_SKIP = CompoundOpSpec(
    op_key="setup.set_section_skip", domain="setup",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_section_skip"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.section_skip")

#: the section-flows slice's step marker. The oracle wrote it through a
#: bare service function with NO audit row (services/setup_session.py
#: ``mark_in_progress``) — the K7 central audit row is additive, the
#: SET_DEPTH ledger note's class.
MARK_IN_PROGRESS = CompoundOpSpec(
    op_key="setup.mark_in_progress", domain="setup",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_in_progress"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.step_marked")

#: the final-review slice's session writes. ``setup.session.completed``
#: is the shipped mutation vocabulary (services/setup_session.py
#: ``_emit_session_audit`` — started/completed/dismissed); the pointer
#: clear had NO oracle audit (a bare service write) — the K7 central
#: audit row is additive, the SET_DEPTH ledger note's class.
MARK_COMPLETE = CompoundOpSpec(
    op_key="setup.mark_complete", domain="setup", lane=WorkflowLane.DOMAIN,
    authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_session_complete"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.completed")

CLEAR_WORKSPACE_POINTER = CompoundOpSpec(
    op_key="setup.clear_workspace_pointer", domain="setup",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_workspace_pointer_clear"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.workspace_cleared")

#: the essential-steps slice's session writes. The oracle wrote both
#: through bare service functions with NO audit row (services/
#: setup_session.py) — the K7 central audit row is additive, the
#: SET_DEPTH ledger note's class.
SET_ESSENTIAL_STEP = CompoundOpSpec(
    op_key="setup.set_essential_step", domain="setup",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_essential_step"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.essential_step_set")

CLEAR_ESSENTIAL_ANCHOR = CompoundOpSpec(
    op_key="setup.clear_essential_anchor", domain="setup",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("setup.record_essential_anchor_clear"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.session.essential_anchor_cleared")

#: the K9 ``create_channel`` apply lane (the logging_presets named
#: successor): the oracle ResourceProvisioningPipeline's reachable core —
#: ensure (reuse-by-name or create) → slot bind → audit — as ONE K7 op.
#: NATURAL_KEY: the ensure is name-idempotent (get-before-create — the
#: designed shared-channel semantics: "on a name match [the pipeline]
#: returns the existing channel and binds it to the slot") and the bind
#: an ON CONFLICT upsert, so a resumed apply reuses instead of
#: duplicating. The create leg is COMPENSATABLE with the D-0077
#: id-guarded compensator (module docstring); the bind leg deliberately
#: carries NONE (oracle ``binding_failed``: channel stands, op fails).
ENSURE_CHANNEL = CompoundOpSpec(
    op_key="setup.ensure_channel", domain="setup",
    lane=WorkflowLane.RESOURCE, authority_ref="",
    legs=(
        LegSpec("ensure", LegKind.EFFECT,
                WorkflowRef("setup.ensure_channel_resource"),
                "compensatable",
                compensator=WorkflowRef("setup.compensate_create_channel")),
        LegSpec("bind", LegKind.EFFECT,
                WorkflowRef("setup.bind_ensured_channel"), "reversible"),
    ),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="setup.channel_provisioned")

_OPS = (START_SESSION, OPEN_WORKSPACE, SET_DEPTH, SET_SECTION_SKIP,
        MARK_IN_PROGRESS, MARK_COMPLETE, CLEAR_WORKSPACE_POINTER,
        SET_ESSENTIAL_STEP, CLEAR_ESSENTIAL_ANCHOR, ENSURE_CHANNEL)

_REF_TABLE = (
    ("setup.compensate_create_channel", _compensate_create_channel),
    ("setup.record_session_started", _record_session_started),
    ("setup.record_workspace_open", _record_workspace_open),
    ("setup.record_depth", _record_depth),
    ("setup.record_section_skip", _record_section_skip),
    ("setup.record_in_progress", _record_in_progress),
    ("setup.record_session_complete", _record_session_complete),
    ("setup.record_essential_step", _record_essential_step),
    ("setup.record_essential_anchor_clear", _record_essential_anchor_clear),
    ("setup.record_workspace_pointer_clear", _record_workspace_pointer_clear),
    ("setup.ensure_channel_resource", _ensure_channel_resource),
    ("setup.bind_ensured_channel", _bind_ensured_channel),
    ("setup.erase_subject_session", _erase_subject_session),
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
    register_ops()
