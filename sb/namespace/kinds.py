"""Kinds, surfaces, origins, and the scope key (frozen L0 spec 03 §3.1).

Stdlib-only leaf. The scope key: every reservation is keyed by
`(kind, normalize(value), scope)` where `scope = CommandScope(surface,
parent_group)` for kind=command and `None` (global) for every other kind.
The collision rule (one rule, all kinds): two reservations collide iff same
kind AND same normalize(value) AND same scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NamespaceKind(str, Enum):
    """The 16 kinds frozen at design-spec §3.1, verbatim."""

    COMMAND = "command"
    CUSTOM_ID = "custom_id"
    EVENT = "event"
    SETTING_KEY = "setting_key"
    SUBSYSTEM_KEY = "subsystem_key"
    CAPABILITY = "capability"
    PANEL = "panel"
    HANDLER_REF = "handler_ref"
    TASK_PREFIX = "task_prefix"
    STAT_KEY = "stat_key"
    ITEM_KEY = "item_key"
    AI_TASK = "ai_task"
    CONTEXT_ID = "context_id"
    ACTOR_TYPE = "actor_type"
    INVARIANT_TAG = "invariant_tag"
    TABLE = "table"


class Surface(str, Enum):
    """CommandSpec.kind="both" expands to ONE reservation per surface."""

    PREFIX = "prefix"
    SLASH = "slash"


class Origin(str, Enum):
    MANIFEST = "manifest"    # derived from a live SubsystemManifest spec
    LEGACY = "legacy"        # frozen compat core (legacy_reservations.json), compat=True
    TOMBSTONE = "tombstone"  # retired/renamed; never claimable; may carry renamed_to
    BAN = "ban"              # permanent deny, no successor


@dataclass(frozen=True)
class CommandScope:
    """Only the COMMAND kind has a 2-D scope; every other kind is global."""

    surface: Surface
    parent_group: str | None = None  # dotted group PATH, <=2 segments (1-nest)


def normalize(value: str, kind: NamespaceKind) -> str:
    """Commands are case-insensitive (Discord); every other kind byte-exact."""
    return value.casefold() if kind is NamespaceKind.COMMAND else value


def namespace_id(value: str, scope: CommandScope | None) -> str:
    """The deterministic identity/sort key — a TOTAL order under str sort.

    Derivable from the six harvested corpus fields alone (spec 03 §3.5).
    """
    if scope is None:
        return f"//{value}"  # non-command kinds (global)
    return f"{scope.surface.value}/{scope.parent_group or ''}/{value}"
