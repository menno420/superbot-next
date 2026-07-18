"""Audited writes for the guild Help overlay — the K7 lanes (ORACLE
disbot/services/help_overlay_mutation.py + utils/db/help_overlay.py,
ported onto the compiled workflow engine).

Single chokepoint for the ``help_overlay`` table (migration 0051).
Shipped contract, verbatim:

* **Presentation only** (Q-0055/HLP-4): the overlay can hide/rename/
  re-describe entries *in Help*; it never touches command access or
  governance, and nothing in any admission path reads it.
* **Stable keys validated at write time** against the compiled catalogue
  (categories + live manifest inventory) — an unknown hub/subsystem key
  is rejected (orphans can only *become* orphans later, via registry
  changes; the read side preserves + reports them).
* **Store only deviations**: a row whose override fields all become
  ``None`` is deleted, so "no rows" stays the byte-identical default.
* Every write invalidates the per-guild overlay cache; the workflow
  engine's audit spine records the op (audit verbs
  ``help_overlay_update`` / ``help_overlay_reset`` — the shipped
  mutation_type strings).

Partial-edit semantics (the shipped ``UNSET`` sentinel): a field ABSENT
from ``ctx.params["fields"]`` is left untouched; present-as-``None``
resets it to inherit; present-with-value overrides. User-facing
rejections raise ``ValidatorError`` with FINAL copy (D-0060/D-0061
posture — the sentence renders bare).
"""

from __future__ import annotations

import logging
from typing import Any

from sb.kernel.db.pool import execute, fetchone
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

logger = logging.getLogger("sb.domain.help.overlay_ops")

__all__ = [
    "RESET_OVERLAY",
    "SET_HOME_MESSAGE",
    "SET_OVERLAY_FIELDS",
    "delete_guild_rows",
    "ensure_refs",
    "register_ops",
]

#: the editable override fields (the shipped mutation surface).
_FIELDS = ("display_hidden", "display_name", "description")

#: the Q-0059 Home-message fields (partial-edit surface).
_HOME_FIELDS = ("title", "body", "color")


def _reject(sentence: str):
    from sb.kernel.interaction.errors import ValidatorError

    # copy-only form: the sentence renders bare (D-0060/D-0061 posture).
    return ValidatorError("", sentence)


def _check_entity(entity_kind: str, entity_key: str) -> None:
    """Reject unknown kinds/keys — stable keys are validated at write
    time (shipped rule; final user copy)."""
    from sb.domain.help.overlay import VALID_ENTITY_KINDS, known_entities

    if entity_kind not in VALID_ENTITY_KINDS:
        raise _reject("Pick a hub or a subsystem to edit.")
    if entity_key not in known_entities(entity_kind):
        raise _reject(
            f"`{entity_key}` is not a current Help "
            f"{'category' if entity_kind == 'hub' else 'feature'} — "
            "pick one from the list.")


def _check_text(label: str, value: str | None, max_len: int,
                reset_hint: str) -> str | None:
    """Bound-check an optional text override (``None`` = reset)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise _reject(
            f"The {label} can't be empty — use {reset_hint} to return to "
            "the default.")
    if len(text) > max_len:
        raise _reject(f"The {label} is limited to {max_len} characters "
                      f"(got {len(text)}).")
    return text


async def _get_row(gid: int, kind: str, key: str, conn: Any):
    return await fetchone(
        "SELECT display_hidden, display_name, description FROM help_overlay "
        "WHERE guild_id=$1 AND entity_kind=$2 AND entity_key=$3",
        (gid, kind, key), conn=conn)


@workflow("help.record_set_overlay_fields")
async def _record_set_overlay_fields(conn, ctx: WorkflowContext) -> LegOutcome:
    """Set / reset override fields for one Help entity (partial edit —
    the shipped ``set_overlay_fields``, UNSET = key absent from params)."""
    from sb.domain.help.overlay import (
        MAX_DESCRIPTION_LEN,
        MAX_DISPLAY_NAME_LEN,
        HelpOverlayRow,
    )

    gid = int(ctx.guild_id or 0)
    kind = str(ctx.params.get("entity_kind", "") or "")
    key = str(ctx.params.get("entity_key", "") or "")
    fields = dict(ctx.params.get("fields") or {})
    _check_entity(kind, key)
    unknown = set(fields) - set(_FIELDS)
    if unknown:
        raise _reject("Pick a name, description, or visibility edit.")
    if "display_hidden" in fields and fields["display_hidden"] is not None \
            and not isinstance(fields["display_hidden"], bool):
        raise _reject("Visibility can only be hidden or shown.")
    if "display_name" in fields:
        fields["display_name"] = _check_text(
            "name", fields["display_name"], MAX_DISPLAY_NAME_LEN,
            "♻️ Reset name")
    if "description" in fields:
        fields["description"] = _check_text(
            "description", fields["description"], MAX_DESCRIPTION_LEN,
            "♻️ Reset description")

    current = await _get_row(gid, kind, key, conn)
    prev = HelpOverlayRow(
        entity_kind=kind, entity_key=key,
        display_hidden=current["display_hidden"] if current else None,
        display_name=current["display_name"] if current else None,
        description=current["description"] if current else None)
    merged = HelpOverlayRow(
        entity_kind=kind, entity_key=key,
        display_hidden=fields.get("display_hidden", prev.display_hidden),
        display_name=fields.get("display_name", prev.display_name),
        description=fields.get("description", prev.description))

    actor = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    if merged.is_noop:
        # store only deviations: an all-inherit row is deleted.
        await execute(
            "DELETE FROM help_overlay WHERE guild_id=$1 AND entity_kind=$2 "
            "AND entity_key=$3", (gid, kind, key), conn=conn)
        after: dict[str, Any] | None = None
    else:
        await execute(
            "INSERT INTO help_overlay (guild_id, entity_kind, entity_key, "
            "display_hidden, display_name, description, updated_by) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) "
            "ON CONFLICT (guild_id, entity_kind, entity_key) DO UPDATE SET "
            "display_hidden = EXCLUDED.display_hidden, "
            "display_name = EXCLUDED.display_name, "
            "description = EXCLUDED.description, "
            "updated_by = EXCLUDED.updated_by, updated_at = NOW()",
            (gid, kind, key, merged.display_hidden, merged.display_name,
             merged.description, actor or None), conn=conn)
        after = {"display_hidden": merged.display_hidden,
                 "display_name": merged.display_name,
                 "description": merged.description}
    return LegOutcome(
        step=StepResult(gid, "set_overlay_fields", True),
        before={"display_hidden": prev.display_hidden,
                "display_name": prev.display_name,
                "description": prev.description} if current else {},
        after=after or {})


async def _get_home_row(gid: int, conn: Any):
    return await fetchone(
        "SELECT home_title, home_body, home_color FROM help_overlay "
        "WHERE guild_id=$1 AND entity_kind='home' AND entity_key='home'",
        (gid,), conn=conn)


@workflow("help.record_set_home_message")
async def _record_set_home_message(conn, ctx: WorkflowContext) -> LegOutcome:
    """Set / reset the Q-0059 Help-Home message (partial edit — the shipped
    ``set_home_message``; a field ABSENT from ``params['fields']`` is left
    untouched, present-as-``None`` resets it to the default, present-with-
    value overrides). An all-``None`` row is deleted (absence renders the
    byte-identical default Home — "store only deviations")."""
    from sb.domain.help.overlay import (
        MAX_HOME_BODY_LEN,
        MAX_HOME_COLOR,
        MAX_HOME_TITLE_LEN,
        HomeMessage,
    )

    gid = int(ctx.guild_id or 0)
    fields = dict(ctx.params.get("fields") or {})
    unknown = set(fields) - set(_HOME_FIELDS)
    if unknown:
        raise _reject("Pick a Home title, body, or color edit.")
    if "title" in fields:
        fields["title"] = _check_text(
            "Home title", fields["title"], MAX_HOME_TITLE_LEN,
            "♻️ Reset to default")
    if "body" in fields:
        fields["body"] = _check_text(
            "Home body", fields["body"], MAX_HOME_BODY_LEN,
            "♻️ Reset to default")
    if "color" in fields and fields["color"] is not None:
        color = fields["color"]
        if not isinstance(color, int) or isinstance(color, bool):
            raise _reject("Pick an embed color from the list.")
        if not 0 <= color <= MAX_HOME_COLOR:
            raise _reject("That embed color is out of range.")

    current = await _get_home_row(gid, conn)
    prev = HomeMessage(
        title=current["home_title"] if current else None,
        body=current["home_body"] if current else None,
        color=current["home_color"] if current else None)
    merged = HomeMessage(
        title=fields.get("title", prev.title),
        body=fields.get("body", prev.body),
        color=fields.get("color", prev.color))

    actor = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    if merged.is_noop:
        # store only deviations: an all-default home row is deleted.
        await execute(
            "DELETE FROM help_overlay WHERE guild_id=$1 AND "
            "entity_kind='home' AND entity_key='home'", (gid,), conn=conn)
        after: dict[str, Any] | None = None
    else:
        await execute(
            "INSERT INTO help_overlay (guild_id, entity_kind, entity_key, "
            "home_title, home_body, home_color, updated_by) "
            "VALUES ($1, 'home', 'home', $2, $3, $4, $5) "
            "ON CONFLICT (guild_id, entity_kind, entity_key) DO UPDATE SET "
            "home_title = EXCLUDED.home_title, "
            "home_body = EXCLUDED.home_body, "
            "home_color = EXCLUDED.home_color, "
            "updated_by = EXCLUDED.updated_by, updated_at = NOW()",
            (gid, merged.title, merged.body, merged.color, actor or None),
            conn=conn)
        after = {"title": merged.title, "body": merged.body,
                 "color": merged.color}
    return LegOutcome(
        step=StepResult(gid, "set_home_message", True),
        before={"title": prev.title, "body": prev.body,
                "color": prev.color} if current else {},
        after=after or {})


@workflow("help.record_reset_overlay")
async def _record_reset_overlay(conn, ctx: WorkflowContext) -> LegOutcome:
    """Full reset: delete every overlay row for the guild (the shipped
    ``reset_guild_overlay``)."""
    gid = int(ctx.guild_id or 0)
    row = await fetchone(
        "SELECT COUNT(*) AS n FROM help_overlay WHERE guild_id=$1",
        (gid,), conn=conn)
    removed = int(row["n"]) if row else 0
    await execute("DELETE FROM help_overlay WHERE guild_id=$1", (gid,),
                  conn=conn)
    return LegOutcome(
        step=StepResult(gid, "reset_overlay", True),
        before={"rows": removed}, after={"rows": 0})


def _op(op_key: str, verb: str, ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="help", lane=WorkflowLane.DOMAIN,
        authority_ref="administrator",       # the shipped admin floor
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


SET_OVERLAY_FIELDS = _op("help.set_overlay_fields", "help_overlay_update",
                         "help.record_set_overlay_fields")
SET_HOME_MESSAGE = _op("help.set_home_message", "help_overlay_update",
                       "help.record_set_home_message")
RESET_OVERLAY = _op("help.reset_overlay", "help_overlay_reset",
                    "help.record_reset_overlay")

_OPS = (SET_OVERLAY_FIELDS, SET_HOME_MESSAGE, RESET_OVERLAY)

_REF_TABLE = (
    ("help.record_set_overlay_fields", _record_set_overlay_fields),
    ("help.record_set_home_message", _record_set_home_message),
    ("help.record_reset_overlay", _record_reset_overlay),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
        from sb.domain.help.overlay import invalidate_help_overlay_cache
        from sb.kernel.workflow import engine as _engine

        result = await _engine.run(op, ctx)
        if getattr(result, "outcome", None) == "success":
            # write-through: the read cache never serves a stale overlay
            # (the shipped invalidate-after-write contract).
            invalidate_help_overlay_cache(int(ctx.guild_id or 0))
        return result
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


async def delete_guild_rows(guild_id: int, conn: Any = None) -> int:
    """Guild-teardown delete (paired cache drop — the command_access
    forget contract: they never diverge)."""
    from sb.domain.help.overlay import invalidate_help_overlay_cache
    from sb.kernel.db.pool import fetchone as _fetchone

    row = await _fetchone(
        "SELECT COUNT(*) AS n FROM help_overlay WHERE guild_id=$1",
        (int(guild_id),), conn=conn)
    await execute("DELETE FROM help_overlay WHERE guild_id=$1",
                  (int(guild_id),), conn=conn)
    invalidate_help_overlay_cache(guild_id)
    return int(row["n"]) if row else 0


def _register_teardown() -> None:
    from sb.domain.platform.guild_teardown import register_teardown

    async def _hook(guild_id: int) -> None:
        await delete_guild_rows(int(guild_id))

    try:
        register_teardown("help_overlay", _hook)
    except Exception as exc:  # noqa: BLE001 — duplicate re-arm is benign
        logger.debug("help_overlay teardown re-register: %s", exc)


def ensure_refs() -> None:
    from sb.spec.refs import EngineRef, engine, is_registered
    from sb.spec.refs import workflow as _workflow

    from sb.domain.help.overlay import _store_marker

    if not is_registered(EngineRef("help.overlay_store")):
        engine("help.overlay_store")(_store_marker)
    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()


register_ops()
_register_teardown()
