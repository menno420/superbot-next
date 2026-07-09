"""Typed permission tier metadata (band 5) — governance/permission_tiers.py
verbatim. The string values match sb.spec.authority.TIERS (the runtime
comparisons stay on the string order there); this module carries the RICH
metadata (descriptions, inheritance, recommended roles) for wizard /
role-provisioning surfaces plus the reserved PLATFORM_OWNER member.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "PermissionTier",
    "PermissionTierMeta",
    "all_tiers_ordered",
    "metadata_for",
    "tier_at_or_above",
    "tier_index",
]


class PermissionTier(Enum):
    USER = "user"
    TRUSTED = "trusted"
    STAFF = "staff"
    MODERATOR = "moderator"
    ADMINISTRATOR = "administrator"
    OWNER = "owner"
    PLATFORM_OWNER = "platform_owner"


_TIER_ORDER: tuple[PermissionTier, ...] = (
    PermissionTier.USER,
    PermissionTier.TRUSTED,
    PermissionTier.STAFF,
    PermissionTier.MODERATOR,
    PermissionTier.ADMINISTRATOR,
    PermissionTier.OWNER,
    PermissionTier.PLATFORM_OWNER,
)


@dataclass(frozen=True)
class PermissionTierMeta:
    tier: PermissionTier
    tier_index: int
    description: str
    inherits_from: PermissionTier | None
    recommended_role_names: tuple[str, ...]


_TIER_METADATA: dict[PermissionTier, PermissionTierMeta] = {
    PermissionTier.USER: PermissionTierMeta(
        tier=PermissionTier.USER, tier_index=0,
        description="Any guild member.  No elevated permissions.",
        inherits_from=None, recommended_role_names=()),
    PermissionTier.TRUSTED: PermissionTierMeta(
        tier=PermissionTier.TRUSTED, tier_index=1,
        description=("Members the guild has chosen to extend modest trust to "
                     "(e.g. veterans, donors).  Bound via the "
                     "``TRUSTED_TIER_ROLE_ID`` setting."),
        inherits_from=PermissionTier.USER,
        recommended_role_names=("Trusted", "Veteran", "Member+")),
    PermissionTier.STAFF: PermissionTierMeta(
        tier=PermissionTier.STAFF, tier_index=2,
        description=("Non-moderation staff with elevated access to "
                     "subsystem-specific surfaces (e.g. event organizers)."),
        inherits_from=PermissionTier.TRUSTED,
        recommended_role_names=("Staff", "Organizer", "Helper")),
    PermissionTier.MODERATOR: PermissionTierMeta(
        tier=PermissionTier.MODERATOR, tier_index=3,
        description=("Members authorized to enforce community rules — warns, "
                     "timeouts, kicks.  Minimum tier for governance writes."),
        inherits_from=PermissionTier.STAFF,
        recommended_role_names=("Moderator", "Mod")),
    PermissionTier.ADMINISTRATOR: PermissionTierMeta(
        tier=PermissionTier.ADMINISTRATOR, tier_index=4,
        description=("Server administrators — full configuration authority, "
                     "including subsystem visibility and cleanup policy."),
        inherits_from=PermissionTier.MODERATOR,
        recommended_role_names=("Administrator", "Admin")),
    PermissionTier.OWNER: PermissionTierMeta(
        tier=PermissionTier.OWNER, tier_index=5,
        description=("Discord guild owner.  Resolved via "
                     ":data:`guild.owner_id`; no role mapping needed."),
        inherits_from=PermissionTier.ADMINISTRATOR,
        recommended_role_names=()),
    PermissionTier.PLATFORM_OWNER: PermissionTierMeta(
        tier=PermissionTier.PLATFORM_OWNER, tier_index=6,
        description=("Reserved for platform-level operations: feature flag "
                     "mutation, environment-tier assignment, cross-guild "
                     "template publishing.  Not discoverable via Discord "
                     "permissions; declared at deploy time."),
        inherits_from=PermissionTier.OWNER,
        recommended_role_names=()),
}


def metadata_for(tier: PermissionTier) -> PermissionTierMeta:
    return _TIER_METADATA[tier]


def tier_index(tier: PermissionTier | str) -> int:
    if isinstance(tier, str):
        try:
            tier = PermissionTier(tier)
        except ValueError:
            valid = ", ".join(t.value for t in PermissionTier)
            raise ValueError(
                f"unknown permission tier {tier!r}; valid: {valid}") from None
    return _TIER_METADATA[tier].tier_index


def tier_at_or_above(holder: PermissionTier | str,
                     required: PermissionTier | str) -> bool:
    return tier_index(holder) >= tier_index(required)


def all_tiers_ordered() -> tuple[PermissionTier, ...]:
    return _TIER_ORDER
