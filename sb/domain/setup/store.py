"""Setup-session CRUD (the setup parity flip) — asyncpg SQL behind the K3
seam; migration ``0037_setup_session.sql`` (the oracle's disbot/migrations/
031_setup_session.sql shape, imported NAME_STABLE; reconstructed @befc6d0d).
Sole-writer discipline: mutations happen only in the K7 setup ops
(sb/domain/setup/ops.py).

Rollback disposition (S14): setup_session is guild ONBOARDING state —
bears_value=False, NAME_STABLE, no reverse importers (Q3-B: a wizard
session is re-enterable; nothing of monetary value rides it). The row is
keyed on the guild but CARRIES member ids (owner_id + delegated_admins)
=> MEMBER_ID with a scrub erasure body (the owner's row is the guild's
live wizard pointer, not a trail — deleting it would silently reset the
guild's onboarding, so erasure zeroes the subject ids instead: the
role_grants delete-pointer vs karma tombstone middle ground).
"""

from __future__ import annotations

from typing import Any

from sb.kernel.db.pool import execute, fetchone
from sb.spec.refs import EngineRef, WorkflowRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "KNOWN_DEPTHS",
    "SETUP_SESSION_STORE",
    "clear_essential_anchor",
    "clear_workspace_pointers",
    "ensure_refs",
    "get_session_row",
    "list_resumable_sessions",
    "mark_in_progress",
    "scrub_subject_session",
    "set_depth",
    "set_essential_step",
    "set_section_skip",
    "set_session_status",
    "upsert_session",
]

#: shipped value set, verbatim (disbot utils/db/setup_session.py
#: ``KNOWN_DEPTHS`` — the migration-038 CHECK constraint's Python twin).
KNOWN_DEPTHS: frozenset[str] = frozenset({"quick", "standard", "advanced"})

SETUP_SESSION_STORE = register_store(StoreSpec(
    table="setup_session",
    sole_writer=EngineRef("setup.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="setup_session",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("setup.erase_subject_session"),
))


@engine("setup.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/setup/store.py"


def ensure_refs() -> None:
    """Re-arm the sole-writer marker after a sanctioned clear_ref_table
    (the #141 doctrine)."""
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("setup.store")):
        _engine("setup.store")(_store_marker)


# --- reads -------------------------------------------------------------------------

async def get_session_row(guild_id: int, conn: Any = None) -> dict | None:
    """The shipped ``setup_session.resume_session`` row read (None until a
    wizard entry mints the guild's row — goldens/setup/
    sweep_slash_setup-status pins the ``no session`` branch)."""
    row = await fetchone(
        "SELECT guild_id, guild_name, owner_id, setup_status, joined_at, "
        "setup_channel_id, setup_message_id, last_readiness_score, "
        "current_step, delegated_admins, skipped_sections, "
        "acknowledged_sections, depth, purpose, essential_message_id, "
        "essential_step, created_at, updated_at "
        "FROM setup_session WHERE guild_id=$1", (guild_id,), conn=conn)
    return dict(row) if row else None


async def list_resumable_sessions() -> list[dict]:
    """The on-ready resume sweep's roster read: every session row still
    carrying a persisted message pointer — a workspace anchor
    (``setup_channel_id`` + ``setup_message_id``, the launcher-refresh
    leg's input) and/or an interrupted essential flow
    (``setup_channel_id`` + ``essential_message_id``, the revive leg's
    input). The oracle iterated ``bot.guilds`` and read each row
    (setup_cog._resume_launchers / essential_setup.revive_essential_flows);
    the durable rows already know, so ONE query replaces the guild walk."""
    from sb.kernel.db.pool import fetchall

    rows = await fetchall(
        "SELECT guild_id, setup_status, setup_channel_id, setup_message_id, "
        "essential_message_id, essential_step "
        "FROM setup_session "
        "WHERE setup_channel_id IS NOT NULL "
        "  AND (setup_message_id IS NOT NULL "
        "       OR essential_message_id IS NOT NULL) "
        "ORDER BY guild_id")
    return [dict(row) for row in rows or ()]


# --- write primitives (K7 leg only — conn REQUIRED) ---------------------------------

async def upsert_session(conn: Any, *, guild_id: int, guild_name: str,
                         owner_id: int, setup_status: str,
                         setup_channel_id: int | None,
                         setup_message_id: int | None,
                         current_step: str | None) -> None:
    """The shipped ``start_session`` upsert verbatim shape (disbot
    utils/db/setup_session.py: INSERT the identity/pointer columns, let
    the column defaults mint the array/timestamp state; ON CONFLICT
    refreshes status/pointers/updated_at). goldens/setup/
    sweep_slash_setup-hub pins the fresh pending row,
    sweep_slash_setup-advanced the in_progress + workspace-pointer row."""
    await execute(
        "INSERT INTO setup_session "
        "    (guild_id, guild_name, owner_id, setup_status, "
        "     setup_channel_id, setup_message_id, current_step) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7) "
        "ON CONFLICT (guild_id) DO UPDATE SET "
        "    guild_name       = EXCLUDED.guild_name, "
        "    setup_status     = EXCLUDED.setup_status, "
        "    setup_channel_id = EXCLUDED.setup_channel_id, "
        "    setup_message_id = EXCLUDED.setup_message_id, "
        "    current_step     = EXCLUDED.current_step, "
        "    updated_at       = NOW()",
        (guild_id, guild_name, owner_id, setup_status,
         setup_channel_id, setup_message_id, current_step), conn=conn)


async def set_depth(conn: Any, *, guild_id: int, depth: str | None) -> None:
    """The shipped ``set_depth`` UPDATE verbatim shape (disbot
    utils/db/setup_session.py: value-checked against ``KNOWN_DEPTHS``, a
    bare UPDATE keyed on the guild — no row means a silent no-op, the
    shipped semantics)."""
    if depth is not None and depth not in KNOWN_DEPTHS:
        raise ValueError(
            f"depth must be one of {sorted(KNOWN_DEPTHS)} or None, got {depth!r}")
    await execute(
        "UPDATE setup_session SET depth = $2, updated_at = NOW() "
        "WHERE guild_id = $1", (guild_id, depth), conn=conn)


async def set_section_skip(conn: Any, *, guild_id: int, slug: str,
                           skipped: bool) -> None:
    """The shipped ``add_skipped_section`` / ``remove_skipped_section``
    UPDATE pair verbatim shape (idempotent set semantics: append via
    DISTINCT UNNEST, drop via ARRAY_REMOVE; no row = silent no-op)."""
    if skipped:
        await execute(
            "UPDATE setup_session "
            "   SET skipped_sections = ("
            "           SELECT ARRAY(SELECT DISTINCT UNNEST(skipped_sections || $2::TEXT)) "
            "           FROM setup_session WHERE guild_id = $1"
            "       ), "
            "       updated_at = NOW() "
            " WHERE guild_id = $1", (guild_id, slug), conn=conn)
    else:
        await execute(
            "UPDATE setup_session "
            "   SET skipped_sections = ARRAY_REMOVE(skipped_sections, $2::TEXT), "
            "       updated_at = NOW() "
            " WHERE guild_id = $1", (guild_id, slug), conn=conn)


async def mark_in_progress(conn: Any, *, guild_id: int,
                           step: str | None) -> None:
    """The shipped ``setup_session.mark_in_progress`` write shape
    (services/setup_session.py: ``set_status("in_progress")`` +
    ``set_step(step)`` — two bare keyed UPDATEs, folded into one; no row
    means a silent no-op, the set_depth semantics twin). Every section
    open / staging lane records its step marker through this (the
    section-flows slice)."""
    if step is None:
        await execute(
            "UPDATE setup_session SET setup_status = 'in_progress', "
            "updated_at = NOW() WHERE guild_id = $1", (guild_id,), conn=conn)
    else:
        await execute(
            "UPDATE setup_session SET setup_status = 'in_progress', "
            "current_step = $2, updated_at = NOW() "
            "WHERE guild_id = $1", (guild_id, step), conn=conn)


async def set_session_status(conn: Any, *, guild_id: int,
                             status: str) -> None:
    """The shipped ``mark_complete`` UPDATE shape (disbot
    utils/db/setup_session.py: a bare status UPDATE keyed on the guild —
    no row means a silent no-op, the set_depth semantics twin). The
    final-review apply lane writes ``complete`` on full success."""
    await execute(
        "UPDATE setup_session SET setup_status = $2, updated_at = NOW() "
        "WHERE guild_id = $1", (guild_id, status), conn=conn)


async def set_essential_step(conn: Any, *, guild_id: int, step: int) -> None:
    """The shipped ``setup_session.set_essential_step`` UPDATE shape
    (the migration-099 essential-flow anchor: the 0-based step index the
    resume lane rebuilds at). A bare keyed UPDATE — no row means a
    silent no-op, the set_depth semantics twin (the ``!setup`` entry
    mints no session row; the golden-pinned empty delta stands)."""
    await execute(
        "UPDATE setup_session SET essential_step = $2, updated_at = NOW() "
        "WHERE guild_id = $1", (guild_id, int(step)), conn=conn)


async def clear_essential_anchor(conn: Any, *, guild_id: int) -> None:
    """The shipped ``setup_session.clear_essential_anchor`` UPDATE shape
    (the flow reached the summary — null the anchor pair so the on-ready
    resume sweep stops trying to revive a done flow)."""
    await execute(
        "UPDATE setup_session SET essential_message_id = NULL, "
        "essential_step = NULL, updated_at = NOW() "
        "WHERE guild_id = $1", (guild_id,), conn=conn)


async def clear_workspace_pointers(conn: Any, *, guild_id: int) -> None:
    """The shipped post-cleanup pointer nulls (setup_channel.py
    ``set_session_channel_id(guild_id, None)`` +
    ``set_session_message_id(guild_id, None)`` — folded into one keyed
    UPDATE; no row = silent no-op) so the next ``/setup`` re-creates a
    fresh channel."""
    await execute(
        "UPDATE setup_session SET setup_channel_id = NULL, "
        "setup_message_id = NULL, updated_at = NOW() "
        "WHERE guild_id = $1", (guild_id,), conn=conn)


# --- privacy erasure row helper (flag-18 discipline) --------------------------------

async def scrub_subject_session(conn: Any, *, user_id: int) -> int:
    """Zero the subject's ids wherever they appear (owner slot +
    delegated_admins entries); the guild's wizard row itself stays."""
    from sb.kernel.db.pool import fetchall

    tagged = await fetchall(
        "UPDATE setup_session SET owner_id = 0 "
        "WHERE owner_id = $1 RETURNING guild_id", (user_id,), conn=conn)
    await execute(
        "UPDATE setup_session SET delegated_admins = "
        "array_remove(delegated_admins, $1) "
        "WHERE $1 = ANY(delegated_admins)", (user_id,), conn=conn)
    return len(tagged or ())
