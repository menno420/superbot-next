"""The ``DraftPipeline`` facade + error types (K9/S10 — frozen L0 spec 06
§3.6). Final Review, rung-4 AI orchestration, C-3 presets, and the
release-test flow are all THIN surfaces over this — none re-implements
staging, preview, gate, or apply.
"""

from __future__ import annotations

from sb.kernel.authority.decision import AuthorityRequest
from sb.kernel.draft.accept import derive_accept_authority, resolve_draft_accept
from sb.kernel.draft.apply import DraftApplyResult, apply_draft
from sb.kernel.draft.preview import (
    DraftPreview,
    PreviewContext,
    build_draft_preview,
    preview_hash_of,
)
from sb.kernel.draft.registry import OP_KINDS, OpKindRegistry
from sb.kernel.draft.store import DraftStore
from sb.kernel.interaction.request import ActorRef
from sb.kernel.scheduler.poll import SYSTEM_CLOCK
from sb.spec.draft import (
    AcceptHook,
    ConfirmationResponse,
    Draft,
    DraftOperation,
    DraftStatus,
    OwnerScope,
    Producer,
    TERMINAL_STATUSES,
    VerificationContext,
)

__all__ = [
    "AcceptDenied",
    "ConfirmDeclined",
    "DraftClosed",
    "DraftNotFound",
    "DraftPipeline",
    "StalePreview",
    "UndraftableOperation",
]


class UndraftableOperation(Exception):
    """No registered op-kind binding — FAIL-CLOSED at add (user_error)."""


class DraftNotFound(Exception):
    pass


class DraftClosed(Exception):
    """Mutate/apply a terminal draft (user_error)."""


class StalePreview(Exception):
    """preview_hash ≠ the draft's current — the op set changed (re-preview)."""


class AcceptDenied(Exception):
    """resolve_draft_accept denied a distinct ref (carries K6 copy)."""

    def __init__(self, denial_message: str | None) -> None:
        super().__init__(denial_message or "You can't apply this draft.")
        self.denial_message = denial_message


class ConfirmDeclined(Exception):
    """requires_confirmation and the challenge was unmet/mismatched."""


class DraftPipeline:
    def __init__(self, *, store: DraftStore | None = None,
                 registry: OpKindRegistry = OP_KINDS, clock=SYSTEM_CLOCK,
                 hook: AcceptHook | None = None) -> None:
        self.store = store or DraftStore(clock=clock)
        self.registry = registry
        self.clock = clock
        self.hook = hook

    async def create(self, *, producer: Producer, owner_scope: OwnerScope,
                     expires_in_s: int | None = None,
                     verification: VerificationContext | None = None) -> Draft:
        return await self.store.create(
            producer=producer, owner_scope=owner_scope,
            expires_in_s=expires_in_s, verification=verification)

    async def _load_open(self, draft_id: str) -> Draft:
        draft = await self.store.load(draft_id)
        if draft is None:
            raise DraftNotFound(draft_id)
        if draft.status in TERMINAL_STATUSES:
            raise DraftClosed(f"{draft_id} is {draft.status.value}")
        return draft

    async def add(self, draft_id: str, op: DraftOperation) -> Draft:
        if not self.registry.is_draftable(op.op_kind):
            raise UndraftableOperation(op.op_kind)   # fail-closed
        await self._load_open(draft_id)
        draft = await self.store.add(draft_id, op)
        # refresh the derived DISPLAY floor (never the gate).
        from sb.kernel.db.pool import execute, transaction
        async with transaction() as conn:
            await execute(
                "UPDATE sb_drafts SET accept_authority_ref=$2 WHERE draft_id=$1",
                (draft_id, derive_accept_authority(draft.operations)), conn=conn)
        return draft

    async def remove(self, draft_id: str, op_seq: int) -> Draft:
        await self._load_open(draft_id)
        draft = await self.store.remove(draft_id, op_seq)
        assert draft is not None
        return draft

    async def preview(self, draft_id: str, ctx: PreviewContext) -> DraftPreview:
        draft = await self._load_open(draft_id)
        result = await build_draft_preview(draft, ctx, registry=self.registry)
        await self.store.set_status(draft_id, DraftStatus.PREVIEWED)
        return result

    async def confirm_and_apply(self, draft_id: str, req: AuthorityRequest,
                                actor: ActorRef, *, preview_hash: str,
                                confirmation: ConfirmationResponse | None = None,
                                ) -> DraftApplyResult:
        """The fixed confirm→accept→hook→apply order (spec 06 §3.6)."""
        # 1. load; terminal ⇒ closed.
        draft = await self._load_open(draft_id)
        # 2. re-build the preview; a changed op set ⇒ StalePreview.
        current_hash = preview_hash_of(draft)
        if preview_hash != current_hash:
            raise StalePreview(f"expected {preview_hash}, current {current_hash}")
        pctx = PreviewContext(
            actor=actor, guild_id=draft.owner_scope.guild_id,
            member_tier=getattr(actor, "member_tier", None), clock=self.clock,
            test_mode=bool(draft.verification.test_mode)
            if draft.verification else False)
        preview = await build_draft_preview(draft, pctx, registry=self.registry)
        # 3. the accept gate — AND over every distinct ref.
        decision = await resolve_draft_accept(draft, req)
        if not decision.allowed:
            raise AcceptDenied(decision.denial_message)
        # 4. facade-level confirmation check (apply re-asserts fail-closed).
        if preview.requires_confirmation and not _verify(preview, confirmation):
            raise ConfirmDeclined(draft_id)
        # 5. the hook — authority + challenge passed, no op has run yet.
        if self.hook is not None:
            try:
                await self.hook.on_confirmed(draft, decision)
            except Exception:  # noqa: BLE001 — fail-open
                import logging
                logging.getLogger(__name__).warning(
                    "AcceptHook.on_confirmed failed", exc_info=True)
        # 6. apply.
        return await apply_draft(draft, decision, preview, confirmation,
                                 actor=actor, store=self.store,
                                 registry=self.registry, clock=self.clock,
                                 hook=self.hook)

    async def discard(self, draft_id: str) -> None:
        await self._load_open(draft_id)
        await self.store.discard(draft_id)


def _verify(preview: DraftPreview, confirmation: ConfirmationResponse | None) -> bool:
    from sb.kernel.draft.preview import verify_confirmation
    return verify_confirmation(preview.confirmation, confirmation)
