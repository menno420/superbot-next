"""Role feasibility (band 5) — utils/role_feasibility.py headless: the
ONE source of truth for "can the bot manage this role?" shared by the
preflight, the apply-time guard, and selector surfaces (they must never
drift). Duck-typed over any role/member shape carrying id/name/position/
managed/guild_permissions/top_role.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ABOVE_ACTOR",
    "ABOVE_BOT",
    "BOT_MISSING_MANAGE_ROLES",
    "EVERYONE",
    "MANAGED",
    "SELECTABLE",
    "RoleFeasibility",
    "evaluate_role",
]

SELECTABLE = "selectable"
EVERYONE = "everyone"
MANAGED = "managed"
BOT_MISSING_MANAGE_ROLES = "bot_missing_manage_roles"
ABOVE_BOT = "above_bot"
ABOVE_ACTOR = "above_actor"

_REASONS: dict[str, str] = {
    EVERYONE: "the @everyone role cannot be assigned",
    MANAGED: "integration-managed role (bot/booster) cannot be assigned",
    BOT_MISSING_MANAGE_ROLES: "the bot lacks the Manage Roles permission",
    ABOVE_BOT: "role is at or above the bot's top role",
    ABOVE_ACTOR: "role is at or above your top role",
}


@dataclass(frozen=True)
class RoleFeasibility:
    role_id: int
    role_name: str
    ok: bool
    code: str
    reason: str


def _is_default(role: object) -> bool:
    """@everyone: role.id == guild.id (Discord invariant); honours an
    explicit is_default() when the object offers one."""
    probe = getattr(role, "is_default", None)
    if callable(probe):
        try:
            return bool(probe())
        except Exception:  # noqa: BLE001 — fall through to the id compare
            pass
    guild = getattr(role, "guild", None)
    return (guild is not None
            and getattr(role, "id", None) == getattr(guild, "id", object()))


def _has_manage_roles(member: object) -> bool:
    return bool(getattr(getattr(member, "guild_permissions", None),
                        "manage_roles", False))


def _at_or_above(role: object, top: object) -> bool:
    """Discord's (position, id) tiebreak — raw position>= mis-flags roles
    that merely tie the bot's position (shipped comment, verbatim rule)."""
    rp = int(getattr(role, "position", 0) or 0)
    tp = int(getattr(top, "position", 0) or 0)
    if rp != tp:
        return rp > tp
    return int(getattr(role, "id", 0) or 0) >= int(getattr(top, "id", 0) or 0)


def evaluate_role(role: object, *, bot_member: object | None = None,
                  actor: object | None = None) -> RoleFeasibility:
    """First blocking reason in precedence order: @everyone → managed →
    bot permission → bot hierarchy → actor hierarchy."""
    rid = int(getattr(role, "id", 0) or 0)
    name = str(getattr(role, "name", "") or "")

    def _verdict(code: str) -> RoleFeasibility:
        ok = code == SELECTABLE
        return RoleFeasibility(rid, name, ok, code,
                               "" if ok else _REASONS.get(code, code))

    if _is_default(role):
        return _verdict(EVERYONE)
    if bool(getattr(role, "managed", False)):
        return _verdict(MANAGED)
    if bot_member is not None:
        if not _has_manage_roles(bot_member):
            return _verdict(BOT_MISSING_MANAGE_ROLES)
        bot_top = getattr(bot_member, "top_role", None)
        if bot_top is not None and _at_or_above(role, bot_top):
            return _verdict(ABOVE_BOT)
    if actor is not None:
        actor_top = getattr(actor, "top_role", None)
        if actor_top is not None and _at_or_above(role, actor_top):
            return _verdict(ABOVE_ACTOR)
    return _verdict(SELECTABLE)
