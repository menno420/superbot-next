"""Fishing weather — a daily, date-seeded global bias (the shipped
``utils/fishing/weather.py``, verbatim; reconstructed fragment-by-fragment
via search_code).

The weather is **derived from the calendar date**, not stored — the same
ISO date always maps to the same condition (a deterministic sha256-seeded
weighted pick), so everyone in every guild sees the same weather on the
same day. ``bite_speed_mult`` (≤ 1 = faster bites) multiplies the bite
speed; ``rarity_mult`` (≥ 1 = biases bigger) multiplies the rarity pull.

REPLAY SEAM (:func:`seed_weather_for_replay`): the shipped pick read the
capture machine's REAL wall-clock date (``datetime.now(timezone.utc)``,
unpatched in the capture harness), so goldens pin the capture DAY's
weather — 🌧️ Rain in ``goldens/fishing/sweep_fish.json`` — while the
replay's frozen per-case clock lands on a different (clear-sky) date.
That is capture-world WORLD STATE, reconstructed exactly like
``CAPTURE_WORLD_SETTINGS`` / ``CAPTURE_WORLD_COUNTERS`` (the #163→#167
reseed lane): sb/adapters/parity/runner.py seeds the capture-day
condition per observing case and CLEARS it at every case head (trap 20 —
runner-seeded, never accumulated). Live reads stay date-derived.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone

__all__ = [
    "CONDITIONS",
    "Weather",
    "current_weather",
    "effect_text",
    "seed_weather_for_replay",
    "weather_for_date",
]


@dataclass(frozen=True)
class Weather:
    """One weather condition — its identity, flavour, and the two cast knobs."""

    key: str
    name: str
    emoji: str
    #: Multiplier on the bite wait (≤ 1 = faster bites, > 1 = slower/patient).
    bite_speed_mult: float
    #: Multiplier on the rarity pull (≥ 1 = biases the catch toward bigger fish).
    rarity_mult: float
    #: Relative frequency weight (the table sums to 100 — rough %-of-days).
    weight: int
    #: One-line player-facing flavour for the forecast / cast embeds.
    blurb: str


#: The weather table. Weights sum to 100 (read as rough %-of-days). The spread is
#: a deliberate risk/reward: rain = fast & common, storm = slow but the rarest
#: fish run, fog = patient but rarer, calm = a gently better all-rounder.
CONDITIONS: tuple[Weather, ...] = (
    Weather(
        "clear",
        "Clear skies",
        "☀️",
        bite_speed_mult=1.0,
        rarity_mult=1.0,
        weight=38,
        blurb="Calm and clear — a steady, ordinary day to fish.",
    ),
    Weather(
        "rain",
        "Rain",
        "🌧️",
        bite_speed_mult=0.85,
        rarity_mult=1.0,
        weight=22,
        blurb="Rain stirs the surface — the fish are biting fast today.",
    ),
    Weather(
        "calm",
        "Glassy calm",
        "🌅",
        bite_speed_mult=0.92,
        rarity_mult=1.08,
        weight=18,
        blurb="Glassy, still water — quick bites and a touch more chance at a prize.",
    ),
    Weather(
        "fog",
        "Fog",
        "🌫️",
        bite_speed_mult=1.15,
        rarity_mult=1.12,
        weight=14,
        blurb="Thick fog — slow, patient bites, but rarer fish lurk beneath.",
    ),
    Weather(
        "storm",
        "Storm",
        "⛈️",
        bite_speed_mult=1.12,
        rarity_mult=1.30,
        weight=8,
        blurb="Storm's up — choppy and slow, but the big, rare ones are running.",
    ),
)

_NEUTRAL = CONDITIONS[0]
_TOTAL_WEIGHT = sum(c.weight for c in CONDITIONS)
_BY_KEY: dict[str, Weather] = {c.key: c for c in CONDITIONS}

#: Parity-replay override (see module docstring) — a condition KEY or None.
_REPLAY_OVERRIDE: str | None = None


def _date_fraction(d: date) -> float:
    """Map a date to a stable fraction of [0, 1).

    Uses sha256 (not Python's salted ``hash``) so the mapping is stable across
    processes and machines — every agent / shard computes the same weather for a
    given day.
    """
    digest = hashlib.sha256(d.isoformat().encode("utf-8")).digest()
    # First 8 bytes → a 64-bit int → a fraction of its range.
    value = int.from_bytes(digest[:8], "big")
    return value / float(1 << 64)


def weather_for_date(d: date) -> Weather:
    """The weather for calendar date *d* — deterministic, weighted by frequency."""
    if _TOTAL_WEIGHT <= 0:
        return _NEUTRAL
    target = _date_fraction(d) * _TOTAL_WEIGHT
    cumulative = 0.0
    for condition in CONDITIONS:
        cumulative += condition.weight
        if target < cumulative:
            return condition
    return CONDITIONS[-1]


def current_weather(now: datetime | None = None) -> Weather:
    """Today's shared condition (UTC calendar day).

    The replay override wins when armed (capture-world reconstruction —
    module docstring); live paths never arm it."""
    if _REPLAY_OVERRIDE is not None:
        return _BY_KEY.get(_REPLAY_OVERRIDE, _NEUTRAL)
    moment = now or datetime.now(timezone.utc)
    return weather_for_date(moment.date())


def effect_text(weather: Weather) -> str:
    """A compact "what it does" line, e.g. ``faster bites · rarer fish``.

    Only names the knobs that actually move, so ``clear`` reads as "no effect".
    """
    parts: list[str] = []
    if weather.bite_speed_mult < 1.0:
        parts.append("faster bites")
    elif weather.bite_speed_mult > 1.0:
        parts.append("slower bites")
    if weather.rarity_mult > 1.0:
        parts.append("rarer fish")
    return " · ".join(parts) if parts else "no effect — a fair, ordinary day"


def seed_weather_for_replay(key: str | None) -> None:
    """Arm (or clear, ``None``) the capture-world condition for one replay
    case — called by sb/adapters/parity/runner.py at every case head."""
    global _REPLAY_OVERRIDE
    _REPLAY_OVERRIDE = key
