"""The owner-override transparency contract (K6, spec 04 §3.5 — RC-5/RC-15).

A ``TransparencyAudit`` is NOT a mutation: it never routes through the
11-field ``emit_audit_action`` mutation seam (it cannot supply
``mutation_id``/``mutation_type``/``prev_value``/``new_value``). Its two
designed carriers are (1) the ``TransparencySink`` port (this module) — the
K8 resolver calls ``build_transparency_audit(...)`` at its step 4 and, when
non-``None``, ``sink.emit(audit)``; and (2) the ``override_applied`` /
``base_allowed`` flags the resolver derives onto the ``command.dispatched``
observability trace (spec 02 §3.5).

Sink policy (owner-gated §8-c; v1 built default = operator-notice only, no
durable row): dual bot-log + server-log; no-log-channel fallback = bot-log +
batched owner-DM digest. The concrete Discord sink
(``sb/adapters/discord/transparency_sink.py``) lands with the logging band
(spec 04 §9 deferral); ``LoggingTransparencySink`` is the in-repo default so
the seam is live from S7.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Protocol, runtime_checkable

from sb.kernel.authority.decision import (
    AuthorityDecision,
    ChannelAccessDecision,
    TransparencyAudit,
)
from sb.spec.outcomes import DenialReason

logger = logging.getLogger("sb.kernel.authority.transparency")

__all__ = [
    "LoggingTransparencySink",
    "TransparencySink",
    "build_transparency_audit",
]


@runtime_checkable
class TransparencySink(Protocol):
    """The transparency emit PORT (spec 04 §2/§3.5 — defined by the kernel,
    implemented in adapters; the DM digest is batched, hence flush)."""

    async def emit(self, audit: TransparencyAudit) -> None: ...
    async def flush_digest(self) -> None: ...


class LoggingTransparencySink:
    """v1 in-repo sink: structured log line (the bot-log carrier until the
    Discord adapter lands at the logging band)."""

    async def emit(self, audit: TransparencyAudit) -> None:
        logger.warning(
            "owner-override transparency: actor=%s guild=%s ref=%r target=%r "
            "surface=%s would_deny=%s at=%s",
            audit.actor_id, audit.guild_id, audit.authority_ref,
            audit.target_key, audit.surface, audit.would_deny_reason.value,
            audit.timestamp.isoformat(),
        )

    async def flush_digest(self) -> None:  # nothing batched in the log sink
        return None


def build_transparency_audit(
    auth: AuthorityDecision,
    channel: ChannelAccessDecision | None,
    *,
    actor_id: int,
    guild_id: int,
    target_key: str,
    surface: str,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> TransparencyAudit | None:
    """The trigger predicate + payload build (spec 04 §3.5, RC-5).

    Trigger = would-not-otherwise-authorize:
    ``auth.owner_override AND (auth.lane_would_deny OR (channel is not None
    AND channel.would_deny_without_override))``. Returns ``None`` when the
    owner would have been authorized anyway (no audit noise). A
    setup_delegate has ``owner_override=False`` so it never fires (correct —
    a delegate is not the owner).
    """
    if not auth.owner_override:
        return None
    channel_would_deny = channel is not None and channel.would_deny_without_override
    if not (auth.lane_would_deny or channel_would_deny):
        return None
    return TransparencyAudit(
        actor_id=actor_id,
        guild_id=guild_id,
        authority_ref=auth.authority_ref,
        target_key=target_key,
        surface=surface,
        would_deny_reason=(
            DenialReason.AUTHORITY if auth.lane_would_deny else DenialReason.CHANNEL
        ),
        timestamp=clock(),
    )
