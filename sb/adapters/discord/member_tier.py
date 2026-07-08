"""`member_tier_from_member` — the ONE discord-aware tier read (frozen L0
spec 04 §2, ported verbatim from `utils/visibility_rules.py:44`).

Called by each surface adapter when it builds `ActorRef.member_tier`
(RC-12); the kernel never dereferences a Member. Duck-typed (reads
`member.id` / `member.guild_permissions.*`), so no discord import is needed
and the INTERACTION_CREATE payload's resolved member works too (spec 14 —
no privileged intent required).
"""

from __future__ import annotations

__all__ = ["member_tier_from_member", "role_ids_from_member"]


def member_tier_from_member(member: object, guild_owner_id: int) -> str:
    """The highest tier this member qualifies for (shipped verbatim:
    owner -> administrator -> moderator(moderate_members) ->
    staff(manage_guild) -> user)."""
    if getattr(member, "id", None) == guild_owner_id:
        return "owner"
    p = getattr(member, "guild_permissions", None)
    if p is None:
        return "user"
    if getattr(p, "administrator", False):
        return "administrator"
    if getattr(p, "moderate_members", False):
        return "moderator"
    if getattr(p, "manage_guild", False):
        return "staff"
    return "user"


def role_ids_from_member(member: object) -> frozenset[int]:
    """The A-12/R-16 role-id set, derived FRESH per interaction (the
    interaction-time re-check is structural)."""
    roles = getattr(member, "roles", None) or ()
    out = set()
    for role in roles:
        role_id = getattr(role, "id", None)
        if isinstance(role_id, int):
            out.add(role_id)
    return frozenset(out)
