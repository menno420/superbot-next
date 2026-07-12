"""BTD6 paragon catalogue + power thresholds — the focused port of shipped
``utils/btd6/paragon_math.py`` @7f7628e1 (the pieces the grounding layer
consumes: the 13-paragon catalogue with medium base prices, the colloquial
shorthand resolver, the degree power-threshold cubic). The full paragon
power calculator / reverse solver (sacrifice math, co-op splits) is a
NAMED SUCCESSOR PORT riding the deep-BTD6-tools lane (D-0046).

Pure, stdlib-only."""

from __future__ import annotations

from dataclasses import dataclass

MAX_DEGREE = 100
TOTAL_POWER_FOR_MAX_DEGREE = 200_000

# Extra-T5 sacrifice caps (shipped ``utils/btd6/paragon_math.py`` @7f7628e1
# verbatim): only the Dart paragon may sacrifice one extra T5 in solo; co-op
# splits the reserve across the team (up to 9). The calculator landing panel's
# extra-T5 selector reads these to bound its options.
SOLO_DART_MAX_EXTRA_T5 = 1
COOP_MAX_EXTRA_T5 = 9

_DART_PARAGON_ID = "apex_plasma_master"


@dataclass(frozen=True)
class Paragon:
    """A BTD6 paragon and its medium-difficulty adjusted base price."""

    paragon_id: str
    name: str
    tower: str
    base_price_medium: int

    @property
    def is_dart(self) -> bool:
        return self.paragon_id == _DART_PARAGON_ID


# base_price_medium values captured once from the live Paragon Calculator API
# and committed so the local fallback stays deterministic (shipped verbatim).
PARAGONS: tuple[Paragon, ...] = (
    Paragon("apex_plasma_master", "Apex Plasma Master", "Dart Monkey", 150_000),
    Paragon("glaive_dominus", "Glaive Dominus", "Boomerang Monkey", 375_000),
    Paragon("ascended_shadow", "Ascended Shadow", "Ninja Monkey", 500_000),
    Paragon("navarch_of_the_seas", "Navarch of the Seas", "Monkey Buccaneer", 500_000),
    Paragon("nautic_siege_core", "Nautic Siege Core", "Monkey Sub", 400_000),
    Paragon("master_builder", "Master Builder", "Engineer Monkey", 650_000),
    Paragon("magus_perfectus", "Magus Perfectus", "Wizard Monkey", 800_000),
    Paragon("goliath_doomship", "Goliath Doomship", "Monkey Ace", 900_000),
    Paragon(
        "crucible_of_steel_and_flame",
        "Crucible of Steel and Flame",
        "Tack Shooter",
        200_000,
    ),
    Paragon(
        "mega_massive_munitions_factory",
        "Mega Massive Munitions Factory",
        "Spike Factory",
        750_000,
    ),
    Paragon(
        "ballistic_obliteration_missile_bunker",
        "Ballistic Obliteration Missile Bunker (B.O.M.B.)",
        "Bomb Shooter",
        600_000,
    ),
    Paragon("herald_of_everfrost", "Herald of Everfrost", "Ice Monkey", 300_000),
    Paragon("root_of_all_nature", "Root of all Nature", "Druid", 475_000),
)

BASE_PRICES_MEDIUM: dict[str, int] = {
    p.paragon_id: p.base_price_medium for p in PARAGONS
}

_BY_ID: dict[str, Paragon] = {p.paragon_id: p for p in PARAGONS}

# Player-facing shorthand -> paragon id (shipped verbatim). Tower names,
# paragon names, and ids are matched automatically; this adds the extras.
_ALIASES: dict[str, str] = {
    "dart": "apex_plasma_master",
    "apex": "apex_plasma_master",
    "apex plasma": "apex_plasma_master",
    "boomer": "glaive_dominus",
    "boomerang": "glaive_dominus",
    "glaive": "glaive_dominus",
    "ninja": "ascended_shadow",
    "shadow": "ascended_shadow",
    "ascended": "ascended_shadow",
    "bucc": "navarch_of_the_seas",
    "buccaneer": "navarch_of_the_seas",
    "boat": "navarch_of_the_seas",
    "navarch": "navarch_of_the_seas",
    "sub": "nautic_siege_core",
    "submarine": "nautic_siege_core",
    "nautic": "nautic_siege_core",
    "nautic siege": "nautic_siege_core",
    "engi": "master_builder",
    "engineer": "master_builder",
    "builder": "master_builder",
    "wizard": "magus_perfectus",
    "magus": "magus_perfectus",
    "ace": "goliath_doomship",
    "goliath": "goliath_doomship",
    "doomship": "goliath_doomship",
    "tack": "crucible_of_steel_and_flame",
    "crucible": "crucible_of_steel_and_flame",
    "spact": "mega_massive_munitions_factory",
    "spike": "mega_massive_munitions_factory",
    "spike factory": "mega_massive_munitions_factory",
    "mmmf": "mega_massive_munitions_factory",
    "munitions": "mega_massive_munitions_factory",
    "bomb": "ballistic_obliteration_missile_bunker",
    "b.o.m.b.": "ballistic_obliteration_missile_bunker",
    "bomb shooter": "ballistic_obliteration_missile_bunker",
    "ice": "herald_of_everfrost",
    "herald": "herald_of_everfrost",
    "everfrost": "herald_of_everfrost",
    "druid": "root_of_all_nature",
    "root": "root_of_all_nature",
    "nature": "root_of_all_nature",
}


def resolve_paragon(text: str) -> Paragon | None:
    """Resolve a tower name, paragon name, paragon id, or shorthand alias.

    Case-insensitive; tolerates a trailing " paragon" ("dart paragon").
    Exact-key only (shipped), so a long sentence can't false-positive."""
    key = " ".join(text.strip().lower().split())
    if not key:
        return None
    if key.endswith(" paragon"):
        key = key[: -len(" paragon")].strip()
    if key in _BY_ID:
        return _BY_ID[key]
    for paragon in PARAGONS:
        if key in (paragon.name.lower(), paragon.tower.lower(), paragon.paragon_id):
            return paragon
    alias = _ALIASES.get(key)
    return _BY_ID[alias] if alias else None


def threshold(degree: int) -> int:
    """Minimum total power required to reach ``degree`` (1..100)."""
    if degree >= MAX_DEGREE:
        return TOTAL_POWER_FOR_MAX_DEGREE
    if degree <= 1:
        return (50 + 5025 + 168324 + 843000) // 600  # threshold(1) == 1693
    return (50 * degree**3 + 5025 * degree**2 + 168324 * degree + 843000) // 600


def game_mode_for(player_count: int) -> str:
    """``"solo"`` for 1 player, ``"coop"`` for 2-4 (shipped verbatim)."""
    return "solo" if player_count <= 1 else "coop"


def max_extra_t5_count(game_mode: str, *, is_dart: bool) -> int:
    """Max extra T5 sacrifices: solo Dart 1, solo other 0, co-op 9
    (shipped verbatim)."""
    if game_mode == "coop":
        return COOP_MAX_EXTRA_T5
    return SOLO_DART_MAX_EXTRA_T5 if is_dart else 0


__all__ = [
    "BASE_PRICES_MEDIUM",
    "COOP_MAX_EXTRA_T5",
    "MAX_DEGREE",
    "PARAGONS",
    "Paragon",
    "SOLO_DART_MAX_EXTRA_T5",
    "TOTAL_POWER_FOR_MAX_DEGREE",
    "game_mode_for",
    "max_extra_t5_count",
    "resolve_paragon",
    "threshold",
]
