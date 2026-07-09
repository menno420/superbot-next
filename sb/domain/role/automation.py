"""Role-automation decision logic (band 5) — services/role_automation.py
ported verbatim, headless: the time/threshold progression planner
(compute_assignments), single-member reasoning (explain_assignment_for),
the owner-facing preflight, and the classified apply loop.

``apply`` performs Discord role mutations through the installable
GuildRoleActions port (sb/domain/role/service.py — the band-2
GuildModerationActions pattern, fail-loud default) and emits one
``audit.action_recorded`` fact per successful change through the
installed bus (the shipped emit_audit_action was the same best-effort
in-process emit).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sb.domain.role.feasibility import (
    ABOVE_BOT,
    BOT_MISSING_MANAGE_ROLES,
    EVERYONE,
    MANAGED,
    evaluate_role,
)

logger = logging.getLogger("sb.domain.role.automation")

__all__ = [
    "Assignment",
    "ApplyError",
    "ApplyResult",
    "PreflightResult",
    "RoleThreshold",
    "apply",
    "check_preflight",
    "compute_assignments",
    "explain_assignment_for",
    "summarize_failures",
]


@dataclass(frozen=True)
class RoleThreshold:
    """One progression row; role_id (old migration 056) resolves id-first
    so a rename never orphans the tier; None = legacy name-only row."""

    role_name: str
    days_required: int
    role_id: int | None = None


@dataclass(frozen=True)
class Assignment:
    member_id: int
    member_display: str
    add_role_id: int | None
    add_role_name: str | None
    remove_role_ids: tuple[int, ...]
    remove_role_names: tuple[str, ...]
    reason: str
    days_in_guild: int


@dataclass(frozen=True)
class PreflightResult:
    bot_has_manage_roles: bool
    hierarchy_blockers: tuple[str, ...] = ()
    missing_roles: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return (self.bot_has_manage_roles and not self.hierarchy_blockers
                and not self.missing_roles)


# apply-specific reason codes (manageability codes come from feasibility)
MEMBER_NOT_CACHED = "member_not_cached"
FORBIDDEN = "forbidden"
NOT_FOUND = "not_found"
HTTP_ERROR = "http_error"
UNKNOWN = "unknown"

_FAILURE_LABELS: dict[str, str] = {
    BOT_MISSING_MANAGE_ROLES: "missing Manage Roles",
    ABOVE_BOT: "role above my top role",
    MANAGED: "integration-managed role",
    EVERYONE: "the @everyone role",
    MEMBER_NOT_CACHED: "member not in cache",
    FORBIDDEN: "permission denied",
    NOT_FOUND: "member or role not found",
    HTTP_ERROR: "Discord API error",
    UNKNOWN: "unexpected error",
}


@dataclass(frozen=True)
class ApplyError:
    member_id: int
    phase: str   # "lookup" | "preflight" | "mutate"
    code: str
    detail: str


@dataclass(frozen=True)
class ApplyResult:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    failures: tuple[ApplyError, ...] = ()

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(f"member {f.member_id}: {f.detail}"
                     for f in self.failures)

    def failure_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.failures:
            counts[f.code] = counts.get(f.code, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def summarize_failures(result: ApplyResult) -> str:
    return ", ".join(
        f"{_FAILURE_LABELS.get(code, code)}: {n}"
        for code, n in result.failure_counts().items())


# --- pure decision logic (shipped verbatim) ---------------------------------------

def _normalize(name: str | None) -> str:
    return (name or "").strip().lower()


def _resolve_role(guild: Any, name: str) -> Any | None:
    norm = _normalize(name)
    for role in getattr(guild, "roles", ()) or ():
        if _normalize(role.name) == norm:
            return role
    return None


def _resolve_threshold_role(guild: Any, threshold: RoleThreshold) -> Any | None:
    """Id-first, normalized-name fallback; cache-only iteration."""
    rid = getattr(threshold, "role_id", None)
    if rid is not None:
        for role in getattr(guild, "roles", ()) or ():
            if getattr(role, "id", None) == rid:
                return role
    return _resolve_role(guild, threshold.role_name)


def compute_assignments(
    guild: Any,
    thresholds: list[RoleThreshold] | tuple[RoleThreshold, ...],
    *,
    exempt_role_ids: frozenset[int] = frozenset(),
    keep_previous_tier: bool = False,
    now: datetime | None = None,
) -> tuple[Assignment, ...]:
    """Walk guild.members and produce planned operations — pure."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    if not thresholds:
        return ()

    resolved = [
        (role, t.days_required)
        for t in thresholds
        if (role := _resolve_threshold_role(guild, t)) is not None
    ]
    if not resolved:
        return ()
    role_map = {role.name: days for role, days in resolved}
    role_by_name = {role.name: role for role, _ in resolved}
    progression = sorted(role_map, key=lambda r: role_map[r])

    out: list[Assignment] = []
    for member in getattr(guild, "members", ()) or ():
        if getattr(member, "bot", False):
            continue
        if any(getattr(r, "id", None) in exempt_role_ids
               for r in getattr(member, "roles", ())):
            continue
        joined_at = getattr(member, "joined_at", None)
        if joined_at is None:
            continue

        days = (now - joined_at).days

        target_name: str | None = None
        for name in progression:
            if days >= role_map[name]:
                target_name = name

        target_role = role_by_name.get(target_name) if target_name else None
        member_roles = list(getattr(member, "roles", ()) or ())

        current_highest: str | None = None
        for role in member_roles:
            matched = next(
                (n for n in role_map
                 if _normalize(n) == _normalize(role.name)), None)
            if matched is not None:
                if current_highest is None or progression.index(
                        matched) > progression.index(current_highest):
                    current_highest = matched

        if (current_highest and target_name
                and progression.index(current_highest)
                > progression.index(target_name)):
            continue  # never demote

        to_remove = ([] if keep_previous_tier else [
            r for r in member_roles
            if any(_normalize(r.name) == _normalize(n) for n in role_map)
            and r != target_role])

        add_role_id = target_role.id if target_role else None
        add_role_name = target_role.name if target_role else None
        already_assigned = (target_role in member_roles
                            if target_role else False)

        if not to_remove and already_assigned:
            continue  # no-op

        if target_role and not already_assigned and not to_remove:
            reason = (f"{member.display_name} has {days} day(s) in guild; "
                      f"earns role '{target_role.name}'.")
        elif to_remove and target_role and not already_assigned:
            reason = (f"{member.display_name} has {days} day(s); promote to "
                      f"'{target_role.name}', remove "
                      f"{[r.name for r in to_remove]}.")
        elif to_remove and not target_role:
            reason = (f"{member.display_name} no longer earns any "
                      f"progression role at {days} day(s); remove "
                      f"{[r.name for r in to_remove]}.")
        else:
            reason = "no-op"

        out.append(Assignment(
            member_id=member.id,
            member_display=getattr(member, "display_name", str(member.id)),
            add_role_id=add_role_id if not already_assigned else None,
            add_role_name=add_role_name if not already_assigned else None,
            remove_role_ids=tuple(r.id for r in to_remove),
            remove_role_names=tuple(r.name for r in to_remove),
            reason=reason,
            days_in_guild=days))
    return tuple(out)


class _SingleMemberGuild:
    """Adapter exposing one member as guild.members (shipped)."""

    def __init__(self, guild: Any, member: Any) -> None:
        self._guild = guild
        self._member = member

    @property
    def roles(self):
        return getattr(self._guild, "roles", ()) or ()

    @property
    def members(self):
        return (self._member,)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._guild, name)


def explain_assignment_for(
    guild: Any, member: Any,
    thresholds: list[RoleThreshold] | tuple[RoleThreshold, ...],
    *,
    exempt_role_ids: frozenset[int] = frozenset(),
    keep_previous_tier: bool = False,
    now: datetime | None = None,
) -> Assignment | None:
    plans = compute_assignments(
        _SingleMemberGuild(guild, member), thresholds,
        exempt_role_ids=exempt_role_ids,
        keep_previous_tier=keep_previous_tier, now=now)
    return plans[0] if plans else None


# --- preflight -----------------------------------------------------------------------

def _bot_has_manage_roles(me: Any) -> bool:
    return bool(getattr(getattr(me, "guild_permissions", None),
                        "manage_roles", False))


def check_preflight(
    guild: Any,
    thresholds: list[RoleThreshold] | tuple[RoleThreshold, ...],
) -> PreflightResult:
    """Permission + hierarchy + missing-role check (id-first resolve)."""
    me = getattr(guild, "me", None)
    if me is None:
        return PreflightResult(
            bot_has_manage_roles=False,
            missing_roles=tuple(t.role_name for t in thresholds))
    bot_has_manage = _bot_has_manage_roles(me)

    missing: list[str] = []
    blockers: list[str] = []
    for t in thresholds:
        role = _resolve_threshold_role(guild, t)
        if role is None:
            missing.append(t.role_name)
            continue
        if evaluate_role(role, bot_member=me).code == ABOVE_BOT:
            blockers.append(t.role_name)
    return PreflightResult(
        bot_has_manage_roles=bot_has_manage,
        hierarchy_blockers=tuple(blockers),
        missing_roles=tuple(missing))


# --- apply ------------------------------------------------------------------------------

def _classify_exception(exc: Exception) -> tuple[str, bool]:
    """(reason_code, is_unexpected) — name-based discord matching (the
    guarded band-2 errors.py pattern; discord is absent in-container)."""
    name = type(exc).__name__
    if name == "Forbidden":
        return FORBIDDEN, False
    if name == "NotFound":
        return NOT_FOUND, False
    if name == "HTTPException" or "HTTPException" in [
            b.__name__ for b in type(exc).__mro__]:
        return HTTP_ERROR, False
    return UNKNOWN, True


def _blocking_verdict(guild: Any, me: Any, plan: Assignment) -> ApplyError | None:
    roles_by_id = {
        r.id: r for r in (getattr(guild, "roles", ()) or ())
        if getattr(r, "id", None)}
    touched: list[Any] = []
    if plan.add_role_id is not None and plan.add_role_id in roles_by_id:
        touched.append(roles_by_id[plan.add_role_id])
    touched.extend(roles_by_id[rid] for rid in plan.remove_role_ids
                   if rid in roles_by_id)
    for role in touched:
        verdict = evaluate_role(role, bot_member=me)
        if not verdict.ok:
            return ApplyError(
                member_id=plan.member_id, phase="preflight",
                code=verdict.code,
                detail=f"role '{verdict.role_name}': {verdict.reason}")
    return None


async def apply(
    guild: Any,
    assignments: tuple[Assignment, ...] | list[Assignment],
    *,
    dry_run: bool = False,
    actor_id: int | None = None,
    actor_type: str = "system",
) -> ApplyResult:
    """Apply assignments via the installed GuildRoleActions port —
    preflight-guarded per touched role, per-member isolation, classified
    failures, one audit fact per successful change (shipped)."""
    if dry_run:
        return ApplyResult(attempted=len(assignments),
                           skipped=len(assignments))

    from sb.domain.role import service

    me = getattr(guild, "me", None)
    guild_id = int(getattr(guild, "id", 0) or 0)

    if me is not None and not _bot_has_manage_roles(me):
        logger.warning(
            "role.automation.apply: skipping %d assignment(s) in guild=%s "
            "— bot lacks the Manage Roles permission.",
            len(assignments), guild_id)
        return ApplyResult(
            attempted=len(assignments), failed=len(assignments),
            failures=tuple(ApplyError(
                member_id=p.member_id, phase="preflight",
                code=BOT_MISSING_MANAGE_ROLES,
                detail="bot lacks Manage Roles") for p in assignments))

    actions = service.active_actions()
    succeeded = failed = 0
    failures: list[ApplyError] = []
    for plan in assignments:
        blocked = _blocking_verdict(guild, me, plan)
        if blocked is not None:
            failed += 1
            failures.append(blocked)
            continue
        try:
            if plan.add_role_id is not None:
                await actions.add_role(guild_id, plan.member_id,
                                       plan.add_role_id, reason=plan.reason)
            for rid in plan.remove_role_ids:
                await actions.remove_role(guild_id, plan.member_id, rid,
                                          reason=plan.reason)
        except Exception as exc:  # noqa: BLE001 — per-member isolation
            code, unexpected = _classify_exception(exc)
            failed += 1
            failures.append(ApplyError(
                member_id=plan.member_id, phase="mutate", code=code,
                detail=str(exc)))
            if unexpected:
                logger.exception(
                    "role.automation.apply: unexpected failure for "
                    "member=%s guild=%s", plan.member_id, guild_id)
            else:
                logger.warning(
                    "role.automation.apply: %s for member=%s guild=%s",
                    code, plan.member_id, guild_id)
            continue
        succeeded += 1
        await service.emit_role_audit(
            guild_id,
            mutation_id=str(uuid.uuid4()),
            mutation_type="role_automation_apply",
            target=f"member:{plan.member_id}",
            new_value=(f"add={plan.add_role_name or ''};"
                       f"remove={','.join(plan.remove_role_names)}"),
            actor_id=actor_id, actor_type=actor_type)
    return ApplyResult(
        attempted=len(assignments), succeeded=succeeded, failed=failed,
        failures=tuple(failures))
