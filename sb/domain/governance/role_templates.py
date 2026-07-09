"""Role template + collection declarations (band 5) —
governance/role_templates.py verbatim (Phase 1d declarations; the
matcher/provisioner rides the roles slice). Color values match
``discord.Color.*().value`` so the live adapter converts without lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sb.domain.governance.tiers import PermissionTier

__all__ = [
    "ADMIN_TEMPLATE",
    "ADMINISTRATION_ROLES",
    "HELPER_TEMPLATE",
    "MODERATION_ROLES",
    "MODERATOR_TEMPLATE",
    "RoleCollection",
    "RoleColor",
    "RoleTemplate",
    "TRUSTED_TEMPLATE",
    "TRUSTED_USER_TIERS",
    "all_collections",
    "all_templates",
    "get_collection",
    "get_template",
    "register_collection",
    "register_template",
    "reset_role_templates_for_tests",
]


class RoleColor(Enum):
    RED = 0xE74C3C
    ORANGE = 0xE67E22
    YELLOW = 0xF1C40F
    GREEN = 0x2ECC71
    BLUE = 0x3498DB
    PURPLE = 0x9B59B6
    GREY = 0x95A5A6
    WHITE = 0xFFFFFF


@dataclass(frozen=True)
class RoleTemplate:
    """A recommended Discord role declaration (matcher normalizes names)."""

    name: str
    permission_tier: PermissionTier
    description: str
    color: RoleColor = RoleColor.GREY
    mentionable: bool = False
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleCollection:
    """A named bundle of RoleTemplates (setup packs apply collections)."""

    name: str
    description: str
    templates: tuple[RoleTemplate, ...] = ()


MODERATOR_TEMPLATE = RoleTemplate(
    name="Moderator", permission_tier=PermissionTier.MODERATOR,
    description=("Standard moderation role.  Holders may issue warns, "
                 "timeouts, and kicks; minimum tier for governance writes."),
    color=RoleColor.RED, mentionable=True,
    permissions=("manage_messages", "kick_members", "moderate_members",
                 "view_audit_log"))

HELPER_TEMPLATE = RoleTemplate(
    name="Helper", permission_tier=PermissionTier.STAFF,
    description=("Lightweight staff role for trusted helpers who assist "
                 "with user questions but do not perform moderation."),
    color=RoleColor.GREEN, mentionable=False, permissions=())

ADMIN_TEMPLATE = RoleTemplate(
    name="Administrator", permission_tier=PermissionTier.ADMINISTRATOR,
    description=("Server administration role.  Holders may configure "
                 "subsystems, governance overrides, and channel setup."),
    color=RoleColor.PURPLE, mentionable=True, permissions=("administrator",))

TRUSTED_TEMPLATE = RoleTemplate(
    name="Trusted", permission_tier=PermissionTier.TRUSTED,
    description=("Modest-trust role bound to the ``TRUSTED_TIER_ROLE_ID`` "
                 "setting.  Holders see surfaces hidden from the general "
                 "user tier."),
    color=RoleColor.BLUE, mentionable=False, permissions=())

MODERATION_ROLES = RoleCollection(
    name="moderation_essentials",
    description="Recommended roles for a moderation-bearing guild.",
    templates=(MODERATOR_TEMPLATE, HELPER_TEMPLATE))

ADMINISTRATION_ROLES = RoleCollection(
    name="administration_essentials",
    description="Recommended roles for guild administration.",
    templates=(ADMIN_TEMPLATE,))

TRUSTED_USER_TIERS = RoleCollection(
    name="trusted_user_tiers",
    description="Recommended Trusted-tier role for elevated user access.",
    templates=(TRUSTED_TEMPLATE,))


_TEMPLATE_REGISTRY: dict[str, RoleTemplate] = {}
_COLLECTION_REGISTRY: dict[str, RoleCollection] = {}


def register_template(template: RoleTemplate) -> None:
    """Re-registration allowed (hot-reload-friendly, shipped)."""
    _TEMPLATE_REGISTRY[template.name] = template


def register_collection(collection: RoleCollection) -> None:
    _COLLECTION_REGISTRY[collection.name] = collection
    for tpl in collection.templates:
        register_template(tpl)


def get_template(name: str) -> RoleTemplate | None:
    return _TEMPLATE_REGISTRY.get(name)


def get_collection(name: str) -> RoleCollection | None:
    return _COLLECTION_REGISTRY.get(name)


def all_templates() -> dict[str, RoleTemplate]:
    return dict(_TEMPLATE_REGISTRY)


def all_collections() -> dict[str, RoleCollection]:
    return dict(_COLLECTION_REGISTRY)


def _register_builtins() -> None:
    register_collection(MODERATION_ROLES)
    register_collection(ADMINISTRATION_ROLES)
    register_collection(TRUSTED_USER_TIERS)


def reset_role_templates_for_tests() -> None:
    _TEMPLATE_REGISTRY.clear()
    _COLLECTION_REGISTRY.clear()
    _register_builtins()


_register_builtins()
