"""``ExpiryJanitorLane`` (K9/S10) — the draft-expiry + stuck-APPLYING sweep,
HOSTED on 09's one ``PollSupervisor`` (spec 06 §3.3/§6; spec 09 §4 hosts it).

The OPEN/PREVIEWED → EXPIRED transition is a WRITE owned HERE (never lazily
at load — a read primitive must not mutate). The stuck-APPLYING reap is the
strictly-conditional CAS in the DB primitive; this lane owns only the
cadence.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sb.kernel.db import draft as draft_db
from sb.kernel.db.pool import transaction
from sb.kernel.draft.apply import DRAFT_APPLY_STUCK_TTL_S
from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.scheduler.poll import LaneTickResult

logger = logging.getLogger("sb.kernel.draft.janitor")

__all__ = ["ExpiryJanitorLane"]


class ExpiryJanitorLane:
    name = "draft_janitor"

    def __init__(self, *, stuck_ttl_s: int = DRAFT_APPLY_STUCK_TTL_S) -> None:
        self.stuck_ttl_s = stuck_ttl_s

    async def tick(self, now: datetime) -> LaneTickResult:
        expired = 0
        async with transaction() as conn:
            for draft_id in await draft_db.select_expired(now, conn=conn):
                from sb.spec.draft import DraftStatus
                if await draft_db.update_status(draft_id, DraftStatus.EXPIRED,
                                                conn=conn):
                    expired += 1
            reaped = await draft_db.reap_stuck_applying(
                now, self.stuck_ttl_s, conn=conn)
        for draft_id in reaped:
            record_operator_finding(
                source="draft_janitor", severity="warning",
                summary=f"stuck APPLYING draft reaped to PARTIAL: {draft_id}",
                detail=f"no per-op heartbeat for {self.stuck_ttl_s}s — "
                       f"recovery re-run is idempotent (per-op once())",
                correlation_id=draft_id)
        return LaneTickResult(lane=self.name, claimed=expired + len(reaped),
                              fired=expired, failed=len(reaped), skipped=0)

    async def reconcile_on_boot(self, now: datetime) -> None:
        """No auto-apply on boot — drafts are user-initiated. The first
        tick handles expiry/reaping; nothing else to reconcile."""
        return None
