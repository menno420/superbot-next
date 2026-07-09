"""Metadata-only guild snapshot (band 5) — services/guild_snapshot.py
compiled: view-only channel/category/role metadata + the closed field
set with the documented privacy exclusions (EXCLUDED_FIELD_TOKENS is
test-pinned; a widening is a deliberate edit).

Compiled adaptations (D-0041): settings/bindings snapshots read the K7
declaration registry (the shipped subsystem_schema's compiled home);
role manageability delegates to sb.domain.role.feasibility (the shared
(position,id) tiebreak); readiness findings ride an installable
inspector port (the shipped resource_health service is setup-band work).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from typing import Any, Awaitable, Callable

logger = logging.getLogger("sb.domain.platform.guild_snapshot")

__all__ = [
    "EXCLUDED_FIELD_TOKENS",
    "CategoryMeta",
    "ChannelMeta",
    "GuildSnapshot",
    "RoleMeta",
    "collect",
    "documented_field_names",
    "install_readiness_inspector",
    "reset_snapshot_ports_for_tests",
]


@dataclass(frozen=True)
class ChannelMeta:
    id: int
    name: str
    type: str
    topic: str | None
    parent_category: str | None
    position: int
    bot_can_view: bool
    bot_can_send: bool
    bot_can_embed: bool


@dataclass(frozen=True)
class CategoryMeta:
    id: int
    name: str
    position: int
    bot_can_manage: bool


@dataclass(frozen=True)
class RoleMeta:
    id: int
    name: str
    position: int
    bot_can_manage: bool


@dataclass(frozen=True)
class GuildSnapshot:
    """Metadata-only snapshot — the field set is CLOSED (shipped)."""

    guild_id: int
    guild_name: str
    owner_id: int
    channels: tuple[ChannelMeta, ...] = ()
    categories: tuple[CategoryMeta, ...] = ()
    roles: tuple[RoleMeta, ...] = ()
    settings_snapshot: dict[str, Any] = field(default_factory=dict)
    bindings_snapshot: dict[str, Any] = field(default_factory=dict)
    readiness_findings: tuple = ()


EXCLUDED_FIELD_TOKENS: frozenset[str] = frozenset({
    "message_content", "messages", "members", "member_count", "member_list",
    "invites", "permission_overwrites", "overwrites_matrix",
    "raw_permissions",
})

# installable readiness inspector: async (guild) -> tuple of findings
_readiness_inspector: Callable[[Any], Awaitable[tuple]] | None = None


def install_readiness_inspector(inspector) -> None:
    global _readiness_inspector
    _readiness_inspector = inspector


def reset_snapshot_ports_for_tests() -> None:
    global _readiness_inspector
    _readiness_inspector = None


async def collect(guild: Any) -> GuildSnapshot:
    """Pure read; a failing readiness inspection is swallowed (shipped)."""
    me = getattr(guild, "me", None)
    findings: tuple = ()
    if _readiness_inspector is not None:
        try:
            findings = tuple(await _readiness_inspector(guild))
        except Exception:  # noqa: BLE001 — shipped swallow
            logger.exception(
                "guild_snapshot.collect: readiness inspector failed for "
                "guild=%s; continuing with empty findings.",
                getattr(guild, "id", "?"))
    return GuildSnapshot(
        guild_id=int(getattr(guild, "id", 0) or 0),
        guild_name=str(getattr(guild, "name", "") or ""),
        owner_id=int(getattr(guild, "owner_id", 0) or 0),
        channels=_collect_channels(guild, me),
        categories=_collect_categories(guild, me),
        roles=_collect_roles(guild, me),
        settings_snapshot=_collect_settings_snapshot(),
        bindings_snapshot=_collect_bindings_snapshot(),
        readiness_findings=findings,
    )


def _perms(obj: Any, me: Any):
    perms_for = getattr(obj, "permissions_for", None)
    if me is None or perms_for is None:
        return None
    try:
        return perms_for(me)
    except Exception:  # noqa: BLE001 — defensive per-channel
        return None


def _collect_channels(guild: Any, me: Any) -> tuple[ChannelMeta, ...]:
    out: list[ChannelMeta] = []

    def _add(channels, kind_label):
        for ch in channels:
            perms = _perms(ch, me)
            parent = getattr(ch, "category", None)
            out.append(ChannelMeta(
                id=int(getattr(ch, "id", 0) or 0),
                name=str(getattr(ch, "name", "") or ""),
                type=kind_label,
                topic=getattr(ch, "topic", None),
                parent_category=(getattr(parent, "name", None)
                                 if parent is not None else None),
                position=int(getattr(ch, "position", 0) or 0),
                bot_can_view=bool(getattr(perms, "view_channel", False)),
                bot_can_send=bool(getattr(perms, "send_messages", False)),
                bot_can_embed=bool(getattr(perms, "embed_links", False))))

    _add(list(getattr(guild, "text_channels", ()) or ()), "text")
    _add(list(getattr(guild, "voice_channels", ()) or ()), "voice")
    _add(list(getattr(guild, "stage_channels", ()) or ()), "stage")
    return tuple(out)


def _collect_categories(guild: Any, me: Any) -> tuple[CategoryMeta, ...]:
    out: list[CategoryMeta] = []
    for cat in getattr(guild, "categories", ()) or ():
        perms = _perms(cat, me)
        out.append(CategoryMeta(
            id=int(getattr(cat, "id", 0) or 0),
            name=str(getattr(cat, "name", "") or ""),
            position=int(getattr(cat, "position", 0) or 0),
            bot_can_manage=bool(getattr(perms, "manage_channels", False))))
    return tuple(out)


def _collect_roles(guild: Any, me: Any) -> tuple[RoleMeta, ...]:
    from sb.domain.role.feasibility import evaluate_role

    out: list[RoleMeta] = []
    for role in getattr(guild, "roles", ()) or ():
        manageable = bool(me is not None
                          and evaluate_role(role, bot_member=me).ok)
        out.append(RoleMeta(
            id=int(getattr(role, "id", 0) or 0),
            name=str(getattr(role, "name", "") or ""),
            position=int(getattr(role, "position", 0) or 0),
            bot_can_manage=manageable))
    return tuple(out)


def _collect_settings_snapshot() -> dict[str, Any]:
    """Flat {subsystem.name: default} over THE K7 declaration registry
    (defaults only — per-guild values stay out, shipped privacy rule)."""
    try:
        from sb.kernel.settings import iter_declarations

        return {d.key: d.default for d in iter_declarations()}
    except Exception:  # noqa: BLE001
        logger.exception("guild_snapshot: declaration registry unavailable")
        return {}


def _collect_bindings_snapshot() -> dict[str, Any]:
    """Flat {subsystem.name: {kind, required, hint}} over the manifest
    BindingSpec facets (names + kinds only; never targets)."""
    try:
        import importlib
        import pkgutil

        import sb.manifest as manifest_pkg

        out: dict[str, Any] = {}
        for info in pkgutil.iter_modules(manifest_pkg.__path__):
            mod = importlib.import_module(f"sb.manifest.{info.name}")
            manifest = getattr(mod, "MANIFEST", None)
            if manifest is None:
                continue
            for spec in getattr(manifest, "settings", ()) or ():
                kind = getattr(getattr(spec, "kind", None), "value", None)
                if kind is None:
                    continue   # scalar SettingSpec — bindings only
                out[f"{manifest.key}.{spec.name}"] = {
                    "kind": kind,
                    "required": bool(getattr(spec, "required", False)),
                    "hint": getattr(spec, "hint", ""),
                }
        return out
    except Exception:  # noqa: BLE001
        logger.exception("guild_snapshot: binding facet walk failed")
        return {}


def documented_field_names() -> tuple[str, ...]:
    return tuple(f.name for f in fields(GuildSnapshot))
