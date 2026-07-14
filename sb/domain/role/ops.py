"""The role mutation lanes (band 5) — every role-family DB write as a K7
CompoundOpSpec: thresholds, exemptions (the shipped set_role_exemption
audit), the legacy reaction-role bindings + message modes, role menus,
and the temp-grant pair (grant = DB record + post-commit EFFECT through
the actions port; expire = the sweep's pure-DB row drop under
SYSTEM_ACTOR).

Authority: role surfaces were manage_roles-gated (perms_or_owner) —
"staff" is the closest tier floor whose Discord bit is manage_guild;
manage_roles maps onto the shipped role.* capability family. Verbatim
tier mapping: the role subsystem's registry visibility_tier is
administrator; thresholds/menus/exemptions land there, temp grants at
moderator (the operator action shipped as manage_roles).
"""

from __future__ import annotations

import logging
from datetime import datetime

from sb.domain.role import store
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

logger = logging.getLogger("sb.domain.role")

_VALID_MODES = ("normal", "unique", "verify")
_VALID_STYLES = ("dropdown", "buttons")


def _actor_id(ctx: WorkflowContext) -> int:
    return int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)


def _verr(message: str):
    """Copy-only ValidatorError — the raise-site sentence IS the user copy,
    rendered bare (the D-0060/D-0061 refusal-copy posture; the one-arg
    param form wrapped every sentence in the missing-argument
    boilerplate — band-5 was the 5th victim family)."""
    from sb.kernel.interaction.errors import ValidatorError

    return ValidatorError("", message)


# --- threshold legs -----------------------------------------------------------

@workflow("role.record_set_threshold")
async def _record_set_threshold(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    role_name = str(ctx.params.get("role_name", "") or "").strip()
    if not role_name:
        raise _verr("Usage: `!setrole <days> <role name>`")
    days = int(ctx.params.get("days_required", 0) or 0)
    level = ctx.params.get("level_required")
    if days < 0 or (level is not None and int(level) < 0):
        raise _verr("Days/level must be non-negative.")
    await store.upsert_threshold(
        conn, guild_id=gid, role_name=role_name, days_required=days,
        level_required=int(level) if level is not None else None,
        xp_auto_assign=bool(ctx.params.get("xp_auto_assign", False)),
        role_id=ctx.params.get("role_id"),
        display_name=ctx.params.get("display_name"))
    return LegOutcome(step=StepResult(gid, "set_threshold", True),
                      before={}, after={"role_name": role_name,
                                        "days_required": days,
                                        "level_required": level})


@workflow("role.record_remove_threshold")
async def _record_remove_threshold(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    role_name = str(ctx.params.get("role_name", "") or "").strip()
    if not role_name:
        raise _verr("Usage: `!unsetrole <role name>`")
    removed = await store.delete_threshold(conn, guild_id=gid,
                                           role_name=role_name)
    return LegOutcome(step=StepResult(gid, "remove_threshold", True),
                      before={"present": removed},
                      after={"role_name": role_name, "removed": removed})


# --- exemption leg (shipped set_role_exemption semantics) ------------------------

@workflow("role.record_set_exemption")
async def _record_set_exemption(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    role_id = int(ctx.params.get("role_id", 0) or 0)
    if not role_id:
        raise _verr("A role id is required.")
    exempt_xp = bool(ctx.params.get("exempt_xp", False))
    exempt_time = bool(ctx.params.get("exempt_time", False))
    rows = await store.get_exemptions(gid, conn=conn)
    prev = next(((bool(r["exempt_xp"]), bool(r["exempt_time"]))
                 for r in rows if int(r["role_id"]) == role_id),
                (False, False))
    if not exempt_xp and not exempt_time:
        await store.clear_exemption_row(conn, guild_id=gid, role_id=role_id)
    else:
        await store.set_exemption_row(conn, guild_id=gid, role_id=role_id,
                                      exempt_xp=exempt_xp,
                                      exempt_time=exempt_time)
    return LegOutcome(
        step=StepResult(gid, "set_exemption", True),
        before={"xp": prev[0], "time": prev[1]},
        after={"role_id": role_id, "xp": exempt_xp, "time": exempt_time})


# --- reaction-role legs -------------------------------------------------------------

@workflow("role.record_bind_reaction")
async def _record_bind_reaction(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    message_id = int(ctx.params.get("message_id", 0) or 0)
    emoji = str(ctx.params.get("emoji", "") or "")
    role_id = int(ctx.params.get("role_id", 0) or 0)
    if not (message_id and emoji and role_id):
        raise _verr("Usage: `!reactroles <message_id> <emoji> <@role>`")
    await store.bind_reaction(conn, guild_id=gid, message_id=message_id,
                              emoji=emoji, role_id=role_id)
    return LegOutcome(step=StepResult(gid, "bind_reaction", True),
                      before={}, after={"message_id": message_id,
                                        "emoji": emoji, "role_id": role_id})


@workflow("role.record_unbind_reaction")
async def _record_unbind_reaction(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    message_id = int(ctx.params.get("message_id", 0) or 0)
    emoji = str(ctx.params.get("emoji", "") or "")
    if not (message_id and emoji):
        raise _verr("Usage: `!removereactrole <message_id> <emoji>`")
    removed = await store.unbind_reaction(conn, guild_id=gid,
                                          message_id=message_id, emoji=emoji)
    return LegOutcome(step=StepResult(gid, "unbind_reaction", True),
                      before={"present": removed},
                      after={"message_id": message_id, "emoji": emoji,
                             "removed": removed})


@workflow("role.record_set_message_mode")
async def _record_set_message_mode(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    message_id = int(ctx.params.get("message_id", 0) or 0)
    mode = str(ctx.params.get("mode", "normal") or "normal")
    if mode not in _VALID_MODES:
        raise _verr(f"Mode must be one of: {', '.join(_VALID_MODES)}.")
    if not message_id:
        raise _verr("A message id is required.")
    await store.set_message_mode(conn, guild_id=gid, message_id=message_id,
                                 mode=mode)
    return LegOutcome(step=StepResult(gid, "set_message_mode", True),
                      before={}, after={"message_id": message_id,
                                        "mode": mode})


@workflow("role.record_clear_message_mode")
async def _record_clear_message_mode(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    message_id = int(ctx.params.get("message_id", 0) or 0)
    removed = await store.clear_message_mode(conn, guild_id=gid,
                                             message_id=message_id)
    return LegOutcome(step=StepResult(gid, "clear_message_mode", True),
                      before={"present": removed},
                      after={"message_id": message_id, "removed": removed})


# --- role menu legs -------------------------------------------------------------------

@workflow("role.record_create_menu")
async def _record_create_menu(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    channel_id = int(ctx.params.get("channel_id", 0) or 0)
    style = str(ctx.params.get("style", "dropdown") or "dropdown")
    mode = str(ctx.params.get("mode", "normal") or "normal")
    if style not in _VALID_STYLES:
        raise _verr(f"Style must be one of: {', '.join(_VALID_STYLES)}.")
    if mode not in _VALID_MODES:
        raise _verr(f"Mode must be one of: {', '.join(_VALID_MODES)}.")
    options = list(ctx.params.get("options", ()) or ())
    if not channel_id:
        raise _verr("A channel is required for a role menu.")
    if not options:
        raise _verr("A role menu needs at least one role option.")
    menu_id = await store.insert_menu(
        conn, guild_id=gid, channel_id=channel_id,
        title=str(ctx.params.get("title", "Pick your roles")),
        description=ctx.params.get("description"),
        style=style, mode=mode,
        max_roles=int(ctx.params.get("max_roles", 0) or 0),
        theme=str(ctx.params.get("theme", "default")))
    await store.replace_menu_options(conn, menu_id=menu_id, options=options)
    ctx.params["_menu_id"] = menu_id
    return LegOutcome(step=StepResult(gid, "create_menu", True),
                      before={},
                      after={"menu_id": menu_id, "options": len(options)},
                      payload={"menu_id": menu_id})


@workflow("role.record_update_menu")
async def _record_update_menu(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    menu_id = int(ctx.params.get("menu_id", 0) or 0)
    menu = await store.get_menu(menu_id, conn=conn)
    if menu is None or int(menu["guild_id"]) != gid:
        raise _verr(f"Role menu {menu_id} does not exist in this server.")
    fields = {k: v for k, v in ctx.params.items()
              if k in ("title", "description", "style", "mode", "max_roles",
                       "theme", "channel_id", "message_id")}
    if fields.get("style") not in (None,) + _VALID_STYLES:
        raise _verr(f"Style must be one of: {', '.join(_VALID_STYLES)}.")
    if fields.get("mode") not in (None,) + _VALID_MODES:
        raise _verr(f"Mode must be one of: {', '.join(_VALID_MODES)}.")
    if fields:
        await store.update_menu_fields(conn, menu_id=menu_id, **fields)
    options = ctx.params.get("options")
    if options:
        await store.replace_menu_options(conn, menu_id=menu_id,
                                         options=list(options))
    return LegOutcome(step=StepResult(gid, "update_menu", True),
                      before={"menu": dict(menu)},
                      after={"menu_id": menu_id,
                             "fields": sorted(fields)})


@workflow("role.record_delete_menu")
async def _record_delete_menu(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    menu_id = int(ctx.params.get("menu_id", 0) or 0)
    menu = await store.get_menu(menu_id, conn=conn)
    if menu is None or int(menu["guild_id"]) != gid:
        raise _verr(f"Role menu {menu_id} does not exist in this server.")
    removed = await store.delete_menu(conn, menu_id=menu_id)
    return LegOutcome(step=StepResult(gid, "delete_menu", True),
                      before={"present": removed},
                      after={"menu_id": menu_id, "removed": removed})


# --- temp grant legs ----------------------------------------------------------------------

@workflow("role.record_grant_temp")
async def _record_grant_temp(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    member_id = int(ctx.params.get("member_id", 0) or 0)
    role_id = int(ctx.params.get("role_id", 0) or 0)
    expires_iso = str(ctx.params.get("expires_at_iso", "") or "")
    if not (member_id and role_id and expires_iso):
        raise _verr("Usage: `!temprole @member <duration> <@role>`")
    expires_at = datetime.fromisoformat(expires_iso)
    await store.upsert_grant(conn, guild_id=gid, member_id=member_id,
                             role_id=role_id, expires_at=expires_at,
                             granted_by=_actor_id(ctx) or None)
    return LegOutcome(
        step=StepResult(member_id, "grant_temp", True),
        before={},
        after={"member_id": member_id, "role_id": role_id,
               "expires_at": expires_iso})


@workflow("role.apply_grant_temp")
async def _apply_grant_temp(conn, ctx: WorkflowContext) -> LegOutcome:
    """Post-commit EFFECT: the Discord add through the actions port."""
    from sb.domain.role import service

    gid = int(ctx.guild_id or 0)
    await service.active_actions().add_role(
        gid, int(ctx.params.get("member_id", 0) or 0),
        int(ctx.params.get("role_id", 0) or 0), reason="Temporary role")
    return LegOutcome(step=StepResult(0, "apply_grant_temp", True),
                      before={}, after={"applied": "add_role"})


@workflow("role.compensate_grant_temp")
async def _compensate_grant_temp(conn, ctx: WorkflowContext) -> LegOutcome:
    """Grant's compensator: drop the persisted row (pure DB)."""
    gid = int(ctx.guild_id or 0)
    rows = await store.list_grants_for_member(
        gid, int(ctx.params.get("member_id", 0) or 0), conn=conn)
    role_id = int(ctx.params.get("role_id", 0) or 0)
    for row in rows:
        if int(row["role_id"]) == role_id:
            await store.delete_grant(conn, grant_id=int(row["grant_id"]))
    return LegOutcome(step=StepResult(0, "compensate_grant_temp", True),
                      before={}, after={"compensated": "grant_temp"})


@workflow("role.record_expire_temp")
async def _record_expire_temp(conn, ctx: WorkflowContext) -> LegOutcome:
    """The sweep's row drop (pure DB, SYSTEM actor; the Discord removal
    already happened in the fire body)."""
    grant_id = int(ctx.params.get("grant_id", 0) or 0)
    removed = await store.delete_grant(conn, grant_id=grant_id)
    return LegOutcome(
        step=StepResult(int(ctx.params.get("member_id", 0) or 0),
                        "expire_temp", True),
        before={"present": removed},
        after={"grant_id": grant_id,
               "did_remove": bool(ctx.params.get("did_remove", False)),
               "removed": removed})


# --- create-managed-role legs (the setup role-templates apply lane) --------------------------

@workflow("role.apply_create_managed")
async def _apply_create_managed(conn, ctx: WorkflowContext) -> LegOutcome:
    """EFFECT: the apply-time UNCONDITIONAL role create — the oracle
    RoleLifecycleService create path verbatim
    (services/role_lifecycle_service.py:285-312: no name-reuse check in
    the service; dedupe lives upstream at plan/stage time,
    ``plan_template``'s create-vs-exists partition). The cosmetic spec
    (color / hoist / mentionable — NO permissions, by design) rides
    ``ctx.params["role_template"]`` (setup_role_templates.
    suggestion_to_spec's shape); ``parse_color`` fail-safes bad hex to
    the default colour, the shipped posture. Emits the shipped
    ``role.lifecycle_changed`` advisory; the AUDIT fact is the op's ONE
    K7 central row — engine-minted mutation_id, a ledgered divergence
    from the oracle's shared audit/lifecycle id pair."""
    del conn  # EFFECT leg (post-commit)
    import uuid

    from sb.domain.role import service

    gid = int(ctx.guild_id or 0)
    name = str(ctx.params.get("resource_name", "") or "").strip()
    if not name:
        # oracle copy, verbatim (_apply_create_managed_role's guard).
        raise ValueError(
            "create_managed_role: requires resource_name (the role name)")
    spec = dict(ctx.params.get("role_template") or {})
    from sb.domain.setup.role_templates import parse_color

    color = parse_color(spec.get("color"))
    slug = str(spec.get("template_slug") or "manual")
    rid = int(await service.active_provisioning().create_guild_role(
        gid, name=name, color=int(color or 0),
        reason=f"setup role template ({slug})",
        hoist=bool(spec.get("hoist")),
        mentionable=bool(spec.get("mentionable"))))
    # the D-0077 stash contract's role twin — the id the compensating
    # delete is guarded on (never a name lookup).
    ctx.params["_created_role_id"] = rid
    await service.emit_role_lifecycle(
        gid, mutation_id=str(uuid.uuid4()), operation="create",
        outcome="success", applied=[rid], failed=[])
    return LegOutcome(
        step=StepResult(rid, "create_managed_role", True),
        before={}, after={"role_id": rid, "name": name,
                          "template_slug": slug})


@workflow("role.compensate_create_managed")
async def _compensate_create_managed(conn, ctx: WorkflowContext) -> LegOutcome:
    """The create leg's compensator (fork E; conn=None) — the D-0077
    id-guarded best-effort withdrawal class
    (setup.compensate_create_channel's role twin): delete ONLY the exact
    role id the leg stashed; nothing stashed = the create never happened
    = nothing to withdraw (the oracle never rolls back a created role —
    a failed create has no role, and the tier fold never undoes one).
    Best-effort: a refused delete logs and completes."""
    del conn  # fork E runs compensators outside the txn
    rid = int(ctx.params.get("_created_role_id", 0) or 0)
    if not rid:
        return LegOutcome(
            step=StepResult(0, "compensate_create_managed", True),
            before={}, after={"compensated": "nothing"})
    from sb.domain.role import service

    deleted = True
    try:
        await service.active_provisioning().delete_role(
            int(ctx.guild_id or 0), rid,
            reason="setup role create compensated — a later step failed")
    except Exception as exc:  # noqa: BLE001 — best-effort withdrawal
        deleted = False
        logger.warning("role: compensating delete of role %s failed: %s",
                       rid, exc)
    return LegOutcome(
        step=StepResult(0, "compensate_create_managed", True),
        before={}, after={"compensated": "create_managed_role",
                          "role_id": rid, "deleted": deleted})


@workflow("role.apply_template_tier")
async def _apply_template_tier(conn, ctx: WorkflowContext) -> LegOutcome:
    """EFFECT: the best-effort auto-role tier companion (oracle
    ``_apply_template_role_tiers``, setup_operations.py:1810-1857): when
    the template spec carries ``time_days`` / ``xp_level``, thread the
    freshly-created role's id into the audited threshold seam — here the
    K7 ``role.set_threshold`` FULL-ROW fold (time + XP in one upsert,
    the setup roles-section precedent). FAILURE IS CAUGHT IN-LEG and
    never raises (the oracle: "a failed tier never undoes the
    already-created role ... must not flip the op to ``failed``") — the
    op stays SUCCESS, the miss is logged, and the operator can set the
    tier by hand in ``!roles``."""
    del conn  # EFFECT leg (post-commit)
    spec = dict(ctx.params.get("role_template") or {})
    time_days = spec.get("time_days")
    xp_level = spec.get("xp_level")
    rid = int(ctx.params.get("_created_role_id", 0) or 0)
    if not rid or (not time_days and not xp_level):
        return LegOutcome(step=StepResult(rid, "template_tier", True),
                          before={}, after={"tier": "none"})
    name = str(ctx.params.get("resource_name", "") or "")
    from sb.kernel.workflow import engine

    tier_ctx = WorkflowContext(
        actor=ctx.actor, guild_id=int(ctx.guild_id or 0),
        request_id=f"{ctx.request_id}:tier", confirmed=True,
        params={"role_name": name, "display_name": name, "role_id": rid,
                "days_required": int(time_days or 0),
                "level_required": (int(xp_level) if xp_level else None),
                "xp_auto_assign": bool(xp_level)},
        correlation_id=ctx.correlation_id, test_mode=ctx.test_mode,
        clock=ctx.clock)
    detail = ""
    try:
        result = await engine.run(WorkflowRef("role.set_threshold"), tier_ctx)
        ok = result.outcome == "success"
        if not ok:
            detail = f"outcome={result.outcome!r}"
    except Exception as exc:  # noqa: BLE001 — best-effort companion (oracle)
        ok = False
        detail = str(exc)
    if not ok:
        # oracle log shape (_apply_template_role_tiers's except arm).
        logger.warning(
            "create_managed_role: auto-role tier companion failed "
            "(role_id=%s): %s — the role itself was created", rid, detail)
    return LegOutcome(
        step=StepResult(rid, "template_tier", True),
        before={}, after={"tier": "set" if ok else "failed",
                          "time_days": time_days, "xp_level": xp_level})


# --- privacy erasure body --------------------------------------------------------------------

@workflow("role.erase_subject_grants")
async def _erase_subject_grants(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_grants(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_grants", True),
                      before={}, after={"rows": rows})


# --- op table -----------------------------------------------------------------------------------

def _db_op(op_key: str, verb: str, ref: str,
           authority: str = "administrator") -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="role", lane=WorkflowLane.DOMAIN,
        authority_ref=authority,
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


SET_THRESHOLD = _db_op("role.set_threshold", "role_threshold_set",
                       "role.record_set_threshold")
REMOVE_THRESHOLD = _db_op("role.remove_threshold", "role_threshold_removed",
                          "role.record_remove_threshold")
SET_EXEMPTION = _db_op("role.set_exemption", "set_role_exemption",
                       "role.record_set_exemption")
BIND_REACTION = _db_op("role.bind_reaction", "reaction_role_bound",
                       "role.record_bind_reaction")
UNBIND_REACTION = _db_op("role.unbind_reaction", "reaction_role_unbound",
                         "role.record_unbind_reaction")
SET_MESSAGE_MODE = _db_op("role.set_message_mode",
                          "reaction_mode_set", "role.record_set_message_mode")
CLEAR_MESSAGE_MODE = _db_op("role.clear_message_mode", "reaction_mode_cleared",
                            "role.record_clear_message_mode")
CREATE_MENU = _db_op("role.create_menu", "role_menu_created",
                     "role.record_create_menu")
UPDATE_MENU = _db_op("role.update_menu", "role_menu_updated",
                     "role.record_update_menu")
DELETE_MENU = _db_op("role.delete_menu", "role_menu_deleted",
                     "role.record_delete_menu")

GRANT_TEMP_ROLE = CompoundOpSpec(
    op_key="role.grant_temp_role", domain="role", lane=WorkflowLane.DOMAIN,
    authority_ref="moderator",           # shipped perms_or_owner(manage_roles)
    legs=(
        LegSpec("record", LegKind.DB,
                WorkflowRef("role.record_grant_temp"), "reversible"),
        LegSpec("apply", LegKind.EFFECT,
                WorkflowRef("role.apply_grant_temp"), "compensatable",
                compensator=WorkflowRef("role.compensate_grant_temp")),
    ),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="grant_temp_role", emits=())

EXPIRE_TEMP_ROLE = _db_op("role.expire_temp_role", "expire_temp_role",
                          "role.record_expire_temp", authority="")

#: the K9 ``create_managed_role`` apply lane (the role_templates named
#: successor): the oracle _apply_create_managed_role route
#: (setup_operations.py:1176/1723 → RoleLifecycleService + the
#: best-effort tier companion) as ONE K7 op. NONE_JUSTIFIED — the
#: oracle-verbatim posture: apply-time create is unconditional, dedupe
#: lives at plan/stage time; a durable once() here would record its
#: outcome PRE-EFFECT (engine step 4f) and false-SUCCESS a retried
#: draft op whose create leg never ran. ``audit_verb`` carries the
#: shipped lifecycle vocabulary (contracts: ``{domain}_{operation}`` =
#: ``role_create``).
CREATE_MANAGED_ROLE = CompoundOpSpec(
    op_key="role.create_managed_role", domain="role",
    lane=WorkflowLane.RESOURCE,
    authority_ref="administrator",       # the role subsystem's tier (thresholds' floor)
    legs=(
        LegSpec("create", LegKind.EFFECT,
                WorkflowRef("role.apply_create_managed"), "compensatable",
                compensator=WorkflowRef("role.compensate_create_managed")),
        LegSpec("tier", LegKind.EFFECT,
                WorkflowRef("role.apply_template_tier"), "reversible"),
    ),
    idempotency=IdempotencyPosture.NONE_JUSTIFIED, dedup_key=None,
    idempotency_justification=(
        "apply-time create is UNCONDITIONAL (the oracle "
        "RoleLifecycleService posture, role_lifecycle_service.py:285-312) "
        "— idempotency lives at plan/stage time (plan_template partitions "
        "already-existing names out before staging); a durable once() "
        "would record its outcome pre-EFFECT and false-SUCCESS a retried "
        "draft op whose create leg never ran"),
    audit_verb="role_create", emits=())

_OPS = (SET_THRESHOLD, REMOVE_THRESHOLD, SET_EXEMPTION, BIND_REACTION,
        UNBIND_REACTION, SET_MESSAGE_MODE, CLEAR_MESSAGE_MODE, CREATE_MENU,
        UPDATE_MENU, DELETE_MENU, GRANT_TEMP_ROLE, EXPIRE_TEMP_ROLE,
        CREATE_MANAGED_ROLE)

_REF_TABLE = (
    ("role.record_set_threshold", _record_set_threshold),
    ("role.record_remove_threshold", _record_remove_threshold),
    ("role.record_set_exemption", _record_set_exemption),
    ("role.record_bind_reaction", _record_bind_reaction),
    ("role.record_unbind_reaction", _record_unbind_reaction),
    ("role.record_set_message_mode", _record_set_message_mode),
    ("role.record_clear_message_mode", _record_clear_message_mode),
    ("role.record_create_menu", _record_create_menu),
    ("role.record_update_menu", _record_update_menu),
    ("role.record_delete_menu", _record_delete_menu),
    ("role.record_grant_temp", _record_grant_temp),
    ("role.apply_grant_temp", _apply_grant_temp),
    ("role.compensate_grant_temp", _compensate_grant_temp),
    ("role.record_expire_temp", _record_expire_temp),
    ("role.apply_create_managed", _apply_create_managed),
    ("role.compensate_create_managed", _compensate_create_managed),
    ("role.apply_template_tier", _apply_template_tier),
    ("role.erase_subject_grants", _erase_subject_grants),
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
    _register_op_markers()
