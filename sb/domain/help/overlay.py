"""Guild Help-overlay read model — the D-0026 named-successor
presentation-deviation store (ORACLE disbot/services/help_overlay.py +
utils/db/help_overlay.py @HEAD, migration 064 → 0051; the Q-0059
home-message half of oracle 067 rides the home-builder successor).

The cached, fault-tolerant read side of the guild Help overlay: which
hubs (categories) / subsystems this guild display-hides, renames, or
re-describes **in Help only**. Overlay rows can only affect presentation
— never execution (Q-0055 / HLP-4): nothing in any admission path reads
this store.

* Reads are cached per guild; :func:`invalidate_help_overlay_cache` is
  called by the audited mutation lanes (:mod:`sb.domain.help.overlay_ops`)
  after every write.
* A DB fault degrades to the **empty overlay** (registry defaults
  render) and is logged — Help must never crash on the overlay path.
* Orphan rows (keys the catalogue no longer knows) are **preserved and
  reported**, never dropped here: the editor home surfaces them.

THE COMPILED CATALOGUE: the oracle validated entity keys against
``services/help_catalogue``; the compiled analog is the category map +
the live manifest inventory (sb/domain/help/categories.py +
service.command_inventory — the same sources the help projection renders
from), exposed here as :func:`known_entities` / :func:`entity_defaults`.

Cycle discipline (the shipped module's rule): cross-package imports are
function-local; top-level imports are stdlib + the K3 store spec only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sb.spec.refs import EngineRef, engine, is_registered
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

logger = logging.getLogger("sb.domain.help.overlay")

__all__ = [
    "EMPTY_OVERLAY",
    "HELP_OVERLAY_STORE",
    "MAX_DESCRIPTION_LEN",
    "MAX_DISPLAY_NAME_LEN",
    "VALID_ENTITY_KINDS",
    "GuildHelpOverlay",
    "HelpOverlayRow",
    "entity_defaults",
    "get_guild_help_overlay",
    "invalidate_help_overlay_cache",
    "known_entities",
    "reset_overlay_cache_for_tests",
]

VALID_ENTITY_KINDS: frozenset[str] = frozenset({"hub", "subsystem"})

# Bounds mirror the tightest Discord surface rendering these fields
# (select option label/description = 100 chars); the DB CHECKs are the
# backstop (oracle bytes verbatim).
MAX_DISPLAY_NAME_LEN = 100
MAX_DESCRIPTION_LEN = 100

HELP_OVERLAY_STORE = register_store(StoreSpec(
    table="help_overlay",
    sole_writer=EngineRef("help.overlay_store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="help_overlay",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("interaction", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,
))


def _store_marker() -> str:
    return "sb/domain/help/overlay_ops.py"


if not is_registered(EngineRef("help.overlay_store")):
    engine("help.overlay_store")(_store_marker)


@dataclass(frozen=True)
class HelpOverlayRow:
    """One entity's presentation deviations (``None`` field = inherit)."""

    entity_kind: str  # 'hub' | 'subsystem'
    entity_key: str
    display_hidden: bool | None = None
    display_name: str | None = None
    description: str | None = None

    @property
    def is_noop(self) -> bool:
        """``True`` when every override field inherits (row should not
        exist — the store keeps only deviations)."""
        return (
            self.display_hidden is None
            and self.display_name is None
            and self.description is None
        )


@dataclass(frozen=True)
class GuildHelpOverlay:
    """All of one guild's Help presentation deviations (possibly empty)."""

    guild_id: int | None
    rows: tuple[HelpOverlayRow, ...] = field(default=())

    def get(self, entity_kind: str, entity_key: str) -> HelpOverlayRow | None:
        return next(
            (r for r in self.rows
             if r.entity_kind == entity_kind and r.entity_key == entity_key),
            None,
        )

    def hidden(self, entity_kind: str, entity_key: str) -> bool:
        row = self.get(entity_kind, entity_key)
        return bool(row.display_hidden) if row is not None else False

    def display_name_for(self, entity_kind: str, entity_key: str,
                         default: str) -> str:
        row = self.get(entity_kind, entity_key)
        if row is not None and row.display_name is not None:
            return row.display_name
        return default

    @property
    def is_empty(self) -> bool:
        return not self.rows


EMPTY_OVERLAY = GuildHelpOverlay(guild_id=None)

# ---------------------------------------------------------------------------
# The compiled catalogue analog (categories + live inventory)
# ---------------------------------------------------------------------------


def known_entities(entity_kind: str) -> tuple[str, ...]:
    """Every current key of one kind — the write-time validation roster.

    hubs = the shipped mother-hub categories (incl. the OTHER honesty
    valve — it renders as a live category panel when non-empty);
    subsystems = the live manifest inventory (minus ``help`` itself,
    which never surfaces under any hub — the shipped rule).
    """
    from sb.domain.help import categories as cats
    from sb.domain.help.service import command_inventory

    if entity_kind == "hub":
        return tuple(cat.key for cat in (*cats.CATEGORIES,
                                         cats.OTHER_CATEGORY))
    return tuple(k for k in command_inventory() if k != "help")


def entity_defaults(entity_kind: str, entity_key: str) -> tuple[str, str]:
    """``(default_display_name, default_description)`` for one entity —
    the Q-0058 admin-view defaults (custom + default + stable key)."""
    from sb.domain.help import categories as cats

    if entity_kind == "hub":
        cat = cats.category_by_key(entity_key)
        if cat is None:
            return entity_key, ""
        return cat.display_name, cat.purpose
    display, _emoji = cats.subsystem_display(entity_key)
    return display, ""


# ---------------------------------------------------------------------------
# Cached read (oracle semantics verbatim)
# ---------------------------------------------------------------------------

_cache: dict[int, GuildHelpOverlay] = {}


async def get_guild_help_overlay(guild_id: int | None) -> GuildHelpOverlay:
    """The guild's overlay (cached; empty for DMs / faults / no rows)."""
    if guild_id is None:
        return EMPTY_OVERLAY
    cached = _cache.get(guild_id)
    if cached is not None:
        return cached
    from sb.kernel.db.pool import fetchall

    try:
        raw = await fetchall(
            "SELECT entity_kind, entity_key, display_hidden, display_name, "
            "description FROM help_overlay WHERE guild_id=$1 "
            "ORDER BY entity_kind, entity_key", (int(guild_id),))
    except Exception as exc:  # noqa: BLE001 — Help must render without it
        logger.warning(
            "help_overlay: read failed for guild %s — rendering defaults: "
            "%s", guild_id, exc)
        return GuildHelpOverlay(guild_id=guild_id)
    overlay = GuildHelpOverlay(
        guild_id=guild_id,
        rows=tuple(
            HelpOverlayRow(
                entity_kind=str(r["entity_kind"]),
                entity_key=str(r["entity_key"]),
                display_hidden=r["display_hidden"],
                display_name=r["display_name"],
                description=r["description"],
            )
            for r in raw
        ),
    )
    _cache[guild_id] = overlay
    return overlay


def invalidate_help_overlay_cache(guild_id: int | None = None) -> None:
    """Drop the cached overlay for ``guild_id`` (or all, when ``None``)."""
    if guild_id is None:
        _cache.clear()
    else:
        _cache.pop(int(guild_id), None)


def reset_overlay_cache_for_tests() -> None:
    _cache.clear()
