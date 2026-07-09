"""Cleanup policy resolution (band 5) — disbot/governance/cleanup.py
verbatim: scope fallback channel > category > guild (cleanup_policies
supports neither role nor thread scope — RC-5); no override row = the
compat default (delete invalid commands after 5s; exempt a channel by
setting its policy to Off — the old hardcoded whitelist stays removed).
"""

from __future__ import annotations

from sb.domain.governance import store
from sb.domain.governance.models import (
    CleanupPolicy,
    GovernanceContext,
    PolicySource,
)
from sb.domain.governance.resolver import build_scope_chain

__all__ = ["resolve_cleanup_policy"]

_SOURCE_MAP = {
    "channel": PolicySource.CHANNEL_OVERRIDE,
    "category": PolicySource.CATEGORY_OVERRIDE,
    "guild": PolicySource.GUILD_OVERRIDE,
}


async def resolve_cleanup_policy(ctx: GovernanceContext) -> CleanupPolicy:
    """Resolve cleanup behavior for this context."""
    chain = build_scope_chain(ctx)
    for scope_type, scope_id in chain:
        if scope_type in ("role", "thread"):
            continue
        row = await store.get_cleanup_policy(ctx.guild_id, scope_type, scope_id)
        if row is not None:
            return CleanupPolicy(
                delete_message=row["delete_invalid_commands"],
                delete_after_seconds=row["delete_after_seconds"],
                send_feedback=True,
                resolved_from=_SOURCE_MAP.get(
                    scope_type, PolicySource.GUILD_OVERRIDE))
    return CleanupPolicy(
        delete_message=True, delete_after_seconds=5, send_feedback=True,
        resolved_from=PolicySource.FALLBACK_DEFAULT)
