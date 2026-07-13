"""Fishing cast energy — the shipped ``utils/fishing/energy.py`` math,
verbatim (reconstructed fragment-by-fragment via search_code; the regen
math mirrors the shipped mining energy module — the oracle's own
rule-of-three note kept the two copies separate).

Pure functions only — no DB, no Discord. The persisted state is
``(energy:int, updated_at:unix)`` on the ``fishing_energy`` table
(migration 0035, shipped 088 shape); *effective* energy at any instant is
computed from elapsed time by :func:`settle` (a stored value + a
timestamp, never a background ticker — the shipped ADR-001/002 posture).
``goldens/fishing/sweep_fish.json`` pins the spent fresh-bar row
(``energy: 58`` = ``MAX_ENERGY - CAST_COST``, ``energy_updated_at`` =
frozen now) and the footer gauge byte-for-byte
(``⚡ 58/60 [▰▰▰▰▰▰▰▰▰▰]`` — ``round(10 * 58/60) = 10`` filled).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CAST_COST",
    "EnergyState",
    "MAX_ENERGY",
    "REGEN_SECONDS",
    "bar",
    "can_cast",
    "regen_seconds_for",
    "seconds_until",
    "settle",
    "spend",
]

# shipped constants verbatim (utils/fishing/energy.py)
MAX_ENERGY = 60  # a full bar ≈ a 30-cast session before you regen-throttle
CAST_COST = 2  # energy spent per cast
REGEN_SECONDS = 30  # +1 energy every 30s (≈ 1 cast / minute sustained at cost 2)


@dataclass(frozen=True)
class EnergyState:
    """The persisted pair — a stored value and its last-settled stamp."""

    current: int
    updated_at: int


def settle(
    state: EnergyState,
    now: int,
    *,
    max_energy: int = MAX_ENERGY,
    regen_seconds: int = REGEN_SECONDS,
) -> EnergyState:
    """Fold elapsed passive regen into *state* (shipped verbatim).

    A fresh/never-stamped row (``updated_at=0``) settles straight to the
    cap; partial regen advances ``updated_at`` by the WHOLE intervals
    consumed so fractional progress never evaporates."""
    if state.current >= max_energy:
        return EnergyState(max_energy, now)
    elapsed = max(0, now - state.updated_at)
    gained = elapsed // regen_seconds
    new = min(max_energy, state.current + gained)
    if new >= max_energy:
        return EnergyState(max_energy, now)
    return EnergyState(new, state.updated_at + gained * regen_seconds)


def can_cast(state: EnergyState, *, cost: int = CAST_COST) -> bool:
    """Enough settled energy for one cast?"""
    return state.current >= cost


def spend(
    state: EnergyState,
    now: int,
    *,
    cost: int = CAST_COST,
    max_energy: int = MAX_ENERGY,
    regen_seconds: int = REGEN_SECONDS,
) -> EnergyState:
    """Settle then pay for one cast — the per-attempt pacing brake.

    Caller checks :func:`can_cast` first; the floor-clamp keeps a raced
    write honest rather than minting negative energy. Returns the
    settled ``updated_at`` (shipped verbatim — ``utils/fishing/energy.py``
    ``spend`` keeps ``s.updated_at``, remainder-preserving): stamping
    ``now`` instead (the pre-wiring port drift) silently discarded up to
    ``regen_seconds - 1`` seconds of partial regen on every below-cap
    spend. A fresh full bar settles to ``(MAX, now)``, so the
    golden-pinned fresh-player row is byte-identical either way."""
    s = settle(state, now, max_energy=max_energy,
               regen_seconds=regen_seconds)
    return EnergyState(max(0, s.current - cost), s.updated_at)


def seconds_until(
    state: EnergyState,
    now: int,
    target: int,
    *,
    max_energy: int = MAX_ENERGY,
    regen_seconds: int = REGEN_SECONDS,
) -> int:
    """Seconds of passive regen until settled energy reaches *target*
    (0 if already) — the shipped ``seconds_until`` verbatim (the
    pre-wiring port carried this function under the WRONG NAME
    ``regen_seconds_for``; that name now belongs to the boathouse
    interval hook below, as shipped)."""
    s = settle(state, now, max_energy=max_energy,
               regen_seconds=regen_seconds)
    if s.current >= target:
        return 0
    needed = min(max_energy, target) - s.current
    remainder = now - s.updated_at  # 0 ≤ remainder < regen_seconds
    return max(0, needed * regen_seconds - remainder)


def regen_seconds_for(regen_mult: float, *, base: int = REGEN_SECONDS) -> int:
    """The effective regen interval when a structure speeds regen by
    *regen_mult* (shipped verbatim — ``utils/fishing/energy.py``).

    A built **Boathouse** (``sb.domain.mining.structures.
    boathouse_regen_mult``) grants a multiplier ≤ 1.0 (lower = faster
    refill); this turns it into the ``regen_seconds`` the
    :func:`settle` / :func:`spend` / :func:`seconds_until` calls use.
    ``regen_mult`` of ``1.0`` (unbuilt) returns exactly *base* ⇒
    byte-identical energy. Never below 1 (a 0-second interval would
    divide-by-zero the regen math)."""
    return max(1, round(base * regen_mult))


def bar(current: int, max_energy: int = MAX_ENERGY, *, width: int = 10) -> str:
    """A compact ``⚡ 42/60 [▰▰▰▰▰▰▰▱▱▱]`` energy gauge for the fishing panel."""
    current = max(0, min(max_energy, current))
    filled = round(width * current / max_energy) if max_energy else 0
    return f"⚡ {current}/{max_energy} [{'▰' * filled}{'▱' * (width - filled)}]"
