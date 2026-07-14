"""Fishing minigame — pure tuning + resolve logic (band 6, D-0043).

The shipped ``utils/fishing/minigame.py`` ported verbatim (oracle
menno420/superbot @ cdb26804; owner design Q-0175): the interactive
``cast → wait → BITE → reel`` loop's tuned numbers and pure resolve
functions. The oracle's load-bearing finding, carried: a reaction
window over Discord is a **presence check, not a reflex test** — the
bot can only measure the whole round trip ``L_down + reaction + L_up``
against the window, so sub-second windows are unwinnable on a normal
connection; hence the generous ~2.5 s window.

CONSUMED IN FULL (D-0043 minigame-timing rung, slices 1+2 —
service.py cast_open/fish_route): :func:`is_trophy` (the result
card's "🏆 Trophy landed!" title + the trophy/fight branch),
:func:`roll_bite_delay` (at cast time, consuming the compounded
effective_bite_speed at the venue's band), :func:`roll_fakeout` (the
pre-bite nibble edit, armed under the oracle lead-fit guard
``delay − FAKEOUT_LEAD > BITE_DELAY_FLOOR``; reeling on it resolves
premature), :func:`roll_premature_grace` (the one forgiven early reel
per cast), :func:`reel_is_in_time` (slice 2 — the late-window /
fight-round-window enforcement on SYSTEM_CLOCK timestamps),
:func:`escape_clue` (the got-away/snap/too-slow terminals),
:func:`reel_fight_taps` + :func:`roll_escape` /
:func:`fight_escape_chance` (the trophy reel-fight, whose rounds open
on :data:`FIGHT_INTER_ROUND_DELAY`). The live cues ride the D-0090
kernel one-shot timer + push-edit seam; enforcement never does.

Pure + stdlib-only (no Discord, no DB, no clock)."""

from __future__ import annotations

import random

from sb.domain.fishing import catalog

__all__ = [
    "BITE_DELAY_FLOOR",
    "BITE_DELAY_MAX",
    "BITE_DELAY_MIN",
    "FAKEOUT_CHANCE",
    "FAKEOUT_LEAD",
    "FIGHT_INTER_ROUND_DELAY",
    "FIGHT_MAX_TAPS",
    "FIGHT_MIN_TAPS",
    "FIGHT_WINDOW",
    "REACTION_WINDOW",
    "SHORE_ESCAPE_CHANCE",
    "TROPHY_BAND_FRACTION",
    "escape_clue",
    "fight_escape_chance",
    "is_trophy",
    "reel_fight_taps",
    "reel_is_in_time",
    "roll_bite_delay",
    "roll_escape",
    "roll_fakeout",
    "roll_premature_grace",
]

# --- tuning (shipped verbatim — utils/fishing/minigame.py) -------------------

#: Shore reaction window, seconds. The window flattens unfair
#: latency-losses to near-zero around 2–2.5 s (sim §2).
REACTION_WINDOW = 2.5

#: Bite wait is randomised in this band so it never feels scripted
#: (sim §3: 3–6 s is "anticipation without boredom").
BITE_DELAY_MIN = 3.0
BITE_DELAY_MAX = 6.0

#: A hard floor so a bite is *never* instant — the floor is the anticipation.
BITE_DELAY_FLOOR = 1.5

#: Chance a cast gets a fake-out: a tiny shake shortly before the real
#: bite. Reeling on the fake-out scares the fish (a premature miss).
#: ``FAKEOUT_LEAD`` is the lead time before the real bite.
FAKEOUT_CHANCE = 0.45
FAKEOUT_LEAD = 0.6

#: A catch is a "trophy" when it sits in the top third of the player's
#: currently unlocked size band — the payoff fish that trigger the
#: reel-fight.
TROPHY_BAND_FRACTION = 1.0 / 3.0

#: Reel-fight (trophy) tuning — a short sequence of timed reel taps, each
#: its own presence-check window (kept at the *full* generous window).
FIGHT_WINDOW = REACTION_WINDOW
FIGHT_INTER_ROUND_DELAY = 0.8  # a suspense beat between reel taps
FIGHT_MIN_TAPS = 2
FIGHT_MAX_TAPS = 4
SHORE_ESCAPE_CHANCE = 0.06  # per-tap snap-free chance on shore (no rod yet)


def roll_bite_delay(
    rng: random.Random | None = None,
    *,
    speed: float = 1.0,
    lo: float = BITE_DELAY_MIN,
    hi: float = BITE_DELAY_MAX,
    floor: float = BITE_DELAY_FLOOR,
) -> float:
    """Seconds to wait before the bite — uniform in the band, never below
    floor (shipped verbatim).

    ``speed`` (the rod ``bite_speed`` knob, ≤ 1 = faster) scales the
    random draw before the floor is applied; ``lo``/``hi``/``floor``
    default to the shore band but the deepwater venue passes its own
    slower band (:mod:`sb.domain.fishing.venue`)."""
    r = rng or random.Random()
    return max(floor, r.uniform(lo, hi) * speed)


def roll_fakeout(rng: random.Random | None = None) -> bool:
    """Whether this cast gets a pre-bite fake-out shake (shipped verbatim)."""
    r = rng or random.Random()
    return r.random() < FAKEOUT_CHANCE


def roll_premature_grace(
    grace: float,
    rng: random.Random | None = None,
) -> bool:
    """Whether a *premature* reel is forgiven instead of spooking the fish
    (shipped verbatim — the rod's ``premature_grace`` knob, 0…1, spent
    once per cast). ``grace <= 0`` can never forgive; ``>= 1`` always
    does."""
    if grace <= 0.0:
        return False
    if grace >= 1.0:
        return True
    r = rng or random.Random()
    return r.random() < grace


def is_trophy(
    species: catalog.FishSpecies,
    fishing_level: int,
    venue: str = catalog.SHORE_VENUE,
) -> bool:
    """True when *species* is a trophy for a player at *fishing_level* in
    *venue* (shipped verbatim).

    Trophy = the top :data:`TROPHY_BAND_FRACTION` of the unlocked size
    band, so it scales with progression. The band is the species' *own*
    venue (a deepwater fish is judged against the deepwater cap) —
    ``species.venue`` is authoritative, so a caller need not pass it."""
    cap = catalog.max_size_rank_for_level(fishing_level,
                                          species.venue or venue)
    threshold = cap - cap * TROPHY_BAND_FRACTION
    return species.size_rank > threshold


def escape_clue(species: catalog.FishSpecies,
                fishing_level: int) -> str | None:
    """A "the one that got away" clue when a *trophy* slips the hook
    (else ``None``) — shipped verbatim. Only trophies earn a story."""
    if not is_trophy(species, fishing_level):
        return None
    return f"💭 *...it looked like a real **{species.name.title()}**, too.*"


def reel_fight_taps(species: catalog.FishSpecies) -> int:
    """How many reel taps it takes to land *species* — scales with its
    size (shipped verbatim): :data:`FIGHT_MIN_TAPS` for the smallest up
    to :data:`FIGHT_MAX_TAPS` for the biggest in the catalog."""
    span = FIGHT_MAX_TAPS - FIGHT_MIN_TAPS
    return FIGHT_MIN_TAPS + round(span * (species.size_rank / 21.0))


def fight_escape_chance(
    species: catalog.FishSpecies,
    escape_resist: float = 0.0,
    *,
    base_escape: float = SHORE_ESCAPE_CHANCE,
) -> float:
    """Per-tap chance the fish snaps free, before/after rod escape-resist
    (shipped verbatim). ``base_escape`` is far higher in deepwater
    (:mod:`sb.domain.fishing.venue` — the boat's ~22%); bigger fish are
    slightly more likely to throw the hook."""
    rarity = species.size_rank / 21.0
    base = base_escape * (0.6 + rarity)
    return max(0.0, base * (1.0 - escape_resist))


def roll_escape(
    species: catalog.FishSpecies,
    *,
    escape_resist: float = 0.0,
    base_escape: float = SHORE_ESCAPE_CHANCE,
    rng: random.Random | None = None,
) -> bool:
    """Roll whether the fish snaps free on this tap (shipped verbatim —
    see :func:`fight_escape_chance`)."""
    r = rng or random.Random()
    return r.random() < fight_escape_chance(
        species,
        escape_resist,
        base_escape=base_escape,
    )


def reel_is_in_time(elapsed: float, window: float = REACTION_WINDOW) -> bool:
    """Did the reel land within the window? (shipped verbatim;
    ``elapsed`` = bite → measured click, network round trip included)."""
    return 0.0 <= elapsed <= window
