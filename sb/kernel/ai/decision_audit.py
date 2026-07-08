"""Persistent AI decision audit (K10) — the single chokepoint. Ported from
shipped ``disbot/services/ai_decision_audit_service.py``.

Every NL-engine invocation produces exactly one ``ai_decision_audit`` row
via :func:`record` — denial, skip, reply, degrade, error. Diagnostics read
through :func:`query`. No raw message content is stored.

DB faults are contained here (never raised to the reply path): a failed
audit write logs loudly and returns ``None`` — the reply must not die on a
diagnostics row, but the miss is never silent.
"""

from __future__ import annotations

import logging
from typing import Any

from sb.kernel.ai.contracts import PolicyDenialReason

__all__ = ["VALID_DECISIONS", "query", "record"]

logger = logging.getLogger("sb.kernel.ai.decision_audit")

VALID_DECISIONS = frozenset(
    {"allowed", "denied", "skipped", "replied", "degraded", "errored"},
)


async def record(
    *,
    guild_id: int,
    channel_id: int,
    category_id: int | None,
    user_id: int,
    message_id: int | None,
    task: str | None,
    route: str | None,
    decision: str,
    reason_code: PolicyDenialReason | str,
    policy_snapshot_hash: str | None = None,
    instruction_profile_ids: list[int] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> int | None:
    """Write one row; returns the new id (None on a contained DB fault).

    Raises ``ValueError`` for unknown ``decision`` values so a typo
    surfaces at the call site rather than corrupting the audit table.
    """
    if decision not in VALID_DECISIONS:
        raise ValueError(
            f"decision must be one of {sorted(VALID_DECISIONS)}, got {decision!r}",
        )
    reason_value = (
        reason_code.value
        if isinstance(reason_code, PolicyDenialReason)
        else str(reason_code)
    )
    # Success rows always carry the sentinel reason_code='none'.
    if decision in ("allowed", "replied") and reason_value != "none":
        reason_value = "none"

    from sb.kernel.db import ai_audit

    try:
        return await ai_audit.insert_decision(
            guild_id=guild_id,
            channel_id=channel_id,
            category_id=category_id,
            user_id=user_id,
            message_id=message_id,
            task=task,
            route=route,
            decision=decision,
            reason_code=reason_value,
            policy_snapshot_hash=policy_snapshot_hash,
            instruction_profile_ids=instruction_profile_ids,
            provider=provider,
            model=model,
        )
    except Exception:  # noqa: BLE001 — the reply path never dies on the audit row
        logger.warning(
            "ai decision audit write failed (guild=%s decision=%s reason=%s)",
            guild_id,
            decision,
            reason_value,
            exc_info=True,
        )
        return None


async def query(
    guild_id: int,
    *,
    channel_id: int | None = None,
    user_id: int | None = None,
    decision: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    from sb.kernel.db import ai_audit

    return await ai_audit.query_decisions(
        guild_id,
        channel_id=channel_id,
        user_id=user_id,
        decision=decision,
        limit=limit,
    )
