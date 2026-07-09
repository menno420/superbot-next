"""Chicken farm — the pure idle domain, ported VERBATIM from the shipped
``utils/farm/farm.py`` (no DB, no Discord; a stored (eggs, updated_at)
pair + flock size, settled in pure code — no background ticker)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "EGG_VALUE",
    "FarmState",
    "LAY_INTERVAL_SECONDS",
    "MAX_CHICKENS",
    "MAX_COOP_LEVEL",
    "STARTER_CHICKENS",
    "can_buy_chicken",
    "can_upgrade_coop",
    "chicken_price",
    "collect_value",
    "coop_capacity",
    "coop_upgrade_price",
    "egg_bar",
    "lay_rate_per_hour",
    "seconds_until_full",
    "settle",
]

LAY_INTERVAL_SECONDS = 300  # one egg per hen every 5 minutes
EGG_VALUE = 2               # coins paid per egg on collect

STARTER_CHICKENS = 1
MAX_CHICKENS = 100
MAX_COOP_LEVEL = 10

BASE_CAPACITY = 20
CAPACITY_PER_LEVEL = 15

BASE_CHICKEN_PRICE = 40
CHICKEN_PRICE_GROWTH = 1.55
BASE_COOP_PRICE = 100
COOP_PRICE_GROWTH = 1.8


@dataclass(frozen=True)
class FarmState:
    """A player's farm: ``eggs`` uncollected as of ``updated_at``."""

    chickens: int
    eggs: int
    updated_at: int
    coop_level: int


def coop_capacity(coop_level: int) -> int:
    return BASE_CAPACITY + CAPACITY_PER_LEVEL * max(0, coop_level)


def settle(state: FarmState, now: int) -> FarmState:
    """Apply passive egg-laying up to *now* (sub-interval remainder
    preserved — settling every second equals settling once)."""
    cap = coop_capacity(state.coop_level)
    if state.chickens <= 0:
        return FarmState(state.chickens, min(state.eggs, cap), now,
                         state.coop_level)
    if state.eggs >= cap:
        return FarmState(state.chickens, cap, now, state.coop_level)
    elapsed = max(0, now - state.updated_at)
    intervals = elapsed // LAY_INTERVAL_SECONDS
    new_eggs = min(cap, state.eggs + intervals * state.chickens)
    if new_eggs >= cap:
        return FarmState(state.chickens, cap, now, state.coop_level)
    return FarmState(
        state.chickens, new_eggs,
        state.updated_at + intervals * LAY_INTERVAL_SECONDS,
        state.coop_level)


def seconds_until_full(state: FarmState, now: int) -> int:
    s = settle(state, now)
    cap = coop_capacity(s.coop_level)
    if s.chickens <= 0 or s.eggs >= cap:
        return 0
    remaining = cap - s.eggs
    intervals_needed = -(-remaining // s.chickens)
    remainder = now - s.updated_at
    return max(0, intervals_needed * LAY_INTERVAL_SECONDS - remainder)


def collect_value(eggs: int) -> int:
    return max(0, eggs) * EGG_VALUE


def chicken_price(current_chickens: int) -> int:
    extra = max(0, current_chickens - STARTER_CHICKENS)
    return round(BASE_CHICKEN_PRICE * (CHICKEN_PRICE_GROWTH ** extra))


def coop_upgrade_price(coop_level: int) -> int:
    return round(BASE_COOP_PRICE * (COOP_PRICE_GROWTH ** max(0, coop_level)))


def can_buy_chicken(current_chickens: int) -> bool:
    return current_chickens < MAX_CHICKENS


def can_upgrade_coop(coop_level: int) -> bool:
    return coop_level < MAX_COOP_LEVEL


def lay_rate_per_hour(chickens: int) -> int:
    return max(0, chickens) * (3600 // LAY_INTERVAL_SECONDS)


def egg_bar(eggs: int, capacity: int, *, width: int = 10) -> str:
    eggs = max(0, min(capacity, eggs))
    filled = round(width * eggs / capacity) if capacity else 0
    return f"🥚 {eggs}/{capacity} [{'▰' * filled}{'▱' * (width - filled)}]"
