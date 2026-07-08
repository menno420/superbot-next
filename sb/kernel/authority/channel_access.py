"""The folded-in channel-access lane (K6, spec 04 §3.4 — RC-4/RC-13, L-12).

Ports the shipped ``core/runtime/command_access.py`` resolver MINUS its
lifecycle/DM legs (those are K5 admission — spec 02 step 0) and PLUS the
owner-override fix: the once-computed ``owner_override`` (member-gated,
threaded from ``AuthorityDecision``) lets a member owner bypass ANY command's
channel restriction — not just bootstrap commands (the ``:351`` fix).

``AccessMode`` keeps the SHIPPED, name-stable value strings verbatim
(command_access.py:184-186 — "mirrors the DB CHECK constraint"), so
``AccessMode(snapshot.mode)`` on a stored value resolves with no migration.

A-12/R-16 leg 2: the policy gains an OPTIONAL per-channel role-set constraint
— NOT a 4th AccessMode (the three shipped strings stay verbatim; usable under
``ALL_CHANNELS``). A channel with a configured role-set admits only actors
holding one of those roles (detail token ``role_not_held``); owner-override
and the bootstrap bypass short-circuit above it, per the fixed order.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from sb.kernel.authority.decision import ChannelAccessDecision
from sb.spec.outcomes import DenialReason

__all__ = [
    "AccessMode",
    "CommandAccessSnapshot",
    "resolve_channel_access",
]


class AccessMode(enum.Enum):
    """Per-guild command-access modes — shipped values VERBATIM
    (command_access.py:184-186; mirrors the DB CHECK constraint)."""

    ALL_CHANNELS = "all_channels"
    SELECTED_CHANNELS = "selected_channels"
    DISABLED_EXCEPT_BOOTSTRAP = "disabled_except_bootstrap"


@dataclass(frozen=True)
class CommandAccessSnapshot:
    """The cached per-guild command-access policy the caller reads through
    the db/settings port and passes in (the engine is stateless — spec 04
    §5). ``mode=None`` = no policy row (safe default: allow).

    ``channel_role_sets`` is the R-16 optional per-channel role-set
    constraint: channel_id -> the frozenset of role ids allowed to run
    commands there (absent channel = unconstrained).
    """

    mode: str | None = None
    allowed_channels: frozenset[int] = field(default_factory=frozenset)
    channel_role_sets: Mapping[int, frozenset[int]] = field(
        default_factory=lambda: MappingProxyType({})
    )


# Ported user copy, verbatim (command_access.py _FEEDBACK_*).
_FEEDBACK_COMMANDS_DISABLED = (
    "Commands are disabled in this server. "
    "Ask a server admin to enable them via `!setup` or the "
    "Command Access settings panel."
)
_FEEDBACK_CHANNEL_NOT_ALLOWED = (
    "Commands aren't enabled in this channel. "
    "Use one of the configured command channels or ask an admin to "
    "update Command Access in `!settings`."
)
# R-16 generic copy (engine-generated, RC-14 posture).
_FEEDBACK_ROLE_NOT_HELD = (
    "Commands in this channel are limited to specific roles. "
    "Ask an admin to update Command Access in `!settings`."
)


def _policy_verdict(
    policy: CommandAccessSnapshot | None,
    channel_id: int | None,
    actor_role_ids: frozenset[int],
) -> tuple[bool, AccessMode | None, str, str | None]:
    """Steps 3-4 (+ the R-16 role-set constraint): the pure policy legs.
    Returns (allowed, mode, detail, denial_message)."""
    mode = AccessMode(policy.mode) if policy is not None and policy.mode is not None else None

    if mode is AccessMode.DISABLED_EXCEPT_BOOTSTRAP:
        return False, mode, "commands_disabled", _FEEDBACK_COMMANDS_DISABLED

    if mode is AccessMode.SELECTED_CHANNELS:
        if channel_id is None or channel_id not in policy.allowed_channels:
            return False, mode, "channel_not_allowed", _FEEDBACK_CHANNEL_NOT_ALLOWED

    # mode is None (unconfigured default-allow) or ALL_CHANNELS, or a
    # SELECTED_CHANNELS hit — apply the R-16 per-channel role-set constraint.
    if policy is not None and channel_id is not None:
        role_set = policy.channel_role_sets.get(channel_id)
        if role_set and not (actor_role_ids & role_set):
            return False, mode, "role_not_held", _FEEDBACK_ROLE_NOT_HELD

    return True, mode, "", None


async def resolve_channel_access(
    policy: CommandAccessSnapshot | None,
    channel_id: int | None,
    *,
    owner_override: bool,
    is_bootstrap: bool,
    is_operator: bool,
    is_owner: bool,
    actor_role_ids: frozenset[int] = frozenset(),
) -> ChannelAccessDecision:
    """The folded-in channel lane (spec 04 §3.4, fixed order):

    1. ``owner_override`` (member-gated, computed ONCE at resolve_authority
       step 4) ⇒ ALLOW for ANY command — the L-12 fix (was bootstrap-only at
       command_access.py:351); ``would_deny_without_override`` = what the
       policy legs would have returned.
    2. bootstrap bypass, shipped verbatim: ``is_bootstrap AND (is_operator OR
       is_owner)`` ⇒ ALLOW. ``is_owner`` = ``actor.is_bot_owner``
       (membership-blind, preserved verbatim; narrowed in the composed order
       because a non-member owner already denied at authority step 2);
       ``is_operator`` = ``actor.is_guild_operator`` — the leg that stays
       live. ``is_bootstrap`` = K1's ``is_bootstrap_command(target.key)``,
       computed by the CALLER (a registry property, consumed here).
    3. ``mode None | ALL_CHANNELS`` ⇒ ALLOW; 4. ``DISABLED_EXCEPT_BOOTSTRAP``
       ⇒ DENY (detail ``commands_disabled``); ``SELECTED_CHANNELS`` miss ⇒
       DENY (detail ``channel_not_allowed``); R-16 per-channel role-set miss
       ⇒ DENY (detail ``role_not_held``). All ``reason=CHANNEL`` (RC-13).
    """
    base_allowed, mode, detail, message = _policy_verdict(
        policy, channel_id, actor_role_ids,
    )

    if owner_override:
        return ChannelAccessDecision(
            allowed=True, mode=mode, reason=DenialReason.ALLOWED, detail="",
            owner_override=True, bootstrap_bypass=False,
            would_deny_without_override=not base_allowed, denial_message=None,
        )

    if is_bootstrap and (is_operator or is_owner):
        return ChannelAccessDecision(
            allowed=True, mode=mode, reason=DenialReason.ALLOWED, detail="",
            owner_override=False, bootstrap_bypass=True,
            would_deny_without_override=not base_allowed, denial_message=None,
        )

    if base_allowed:
        return ChannelAccessDecision(
            allowed=True, mode=mode, reason=DenialReason.ALLOWED, detail="",
            owner_override=False, bootstrap_bypass=False,
            would_deny_without_override=False, denial_message=None,
        )

    return ChannelAccessDecision(
        allowed=False, mode=mode, reason=DenialReason.CHANNEL, detail=detail,
        owner_override=False, bootstrap_bypass=False,
        would_deny_without_override=True, denial_message=message,
    )
