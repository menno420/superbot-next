"""BTD6 committed dataset loader (band 7) — the focused port of shipped
``services/btd6_data_service.py`` @7f7628e1 (3,463 lines): the typed
entity accessors the grounding / resolution / reference layers consume
(towers, heroes, bloons, bosses, maps, modes) plus the raw-blob seam
every catalogue pass reads (``read_blob`` / ``list_blob_names``).

The corpus itself is the committed L4 data (``sb/domain/btd6/data/`` —
74 JSON files, copied file-for-file from ``disbot/data/btd6/``). What is
NOT here (named successor ports, D-0046): the Postgres blob backend +
seeding (``btd6_data_blobs``), the rest of the 20-entity validating
parser (rounds/relics/powers/MK/geraldo/income/round-xp typed
accessors — read via ``read_blob`` for now), crosspath cumulative-cost
tables, and the live NK ingestion.

Local-fixture only, lazy, cached; ``reset_cache()`` is the test seam."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA_ROOT = Path(__file__).resolve().parent / "data"

__all__ = [
    "BloonEntry",
    "BossEntry",
    "DATA_ROOT",
    "HeroEntry",
    "MapEntry",
    "ModeEntry",
    "TowerEntry",
    "bloons",
    "bosses",
    "game_version",
    "get_bloon",
    "get_hero",
    "get_map",
    "get_mode",
    "get_tower",
    "heroes",
    "list_blob_names",
    "maps",
    "modes",
    "read_blob",
    "reset_cache",
    "towers",
]


@dataclass(frozen=True)
class TowerEntry:
    id: str
    canonical: str
    aliases: tuple[str, ...] = ()
    category: str = ""
    base_cost: int | None = None
    description: str = ""
    upgrade_paths: dict[str, tuple[str, ...]] = field(default_factory=dict)
    upgrade_costs: dict[str, tuple[int, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class HeroEntry:
    id: str
    canonical: str
    aliases: tuple[str, ...] = ()
    base_cost: int | None = None
    description: str = ""
    abilities: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class BloonEntry:
    id: str
    canonical: str
    aliases: tuple[str, ...] = ()
    category: str = ""
    immune_to: tuple[str, ...] = ()
    properties: tuple[str, ...] = ()
    children: str = ""
    # structured spawn tree ({"bloon_id", "count", "modifiers"} rows) — the
    # freeplay walk's edge list (oracle BloonEntry.children_list, verbatim
    # parse posture: dict rows only).
    children_list: tuple[dict[str, Any], ...] = ()
    health: int | None = None
    health_fortified: int | None = None
    rbe: int | None = None
    rbe_fortified: int | None = None
    speed: float | None = None
    description: str = ""


@dataclass(frozen=True)
class MapEntry:
    """Shipped ``btd6_data_service.MapEntry`` (the fields the resolver /
    response-builder consume; ``wiki_url`` is attribution-only in the
    oracle and never surfaced, so it is not carried)."""

    id: str
    canonical: str
    aliases: tuple[str, ...] = ()
    difficulty: str = ""
    description: str = ""
    lines_of_sight_notes: str = ""
    has_water: bool = False
    # a blank "" means "no data on this map", never "this map has none"
    # (the shipped bloonswiki-curated removables discipline).
    removables: str = ""


@dataclass(frozen=True)
class ModeEntry:
    """Shipped ``btd6_data_service.ModeEntry`` (resolver / response-
    builder fields; the structured ``rules`` block rides the D-0046
    successor with the rest of the validating parser)."""

    id: str
    canonical: str
    aliases: tuple[str, ...] = ()
    kind: str = ""
    description: str = ""
    restrictions: tuple[str, ...] = ()
    # None for modifiers (relative effect, no fixed value) — shipped note.
    starting_cash: int | None = None
    starting_lives: int | None = None


@dataclass(frozen=True)
class BossEntry:
    id: str
    canonical: str
    tagline: str = ""
    description: str = ""
    immune_to: tuple[str, ...] = ()
    tiers: tuple[dict[str, Any], ...] = ()
    elite_tiers: tuple[dict[str, Any], ...] = ()


_lock = threading.Lock()
_blob_cache: dict[str, Any] = {}
_entity_cache: dict[str, tuple] = {}


def reset_cache() -> None:
    """Drop every cached blob/entity table (test seam)."""
    with _lock:
        _blob_cache.clear()
        _entity_cache.clear()


def read_blob(name: str) -> dict[str, Any] | None:
    """Parse + cache a repo-relative ``*.json`` blob (``"towers.json"``,
    ``"stats/paragons/apex_plasma_master.json"``), or None when absent."""
    with _lock:
        if name in _blob_cache:
            return _blob_cache[name]
    path = DATA_ROOT / name
    if not path.is_file():
        data = None
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    with _lock:
        _blob_cache[name] = data
    return data


def list_blob_names(prefix: str = "") -> tuple[str, ...]:
    """Repo-relative ``*.json`` names under ``prefix`` (the glob seam)."""
    names = sorted(
        p.relative_to(DATA_ROOT).as_posix() for p in DATA_ROOT.rglob("*.json")
    )
    return tuple(n for n in names if n.startswith(prefix))


def game_version() -> str:
    """The dataset's game version ("55.1"), for source labels + the
    version-stamped refusal. Never raises."""
    try:
        raw = read_blob("towers.json") or {}
        return str(raw.get("game_version", "") or "unknown")
    except Exception:  # noqa: BLE001 — a label must not break grounding
        return "unknown"


def _aliases(raw: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(a) for a in raw.get("aliases", ()) or ())


def towers() -> tuple[TowerEntry, ...]:
    if "towers" not in _entity_cache:
        raw = read_blob("towers.json") or {}
        out = tuple(
            TowerEntry(
                id=str(t["id"]),
                canonical=str(t.get("canonical", t["id"])),
                aliases=_aliases(t),
                category=str(t.get("category", "") or ""),
                base_cost=t.get("base_cost"),
                description=str(t.get("description", "") or ""),
                upgrade_paths={
                    k: tuple(str(u) for u in v)
                    for k, v in (t.get("upgrade_paths") or {}).items()
                },
                upgrade_costs={
                    k: tuple(int(c) for c in v)
                    for k, v in (t.get("upgrade_costs") or {}).items()
                },
            )
            for t in raw.get("towers", ())
        )
        with _lock:
            _entity_cache["towers"] = out
    return _entity_cache["towers"]


def heroes() -> tuple[HeroEntry, ...]:
    if "heroes" not in _entity_cache:
        raw = read_blob("heroes.json") or {}
        out = tuple(
            HeroEntry(
                id=str(h["id"]),
                canonical=str(h.get("canonical", h["id"])),
                aliases=_aliases(h),
                base_cost=h.get("base_cost"),
                description=str(h.get("description", "") or ""),
                abilities=tuple(h.get("abilities", ()) or ()),
            )
            for h in raw.get("heroes", ())
        )
        with _lock:
            _entity_cache["heroes"] = out
    return _entity_cache["heroes"]


def bloons() -> tuple[BloonEntry, ...]:
    if "bloons" not in _entity_cache:
        raw = read_blob("bloons.json") or {}
        out = tuple(
            BloonEntry(
                id=str(b["id"]),
                canonical=str(b.get("canonical", b["id"])),
                aliases=_aliases(b),
                category=str(b.get("category", "") or ""),
                immune_to=tuple(str(i) for i in b.get("immune_to", ()) or ()),
                properties=tuple(str(p) for p in b.get("properties", ()) or ()),
                children=str(b.get("children", "") or ""),
                children_list=tuple(
                    dict(c)
                    for c in b.get("children_list", ()) or ()
                    if isinstance(c, dict)
                ),
                health=b.get("health"),
                health_fortified=b.get("health_fortified"),
                rbe=b.get("rbe"),
                rbe_fortified=b.get("rbe_fortified"),
                speed=b.get("speed"),
                description=str(b.get("description", "") or ""),
            )
            for b in raw.get("bloons", ())
        )
        with _lock:
            _entity_cache["bloons"] = out
    return _entity_cache["bloons"]


def bosses() -> tuple[BossEntry, ...]:
    if "bosses" not in _entity_cache:
        raw = read_blob("bosses.json") or {}
        out = tuple(
            BossEntry(
                id=str(b["id"]),
                canonical=str(b.get("canonical", b["id"])),
                tagline=str(b.get("tagline", "") or ""),
                description=str(b.get("description", "") or ""),
                immune_to=tuple(str(i) for i in b.get("immune_to", ()) or ()),
                tiers=tuple(b.get("tiers", ()) or ()),
                elite_tiers=tuple(b.get("elite_tiers", ()) or ()),
            )
            for b in raw.get("bosses", ())
        )
        with _lock:
            _entity_cache["bosses"] = out
    return _entity_cache["bosses"]


def maps() -> tuple[MapEntry, ...]:
    if "maps" not in _entity_cache:
        raw = read_blob("maps.json") or {}
        out = tuple(
            MapEntry(
                id=str(m["id"]),
                canonical=str(m.get("canonical", m["id"])),
                aliases=_aliases(m),
                difficulty=str(m.get("difficulty", "") or ""),
                description=str(m.get("description", "") or ""),
                lines_of_sight_notes=str(
                    m.get("lines_of_sight_notes", "") or ""
                ),
                has_water=bool(m.get("has_water", False)),
                removables=str(m.get("removables", "") or ""),
            )
            for m in raw.get("maps", ())
        )
        with _lock:
            _entity_cache["maps"] = out
    return _entity_cache["maps"]


def modes() -> tuple[ModeEntry, ...]:
    if "modes" not in _entity_cache:
        raw = read_blob("modes.json") or {}
        out = tuple(
            ModeEntry(
                id=str(m["id"]),
                canonical=str(m.get("canonical", m["id"])),
                aliases=_aliases(m),
                kind=str(m.get("kind", "") or ""),
                description=str(m.get("description", "") or ""),
                restrictions=tuple(
                    str(r) for r in m.get("restrictions", ()) or ()
                ),
                starting_cash=(
                    int(m["starting_cash"])
                    if m.get("starting_cash") is not None
                    else None
                ),
                starting_lives=(
                    int(m["starting_lives"])
                    if m.get("starting_lives") is not None
                    else None
                ),
            )
            for m in raw.get("modes", ())
        )
        with _lock:
            _entity_cache["modes"] = out
    return _entity_cache["modes"]


def _by_id(entries: tuple, entity_id: str):
    for entry in entries:
        if entry.id == entity_id:
            return entry
    return None


def get_tower(tower_id: str) -> TowerEntry | None:
    return _by_id(towers(), tower_id)


def get_hero(hero_id: str) -> HeroEntry | None:
    return _by_id(heroes(), hero_id)


def get_bloon(bloon_id: str) -> BloonEntry | None:
    return _by_id(bloons(), bloon_id)


def get_map(map_id: str) -> MapEntry | None:
    """Shipped ``map_fact`` is exactly this lookup (knowledge_service
    delegates to ``get_map``)."""
    return _by_id(maps(), map_id)


def get_mode(mode_id: str) -> ModeEntry | None:
    """Shipped ``mode_fact`` is exactly this lookup."""
    return _by_id(modes(), mode_id)
