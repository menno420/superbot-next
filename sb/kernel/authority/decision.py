"""The K6 decision dataclasses (frozen L0 spec 04 §3.3/§3.4/§3.5 —
RC-2/RC-12/RC-13). All runtime-request and decision fields carry no S/A/O
role tag (not authored, not simulated); the sole manifest [S] field this
engine reads is ``authority_ref`` (RC-14: ``denial_message`` is
engine-generated generic copy, never a spec field).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sb.spec.authority import Lane
from sb.spec.outcomes import DenialReason

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.authority.channel_access import AccessMode

__all__ = [
    "AuthorityDecision",
    "AuthorityRequest",
    "CapabilityDecision",
    "ChannelAccessDecision",
    "TransparencyAudit",
]


@dataclass(frozen=True)
class AuthorityRequest:
    """The discord-free resolver input (spec 04 §3.3, frozen-l0 row 24).

    ``member_tier`` arrives PRE-COMPUTED by the surface adapter (RC-12 —
    never a ``discord.Member``); ``role_ids`` likewise (A-12/R-16: the
    adapter derives them fresh per interaction, so interaction-time re-check
    is structural). ``is_member`` is asserted by the caller (adapter:
    ``guild_id is not None and not actor.is_dm``; K7 cross-guild: real
    check). Defaulted fields trail so the non-default field keeps position.
    """

    authority_ref: str                    # [S] from target.spec
    actor_type: str = "user"              # user | system | backfill | setup_delegate
    user_id: int | None = None            # None for scripted actors
    guild_id: int | None = None           # the TARGET guild (the write target)
    is_member: bool = False               # member of the TARGET guild
    member_tier: str | None = None        # pre-computed tier; None scripted/non-member
    role_ids: frozenset[int] = field(default_factory=frozenset)  # R-16 (A-12)


@dataclass(frozen=True)
class AuthorityDecision:
    """THE frozen 10-field shape (spec 04 §3.3, frozen-l0 row 23, RC-2 —
    spec 02/K8 imports this and DERIVES ``override_applied = owner_override
    AND lane_would_deny`` / ``base_allowed = not lane_would_deny``)."""

    allowed: bool
    authority_ref: str
    lane: Lane                        # CAPABILITY | TIER | ROLE_SET (R-16)
    required_tier: str                # "administrator" (capability) | tier token | "" (role_set/scripted)
    member_tier: str | None           # resolved tier; None scripted-bypass / non-member
    owner_override: bool              # the ONCE-computed verdict — threaded to channel-access
    lane_would_deny: bool             # unconditional on every member path (transparency input)
    reason: DenialReason              # ALLOWED on allow; AUTHORITY on deny
    detail: str                       # ported rich audit reason (capability.py:174-193)
    denial_message: str | None        # engine-generated generic copy (RC-14); None on allow


@dataclass(frozen=True)
class CapabilityDecision:
    """Ported FIELD-FOR-FIELD from the shipped governance/capability.py —
    kept name-stable for the port bands' mutation pipelines; the composed
    path returns ``AuthorityDecision`` (this is the lane-local shape)."""

    allowed: bool
    capability: str
    required_tier: str
    member_tier: str | None
    reason: str


@dataclass(frozen=True)
class ChannelAccessDecision:
    """The 8-field folded-in channel lane result (spec 04 §3.4, frozen-l0
    row 25 — RC-13: ``detail`` disambiguates the two ``reason=CHANNEL``
    denials; R-16 adds the ``role_not_held`` detail token)."""

    allowed: bool
    mode: "AccessMode | None"             # None = unconfigured (default-allow)
    reason: DenialReason                  # ALLOWED | CHANNEL
    detail: str                           # "" | "commands_disabled" | "channel_not_allowed" | "role_not_held"
    owner_override: bool                  # short-circuited by the once-computed override
    bootstrap_bypass: bool                # shipped operator/owner bootstrap path
    would_deny_without_override: bool     # transparency input
    denial_message: str | None


@dataclass(frozen=True)
class TransparencyAudit:
    """The owner-override transparency payload (spec 04 §3.5, RC-5/RC-15).
    ``actor_id`` is a BUILD parameter (the resolver passes
    ``req.actor.user_id``), never an ``AuthorityDecision`` field."""

    actor_id: int                     # the platform owner
    guild_id: int
    authority_ref: str
    target_key: str                   # command name | "<panel_id>.<action_id>"
    surface: str                      # interaction Surface value
    would_deny_reason: DenialReason   # AUTHORITY (lane) | CHANNEL (channel-access)
    timestamp: datetime
