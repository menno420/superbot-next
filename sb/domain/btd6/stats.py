"""BTD6 stats-file access (band 7) — the focused port of shipped
``services/btd6_stats_service.py`` @7f7628e1: the paragon stats path
(resolution + degree headline) and the per-tower paragon identity/cost
lines the grounding layer consumes.

What is NOT here (named successor ports, D-0046): the full tower/hero
normal-view derivation (per-tier headline stats over the cleaned nodes),
minion/sub-tower indexes, and the upgrade-detail resolver
(``btd6_upgrade_detail_service``)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from sb.domain.btd6 import dataset, paragon_degrees, paragon_math
from sb.kernel.ai.grounding.format import is_infinite

__all__ = [
    "ParagonStats",
    "get_paragon_stats",
    "get_paragon_stats_by_tower",
    "get_tower_paragon_line",
    "list_paragon_ids",
    "paragon_main_bits",
    "reset_stats_cache",
    "resolve_paragon_id",
]

_PARAGON_PREFIX = "stats/paragons/"
_JSON_SUFFIX = ".json"

_lock = threading.Lock()
_PARAGON_CACHE: dict[str, "ParagonStats | None"] = {}
_PARAGON_BY_TOWER: dict[str, str] | None = None


@dataclass(frozen=True)
class ParagonStats:
    """Degree-independent base node for one paragon (shipped shape,
    focused: the description/abilities catalogue join is a successor)."""

    paragon_id: str
    tower_id: str
    canonical: str
    tower_canonical: str
    game_version: str
    cost: int | None
    cost_chimps: int | None
    xp: int | None
    base: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    @property
    def has_combat_stats(self) -> bool:
        return bool(self.base.get("attacks") or self.base.get("abilities"))

    @property
    def is_prose_sourced(self) -> bool:
        return "prose" in self.source.lower()


def reset_stats_cache() -> None:
    """Test seam: drop the loaded-stats caches."""
    global _PARAGON_BY_TOWER
    with _lock:
        _PARAGON_CACHE.clear()
        _PARAGON_BY_TOWER = None


def _load_paragon(paragon_id: str) -> ParagonStats | None:
    data = dataset.read_blob(f"{_PARAGON_PREFIX}{paragon_id}{_JSON_SUFFIX}")
    if data is None:
        return None
    return ParagonStats(
        paragon_id=str(data.get("paragon_id", paragon_id)),
        tower_id=str(data.get("tower_id", "")),
        canonical=str(data.get("canonical", "")),
        tower_canonical=str(data.get("tower_canonical", "")),
        game_version=str(data.get("game_version", "")),
        cost=data.get("cost"),
        cost_chimps=data.get("cost_chimps"),
        xp=data.get("xp"),
        base=data.get("base", {}) or {},
        source=str(data.get("source", "")),
    )


def get_paragon_stats(paragon_id: str) -> ParagonStats | None:
    """Return a paragon's stats by paragon id, or None."""
    if paragon_id not in _PARAGON_CACHE:
        loaded = _load_paragon(paragon_id)
        with _lock:
            _PARAGON_CACHE[paragon_id] = loaded
    return _PARAGON_CACHE[paragon_id]


def list_paragon_ids() -> tuple[str, ...]:
    """All paragon ids with a stats blob (sorted)."""
    names = dataset.list_blob_names(_PARAGON_PREFIX)
    return tuple(
        sorted(
            name[len(_PARAGON_PREFIX) : -len(_JSON_SUFFIX)]
            for name in names
            if name.endswith(_JSON_SUFFIX)
        ),
    )


def _paragon_index() -> dict[str, str]:
    """``tower_id -> paragon_id`` for every paragon with a stats file."""
    global _PARAGON_BY_TOWER
    if _PARAGON_BY_TOWER is None:
        index: dict[str, str] = {}
        for paragon_id in list_paragon_ids():
            stats = get_paragon_stats(paragon_id)
            if stats is not None and stats.tower_id:
                index[stats.tower_id] = paragon_id
        with _lock:
            _PARAGON_BY_TOWER = index
    return _PARAGON_BY_TOWER


def get_paragon_stats_by_tower(tower_id: str) -> ParagonStats | None:
    """The tower's tier-6 paragon stats, or None."""
    paragon_id = _paragon_index().get(tower_id)
    return get_paragon_stats(paragon_id) if paragon_id else None


def get_tower_paragon_line(tower_id: str) -> tuple[str, int | None] | None:
    """``(paragon_name, medium_cost)`` from the tower's stats file, or
    None when the tower has no paragon (shipped ``_render_paragon``
    source: ``stats/<tower_id>.json`` paragon_name/paragon_cost)."""
    data = dataset.read_blob(f"stats/{tower_id}{_JSON_SUFFIX}")
    if not isinstance(data, dict):
        return None
    cost = data.get("paragon_cost")
    if not cost:
        return None
    name = str(data.get("paragon_name", "") or "")
    return (name, cost)


def resolve_paragon_id(query: str) -> str | None:
    """Resolve free-form ``query`` (a paragon name, its tower, or the
    colloquial shorthand) to a paragon id (shipped order: canonical-in-
    text → tower resolution → exact-key shorthand)."""
    text = (query or "").lower()
    if not text.strip():
        return None
    for paragon_id in list_paragon_ids():
        pstats = get_paragon_stats(paragon_id)
        if pstats and pstats.canonical and pstats.canonical.lower() in text:
            return paragon_id
    from sb.domain.btd6 import resolver

    intent = resolver.resolve(query)
    for tower in intent.towers:
        paragon_id = _paragon_index().get(tower.id)
        if paragon_id:
            return paragon_id
    resolved = paragon_math.resolve_paragon(query)
    return resolved.paragon_id if resolved is not None else None


def _big(value: float) -> str:
    """Render BTD6's 9,999,999 'infinite' sentinel as ∞ (shipped)."""
    return "∞" if is_infinite(value) else str(value)


def paragon_main_bits(base: dict[str, Any], degree: int) -> list[str]:
    """Headline bits for a paragon's PRIMARY attack at ``degree`` —
    shipped ``_paragon_main_bits`` verbatim (first attack, highest-damage
    projectile, wiki degree formulas, immunity note folded in)."""
    attacks = base.get("attacks") or []
    if not attacks:
        return []
    attack = attacks[0]
    projectiles = attack.get("projectiles") or []
    main = max(projectiles, key=lambda p: p.get("damage") or 0, default=None)

    bits: list[str] = []
    if main is not None:
        damage = main.get("damage")
        if isinstance(damage, (int, float)) and damage > 0:
            dmg = f"{_big(round(paragon_degrees.scale_damage(damage, degree)))} dmg"
            dtype = main.get("damage_type")
            if dtype:
                note = (
                    "pops everything" if dtype == "Normal" else main.get("cannot_pop")
                )
                dmg += f" ({dtype}{f', {note}' if note else ''})"
            bits.append(dmg)
        pierce = main.get("pierce")
        if (
            isinstance(pierce, (int, float))
            and pierce < paragon_degrees.PIERCE_SENTINEL
            and (main.get("maxPierce") or 0) < 1
        ):
            bits.append(
                f"{_big(round(paragon_degrees.scale_pierce(pierce, degree)))} pierce",
            )
    rate = attack.get("rate")
    if isinstance(rate, (int, float)) and rate < paragon_degrees.RATE_SENTINEL:
        cd = paragon_degrees.format_value(paragon_degrees.scale_cooldown(rate, degree))
        bits.append(f"{cd}s cooldown")
    return bits
