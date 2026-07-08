"""The settings-grouping oracle — scroll-to-coverage over the fallback DAG
(canonical plan §5 step 11: kept DISTINCT from the navigation engine).

Candidate shape: an ordered tuple of (group_name, (setting_key, ...))
pairs — the [A] grouping/ordering assignment for one subsystem's settings
surface.

Terms (§2.10.4 aggregation stated, not implied):
  scroll_cost    — usage-weighted mean scroll distance to reach each
                   setting walking the grouped list top-to-bottom (the
                   fallback DAG order = the rendered order).
  group_cohesion — the normalized share of co-edit pair mass falling
                   intra-group; measured pairs (sidecar `pairs`, keys
                   "co_edit|<a>|<b>") override seed priors the moment they
                   exist; with no pair signal the term is neutral (0.5)
                   and confidence stays low.
"""

from __future__ import annotations

from typing import Any

from sim.oracles import ScoreBreakdown

__all__ = ["SettingsGroupingOracle"]

W_SCROLL = 0.6
W_COHESION = 0.4


class SettingsGroupingOracle:
    def score(self, candidate: Any, context: dict[str, Any]) -> ScoreBreakdown:
        groups: tuple[tuple[str, tuple[str, ...]], ...] = tuple(candidate)
        usage = context.get("usage")
        pairs: dict[str, float] = dict(context.get("pairs") or {})
        if usage is not None and not pairs:
            pairs = {k: v for k, v in usage.pairs.items() if k.startswith("co_edit|")}

        ordered: list[str] = [key for _, keys in groups for key in keys]
        if not ordered:
            return ScoreBreakdown(total=0.0, notes="empty settings surface")

        # scroll_cost: usage-weighted mean position, normalized to [0, 1].
        weight_total = 0.0
        cost = 0.0
        for position, key in enumerate(ordered):
            w = usage.weight(key) if usage is not None else 1.0
            weight_total += w
            cost += w * position
        scroll_cost = (cost / weight_total) / max(len(ordered) - 1, 1)

        # group_cohesion: intra-group pair-mass share (neutral without signal).
        group_of = {
            key: name for name, keys in groups for key in keys
        }
        pair_mass = 0.0
        intra_mass = 0.0
        for pair_key, mass in pairs.items():
            parts = pair_key.split("|")
            if len(parts) != 3:
                continue
            _, a, b = parts
            if a not in group_of or b not in group_of:
                continue
            pair_mass += mass
            if group_of[a] == group_of[b]:
                intra_mass += mass
        if pair_mass > 0:
            cohesion = intra_mass / pair_mass
            confidence = usage.confidence if usage is not None else "measured"
            notes = ""
        else:
            cohesion = 0.5
            confidence = "low"
            notes = "no co-edit pair signal — neutral prior (§2.10.4)"

        total = W_COHESION * cohesion - W_SCROLL * scroll_cost
        return ScoreBreakdown(
            total=total,
            terms={"scroll_cost": scroll_cost, "group_cohesion": cohesion},
            confidence=confidence,
            notes=notes,
        )
