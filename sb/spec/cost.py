"""The class-11 cost/quota grammar (S11 — frozen L0 spec 10 §2.A).

``cost_posture`` + ``quota_ref`` home on **CommandSpec** (the frozen
ref-bearing facet — NOT an invented MediaGenerationSpec, spec 10 §8.4),
keyed off the frozen ``effect="external"`` manifest field. The media
default-OFF rule (L-16) IS the FAIL_CLOSED-until-a-counter-binds default:
a paid feature with no counter is OFF, never unbounded.

Phase 1 (Gate-0, now): declaration-presence — enforced by
``tools/check_cost_posture.py``. Phase 2 (after the T2-15 spend-counter
build): ``quota_ref`` must resolve to a REGISTERED counter; until then the
K1 name-reservation + FAIL_CLOSED interim holds.

Scope note (spec 10 §2.A, explicit not silent): quota tiers bound spend at
per-guild / global granularity only — the per-actor SPEND share is a future
``PER_ACTOR_QUOTA`` member sequenced with T2-15 (the per-user RATE axis is
K8's CooldownSpec + AI throttle).

Stdlib-only leaf.
"""

from __future__ import annotations

import enum

from sb.spec.roles import register_field_roles

__all__ = ["CostPosture", "check_command_cost_posture"]


class CostPosture(str, enum.Enum):
    FREE = "free"                        # default; no external cost
    PER_GUILD_QUOTA = "per_guild_quota"  # bounded by a per-guild counter (quota_ref)
    BUDGET_CAP = "budget_cap"            # bounded by a global spend cap (quota_ref)
    FAIL_CLOSED = "fail_closed"          # NO counter yet ⇒ boots DISABLED (the honest interim)


# CommandSpec facet fields (the Gate-0 facet is duck-typed by the compiler;
# the roles registration makes the fields real grammar NOW):
#   cost_posture: CostPosture = CostPosture.FREE   # [S] REQUIRED != FREE iff effect="external"
#   quota_ref: str = ""                            # [S] K1-reserved counter name
register_field_roles("CommandSpec", cost_posture="S", quota_ref="S")

_QUOTA_POSTURES = (CostPosture.PER_GUILD_QUOTA, CostPosture.BUDGET_CAP)


def check_command_cost_posture(spec: object) -> list[str]:
    """Phase-1 declaration-presence over ONE duck-typed command facet.
    Returns violations (empty = clean)."""
    problems: list[str] = []
    name = getattr(spec, "name", "<unnamed>")
    effect = getattr(spec, "effect", "read")
    raw = getattr(spec, "cost_posture", CostPosture.FREE)
    posture = CostPosture(raw) if not isinstance(raw, CostPosture) else raw
    quota_ref = getattr(spec, "quota_ref", "") or ""
    if effect == "external" and posture is CostPosture.FREE:
        problems.append(
            f"{name}: effect='external' with cost_posture=FREE — a paid/externally-"
            f"costed ref must declare PER_GUILD_QUOTA/BUDGET_CAP/FAIL_CLOSED")
    if posture in _QUOTA_POSTURES and not quota_ref:
        problems.append(
            f"{name}: cost_posture={posture.value} requires a non-empty quota_ref")
    if posture in (CostPosture.FREE, CostPosture.FAIL_CLOSED) and quota_ref:
        problems.append(
            f"{name}: quota_ref {quota_ref!r} is inert under cost_posture="
            f"{posture.value} (decorative data — bind it or drop it)")
    return problems
