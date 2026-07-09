"""Role-family CRUD (band 5) — asyncpg SQL behind the K3 seam; migration
``0017_roles.sql``. Sole-writer discipline: mutations happen only in the
K7 role ops (sb/domain/role/ops.py).

Rollback disposition (S14): every table is guild CONFIG or a derived
counter — bears_value=False, NAME_STABLE, DECLARED_LOSS (band-1 Q3-B; no
reverse importers). role_grants carries member ids => MEMBER_ID with a
delete-rows erasure body (a temp grant is a live pointer, not a trail);
role_menu_pickup_stats is aggregate-by-role (no member ids) => NONE.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "REACTION_MODES_STORE",
    "REACTION_ROLES_STORE",
    "ROLE_EXEMPTIONS_STORE",
    "ROLE_GRANTS_STORE",
    "ROLE_MENU_OPTIONS_STORE",
    "ROLE_MENUS_STORE",
    "ROLE_PICKUP_STATS_STORE",
    "ROLE_THRESHOLDS_STORE",
    "ensure_refs",
]


def _config_store(table: str, readers: tuple[str, ...] = ("diagnostics",),
                  **kw) -> StoreSpec:
    return register_store(StoreSpec(
        table=table,
        sole_writer=EngineRef("role.store"),
        retention="permanent",
        checkpoint_class=CheckpointClass.AGGREGATE,
        invariant_tag=table,
        forward_map_kind=ForwardMapKind.NAME_STABLE,
        reader_domains=readers,
        bears_value=False,
        data_class=kw.pop("data_class", DataClass.NONE),
        **kw))


ROLE_THRESHOLDS_STORE = _config_store("role_thresholds", ("xp", "diagnostics"))
REACTION_ROLES_STORE = _config_store("reaction_roles")
REACTION_MODES_STORE = _config_store("reaction_role_message_modes")
ROLE_MENUS_STORE = _config_store("role_menus")
ROLE_MENU_OPTIONS_STORE = _config_store("role_menu_options")
ROLE_GRANTS_STORE = _config_store(
    "role_grants", data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("role.erase_subject_grants"))
ROLE_PICKUP_STATS_STORE = _config_store("role_menu_pickup_stats")
ROLE_EXEMPTIONS_STORE = _config_store("role_automation_exemptions",
                                      ("xp", "diagnostics"))


@engine("role.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/role/store.py"


# --- thresholds ---------------------------------------------------------------

async def get_thresholds(guild_id: int, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT role_name, days_required, level_required, xp_auto_assign, "
        "role_id, display_name FROM role_thresholds WHERE guild_id=$1 "
        "ORDER BY days_required", (guild_id,), conn=conn)


async def upsert_threshold(conn: Any, *, guild_id: int, role_name: str,
                           days_required: int = 0,
                           level_required: int | None = None,
                           xp_auto_assign: bool = False,
                           role_id: int | None = None,
                           display_name: str | None = None) -> None:
    await execute(
        "INSERT INTO role_thresholds (guild_id, role_name, days_required, "
        "level_required, xp_auto_assign, role_id, display_name) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7) "
        "ON CONFLICT (guild_id, role_name) DO UPDATE SET "
        "days_required = EXCLUDED.days_required, "
        "level_required = EXCLUDED.level_required, "
        "xp_auto_assign = EXCLUDED.xp_auto_assign, "
        "role_id = EXCLUDED.role_id, display_name = EXCLUDED.display_name",
        (guild_id, role_name, days_required, level_required, xp_auto_assign,
         role_id, display_name), conn=conn)


async def delete_threshold(conn: Any, *, guild_id: int,
                           role_name: str) -> bool:
    rows = await fetchall(
        "DELETE FROM role_thresholds WHERE guild_id=$1 AND role_name=$2 "
        "RETURNING guild_id", (guild_id, role_name), conn=conn)
    return bool(rows)


# --- legacy reaction roles ------------------------------------------------------

async def bind_reaction(conn: Any, *, guild_id: int, message_id: int,
                        emoji: str, role_id: int) -> None:
    await execute(
        "INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id) "
        "VALUES ($1, $2, $3, $4) "
        "ON CONFLICT (guild_id, message_id, emoji) "
        "DO UPDATE SET role_id = EXCLUDED.role_id",
        (guild_id, message_id, emoji, role_id), conn=conn)


async def unbind_reaction(conn: Any, *, guild_id: int, message_id: int,
                          emoji: str) -> bool:
    rows = await fetchall(
        "DELETE FROM reaction_roles WHERE guild_id=$1 AND message_id=$2 "
        "AND emoji=$3 RETURNING role_id",
        (guild_id, message_id, emoji), conn=conn)
    return bool(rows)


async def get_reaction_binding(guild_id: int, message_id: int, emoji: str,
                               conn: Any = None) -> int | None:
    row = await fetchone(
        "SELECT role_id FROM reaction_roles WHERE guild_id=$1 "
        "AND message_id=$2 AND emoji=$3",
        (guild_id, message_id, emoji), conn=conn)
    return None if row is None else int(row["role_id"])


async def list_reaction_bindings(guild_id: int, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT message_id, emoji, role_id FROM reaction_roles "
        "WHERE guild_id=$1 ORDER BY message_id", (guild_id,), conn=conn)


async def sibling_reaction_bindings(guild_id: int, message_id: int,
                                    conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT emoji, role_id FROM reaction_roles WHERE guild_id=$1 "
        "AND message_id=$2", (guild_id, message_id), conn=conn)


# --- message modes -----------------------------------------------------------------

async def set_message_mode(conn: Any, *, guild_id: int, message_id: int,
                           mode: str) -> None:
    await execute(
        "INSERT INTO reaction_role_message_modes (guild_id, message_id, mode) "
        "VALUES ($1, $2, $3) ON CONFLICT (guild_id, message_id) "
        "DO UPDATE SET mode = EXCLUDED.mode",
        (guild_id, message_id, mode), conn=conn)


async def get_message_mode(guild_id: int, message_id: int,
                           conn: Any = None) -> str:
    row = await fetchone(
        "SELECT mode FROM reaction_role_message_modes WHERE guild_id=$1 "
        "AND message_id=$2", (guild_id, message_id), conn=conn)
    return str(row["mode"]) if row else "normal"


async def clear_message_mode(conn: Any, *, guild_id: int,
                             message_id: int) -> bool:
    rows = await fetchall(
        "DELETE FROM reaction_role_message_modes WHERE guild_id=$1 "
        "AND message_id=$2 RETURNING mode",
        (guild_id, message_id), conn=conn)
    return bool(rows)


# --- role menus ------------------------------------------------------------------------

async def insert_menu(conn: Any, *, guild_id: int, channel_id: int,
                      title: str, description: str | None, style: str,
                      mode: str, max_roles: int, theme: str) -> int:
    row = await fetchone(
        "INSERT INTO role_menus (guild_id, channel_id, title, description, "
        "style, mode, max_roles, theme) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) "
        "RETURNING menu_id",
        (guild_id, channel_id, title, description, style, mode, max_roles,
         theme), conn=conn)
    return int(row["menu_id"])


async def replace_menu_options(conn: Any, *, menu_id: int,
                               options: list[dict]) -> None:
    await execute("DELETE FROM role_menu_options WHERE menu_id=$1",
                  (menu_id,), conn=conn)
    for pos, opt in enumerate(options):
        await execute(
            "INSERT INTO role_menu_options (menu_id, role_id, emoji, label, "
            "position) VALUES ($1,$2,$3,$4,$5)",
            (menu_id, int(opt["role_id"]), opt.get("emoji"),
             opt.get("label"), pos), conn=conn)


async def update_menu_fields(conn: Any, *, menu_id: int, **fields) -> None:
    allowed = {"title", "description", "style", "mode", "max_roles", "theme",
               "channel_id", "message_id"}
    sets, args = [], []
    for i, (k, v) in enumerate(sorted(fields.items()), start=2):
        if k not in allowed:
            raise ValueError(f"role_menus column {k!r} is not updatable")
        sets.append(f"{k} = ${i}")
        args.append(v)
    if not sets:
        return
    await execute(
        f"UPDATE role_menus SET {', '.join(sets)} WHERE menu_id = $1",
        (menu_id, *args), conn=conn)


async def delete_menu(conn: Any, *, menu_id: int) -> bool:
    rows = await fetchall(
        "DELETE FROM role_menus WHERE menu_id=$1 RETURNING menu_id",
        (menu_id,), conn=conn)
    return bool(rows)


async def get_menu(menu_id: int, conn: Any = None) -> dict | None:
    return await fetchone(
        "SELECT menu_id, guild_id, channel_id, message_id, title, "
        "description, style, mode, max_roles, theme FROM role_menus "
        "WHERE menu_id=$1", (menu_id,), conn=conn)


async def get_menu_options(menu_id: int, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT role_id, emoji, label, position FROM role_menu_options "
        "WHERE menu_id=$1 ORDER BY position", (menu_id,), conn=conn)


async def list_menus(guild_id: int, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT menu_id, channel_id, message_id, title, style, mode, "
        "max_roles FROM role_menus WHERE guild_id=$1 ORDER BY menu_id",
        (guild_id,), conn=conn)


async def get_menu_by_message(guild_id: int, message_id: int,
                              conn: Any = None) -> dict | None:
    return await fetchone(
        "SELECT menu_id, guild_id, channel_id, message_id, title, "
        "description, style, mode, max_roles, theme FROM role_menus "
        "WHERE guild_id=$1 AND message_id=$2",
        (guild_id, message_id), conn=conn)


# --- temp role grants -----------------------------------------------------------------

async def upsert_grant(conn: Any, *, guild_id: int, member_id: int,
                       role_id: int, expires_at: datetime,
                       granted_by: int | None) -> None:
    await execute(
        "INSERT INTO role_grants (guild_id, member_id, role_id, expires_at, "
        "granted_by) VALUES ($1,$2,$3,$4,$5) "
        "ON CONFLICT (guild_id, member_id, role_id) "
        "DO UPDATE SET expires_at = EXCLUDED.expires_at, "
        "granted_by = EXCLUDED.granted_by",
        (guild_id, member_id, role_id, expires_at, granted_by), conn=conn)


async def list_grants_for_member(guild_id: int, member_id: int,
                                 conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT grant_id, role_id, expires_at, granted_by FROM role_grants "
        "WHERE guild_id=$1 AND member_id=$2 ORDER BY expires_at",
        (guild_id, member_id), conn=conn)


async def list_expired_grants(now: datetime, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT grant_id, guild_id, member_id, role_id FROM role_grants "
        "WHERE expires_at <= $1 ORDER BY expires_at", (now,), conn=conn)


async def delete_grant(conn: Any, *, grant_id: int) -> bool:
    rows = await fetchall(
        "DELETE FROM role_grants WHERE grant_id=$1 RETURNING grant_id",
        (grant_id,), conn=conn)
    return bool(rows)


async def erase_subject_grants(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM role_grants WHERE member_id=$1 RETURNING grant_id",
        (user_id,), conn=conn)
    return len(rows)


# --- pickup stats ------------------------------------------------------------------------

async def record_pickup(conn: Any, *, guild_id: int, role_id: int,
                        picked: bool, now: datetime) -> None:
    if picked:
        await execute(
            "INSERT INTO role_menu_pickup_stats (guild_id, role_id, picked, "
            "last_picked_at) VALUES ($1,$2,1,$3) "
            "ON CONFLICT (guild_id, role_id) DO UPDATE SET "
            "picked = role_menu_pickup_stats.picked + 1, "
            "last_picked_at = EXCLUDED.last_picked_at",
            (guild_id, role_id, now), conn=conn)
    else:
        await execute(
            "INSERT INTO role_menu_pickup_stats (guild_id, role_id, removed) "
            "VALUES ($1,$2,1) ON CONFLICT (guild_id, role_id) DO UPDATE SET "
            "removed = role_menu_pickup_stats.removed + 1",
            (guild_id, role_id), conn=conn)


async def pickup_stats(guild_id: int, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT role_id, picked, removed, last_picked_at "
        "FROM role_menu_pickup_stats WHERE guild_id=$1 "
        "ORDER BY picked DESC", (guild_id,), conn=conn)


# --- exemptions -------------------------------------------------------------------------

async def get_exemptions(guild_id: int, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT role_id, exempt_xp, exempt_time "
        "FROM role_automation_exemptions WHERE guild_id=$1",
        (guild_id,), conn=conn)


async def set_exemption_row(conn: Any, *, guild_id: int, role_id: int,
                            exempt_xp: bool, exempt_time: bool) -> None:
    await execute(
        "INSERT INTO role_automation_exemptions (guild_id, role_id, "
        "exempt_xp, exempt_time) VALUES ($1,$2,$3,$4) "
        "ON CONFLICT (guild_id, role_id) DO UPDATE SET "
        "exempt_xp = EXCLUDED.exempt_xp, exempt_time = EXCLUDED.exempt_time",
        (guild_id, role_id, exempt_xp, exempt_time), conn=conn)


async def clear_exemption_row(conn: Any, *, guild_id: int,
                              role_id: int) -> bool:
    rows = await fetchall(
        "DELETE FROM role_automation_exemptions WHERE guild_id=$1 "
        "AND role_id=$2 RETURNING role_id", (guild_id, role_id), conn=conn)
    return bool(rows)


# --- guild teardown ---------------------------------------------------------------------

async def delete_guild_role_rows(guild_id: int, conn: Any = None) -> None:
    """Guild-leave teardown (shipped steps 23-30): menus (options cascade),
    modes, grants, pickup stats, thresholds, exemptions, reaction_roles."""
    for sql in (
        "DELETE FROM role_menus WHERE guild_id=$1",
        "DELETE FROM reaction_role_message_modes WHERE guild_id=$1",
        "DELETE FROM role_grants WHERE guild_id=$1",
        "DELETE FROM role_menu_pickup_stats WHERE guild_id=$1",
        "DELETE FROM role_thresholds WHERE guild_id=$1",
        "DELETE FROM role_automation_exemptions WHERE guild_id=$1",
        "DELETE FROM reaction_roles WHERE guild_id=$1",
    ):
        await execute(sql, (guild_id,), conn=conn)


def ensure_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("role.store")):
        _engine("role.store")(_store_marker)
