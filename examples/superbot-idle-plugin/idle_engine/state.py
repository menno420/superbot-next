"""Pure game-state containers for the idle engine.

All quantities are integers: currency balances are integer units and
production rates are integer units-per-second, so the math is exact and
identical on every platform (no float drift, no rounding ambiguity).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class GeneratorSpec:
    """Mechanical description of one generator kind.

    ``spec_id`` and ``produces`` are opaque identifiers that a theme
    pack maps to display nouns; the engine never interprets them as
    words. ``base_rate`` is integer currency units produced per second
    per owned generator. ``rate_multiplier_pct`` is the theme lane's
    bounded balance knob as an integer percent (100 = neutral); the
    BOUNDS (90..110) are the theme contract's business, enforced by the
    schema and the theme loader — this container only requires a
    non-negative integer, like ``base_rate``.
    """

    spec_id: str
    produces: str
    base_rate: int
    rate_multiplier_pct: int = 100

    def __post_init__(self) -> None:
        if not isinstance(self.base_rate, int) or isinstance(self.base_rate, bool):
            raise TypeError("base_rate must be an int")
        if self.base_rate < 0:
            raise ValueError("base_rate must be >= 0")
        if not isinstance(self.rate_multiplier_pct, int) or isinstance(
            self.rate_multiplier_pct, bool
        ):
            raise TypeError("rate_multiplier_pct must be an int")
        if self.rate_multiplier_pct < 0:
            raise ValueError("rate_multiplier_pct must be >= 0")


@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of one save.

    Run-scoped (wiped by a prestige reset):
      ``balances`` maps currency id -> integer units held.
      ``owned`` maps generator spec_id -> integer count owned.
      ``upgrades`` maps upgrade spec_id -> integer level purchased.
      ``lifetime`` maps currency id -> integer units EARNED this run
      (production only — spending never decreases it; prestige awards
      are computed from it).

    Persistent (survives a prestige reset):
      ``prestige`` maps prestige currency id -> integer units held.
      ``milestones`` maps milestone spec_id -> ``1`` once earned
      (meta-progression: awarding is explicit and never revoked — see
      :mod:`idle_engine.achievements`).
      ``last_seen`` is the unix timestamp (integer seconds) up to which
      production has already been credited.
    """

    balances: dict[str, int] = field(default_factory=dict)
    owned: dict[str, int] = field(default_factory=dict)
    last_seen: int = 0
    upgrades: dict[str, int] = field(default_factory=dict)
    lifetime: dict[str, int] = field(default_factory=dict)
    prestige: dict[str, int] = field(default_factory=dict)
    milestones: dict[str, int] = field(default_factory=dict)

    def with_balances(self, balances: dict[str, int], last_seen: int) -> "GameState":
        """Return a new state with replaced balances and last_seen."""
        return replace(self, balances=dict(balances), last_seen=last_seen)

    def with_earnings(
        self, earned: dict[str, int], last_seen: int
    ) -> "GameState":
        """Credit production: add ``earned`` to balances AND lifetime.

        Production is the only path that grows ``lifetime``; spending
        goes through :func:`idle_engine.upgrades.purchase_upgrade` and
        touches balances alone.
        """
        balances = dict(self.balances)
        lifetime = dict(self.lifetime)
        for currency, amount in earned.items():
            balances[currency] = balances.get(currency, 0) + amount
            lifetime[currency] = lifetime.get(currency, 0) + amount
        return replace(self, balances=balances, lifetime=lifetime, last_seen=last_seen)
