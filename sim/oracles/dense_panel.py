"""The dense-panel oracle — ergonomic interaction cost (canonical plan §5
step 11: the third named oracle, distinct from navigation).

Candidate shape: a layout in the PageSpec.rows shape — pages -> rows ->
component ids (sim.space.generate_layout_candidates output).

Terms (stated, not implied — §2.10.4):
  interaction_cost — usage-weighted positional cost; reaching page p, row
                     r, column c costs p*PAGE_COST + r*ROW_COST + c*COL_COST
                     (page turns dominate, rows beat columns).
  co_use_distance  — pair-mass-weighted mean placement distance for co-use
                     pairs (sidecar keys "co_use|<a>|<b>"); neutral 0 with
                     no signal, confidence low.

Hard constraints (destructive placement, Discord caps) are NOT scored here —
they are evaluated deterministically by sim.space.check_hard_constraints and
inadmissible candidates never reach an oracle (§2.10.4).
"""

from __future__ import annotations

from typing import Any

from sim.oracles import ScoreBreakdown

__all__ = ["DensePanelOracle"]

PAGE_COST = 10.0
ROW_COST = 2.0
COL_COST = 1.0
W_INTERACTION = 1.0
W_CO_USE = 0.3


def _positions(layout: Any) -> dict[str, tuple[int, int, int]]:
    positions: dict[str, tuple[int, int, int]] = {}
    for p, rows in enumerate(layout):
        for r, row in enumerate(rows):
            for c, cid in enumerate(row):
                positions[cid] = (p, r, c)
    return positions


class DensePanelOracle:
    def score(self, candidate: Any, context: dict[str, Any]) -> ScoreBreakdown:
        positions = _positions(candidate)
        if not positions:
            return ScoreBreakdown(total=0.0, notes="empty layout")
        usage = context.get("usage")

        weight_total = 0.0
        cost = 0.0
        for cid, (p, r, c) in positions.items():
            w = usage.weight(cid) if usage is not None else 1.0
            weight_total += w
            cost += w * (p * PAGE_COST + r * ROW_COST + c * COL_COST)
        max_unit = PAGE_COST * max(len(candidate) - 1, 0) + ROW_COST * 4 + COL_COST * 4
        interaction_cost = (cost / weight_total) / max(max_unit, 1.0)

        pairs: dict[str, float] = {}
        if usage is not None:
            pairs = {k: v for k, v in usage.pairs.items() if k.startswith("co_use|")}
        pair_mass = 0.0
        distance_mass = 0.0
        for pair_key, mass in pairs.items():
            parts = pair_key.split("|")
            if len(parts) != 3:
                continue
            _, a, b = parts
            if a not in positions or b not in positions:
                continue
            pa, pb = positions[a], positions[b]
            distance = (
                abs(pa[0] - pb[0]) * PAGE_COST
                + abs(pa[1] - pb[1]) * ROW_COST
                + abs(pa[2] - pb[2]) * COL_COST
            )
            pair_mass += mass
            distance_mass += mass * distance
        if pair_mass > 0:
            co_use_distance = (distance_mass / pair_mass) / max(PAGE_COST, 1.0)
            confidence = usage.confidence if usage is not None else "measured"
            notes = ""
        else:
            co_use_distance = 0.0
            confidence = "low"
            notes = "no co-use pair signal — neutral prior (§2.10.4)"

        total = -(W_INTERACTION * interaction_cost + W_CO_USE * co_use_distance)
        return ScoreBreakdown(
            total=total,
            terms={
                "interaction_cost": interaction_cost,
                "co_use_distance": co_use_distance,
            },
            confidence=confidence,
            notes=notes,
        )
