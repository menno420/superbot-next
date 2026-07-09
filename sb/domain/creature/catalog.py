"""The creature catalog + wild-encounter math — ported VERBATIM from the
shipped ``utils/creatures/{creature,encounters}.py`` (creature-game v1,
Q-0187). 36 original creatures served from the committed JSON (copied
byte-identical from ``disbot/data/creatures/creatures.json`` — a data
row, not code). Battle stats deliberately NOT modelled (v1 = catch +
collection; the PvP engine is a later substantial-runtime slice)."""

from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import dataclass

logger = logging.getLogger("sb.domain.creature.catalog")

__all__ = [
    "CREATURES",
    "Creature",
    "Encounter",
    "RARITY_ORDER",
    "attempt_catch",
    "catch_chance",
    "creature_by_name",
    "creature_names",
    "roll_encounter",
]

RARITY_ORDER: tuple[str, ...] = ("Common", "Uncommon", "Rare", "Epic")

RARITY_ENCOUNTER_WEIGHT: dict[str, float] = {
    "Common": 100.0, "Uncommon": 45.0, "Rare": 18.0, "Epic": 6.0,
}

RARITY_CATCH_BASE: dict[str, float] = {
    "Common": 0.90, "Uncommon": 0.65, "Rare": 0.40, "Epic": 0.20,
}

_FALLBACK_EMOJI = "🐾"
_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "data", "creatures.json")

CATCH_BONUS_PER_LEVEL = 0.02
MAX_CATCH_BONUS = 0.20
MAX_CATCH_CHANCE = 0.95


@dataclass(frozen=True)
class Creature:
    name: str
    element: str
    rarity: str
    archetype: str
    emoji: str

    @property
    def encounter_weight(self) -> float:
        return RARITY_ENCOUNTER_WEIGHT.get(self.rarity, 1.0)

    @property
    def catch_base(self) -> float:
        return RARITY_CATCH_BASE.get(self.rarity, 0.5)


def _load_creatures() -> tuple[Creature, ...]:
    try:
        with open(_DATA_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return ()
        element_emoji = raw.get("element_emoji", {})
        creatures = []
        for r in raw.get("creatures", []):
            if not isinstance(r, dict) or not {"name", "element",
                                               "rarity"} <= r.keys():
                continue
            element = str(r["element"]).strip()
            creatures.append(Creature(
                name=str(r["name"]).strip(), element=element,
                rarity=str(r["rarity"]).strip(),
                archetype=str(r.get("archetype", "balanced")).strip(),
                emoji=str(element_emoji.get(element, _FALLBACK_EMOJI))))
        rarity_index = {r: i for i, r in enumerate(RARITY_ORDER)}
        creatures.sort(key=lambda c: (rarity_index.get(c.rarity,
                                                       len(RARITY_ORDER)),
                                      c.name))
        return tuple(creatures)
    except (OSError, ValueError, KeyError, TypeError):
        logger.exception("creatures: failed to load %s", _DATA_FILE)
        return ()


CREATURES: tuple[Creature, ...] = _load_creatures()
_BY_NAME: dict[str, Creature] = {c.name.lower(): c for c in CREATURES}


def creature_by_name(name: str) -> Creature | None:
    return _BY_NAME.get(name.strip().lower())


def creature_names() -> list[str]:
    return [c.name for c in CREATURES]


@dataclass(frozen=True)
class Encounter:
    creature: Creature


def roll_encounter(rng: random.Random | None = None) -> Encounter | None:
    if not CREATURES:
        return None
    r = rng or random.Random()
    weights = [c.encounter_weight for c in CREATURES]
    return Encounter(creature=r.choices(CREATURES, weights=weights,
                                        k=1)[0])


def catch_chance(creature: Creature, level: int) -> float:
    bonus = min(MAX_CATCH_BONUS, max(0, level) * CATCH_BONUS_PER_LEVEL)
    return min(MAX_CATCH_CHANCE, creature.catch_base + bonus)


def attempt_catch(creature: Creature, level: int,
                  rng: random.Random | None = None) -> bool:
    r = rng or random.Random()
    return r.random() < catch_chance(creature, level)
