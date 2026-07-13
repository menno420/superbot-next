"""Upgrades: geometric cost curves and rate effects, all integer-exact.

An :class:`UpgradeSpec` is pure mechanics — id, cost curve, target
generator, effect size. Its player-visible noun lives in the theme pack
(the SKIN side); the curve SHAPE and every parameter are pre-registered
in ``docs/design/upgrades-prestige-v0.md`` (PROVISIONAL pending the
economy design doc slice + Simulator pinning, Q-0264).

Curve shape: ``cost(level) = base_cost * growth_num**level // growth_den**level``
— geometric growth evaluated in exact big-int arithmetic with a single
floor division, so every platform prices level N identically.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Iterable
from math import gcd

from idle_engine.state import GameState


class BulkPurchaseError(ValueError):
    """A bulk purchase could not be afforded IN FULL — nothing was spent.

    Distinct from the single-purchase ``ValueError`` so callers can tell
    "your buy-N was rejected atomically" apart from a plain insufficient
    single purchase, while remaining a ``ValueError`` subclass for
    callers of the existing contract.
    """


def _require_positive_int(value: int, name: str, minimum: int = 1) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


@dataclass(frozen=True)
class UpgradeSpec:
    """Mechanical description of one purchasable upgrade ladder.

    ``spec_id``, ``cost_currency`` and ``target`` are opaque ids mapped
    to display nouns by a theme pack. ``effect_percent`` is the additive
    percent added to the target generator's rate per level purchased
    (level 3 at 25 -> +75%).
    """

    spec_id: str
    cost_currency: str
    base_cost: int
    cost_growth_num: int
    cost_growth_den: int
    target: str
    effect_percent: int

    def __post_init__(self) -> None:
        _require_positive_int(self.base_cost, "base_cost")
        _require_positive_int(self.cost_growth_num, "cost_growth_num")
        _require_positive_int(self.cost_growth_den, "cost_growth_den")
        _require_positive_int(self.effect_percent, "effect_percent")
        if self.cost_growth_num < self.cost_growth_den:
            raise ValueError(
                "cost growth must be >= 1 (num >= den): shrinking costs are an exploit"
            )


def upgrade_cost(spec: UpgradeSpec, level: int) -> int:
    """Exact integer cost of buying ``spec`` when ``level`` are already owned."""
    _require_positive_int(level, "level", minimum=0)
    return spec.base_cost * spec.cost_growth_num**level // spec.cost_growth_den**level


def bulk_upgrade_cost(spec: UpgradeSpec, from_level: int, n: int) -> int:
    """EXACT integer cost of the next ``n`` levels when ``from_level`` are owned.

    Equals ``sum(upgrade_cost(spec, from_level + k) for k in range(n))``
    by definition. A geometric-series closed form with ONE final floor is
    NOT that number: each level's cost floors independently, and the
    single final floor keeps fractional parts the per-level floors
    discard, so the closed form systematically OVER-charges (real v0
    curve, base 60 x1.15, five levels from 0: exact 403 vs closed-form
    404 — pinned in tests). The exact sum is therefore computed level by
    level, but with an incremental quotient/remainder recurrence instead
    of a fresh big-int power + division per level:

    with ``q = base*num^L // den^L`` and ``r = base*num^L mod den^L``,

        base*num^(L+1) = num*q*den^L + num*r
                       = (num*q + a)*den^L + b        (a, b) = divmod(num*r, den^L)
        q' = (num*q + a) // den                       exact, since
        r' = ((num*q + a) mod den)*den^L + b          d*den^L + b < den^(L+1)

    so each step costs a few small-by-big multiplies and one division
    with a tiny quotient — O(n) steps total, fast even when the running
    powers are tens of thousands of digits. ``num/den`` is reduced by
    gcd first (identical rational, identical floors, smaller operands);
    a reduced ratio of exactly 1 means every level costs ``base_cost``
    and the sum is the O(1) closed form ``base_cost * n`` (no floor loss:
    the terms are integers).
    """
    _require_positive_int(from_level, "from_level", minimum=0)
    _require_positive_int(n, "n", minimum=0)
    num, den = spec.cost_growth_num, spec.cost_growth_den
    g = gcd(num, den)
    num //= g
    den //= g
    if num == den:  # ratio exactly 1: flat curve, exact closed form
        return spec.base_cost * n
    den_pow = den**from_level
    q, r = divmod(spec.base_cost * num**from_level, den_pow)
    total = 0
    for _ in range(n):
        total += q
        a, b = divmod(r * num, den_pow)
        q, d = divmod(q * num + a, den)
        r = d * den_pow + b
        den_pow *= den
    return total


def max_affordable_levels(spec: UpgradeSpec, from_level: int, budget: int) -> int:
    """Largest ``n`` with ``bulk_upgrade_cost(spec, from_level, n) <= budget``.

    Efficient at any scale — never a per-level scan. The bulk sum is
    monotone in ``n``, so the answer is found by exponential search then
    bisection. Each probe is decided by EXACT rational bounds around the
    floored sum: with ``T(k)`` the exact geometric-series rational
    (no floors) and ``B(k)`` the true floored sum,

        T(k) - k < B(k) <= T(k)

    (each of the ``k`` per-level floors discards a fraction in ``[0, 1)``).
    ``T(k) <= budget`` proves affordable; ``T(k) >= budget + k`` proves
    unaffordable; both are integer cross-multiplication tests costing a
    couple of big pows — so a 10^3000-scale budget resolves in dozens of
    cheap probes. Only when ``budget`` lands inside the width-``k``
    ambiguity window (measure ~k out of a cost scale of ~budget — rare,
    and only reachable adversarially at large scale) does a probe fall
    back to the exact O(k) sum, which stays the correctness anchor.

    A reduced growth ratio of exactly 1 short-circuits to the closed
    form ``budget // base_cost`` (every level costs ``base_cost``).
    """
    _require_positive_int(from_level, "from_level", minimum=0)
    _require_positive_int(budget, "budget", minimum=0)
    if budget < upgrade_cost(spec, from_level):
        return 0
    base = spec.base_cost
    num, den = spec.cost_growth_num, spec.cost_growth_den
    g = gcd(num, den)
    num //= g
    den //= g
    if num == den:  # flat curve: exact closed form
        return budget // base

    def affordable(k: int) -> bool:
        # T(k) = base * num^f * (num^k - den^k) / (den^(f+k-1) * (num - den))
        lhs = base * num**from_level * (num**k - den**k)
        scale = den ** (from_level + k - 1) * (num - den)
        if lhs <= budget * scale:  # B(k) <= T(k) <= budget
            return True
        if lhs >= (budget + k) * scale:  # B(k) > T(k) - k >= budget
            return False
        return bulk_upgrade_cost(spec, from_level, k) <= budget

    lo = 1  # affordable: budget covers the first level (checked above)
    hi = 2
    while affordable(hi):
        lo = hi
        hi *= 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if affordable(mid):
            lo = mid
        else:
            hi = mid
    return lo


def purchase_upgrade(state: GameState, spec: UpgradeSpec) -> GameState:
    """Spend ``spec.cost_currency`` to raise the upgrade one level.

    Returns a NEW GameState; the input is never mutated. Raises
    ``ValueError`` when the balance cannot cover the current level's
    cost — a purchase either happens exactly or not at all. Spending
    never touches ``lifetime``.
    """
    level = state.upgrades.get(spec.spec_id, 0)
    cost = upgrade_cost(spec, level)
    balance = state.balances.get(spec.cost_currency, 0)
    if balance < cost:
        raise ValueError(
            f"insufficient {spec.cost_currency!r} for {spec.spec_id!r} "
            f"level {level + 1}: have {balance}, need {cost}"
        )
    balances = dict(state.balances)
    balances[spec.cost_currency] = balance - cost
    upgrades = dict(state.upgrades)
    upgrades[spec.spec_id] = level + 1
    return replace(state, balances=balances, upgrades=upgrades)


def purchase_upgrades(state: GameState, spec: UpgradeSpec, n: int) -> GameState:
    """Spend once to raise the upgrade ``n`` levels — atomically.

    Byte-identical to ``n`` sequential :func:`purchase_upgrade` calls
    (the exact bulk cost IS the sum of the per-level costs), but with a
    single all-or-nothing spend: if the balance cannot cover the FULL
    ``n`` levels, :class:`BulkPurchaseError` is raised and nothing is
    spent — never a partial climb. Returns a NEW GameState; the input is
    never mutated. Spending never touches ``lifetime``.
    """
    _require_positive_int(n, "n")
    level = state.upgrades.get(spec.spec_id, 0)
    cost = bulk_upgrade_cost(spec, level, n)
    balance = state.balances.get(spec.cost_currency, 0)
    if balance < cost:
        raise BulkPurchaseError(
            f"insufficient {spec.cost_currency!r} for {spec.spec_id!r} "
            f"levels {level + 1}..{level + n}: have {balance}, need {cost} "
            "(atomic: nothing was spent)"
        )
    balances = dict(state.balances)
    balances[spec.cost_currency] = balance - cost
    upgrades = dict(state.upgrades)
    upgrades[spec.spec_id] = level + n
    return replace(state, balances=balances, upgrades=upgrades)


def upgrade_percent(
    state: GameState, upgrade_specs: Iterable[UpgradeSpec], generator_id: str
) -> int:
    """Rate multiplier for one generator as an integer percent (100 = x1).

    Additive across levels and across upgrades sharing a target:
    ``100 + sum(effect_percent * level)``.
    """
    percent = 100
    for spec in upgrade_specs:
        if spec.target == generator_id:
            level = state.upgrades.get(spec.spec_id, 0)
            if level < 0:
                raise ValueError(f"upgrade level for {spec.spec_id!r} must be >= 0")
            percent += spec.effect_percent * level
    return percent
