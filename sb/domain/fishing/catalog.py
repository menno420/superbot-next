"""The fishing species catalog + weight roll — ported VERBATIM from the
shipped ``utils/fishing/{fish,weight}.py`` (Q-0175: 21 size-ranked fish,
3 per level × 7 levels; data served from the committed JSON, copied
byte-identical). Weight rolls per catch power the trophy records."""

from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import dataclass

logger = logging.getLogger("sb.domain.fishing.catalog")

__all__ = [
    "Catch",
    "FISH_PER_LEVEL",
    "FishSpecies",
    "MAX_LEVEL",
    "SHORE_VENUE",
    "SPECIES",
    "fish_names",
    "fishing_level_from_xp",
    "max_size_rank_for_level",
    "nominal_weight",
    "roll_weight",
    "species_by_name",
    "unlocked_species",
]

FISH_PER_LEVEL = 3
MAX_LEVEL = 7
SHORE_VENUE = "shore"
DEEPWATER = "deepwater"

_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "data", "fish.json")


@dataclass(frozen=True)
class FishSpecies:
    name: str
    size_rank: int
    emoji: str
    venue: str = SHORE_VENUE


@dataclass(frozen=True)
class Catch:
    species: FishSpecies
    weight: float = 0.0


def _load_species() -> tuple[FishSpecies, ...]:
    try:
        with open(_DATA_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        rows = raw.get("fish", []) if isinstance(raw, dict) else []
        species = [FishSpecies(
            name=str(r["name"]).strip().lower(),
            size_rank=int(r["size_rank"]),
            emoji=str(r.get("emoji", "🐟")),
            venue=str(r.get("venue", SHORE_VENUE)).strip().lower())
            for r in rows
            if isinstance(r, dict) and "name" in r and "size_rank" in r]
        species.sort(key=lambda s: s.size_rank)
        return tuple(species)
    except (OSError, ValueError, KeyError, TypeError):
        logger.exception("fishing: failed to load %s", _DATA_FILE)
        return ()


SPECIES: tuple[FishSpecies, ...] = _load_species()
_BY_NAME: dict[str, FishSpecies] = {s.name: s for s in SPECIES}


def species_by_name(name: str) -> FishSpecies | None:
    return _BY_NAME.get(name.strip().lower())


def fish_names() -> list[str]:
    return [s.name for s in SPECIES]


def species_for_venue(venue: str = SHORE_VENUE) -> list[FishSpecies]:
    key = venue.strip().lower()
    return [s for s in SPECIES if s.venue == key]


def venue_size_cap(venue: str = SHORE_VENUE) -> int:
    pool = species_for_venue(venue)
    return max((s.size_rank for s in pool), default=0)


def max_size_rank_for_level(level: int, venue: str = SHORE_VENUE) -> int:
    band = max(1, level) * FISH_PER_LEVEL
    return min(band, venue_size_cap(venue))


def unlocked_species(level: int,
                     venue: str = SHORE_VENUE) -> list[FishSpecies]:
    cap = max_size_rank_for_level(level, venue)
    return [s for s in species_for_venue(venue) if s.size_rank <= cap]


def fishing_level_from_xp(fishing_xp: int) -> int:
    """1…MAX_LEVEL from the shared game-xp curve (shipped verbatim)."""
    from sb.domain.xp.levels import level_progress

    level_index, _, _ = level_progress(max(0, fishing_xp))
    return min(MAX_LEVEL, 1 + level_index)


# --- per-catch weight (utils/fishing/weight.py verbatim) --------------------------

_BASE = 0.18
_EXP = 1.65
_SPREAD_LO = 0.65
_SPREAD_HI = 1.55


def nominal_weight(species: FishSpecies) -> float:
    return round(_BASE * (species.size_rank ** _EXP), 2)


def roll_weight(species: FishSpecies,
                rng: random.Random | None = None) -> float:
    r = rng or random.Random()
    factor = r.uniform(_SPREAD_LO, _SPREAD_HI)
    return max(0.01, round(nominal_weight(species) * factor, 2))
