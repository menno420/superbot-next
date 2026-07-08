"""``resolve_authority`` — the runtime two-lane (+R-16 role-set) resolver
(K6, frozen L0 spec 04 §3.3). Owner-override computed ONCE at the top;
discord-free (consumes the pre-computed ``req.member_tier`` / ``req.role_ids``
— never dereferences a discord object).

Ports the shipped ``governance/capability.py`` step order field-for-field:
scripted bypass (:85) → target-guild membership gate (:98-113) → tier + lane
result (+ revoke overlay :157-171) → platform-owner override (:125, AFTER
membership so it composes with no-cross-guild-escalation, BEFORE the revoke
result so a guild cannot revoke the owner) → setup_delegate (Q-0098) → lane.

``allowed = scripted OR (member AND (owner_override OR (setup_delegate AND
not revoked) OR lane_allows))``.

The revoke overlay + role-binding reads go through installable read PORTS
(spec 04 §5: the engine is stateless, reads existing rows through the db
port). The governance/settings bands install the real readers at their port
bands; the defaults are "no overlay row" / "no binding configured".
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from sb.kernel.authority.decision import AuthorityDecision, AuthorityRequest
from sb.kernel.authority.owner import owner_override_holds
from sb.spec.authority import (
    ADMIN_FLOOR_TIER,
    Lane,
    classify_authority_ref,
    is_tier_sufficient,
    role_binding_name,
)
from sb.spec.outcomes import DenialReason

logger = logging.getLogger("sb.kernel.authority")

__all__ = [
    "install_capability_override_reader",
    "install_role_binding_reader",
    "reset_readers_for_tests",
    "resolve_authority",
]

# --- installable read ports (db-band consumers install the real readers) ----

# (guild_id, capability) -> True | False | None (None = no overlay row).
# An explicit False REVOKES; an explicit True never grants below-floor
# (no privilege escalation via a guild-config row — capability.py:157-171).
CapabilityOverrideReader = Callable[[int, str], Awaitable[bool | None]]

# (guild_id, binding_name) -> the guild's configured role-id set for a
# declared BindingKind.ROLE binding, or None when unconfigured (R-16).
RoleBindingReader = Callable[[int, str], Awaitable[frozenset[int] | None]]


async def _no_override(guild_id: int, capability: str) -> bool | None:
    return None


async def _no_role_binding(guild_id: int, binding_name: str) -> frozenset[int] | None:
    return None


_override_reader: CapabilityOverrideReader = _no_override
_role_binding_reader: RoleBindingReader = _no_role_binding


def install_capability_override_reader(reader: CapabilityOverrideReader) -> None:
    """Install the ``capability_execution_overrides`` read port (the shipped
    ``governance.execution.get_capability_override`` semantics)."""
    global _override_reader
    _override_reader = reader


def install_role_binding_reader(reader: RoleBindingReader) -> None:
    """Install the R-16 role-binding read port (binding name -> the guild's
    configured role-id set)."""
    global _role_binding_reader
    _role_binding_reader = reader


def reset_readers_for_tests() -> None:
    global _override_reader, _role_binding_reader
    _override_reader = _no_override
    _role_binding_reader = _no_role_binding


# --- the generic denial-copy table (v1, RC-14 — engine-generated) -----------

def _denial_message(lane: Lane, required_tier: str, *, revoked: bool,
                    non_member: bool) -> str:
    if non_member:
        return "You must be a member of this server to use this."
    if revoked:
        return "This action has been turned off for your role in this server."
    if lane is Lane.TIER:
        return f"You need the **{required_tier}** role (or higher) to use this."
    if lane is Lane.ROLE_SET:
        return "You need one of this server's configured roles to use this."
    return "You need administrator permission to use this."


async def resolve_authority(req: AuthorityRequest) -> AuthorityDecision:
    """The fixed internal order (spec 04 §3.3 — steps 0-6)."""
    # 0. classify — pure syntactic; touches nothing tier-dependent.
    lane = classify_authority_ref(req.authority_ref)
    required_tier = ADMIN_FLOOR_TIER if lane is Lane.CAPABILITY else (
        req.authority_ref if lane is Lane.TIER else ""
    )

    # 1. scripted bypass — never dereferences user_id/guild_id (capability.py:85).
    if req.actor_type in ("system", "backfill"):
        return AuthorityDecision(
            allowed=True, authority_ref=req.authority_ref, lane=lane,
            required_tier="", member_tier=None, owner_override=False,
            lane_would_deny=False, reason=DenialReason.ALLOWED,
            detail=f"{req.actor_type} actor bypasses the authority check",
            denial_message=None,
        )

    # 2. membership gate — owner is NOT exempt (member-guilds-only, X-7).
    if not req.is_member or req.guild_id is None:
        return AuthorityDecision(
            allowed=False, authority_ref=req.authority_ref, lane=lane,
            required_tier=required_tier, member_tier=None,
            owner_override=False, lane_would_deny=False,
            reason=DenialReason.AUTHORITY,
            detail=(
                "authority requires a guild-member actor in the target guild "
                f"(actor_type={req.actor_type!r})"
            ),
            denial_message=_denial_message(lane, required_tier,
                                           revoked=False, non_member=True),
        )

    # 3. compute tier + the pure lane result (UNCONDITIONAL on every member
    #    path — lane_would_deny "always populated", closes M6).
    member_tier = req.member_tier
    revoked = False
    if lane is Lane.TIER:
        lane_allows = is_tier_sufficient(member_tier or "", req.authority_ref)
    elif lane is Lane.ROLE_SET:
        # R-16: allow-set semantics — the actor holds >=1 role of the guild's
        # configured binding. Unconfigured binding => FAIL-CLOSED (the lane
        # must express deny-until-role / quarantine; A-14 is its first
        # consumer — a missing verification-role binding must not admit).
        binding = role_binding_name(req.authority_ref)
        try:
            bound = await _role_binding_reader(req.guild_id, binding)
        except Exception as exc:  # pragma: no cover - defensive (shipped posture)
            logger.debug("role-binding read failed (%s); treating unconfigured", exc)
            bound = None
        lane_allows = bool(bound) and bool(req.role_ids & bound)
    else:  # CAPABILITY — ADMIN floor; dotted refs also carry the revoke key.
        lane_allows = is_tier_sufficient(member_tier or "", ADMIN_FLOOR_TIER)
        if req.authority_ref:
            try:
                override = await _override_reader(req.guild_id, req.authority_ref)
            except Exception as exc:  # pragma: no cover - defensive (capability.py)
                logger.debug("capability override read failed (%s); ignoring", exc)
                override = None
            if override is False:
                lane_allows = False
                revoked = True
    lane_would_deny = not lane_allows

    # 4. owner-override — ONCE, at the top of the allow computation; before
    #    the revoke result decides the final allow (a guild cannot revoke the
    #    owner), after membership (step 2 gated it already).
    owner_override = owner_override_holds(req.user_id, req.is_member)

    # 5-6. setup_delegate (floor-satisfying, still revoke-subject) | lane.
    if owner_override:
        allowed = True
    elif req.actor_type == "setup_delegate":
        allowed = not revoked
    else:
        allowed = lane_allows

    if allowed:
        if owner_override:
            detail = (
                f"platform owner {req.user_id!r} override for "
                f"authority_ref={req.authority_ref or '(default)'!r}"
            )
        elif req.actor_type == "setup_delegate":
            detail = (
                f"delegated setup admin {req.user_id!r} (tier={member_tier!r}) "
                f"authorized for {req.authority_ref or '(default)'!r} via "
                "setup-delegate apply authority (Q-0098)"
            )
        else:
            detail = (
                f"member {req.user_id!r} (tier={member_tier!r}) authorized "
                f"for {req.authority_ref or '(default)'!r}"
            )
        reason = DenialReason.ALLOWED
        denial_message = None
    else:
        if req.actor_type == "setup_delegate":
            detail = (
                f"delegated setup admin {req.user_id!r} (tier={member_tier!r}) "
                f"REVOKED for {req.authority_ref or '(default)'!r}"
            )
        elif lane is Lane.ROLE_SET:
            detail = (
                f"member {req.user_id!r} holds no role of binding "
                f"{role_binding_name(req.authority_ref)!r} (role_not_held)"
            )
        else:
            detail = (
                f"member {req.user_id!r} (tier={member_tier!r}) requires at "
                f"least {required_tier or ADMIN_FLOOR_TIER!r} for "
                f"{req.authority_ref or '(default)'!r}"
            )
        reason = DenialReason.AUTHORITY
        denial_message = _denial_message(lane, required_tier,
                                         revoked=revoked, non_member=False)

    return AuthorityDecision(
        allowed=allowed, authority_ref=req.authority_ref, lane=lane,
        required_tier=required_tier, member_tier=member_tier,
        owner_override=owner_override, lane_would_deny=lane_would_deny,
        reason=reason, detail=detail, denial_message=denial_message,
    )
