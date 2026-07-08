"""The producer-agnostic draft grammar leaf (K9/S10 — frozen L0 spec 06 §3.1).

The multi-op durable draft primitive keyed ``(producer, owner_scope,
draft_id)`` — the structural fix for L-7's per-guild-singleton collapse:
op identity is ``(draft_id, op_seq)`` (position in the draft), never a slot
key, so 10 ``create_channel`` ops persist as 10 rows and two producers
coexist without destructive merge.

``ConfirmChallenge`` is an ALIAS of the frozen §2.7 ``Challenge`` (one
grammar, spec 06 says "§2.7 verbatim" — a second enum would be the exact
duplicate-grammar hazard RC-17 fenced for DeliveryClass).

Stdlib-only leaf.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol

from sb.spec.confirmation import Challenge as ConfirmChallenge

__all__ = [
    "AI_PRODUCERS",
    "AcceptHook",
    "ConfirmChallenge",
    "ConfirmationResponse",
    "Draft",
    "DraftOperation",
    "DraftStatus",
    "OwnerScope",
    "Producer",
    "VerificationContext",
]


class Producer(str, enum.Enum):
    """WHO composed the draft — the (producer, …) key component."""

    HUMAN_SETUP = "human_setup"             # setup wizard click-through
    AI_ORCHESTRATION = "ai_orchestration"   # rung-4 NL goal→draft
    PRESET = "preset"                       # C-3 template instantiation
    FUZZY_DESTRUCTIVE = "fuzzy_destructive" # typo-corrected destructive action (rung-2)
    NL_ACTION = "nl_action"                 # rung-3 NL intent → single action
    RELEASE_TEST = "release_test"           # test-mode verified_live sign-off
    IMPORT_REPAIR = "import_repair"         # operator repair / recovery draft


AI_PRODUCERS = frozenset({
    Producer.AI_ORCHESTRATION, Producer.NL_ACTION, Producer.FUZZY_DESTRUCTIVE,
})


class DraftStatus(str, enum.Enum):
    OPEN = "open"             # accepting ops / edits
    PREVIEWED = "previewed"   # preview built, awaiting confirm (preview_hash pinned)
    APPLYING = "applying"     # apply in progress — crash-visible
    APPLIED = "applied"       # terminal: full success
    PARTIAL = "partial"       # terminal: ≥1 op failed; recovery re-run available
    DISCARDED = "discarded"   # terminal: operator dropped it
    EXPIRED = "expired"       # terminal: TTL elapsed unapplied (written ONLY by the janitor)


TERMINAL_STATUSES = frozenset({
    DraftStatus.APPLIED, DraftStatus.PARTIAL, DraftStatus.DISCARDED,
    DraftStatus.EXPIRED,
})


@dataclass(frozen=True)
class OwnerScope:
    """WHO is accountable — the (…, owner_scope, …) key component."""

    guild_id: int                 # the TARGET guild (write target)
    actor_id: int | None          # accountable producer identity; None for system/backfill

    def render(self) -> str:
        """DISPLAY/log key ONLY — never the SQL predicate value (the DB
        stores NULL for system actors; list_open_drafts uses
        IS NOT DISTINCT FROM)."""
        return f"g{self.guild_id}:a{self.actor_id or 0}"


@dataclass(frozen=True)
class DraftOperation:
    op_seq: int                   # 1-based order WITHIN the draft (identity ≠ slot)
    op_kind: str                  # [S] the ONE registry key; MUST resolve or un-draftable
    subsystem: str                # [S]
    authority_ref: str            # [S] the op's own authority label → accept-authority AND
    payload: Mapping[str, Any]    # typed per op_kind's payload_schema; → K7 ctx.params
    label: str                    # human one-liner rendered in preview
    dedup_token: str = ""         # apply-idempotency natural key; "" ⇒ f"{draft_id}:{op_seq}"
    # is_resource_create + the preview provider are REGISTRY properties on
    # the OpKindBinding, resolved by op_kind — never op fields.


@dataclass(frozen=True)
class VerificationContext:
    """The test-mode / verified_live plug-point payload."""

    test_mode: bool                       # True ⇒ threads into every op's WorkflowContext
    debug_channel_id: int | None = None   # where the suppressed-effect plan renders
    sign_off_store_ref: str | None = None # where the verified_live sign-off is recorded


@dataclass(frozen=True)
class ConfirmationResponse:
    """The challenge-satisfaction input to confirm_and_apply."""

    challenge: ConfirmChallenge
    typed_value: str | None = None        # None for BUTTON


@dataclass(frozen=True)
class Draft:
    draft_id: str                             # uuid4 — the PK
    producer: Producer
    owner_scope: OwnerScope
    status: DraftStatus
    operations: tuple[DraftOperation, ...]    # ORDERED by op_seq; N rows coexist
    created_at: datetime
    updated_at: datetime                      # bumped on add/remove — invalidates a stale preview_hash
    expires_at: datetime | None = None
    accept_authority_ref: str = ""            # DERIVED display/list floor; the GATE is the per-ref AND
    correlation_id: str = ""                  # = draft_id — the shared audit correlation id
    verification: VerificationContext | None = None


class AcceptHook(Protocol):
    """Port — the concrete impl lives in the release-testing band."""

    async def on_confirmed(self, draft: Draft, decision: object) -> None:
        """After authority + challenge pass, BEFORE the first op runs."""
        ...

    async def on_applied(self, draft: Draft, result: object) -> None:
        """After apply_draft returns any terminal outcome."""
        ...
