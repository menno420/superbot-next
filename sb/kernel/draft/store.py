"""The domain draft store over the DB primitive (K9/S10 — frozen L0 spec 06
§2). Owns transactions for staging writes; reads pass through. Status
WRITES beyond staging (EXPIRED, stuck-APPLYING→PARTIAL) belong to the
janitor lane; APPLYING/APPLIED/PARTIAL transitions belong to apply.py.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sb.kernel.db import draft as db
from sb.kernel.db.pool import transaction
from sb.kernel.scheduler.poll import SYSTEM_CLOCK
from sb.spec.draft import (
    Draft,
    DraftOperation,
    DraftStatus,
    OwnerScope,
    Producer,
    VerificationContext,
)

__all__ = ["DraftStore"]


class DraftStore:
    def __init__(self, *, clock=SYSTEM_CLOCK) -> None:
        self.clock = clock

    async def create(self, *, producer: Producer, owner_scope: OwnerScope,
                     expires_in_s: int | None = None,
                     verification: VerificationContext | None = None,
                     accept_authority_ref: str = "") -> Draft:
        now = self.clock()
        draft_id = str(uuid.uuid4())
        draft = Draft(
            draft_id=draft_id, producer=producer, owner_scope=owner_scope,
            status=DraftStatus.OPEN, operations=(), created_at=now,
            updated_at=now,
            expires_at=(now + timedelta(seconds=expires_in_s)
                        if expires_in_s else None),
            accept_authority_ref=accept_authority_ref,
            correlation_id=draft_id, verification=verification)
        async with transaction() as conn:
            await db.insert_draft(draft, conn=conn)
        return draft

    async def add(self, draft_id: str, op: DraftOperation) -> Draft:
        async with transaction() as conn:
            op_seq = await db.append_operation(draft_id, op, conn=conn)
            if not op.dedup_token:
                # default the ④.2 token in place: f"{draft_id}:{op_seq}"
                from sb.kernel.db.pool import execute
                await execute(
                    "UPDATE sb_draft_operations SET dedup_token=$3"
                    " WHERE draft_id=$1 AND op_seq=$2",
                    (draft_id, op_seq, f"{draft_id}:{op_seq}"), conn=conn)
        loaded = await self.load(draft_id)
        assert loaded is not None
        return loaded

    async def remove(self, draft_id: str, op_seq: int) -> Draft | None:
        async with transaction() as conn:
            await db.delete_operation(draft_id, op_seq, conn=conn)
        return await self.load(draft_id)

    async def load(self, draft_id: str) -> Draft | None:
        return await db.load_draft(draft_id)

    async def list_open(self, scope: OwnerScope) -> tuple[Draft, ...]:
        return await db.list_open_drafts(scope)

    async def set_status(self, draft_id: str, status: DraftStatus, *,
                         expect: DraftStatus | None = None) -> bool:
        async with transaction() as conn:
            return await db.update_status(draft_id, status, conn=conn, expect=expect)

    async def discard(self, draft_id: str) -> None:
        async with transaction() as conn:
            await db.delete_draft(draft_id, conn=conn)

    async def select_expired(self, now) -> tuple[str, ...]:
        return await db.select_expired(now)
