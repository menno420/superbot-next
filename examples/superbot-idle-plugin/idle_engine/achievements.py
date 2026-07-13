"""Achievements: threshold milestones with permanent, deterministic bonuses.

A :class:`MilestoneSpec` is pure mechanics — which metric it watches
(``owned``: total generators owned; ``lifetime``: run-lifetime earnings
of one currency; ``prestige``: persistent prestige-currency units held),
the threshold, and the permanent global ``bonus_percent`` it grants once
earned. Every threshold and bonus is pre-registered ENGINE-side in
``docs/design/achievements-v0.md`` (PROVISIONAL pending Simulator
pinning, Q-0264); a theme pack only names the slots (nouns/flavor/emoji
in its optional ``milestones`` block — the SKIN side).

Earned-set semantics (the design decisions this module encodes):

- **Earned once, kept forever.** ``state.milestones`` maps milestone
  spec_id -> ``1`` once earned; awarding never revokes, and
  :func:`idle_engine.prestige.apply_prestige` preserves the mapping —
  milestones are META-progression, like the prestige currency, while
  the counters they watch are (mostly) run-scoped.
- **Awarding is an explicit ACTION.** :func:`award_milestones` is a
  boundary step the runtime calls between production spans (exactly
  like an upgrade purchase). Production within a span reads the earned
  set at span start via :func:`milestone_percent`, so the closed-form
  offline credit stays EXACTLY equal to looped ticks by construction —
  the rate cannot drift mid-span.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Iterable

from idle_engine.state import GameState

#: The three pre-registered milestone tracks (docs/design/achievements-v0.md).
MILESTONE_KINDS = ("owned", "lifetime", "prestige")


@dataclass(frozen=True)
class MilestoneSpec:
    """Mechanical description of one threshold milestone.

    ``spec_id`` is the opaque slot id a theme pack maps to display
    nouns. ``kind`` picks the metric; ``subject`` is the measured
    currency id for the ``lifetime``/``prestige`` kinds and MUST be
    empty for ``owned`` (which watches the TOTAL generator count —
    v0 deliberately pre-registers no per-generator track).
    ``bonus_percent`` is the additive percent added to ALL production,
    permanently, once the milestone is earned.
    """

    spec_id: str
    kind: str
    subject: str
    threshold: int
    bonus_percent: int

    def __post_init__(self) -> None:
        if self.kind not in MILESTONE_KINDS:
            raise ValueError(
                f"kind must be one of {MILESTONE_KINDS}, got {self.kind!r}"
            )
        for name, value, minimum in (
            ("threshold", self.threshold, 1),
            ("bonus_percent", self.bonus_percent, 0),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an int")
            if value < minimum:
                raise ValueError(f"{name} must be >= {minimum}")
        if self.kind == "owned":
            if self.subject:
                raise ValueError(
                    "an 'owned' milestone watches the TOTAL generator count "
                    "and takes no subject"
                )
        elif not self.subject:
            raise ValueError(f"a {self.kind!r} milestone requires a subject currency id")


def milestone_progress(state: GameState, spec: MilestoneSpec) -> int:
    """The metric's current integer value for ``spec``'s track."""
    if spec.kind == "owned":
        return sum(state.owned.values())
    if spec.kind == "lifetime":
        return state.lifetime.get(spec.subject, 0)
    return state.prestige.get(spec.subject, 0)


def milestone_reached(state: GameState, spec: MilestoneSpec) -> bool:
    """True when the LIVE metric meets the threshold (earned or not)."""
    return milestone_progress(state, spec) >= spec.threshold


def milestone_earned(state: GameState, spec: MilestoneSpec) -> bool:
    """True once the milestone has been awarded (``state.milestones``)."""
    return state.milestones.get(spec.spec_id, 0) >= 1


def award_milestones(
    state: GameState, specs: Iterable[MilestoneSpec]
) -> GameState:
    """Mark every reached-but-unearned milestone as earned.

    The explicit action-boundary step: the runtime calls this between
    production spans (after crediting offline progress, after a
    purchase, after a reset) — never implicitly inside ``tick``, so the
    tick == closed-form-offline exactness is preserved by construction.
    Returns a NEW GameState when anything was awarded, the input
    unchanged otherwise; earned milestones are never revoked.
    """
    newly = [
        spec.spec_id
        for spec in specs
        if not milestone_earned(state, spec) and milestone_reached(state, spec)
    ]
    if not newly:
        return state
    milestones = dict(state.milestones)
    for spec_id in newly:
        milestones[spec_id] = 1
    return replace(state, milestones=milestones)


def milestone_percent(
    state: GameState, milestone_specs: Iterable[MilestoneSpec]
) -> int:
    """Global production multiplier as an integer percent (100 = x1).

    Additive across EARNED milestones only: ``100 + sum(bonus_percent)``
    over specs marked in ``state.milestones``. Live progress never
    counts — a reached-but-unawarded milestone contributes nothing
    until :func:`award_milestones` banks it, which keeps the rate a
    pure function of the state the span started from.
    """
    percent = 100
    for spec in milestone_specs:
        mark = state.milestones.get(spec.spec_id, 0)
        if mark < 0:
            raise ValueError(
                f"milestone mark for {spec.spec_id!r} must be >= 0"
            )
        if mark >= 1:
            percent += spec.bonus_percent
    return percent
