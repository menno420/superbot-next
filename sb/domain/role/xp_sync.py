"""Shared XP level-role planning (band 5) — services/xp_role_sync.py
verbatim, headless: ONE pure planner shared by the live level-up path
(the granter this band installs into sb.domain.xp.service) and the
bot-to-bot migration, so stack/exempt logic can never drift.
"""

from __future__ import annotations

from typing import Any

from sb.domain.role.automation import Assignment

__all__ = ["plan_level_role_assignments"]


def _resolve_role(guild: Any, *, role_id: int | None, name: str) -> Any | None:
    """Cache-only id-first resolve with normalized-name fallback."""
    roles = getattr(guild, "roles", ()) or ()
    if role_id is not None:
        for role in roles:
            if getattr(role, "id", None) == role_id:
                return role
    norm = (name or "").strip().lower()
    for role in roles:
        if (getattr(role, "name", "") or "").strip().lower() == norm:
            return role
    return None


def plan_level_role_assignments(
    guild: Any,
    member: Any,
    new_level: int,
    *,
    stack: bool,
    exempt_xp_ids: frozenset[int],
    xp_roles: list[dict],
    reason: str,
) -> list[Assignment]:
    """The role add/remove set that brings *member* to *new_level* — pure.

    Stacking: one promote per newly-earned unheld role. Single-role mode:
    keep only the highest earned tier (xp_roles ordered ascending by
    level_required). [] when exempt / nothing resolves / already correct.
    """
    member_role_ids = {r.id for r in getattr(member, "roles", ())}
    if member_role_ids & exempt_xp_ids:
        return []

    qualifying: list = []
    configured: list = []
    for role_cfg in xp_roles:
        discord_role = _resolve_role(
            guild, role_id=role_cfg.get("role_id"), name=role_cfg["role_name"])
        if discord_role is None:
            continue
        configured.append(discord_role)
        if role_cfg["level_required"] <= new_level:
            qualifying.append(discord_role)
    if not qualifying:
        return []

    member_roles = member.roles
    member_display = getattr(member, "display_name",
                             str(getattr(member, "id", "?")))
    assignments: list[Assignment] = []

    if stack:
        for r in (role for role in qualifying if role not in member_roles):
            assignments.append(Assignment(
                member_id=member.id, member_display=member_display,
                add_role_id=r.id, add_role_name=r.name,
                remove_role_ids=(), remove_role_names=(),
                reason=reason, days_in_guild=0))
    else:
        target = qualifying[-1]
        add = None if target in member_roles else target
        to_remove = [r for r in configured
                     if r != target and r in member_roles]
        if add is not None or to_remove:
            assignments.append(Assignment(
                member_id=member.id, member_display=member_display,
                add_role_id=add.id if add is not None else None,
                add_role_name=add.name if add is not None else None,
                remove_role_ids=tuple(r.id for r in to_remove),
                remove_role_names=tuple(r.name for r in to_remove),
                reason=reason, days_in_guild=0))
    return assignments
