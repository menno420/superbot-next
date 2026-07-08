"""The dispatch `Result` + the ephemerality resolver (frozen L0 spec 02
§3.4/§3.6, T2-17). `DenialReason`/`ErrorClass`/`ReplyVisibility` live in the
`sb.spec.outcomes` leaf (RC-6 — 02's inline copies were illustrative);
`lane_default` uses 04's canonical `Lane` (RC-3 — `CAPABILITY` ≡ 02's
CONFIG_GOVERNANCE ⇒ EPHEMERAL, `TIER`/`ROLE_SET` domain-facing ⇒ PUBLIC for
TIER; ROLE_SET follows CAPABILITY's EPHEMERAL posture, a guild-config gate).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sb.spec.authority import Lane
from sb.spec.outcomes import (
    DISCORD_FAILED,
    PARTIAL,
    SUCCESS,
    DenialReason,
    ErrorClass,
    ReplyVisibility,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.interaction.request import Surface
    from sb.kernel.workflow.result import WorkflowResult

__all__ = ["Result", "lane_default", "resolve_reply_visibility"]


@dataclass(frozen=True)
class Result:
    outcome: str                       # §2.7 frozen vocab ONLY — no 6th constant
    reason: DenialReason               # ALLOWED on success
    error_class: ErrorClass            # NONE on success
    retryable: bool
    reply_visibility: ReplyVisibility  # resolved below
    user_message: str | None           # None = silent
    surface: "Surface"
    workflow: "WorkflowResult | None"  # None for OPEN_PANEL / confirm-pending
    audit_emitted: bool                # dispatch-trace emitted (publish-accepted)
    request_id: str


_PRE_DISPATCH_DENIALS = frozenset({
    DenialReason.AUTHORITY, DenialReason.DISABLED, DenialReason.VISIBILITY,
    DenialReason.CHANNEL, DenialReason.USER_ERROR, DenialReason.COOLDOWN,
    DenialReason.AI_THROTTLE, DenialReason.NOT_FOUND,
})


def lane_default(lane: Lane) -> ReplyVisibility:
    """RC-3: EPHEMERAL iff the lane is a config/governance gate."""
    return (ReplyVisibility.PUBLIC if lane is Lane.TIER
            else ReplyVisibility.EPHEMERAL)


def resolve_reply_visibility(*, outcome: str, reason: DenialReason,
                             lane: Lane, declared: ReplyVisibility | None,
                             committed: ReplyVisibility | None) -> ReplyVisibility:
    """Complete over all five §2.7 outcomes, ONE place (02 §3.4 verbatim)."""
    if committed is not None:            # a defer froze the flag — Discord binds it
        return committed
    if reason is DenialReason.DRAINING:
        return ReplyVisibility.SILENT
    if reason in _PRE_DISPATCH_DENIALS:
        return ReplyVisibility.EPHEMERAL
    if outcome in (SUCCESS, PARTIAL):
        return declared or lane_default(lane)
    _ = DISCORD_FAILED                    # documentation anchor
    return ReplyVisibility.EPHEMERAL      # DISCORD_FAILED / bug / DECLINED, uncommitted
