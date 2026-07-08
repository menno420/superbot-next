"""K6 — the authority engine (frozen L0 spec 04).

The ONE place authority resolves: ``resolve_authority`` (two-lane + R-16
role-set resolver, owner-override-once-at-top), the folded-in channel-access
lane (``resolve_channel_access``), the single owner predicate
(``owner_override_holds``), and the owner-override transparency contract
(``build_transparency_audit`` + the ``TransparencySink`` port).

Discord-free by design (spec 04 hardening pass): the ``Member``→tier read is
pre-computed by the K8 surface adapter and arrives on
``AuthorityRequest.member_tier``; role ids likewise (R-16). Imports ``spec``,
``namespace``, ``observability`` and the ports it defines — never ``domain``,
``manifest``, ``kernel/interaction``, or adapter internals.
"""

from sb.kernel.authority.channel_access import (
    AccessMode,
    CommandAccessSnapshot,
    resolve_channel_access,
)
from sb.kernel.authority.decision import (
    AuthorityDecision,
    AuthorityRequest,
    CapabilityDecision,
    ChannelAccessDecision,
    TransparencyAudit,
)
from sb.kernel.authority.owner import is_platform_owner, owner_override_holds
from sb.kernel.authority.resolve import resolve_authority
from sb.kernel.authority.transparency import TransparencySink, build_transparency_audit

__all__ = [
    "AccessMode",
    "AuthorityDecision",
    "AuthorityRequest",
    "CapabilityDecision",
    "ChannelAccessDecision",
    "CommandAccessSnapshot",
    "TransparencyAudit",
    "TransparencySink",
    "build_transparency_audit",
    "is_platform_owner",
    "owner_override_holds",
    "resolve_authority",
    "resolve_channel_access",
]
