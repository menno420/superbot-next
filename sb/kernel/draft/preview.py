"""Batch preview / confirmation shapes over K7's single-op ``preview()``
(K9/S10 — frozen L0 spec 06 §3.3). The preview provider IS the op's K7
engine preview — no separate provider registry exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from sb.kernel.draft.registry import OpKindRegistry
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.context import WorkflowContext
from sb.kernel.workflow.result import (
    COMPENSATABLE,
    IRREVERSIBLE,
    REVERSIBILITY_ORDER,
    REVERSIBLE,
    MutationPreview,
)
from sb.spec.draft import (
    AI_PRODUCERS,
    ConfirmChallenge,
    ConfirmationResponse,
    Draft,
)
from sb.spec.outcomes import DenialReason

__all__ = [
    "DraftConfirmationSpec",
    "DraftPreview",
    "PreviewBlock",
    "PreviewContext",
    "build_draft_preview",
    "preview_hash_of",
    "requires_confirmation",
    "verify_confirmation",
]


@dataclass(frozen=True)
class PreviewContext:
    actor: object                 # ActorRef (carries member_tier, RC-12)
    guild_id: int
    member_tier: str | None = None
    clock: object = None
    test_mode: bool = False


@dataclass(frozen=True)
class PreviewBlock:
    op_seq: int
    reason: DenialReason          # NOT_FOUND (un-draftable) | USER_ERROR | …
    detail: str


@dataclass(frozen=True)
class DraftConfirmationSpec:
    """§2.7 ConfirmationSpec generalized to a draft (batch level). NO
    batch-level snapshot_before — per-op before-images are K7's."""

    reversibility: str
    challenge: ConfirmChallenge
    timeout_s: int = 60
    re_check_actor: Literal[True] = True
    expected_phrase: str | None = None
    expected_hash: str | None = None


@dataclass(frozen=True)
class DraftPreview:
    draft_id: str
    preview_hash: str             # pins confirm to this exact op set
    allowed: bool
    op_previews: tuple[MutationPreview, ...]
    aggregate_reversibility: str
    warnings: tuple[str, ...]
    requires_confirmation: bool
    confirmation: DraftConfirmationSpec
    blocking: tuple[PreviewBlock, ...]


def preview_hash_of(draft: Draft) -> str:
    basis = "|".join([
        draft.draft_id, draft.updated_at.isoformat(),
        *(f"{op.op_seq}:{op.op_kind}:{sorted(op.payload.items())!r}"
          for op in draft.operations),
    ])
    return hashlib.sha256(basis.encode()).hexdigest()


def requires_confirmation(draft: Draft, aggregate_reversibility: str,
                          op_count: int) -> bool:
    """T2-5: destructive ∨ AI-produced ∨ bulk/compound MUST confirm; a
    single reversible direct-lane op is exempt."""
    if draft.producer in AI_PRODUCERS:
        return True
    if aggregate_reversibility != REVERSIBLE:
        return True
    return op_count > 1


def verify_confirmation(spec: DraftConfirmationSpec,
                        resp: ConfirmationResponse | None) -> bool:
    """The KERNEL verifies the challenge — fail-closed."""
    if resp is None or resp.challenge != spec.challenge:
        return False
    if spec.challenge is ConfirmChallenge.BUTTON:
        return True
    if spec.challenge is ConfirmChallenge.TYPED_PHRASE:
        return resp.typed_value == spec.expected_phrase
    if spec.challenge is ConfirmChallenge.TYPED_HASH:
        digest = hashlib.sha256((resp.typed_value or "").encode()).hexdigest()
        return digest == spec.expected_hash
    return False


def _aggregate(reversibilities: list[str]) -> str:
    rank = {r: i for i, r in enumerate(REVERSIBILITY_ORDER)}
    worst = REVERSIBLE
    for r in reversibilities:
        if rank.get(r, 0) > rank.get(worst, 0):
            worst = r
    return worst


async def build_draft_preview(draft: Draft, ctx: PreviewContext, *,
                              registry: OpKindRegistry) -> DraftPreview:
    op_previews: list[MutationPreview] = []
    blocking: list[PreviewBlock] = []
    warnings: list[str] = []
    reversibilities: list[str] = []

    for op in draft.operations:
        binding = registry.get(op.op_kind)
        if binding is None:
            blocking.append(PreviewBlock(
                op_seq=op.op_seq, reason=DenialReason.NOT_FOUND,
                detail="no_op_kind_binding"))
            continue
        wctx = WorkflowContext(
            actor=ctx.actor, guild_id=ctx.guild_id,
            request_id=f"preview:{draft.draft_id}", dry_run=True,
            params=dict(op.payload), correlation_id=draft.draft_id,
            test_mode=ctx.test_mode)
        try:
            mp = await workflow_engine.preview(binding.workflow_ref, wctx)
        except Exception as exc:  # noqa: BLE001 — a broken preview blocks, never crashes
            blocking.append(PreviewBlock(
                op_seq=op.op_seq, reason=DenialReason.USER_ERROR,
                detail=f"preview_failed: {exc}"))
            continue
        op_previews.append(mp)
        reversibilities.append(mp.reversibility or REVERSIBLE)
        warnings.extend(mp.warnings)
        if not mp.allowed:
            blocking.append(PreviewBlock(
                op_seq=op.op_seq, reason=DenialReason.USER_ERROR,
                detail=f"preview_disallowed: {mp.summary}"))
        if binding.is_resource_create:
            warnings.append(
                f"op {op.op_seq} ({op.op_kind}): creates a Discord resource — "
                f"best-effort, not rollback-able (T2-1)")

    aggregate = _aggregate(reversibilities or [REVERSIBLE])
    needs_confirm = requires_confirmation(draft, aggregate, len(draft.operations))
    challenge = (ConfirmChallenge.TYPED_PHRASE if aggregate == IRREVERSIBLE
                 else ConfirmChallenge.BUTTON)
    confirmation = DraftConfirmationSpec(
        reversibility=aggregate, challenge=challenge,
        expected_phrase=(f"apply {draft.draft_id[:8]}"
                         if challenge is ConfirmChallenge.TYPED_PHRASE else None))
    if aggregate == COMPENSATABLE:
        warnings.append("draft contains compensatable (not freely reversible) ops")
    return DraftPreview(
        draft_id=draft.draft_id, preview_hash=preview_hash_of(draft),
        allowed=not blocking and all(p.allowed for p in op_previews),
        op_previews=tuple(op_previews), aggregate_reversibility=aggregate,
        warnings=tuple(warnings), requires_confirmation=needs_confirm,
        confirmation=confirmation, blocking=tuple(blocking))
