"""Role service (band 5) — the installable Discord-mutation port
(GuildRoleActions, the band-2 GuildModerationActions pattern), the audit
fact emitter, the exemption/stacking read model
(role_exemption_service.py), the reaction-role runtime core
(reaction_role_service.py fast paths, headless), temp-grant listing +
the expiry sweep (role_grants_service.py), and THE BAND-4 WAITING-PORT
FILL: install_xp_ports() installs the real level-role granter
(xp_role_sync planner + thresholds + exemptions + the actions port) into
sb.domain.xp.service.install_level_role_granter.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from sb.domain.role import store
from sb.domain.role.automation import apply as apply_assignments  # noqa: F401 (re-export)

logger = logging.getLogger("sb.domain.role")

__all__ = [
    "ExemptRoleIds",
    "GuildRoleActions",
    "active_actions",
    "emit_role_audit",
    "get_exempt_role_ids",
    "grant_temp_role",
    "handle_reaction_add",
    "handle_reaction_remove",
    "install_guild_source",
    "install_role_actions",
    "install_xp_ports",
    "list_active_grants",
    "reaction_roles_enabled",
    "reset_role_ports_for_tests",
    "subscribe",
    "sweep_expired",
    "time_roles_stack",
    "xp_roles_stack",
]


# --- the Discord-mutation port -----------------------------------------------------

class GuildRoleActions(Protocol):
    """Adapter-implemented Discord role mutations (RC-21 sibling; the
    egress fence owns bare verbs — *_role method names)."""

    async def add_role(self, guild_id: int, member_id: int, role_id: int,
                       *, reason: str) -> None: ...
    async def remove_role(self, guild_id: int, member_id: int, role_id: int,
                          *, reason: str) -> None: ...


class _NoActions:
    async def _refuse(self, *_a, **_k) -> None:
        raise RuntimeError(
            "GuildRoleActions not installed — the composition root must "
            "install the discord adapter's implementation "
            "(sb.domain.role.service.install_role_actions)")

    add_role = remove_role = _refuse


_actions: GuildRoleActions = _NoActions()  # fail-loud default

# guild view port: guild_id -> a duck guild (roles/members/me) or None.
# The live adapter installs the gateway-cache read; headless default None
# keeps every automation surface honestly blocked (never fakes a grant).
_guild_source = None

_bus = None  # in-process bus for audit facts (subscribe pattern)


def install_role_actions(actions: GuildRoleActions) -> None:
    global _actions
    _actions = actions


def active_actions() -> GuildRoleActions:
    return _actions


def install_guild_source(source) -> None:
    """source: async (guild_id) -> duck guild | None (live adapter)."""
    global _guild_source
    _guild_source = source


async def guild_view(guild_id: int):
    if _guild_source is None:
        return None
    return await _guild_source(guild_id)


def subscribe(bus) -> None:
    """Composition-root/harness obligation (the band-2 fan-out roster):
    gives this module the bus its audit facts ride."""
    global _bus
    _bus = bus


async def emit_role_audit(guild_id: int, *, mutation_id: str,
                          mutation_type: str, target: str,
                          new_value: str | None, actor_id: int | None,
                          actor_type: str) -> None:
    """audit.action_recorded fact for a role mutation performed OUTSIDE a
    K7 lane (the shipped emit_audit_action twin — best-effort in-process
    emit; K7-lane role ops get their audit row from the engine)."""
    if _bus is None:
        return
    try:
        await _bus.emit("audit.action_recorded", **{
            "mutation_id": mutation_id, "subsystem": "role",
            "mutation_type": mutation_type, "target": target,
            "scope": "guild", "guild_id": guild_id, "prev_value": None,
            "new_value": new_value, "actor_id": actor_id,
            "actor_type": actor_type,
            "occurred_at": datetime.now(tz=timezone.utc).isoformat()})
    except Exception:  # noqa: BLE001 — audit fact is best-effort (shipped)
        logger.warning("role: audit fact emit failed", exc_info=True)


def reset_role_ports_for_tests() -> None:
    global _actions, _guild_source, _bus
    _actions = _NoActions()
    _guild_source = None
    _bus = None


# --- exemptions + stacking (role_exemption_service.py) --------------------------------

@dataclass(frozen=True)
class ExemptRoleIds:
    xp: frozenset[int]
    time: frozenset[int]


async def get_exempt_role_ids(guild_id: int) -> ExemptRoleIds:
    rows = await store.get_exemptions(guild_id)
    return ExemptRoleIds(
        xp=frozenset(int(r["role_id"]) for r in rows if r["exempt_xp"]),
        time=frozenset(int(r["role_id"]) for r in rows if r["exempt_time"]))


async def _bool_setting(guild_id: int, name: str, default: bool) -> bool:
    try:
        from sb.kernel.settings import resolve

        value = await resolve(guild_id, "role", name)
    except Exception:  # noqa: BLE001 — undeclared/unreadable = default
        return default
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


async def time_roles_stack(guild_id: int) -> bool:
    """Tenure roles keep the previous tier (shipped default False)."""
    return await _bool_setting(guild_id, "time_roles_stack", False)


async def xp_roles_stack(guild_id: int) -> bool:
    """XP/level roles keep lower tiers (shipped default True)."""
    return await _bool_setting(guild_id, "xp_roles_stack", True)


async def reaction_roles_enabled(guild_id: int) -> bool:
    return await _bool_setting(guild_id, "reaction_roles_enabled", True)


# --- reaction-role runtime core (headless fast paths) -----------------------------------

async def handle_reaction_add(guild_id: int, message_id: int, emoji: str,
                              member_id: int, *,
                              member_role_ids: frozenset[int] = frozenset(),
                              is_bot: bool = False) -> str | None:
    """The on_raw_reaction_add core: enabled gate -> binding lookup ->
    message mode -> role add through the port. Returns the action taken
    ('added' | 'unique_swap' | None) — silent on every block (shipped).

    ``verify`` mode acks membership without granting on ADD (the shipped
    verify flow grants on reaction REMOVE — the "click to verify" pattern
    stays adapter-sequenced); it returns None here.
    """
    if is_bot or not await reaction_roles_enabled(guild_id):
        return None
    role_id = await store.get_reaction_binding(guild_id, message_id, emoji)
    if role_id is None:
        return None
    mode = await store.get_message_mode(guild_id, message_id)
    if mode == "verify":
        return None
    if mode == "unique":
        siblings = await store.sibling_reaction_bindings(guild_id, message_id)
        held = [int(s["role_id"]) for s in siblings
                if int(s["role_id"]) in member_role_ids
                and int(s["role_id"]) != role_id]
        for rid in held:
            await _actions.remove_role(guild_id, member_id, rid,
                                       reason="Reaction role (unique mode)")
        await _actions.add_role(guild_id, member_id, role_id,
                                reason="Reaction role")
        return "unique_swap" if held else "added"
    await _actions.add_role(guild_id, member_id, role_id,
                            reason="Reaction role")
    return "added"


async def handle_reaction_remove(guild_id: int, message_id: int, emoji: str,
                                 member_id: int) -> str | None:
    """The on_raw_reaction_remove core: normal mode removes the bound
    role; verify mode GRANTS it (shipped verify semantics)."""
    if not await reaction_roles_enabled(guild_id):
        return None
    role_id = await store.get_reaction_binding(guild_id, message_id, emoji)
    if role_id is None:
        return None
    mode = await store.get_message_mode(guild_id, message_id)
    if mode == "verify":
        await _actions.add_role(guild_id, member_id, role_id,
                                reason="Reaction role (verified)")
        return "verified"
    await _actions.remove_role(guild_id, member_id, role_id,
                               reason="Reaction role removed")
    return "removed"


# --- temp grants (role_grants_service.py) ------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


async def grant_temp_role(ctx, *, member_id: int, role_id: int,
                          seconds: int) -> datetime:
    """Discord add + audited persisted grant via the K7 lane. Returns the
    expiry. Caller verified manageability; a late Forbidden propagates."""
    from sb.domain.role.ops import GRANT_TEMP_ROLE
    from sb.kernel.workflow import engine

    expires_at = _utcnow() + timedelta(seconds=seconds)
    ctx.params.update({"member_id": member_id, "role_id": role_id,
                       "expires_at_iso": expires_at.isoformat()})
    result = await engine.run(GRANT_TEMP_ROLE, ctx)
    if getattr(result, "outcome", None) != "success":
        raise RuntimeError(f"temp-role grant failed: {result!r}")
    return expires_at


async def list_active_grants(guild_id: int,
                             member_id: int) -> list[tuple[int, datetime]]:
    """Still-active grants as (role_id, expires_at), soonest first —
    lapsed-but-unswept rows dropped (shipped). Role-existence filtering is
    the presenter's job headlessly (no gateway cache here — deviation)."""
    now = _utcnow()
    rows = await store.list_grants_for_member(guild_id, member_id)
    return [(int(r["role_id"]), r["expires_at"]) for r in rows
            if r["expires_at"] > now]


async def sweep_expired(now: datetime | None = None) -> int:
    """The expiry sweep fire (role:grants_expiry ManagedTaskSpec body):
    remove the lapsed role via the port, then drop the row through the
    audited K7 expire lane. A hierarchy-blocked removal KEEPS the grant
    to retry (shipped); a vanished member/role cleans up with no
    mutation attempt only when the actions port reports NotFound."""
    from sb.domain.role.ops import EXPIRE_TEMP_ROLE
    from sb.kernel.scheduler.due_queue import SYSTEM_ACTOR
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext

    now = now or _utcnow()
    expired = await store.list_expired_grants(now)
    resolved = 0
    for row in expired:
        gid, mid, rid = (int(row["guild_id"]), int(row["member_id"]),
                         int(row["role_id"]))
        try:
            await _actions.remove_role(gid, mid, rid,
                                       reason="Temporary role expired")
            removed = True
        except Exception as exc:  # noqa: BLE001 — classify by name (guarded)
            name = type(exc).__name__
            if name == "Forbidden":
                logger.warning(
                    "role_grants: cannot remove expired role %s from "
                    "member %s in guild %s (hierarchy); keeping to retry",
                    rid, mid, gid)
                continue
            if name == "NotFound":
                removed = False   # member/role gone — clean the row
            elif name == "RuntimeError":
                # actions port not installed — honest wait, keep every row
                logger.warning("role_grants: actions port not installed; "
                               "sweep deferred")
                return resolved
            else:
                continue
        ctx = WorkflowContext(
            actor=SYSTEM_ACTOR, guild_id=gid, request_id=f"grantexp:{row['grant_id']}",
            confirmed=True,
            params={"grant_id": int(row["grant_id"]), "member_id": mid,
                    "role_id": rid, "did_remove": removed},
            clock=lambda: _utcnow())
        await engine.run(EXPIRE_TEMP_ROLE, ctx)
        resolved += 1
    return resolved


# --- THE BAND-4 WAITING-PORT FILL ----------------------------------------------------------

async def _level_role_granter(guild_id: int, user_id: int,
                              new_level: int) -> None:
    """The real xp.service.install_level_role_granter body: xp-threshold
    rows (level_required / xp_auto_assign) + stack flag + exemptions ->
    the ONE planner -> apply through the actions port. Without a live
    guild view (install_guild_source) it records nothing and never fakes
    a grant (the honest-wait contract, D-0040)."""
    from sb.domain.role.automation import apply as _apply
    from sb.domain.role.xp_sync import plan_level_role_assignments

    guild = await guild_view(guild_id)
    if guild is None:
        logger.debug("role: level-role grant skipped — no guild view "
                     "installed (guild=%s user=%s level=%s)",
                     guild_id, user_id, new_level)
        return
    member = None
    for m in getattr(guild, "members", ()) or ():
        if getattr(m, "id", None) == user_id:
            member = m
            break
    if member is None:
        return
    rows = await store.get_thresholds(guild_id)
    xp_roles = [
        {"role_name": r["role_name"], "role_id": r["role_id"],
         "level_required": int(r["level_required"])}
        for r in rows
        if r.get("xp_auto_assign") and r.get("level_required") is not None
    ]
    xp_roles.sort(key=lambda r: r["level_required"])
    if not xp_roles:
        return
    exempt = await get_exempt_role_ids(guild_id)
    stack = await xp_roles_stack(guild_id)
    plans = plan_level_role_assignments(
        guild, member, new_level, stack=stack, exempt_xp_ids=exempt.xp,
        xp_roles=xp_roles, reason=f"Reached level {new_level}")
    if plans:
        await _apply(guild, tuple(plans), actor_type="system")


def install_xp_ports() -> None:
    """Fill sb.domain.xp.service.install_level_role_granter with the real
    planner-backed granter (the D-0031/D-0036 waiting port; called at
    manifest import, idempotent)."""
    from sb.domain.xp.service import install_level_role_granter

    install_level_role_granter(_level_role_granter)
