"""WorkflowContext + the leg protocol (frozen L0 spec 07 §3.2).

`actor` is spec 02's `ActorRef` once S9 lands it; K7 duck-reads only
`user_id` / `actor_type` / `member_tier` / `role_ids` / `is_dm` (RC-12/RC-18
— K7 maps `ctx.actor.actor_type → AuthorityRequest.actor_type` so the
reserved scripted values `"system"`/`"backfill"` hit `resolve_authority`'s
step-1 bypass).

`test_mode` (build-order note: WorkflowContext gains correlation_id /
test_mode / actor_type mapping) marks a test-guild / verify-boot invocation;
the engine threads it, domains may branch presentation on it — it NEVER
changes idempotency/audit semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Protocol

from sb.spec.outcomes import OUTCOMES  # noqa: F401 — re-exported grammar anchor

__all__ = ["LegOutcome", "LegHandler", "SYSTEM_CLOCK", "WorkflowContext"]


def SYSTEM_CLOCK() -> datetime:
    """The default clock — UTC now (a callable so tests inject)."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WorkflowContext:
    actor: object                              # ActorRef (S9); duck-read only
    guild_id: int
    request_id: str                            # confirm re-entry dedup (vocab §④.2)
    confirmed: bool = False                    # set by the resolver on confirm re-entry
    dry_run: bool = False                      # set by preview()
    test_mode: bool = False                    # test-guild / verify-boot marker
    correlation_id: str | None = None          # set ONLY by the draft pipeline (= draft_id)
    params: Mapping[str, object] = field(default_factory=dict)
    clock: object = SYSTEM_CLOCK


@dataclass(frozen=True)
class LegOutcome:
    step: object                               # StepResult (shipped :56 shape)
    before: object | None = None               # -> central-row prev_value + diff
    after: object | None = None                # -> central-row new_value + diff
    payload: object | None = None              # typed value the op result surfaces
    warnings: tuple[str, ...] = ()
    user_message: str | None = None            # success copy line — legs in order,
                                               # newline-joined into WorkflowResult
                                               # .user_message (None = no line)


class LegHandler(Protocol):
    """conn is the txn-bound Connection for DB legs; None for EFFECT legs."""

    async def __call__(self, conn: object | None, ctx: WorkflowContext) -> LegOutcome: ...
