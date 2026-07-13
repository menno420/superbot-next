"""Prestige: the reset mechanic and its persistent global multiplier.

A :class:`PrestigeSpec` is pure mechanics — which currency's lifetime
earnings it measures, the eligibility threshold, the award curve, the
per-unit bonus. The prestige currency's name and the action's name are
theme-pack nouns (SKIN side). Curve shape and parameters are
pre-registered in ``docs/design/upgrades-prestige-v0.md`` (PROVISIONAL
pending the economy design doc slice + Simulator pinning, Q-0264).

Award shape: ``award = isqrt(lifetime_measured // award_divisor)`` —
integer square root of the lifetime earnings this run, in units of the
divisor. Deterministic, monotonic, strongly diminishing: doubling a run
does not double the award, so the optimal loop is reset-and-grow rather
than one endless grind.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Iterable
from math import isqrt

from idle_engine.state import GameState


def _require_int(value: int, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


@dataclass(frozen=True)
class PrestigeSpec:
    """Mechanical description of one prestige (reset) track.

    ``awards`` is the opaque id of the persistent prestige currency;
    ``measures`` is the opaque id of the run currency whose LIFETIME
    earnings drive eligibility and the award. ``bonus_percent`` is the
    additive percent added to ALL production per unit of the prestige
    currency held.
    """

    awards: str
    measures: str
    threshold: int
    award_divisor: int
    bonus_percent: int

    def __post_init__(self) -> None:
        _require_int(self.threshold, "threshold", 1)
        _require_int(self.award_divisor, "award_divisor", 1)
        _require_int(self.bonus_percent, "bonus_percent", 0)
        if self.threshold < self.award_divisor:
            raise ValueError(
                "threshold must be >= award_divisor so an eligible reset always awards >= 1"
            )


def prestige_award(state: GameState, spec: PrestigeSpec) -> int:
    """Deterministic award for resetting now: isqrt(lifetime // divisor)."""
    lifetime = state.lifetime.get(spec.measures, 0)
    if lifetime < 0:
        raise ValueError(f"lifetime for {spec.measures!r} must be >= 0")
    return isqrt(lifetime // spec.award_divisor)


def prestige_eligible(state: GameState, spec: PrestigeSpec) -> bool:
    """True once this run's lifetime earnings reach the threshold."""
    return state.lifetime.get(spec.measures, 0) >= spec.threshold


def apply_prestige(state: GameState, spec: PrestigeSpec) -> GameState:
    """Reset the run and bank the award.

    Wipes balances, owned generators, upgrade levels and lifetime
    earnings; credits the prestige currency; preserves ``last_seen``
    (the wall-clock anchor is not part of the run) and every other
    prestige balance. Returns a NEW GameState; raises ``ValueError``
    when the state is not eligible — a reset either happens exactly or
    not at all.
    """
    if not prestige_eligible(state, spec):
        lifetime = state.lifetime.get(spec.measures, 0)
        raise ValueError(
            f"not eligible to reset: lifetime {spec.measures!r} is "
            f"{lifetime}, threshold is {spec.threshold}"
        )
    prestige = dict(state.prestige)
    prestige[spec.awards] = prestige.get(spec.awards, 0) + prestige_award(state, spec)
    return replace(
        state, balances={}, owned={}, upgrades={}, lifetime={}, prestige=prestige
    )


def prestige_percent(state: GameState, prestige_specs: Iterable[PrestigeSpec]) -> int:
    """Global production multiplier as an integer percent (100 = x1).

    Additive across specs: ``100 + sum(bonus_percent * units_held)``.
    Applies to every generator, this run and every run after — the
    persistence lives in ``state.prestige`` surviving resets.
    """
    percent = 100
    for spec in prestige_specs:
        held = state.prestige.get(spec.awards, 0)
        if held < 0:
            raise ValueError(f"prestige balance for {spec.awards!r} must be >= 0")
        percent += spec.bonus_percent * held
    return percent
