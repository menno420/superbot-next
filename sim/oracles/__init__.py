"""The pluggable scoring-oracle registry (canonical plan §5 step 11: 'a
shared harness hosting pluggable per-surface scoring oracles').

An oracle scores ONE candidate arrangement for one surface kind. The runner
(sim/run.py) owns search + records; oracles own meaning. Registered by
name; the three named oracles self-register on package import:

  navigation        — the Q-0235 instruction-driven navigation engine
  settings_grouping — scroll-to-coverage over the fallback DAG
  dense_panel       — ergonomic interaction cost

The navigation engine deliberately does NOT subsume the other two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

__all__ = [
    "ScoreBreakdown",
    "ScoringOracle",
    "clear_oracles_for_tests",
    "get_oracle",
    "register_oracle",
    "registered_oracles",
]


@dataclass(frozen=True)
class ScoreBreakdown:
    """Per-term breakdown (§2.10.5 'per-term score breakdown'). Higher total
    = better. `confidence` mirrors the sidecar provenance (§2.10.4: every
    scorecard carries one; low-confidence arrangement changes are
    deferred)."""

    total: float
    terms: dict[str, float] = field(default_factory=dict)
    confidence: str = "low"
    notes: str = ""


class ScoringOracle(Protocol):
    def score(self, candidate: Any, context: dict[str, Any]) -> ScoreBreakdown:
        """Score one candidate arrangement. `context` carries the sidecar
        (`usage`), the declared specs, and space params."""


_ORACLES: dict[str, Callable[[], ScoringOracle]] = {}


def register_oracle(name: str, factory: Callable[[], ScoringOracle]) -> None:
    if name in _ORACLES:
        raise ValueError(f"oracle {name!r} already registered")
    _ORACLES[name] = factory


def get_oracle(name: str) -> ScoringOracle:
    try:
        return _ORACLES[name]()
    except KeyError:
        raise KeyError(
            f"no oracle {name!r}; registered: {sorted(_ORACLES)}"
        ) from None


def registered_oracles() -> tuple[str, ...]:
    return tuple(sorted(_ORACLES))


def clear_oracles_for_tests() -> None:
    _ORACLES.clear()
    _register_named()


def _register_named() -> None:
    from sim.oracles.dense_panel import DensePanelOracle
    from sim.oracles.navigation import NavigationOracle
    from sim.oracles.settings_grouping import SettingsGroupingOracle

    for name, factory in (
        ("navigation", NavigationOracle),
        ("settings_grouping", SettingsGroupingOracle),
        ("dense_panel", DensePanelOracle),
    ):
        if name not in _ORACLES:
            register_oracle(name, factory)


_register_named()
