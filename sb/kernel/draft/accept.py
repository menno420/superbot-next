"""Derived accept authority — mixed-draft-safe (K9/S10 — frozen L0 spec 06
§3.4). THE GATE is an AND over every DISTINCT op ``authority_ref``; the
derived single ref is a DISPLAY/list floor ONLY (a union-max collapse would
strip a capability op's revoke overlay in a mixed draft — a revoked role
could Accept a setup-containing draft).
"""

from __future__ import annotations

from sb.kernel.authority.decision import AuthorityDecision, AuthorityRequest
from sb.kernel.authority.resolve import resolve_authority
from sb.spec.authority import ADMIN_FLOOR_TIER, Lane, TIERS, classify_authority_ref
from sb.spec.draft import Draft, DraftOperation

__all__ = ["derive_accept_authority", "resolve_draft_accept"]

_TIER_RANK = {t: i for i, t in enumerate(TIERS)}


def _tier_floor(ref: str) -> str:
    """TIER lane → the tier itself; CAPABILITY (dotted or empty) → the
    admin floor; ROLE_SET → the admin floor for display purposes."""
    lane = classify_authority_ref(ref)
    if lane is Lane.TIER:
        return ref
    return ADMIN_FLOOR_TIER


def derive_accept_authority(operations: tuple[DraftOperation, ...]) -> str:
    """DISPLAY/LIST FLOOR ONLY (Draft.accept_authority_ref)."""
    refs = {op.authority_ref for op in operations}
    if not refs:
        return ""
    lanes = {classify_authority_ref(r) for r in refs}
    if lanes == {Lane.CAPABILITY} and len(refs) == 1:
        return next(iter(refs))         # the homogeneous common case
    floors = sorted((_tier_floor(r) for r in refs),
                    key=lambda t: _TIER_RANK.get(t, 0))
    return floors[-1]                    # max floor


async def resolve_draft_accept(draft: Draft, req: AuthorityRequest,
                               *, resolver=resolve_authority) -> AuthorityDecision:
    """THE GATE (fail-closed): resolve the actor against EVERY distinct op
    ref; the first denial wins. owner_override_holds (member-gated) is
    computed per ref inside resolve_authority — a member-gated bot-owner
    passes every ref uniformly (Q-0227)."""
    refs = sorted({op.authority_ref for op in draft.operations})
    decision: AuthorityDecision | None = None
    for ref in refs:
        decision = await resolver(AuthorityRequest(
            authority_ref=ref, actor_type=req.actor_type, user_id=req.user_id,
            guild_id=req.guild_id, is_member=req.is_member,
            member_tier=req.member_tier, role_ids=req.role_ids))
        if not decision.allowed:
            return decision              # first denial wins → AcceptDenied
    if decision is None:
        # an empty draft: gate on the request's own ref ("" ⇒ admin floor).
        decision = await resolver(req)
    return decision
