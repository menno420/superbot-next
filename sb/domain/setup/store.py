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
    "SETUP_SESSION_STORE",
    "ensure_refs",
    "get_session_row",
    "scrub_subject_session",
    "upsert_session",
]

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
