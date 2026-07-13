"""Fishing venues — shore vs the boat's deepwater (band 6, D-0043 slice 1).

The shipped ``utils/fishing/venue.py`` ported (oracle menno420/superbot;
owner design Q-0175 §5): a player picks *where* they fish, and the venue
choice changes both **what** bites (a separate species pool — deepwater
holds boat-only fish uncatchable from shore) and **how hard** it is to
land (the deep bites slower and fights harder).

The design's load-bearing finding, carried verbatim: deepwater is **an
optimization, not a gate**. A starter rod *can* fish the deep — it is
just worse reward/min there — so deepwater is tuned tougher (a much
higher base escape + longer bites), **not** hard-locked behind a level
or a rod.

Pure + stdlib-only (no Discord, no DB). The shipped module sourced the
shore numbers from ``utils/fishing/minigame.py``'s constants; this repo
has no minigame module yet (the live reel-timing layer rides the D-0043
rod/bait/minigame rung), so those shore constants are inlined here as
the profile's data — values verbatim (REACTION_WINDOW 2.5,
BITE_DELAY 3.0/6.0 floor 1.5, SHORE_ESCAPE_CHANCE 0.06)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEEPWATER",
    "DEEPWATER_PROFILE",
    "SHORE",
    "SHORE_PROFILE",
    "VenueProfile",
    "normalize",
    "profile_for",
    "toggle",
]

#: The two venue keys (also the stored ``fishing_venue.venue`` values).
SHORE = "shore"
DEEPWATER = "deepwater"


@dataclass(frozen=True)
class VenueProfile:
    """One fishing venue — its identity + the minigame numbers it runs at."""

    key: str
    name: str
    emoji: str
    #: The species ``venue`` tag whose pool is catchable here.
    species_venue: str
    #: Bite-wait band (seconds), randomised per cast; ``floor`` is the hard min.
    bite_delay_min: float
    bite_delay_max: float
    bite_delay_floor: float
    #: Base reaction window (seconds) before the rod ``window_bonus`` is added.
    reaction_window: float
    #: Per-tap base escape chance in the reel-fight (before rod ``escape_resist``).
    base_escape: float
    #: One-line flavour for the cast / menu embeds.
    blurb: str


#: Shore — the relaxing default (the shipped/tuned shore minigame constants,
#: inlined — see module docstring).
SHORE_PROFILE = VenueProfile(
    key=SHORE,
    name="Shore",
    emoji="🏖️",
    species_venue=SHORE,
    bite_delay_min=3.0,
    bite_delay_max=6.0,
    bite_delay_floor=1.5,
    reaction_window=2.5,
    base_escape=0.06,
    blurb="Relaxed casting from the shoreline.",
)

#: Deepwater — the boat venue (sim §5): slower, bigger bites that fight free far
#: more often, so a good rod's escape-resist is what makes the trip pay off.
DEEPWATER_PROFILE = VenueProfile(
    key=DEEPWATER,
    name="Deepwater",
    emoji="⛵",
    species_venue=DEEPWATER,
    bite_delay_min=6.0,
    bite_delay_max=12.0,
    bite_delay_floor=3.0,
    reaction_window=2.0,
    base_escape=0.22,
    blurb="Out on the boat — rare deep-sea fish that fight to break free.",
)

_PROFILES: dict[str, VenueProfile] = {
    SHORE: SHORE_PROFILE,
    DEEPWATER: DEEPWATER_PROFILE,
}


def normalize(venue: str | None) -> str:
    """Coerce a stored / user value to a known venue key (unknown → shore)."""
    if venue is None:
        return SHORE
    key = venue.strip().lower()
    return key if key in _PROFILES else SHORE


def profile_for(venue: str | None) -> VenueProfile:
    """The :class:`VenueProfile` for *venue* (unknown / ``None`` → shore)."""
    return _PROFILES[normalize(venue)]


def toggle(venue: str | None) -> str:
    """The *other* venue key — shore ↔ deepwater (the Set sail / Dock action)."""
    return DEEPWATER if normalize(venue) == SHORE else SHORE
