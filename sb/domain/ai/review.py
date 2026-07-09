"""AI answer review-log service (band 7) — shipped
``services/ai_review_log_service.py`` semantics: the bounded in-memory
answer registry (correction matching; process-local BY DESIGN, shipped
ADR-001/ADR-002), redaction-before-storage, and the fail-safe
record_unknown / record_correction writers over the K7 lane. Every
public call is fail-safe — a logging failure never disturbs the reply
path."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("sb.domain.ai.review")

__all__ = [
    "AnswerContext",
    "KIND_CORRECTION",
    "KIND_UNKNOWN",
    "already_flagged",
    "lookup_answer",
    "record_correction",
    "record_unknown",
    "remember_answer",
    "reset_registry_for_tests",
]

KIND_UNKNOWN = "unknown"
KIND_CORRECTION = "correction"
SIGNAL_REACTION = "reaction"
SIGNAL_REPLY = "reply"

_TEXT_CAP = 2000
_REGISTRY_MAX = 1000
_REGISTRY_TTL_SECONDS = 60 * 60


@dataclass(frozen=True)
class AnswerContext:
    """What the registry remembers about one sent AI answer."""

    guild_id: int
    channel_id: int
    user_id: int
    message_id: int | None
    question: str | None
    answer: str | None
    task: str | None
    route: str | None
    provider: str | None
    model: str | None
    recorded_at: float


_REGISTRY: OrderedDict[int, AnswerContext] = OrderedDict()
_FLAGGED: dict[int, set[int]] = {}


def _redact(text: str | None) -> str | None:
    if not text:
        return None
    try:
        from sb.kernel.observability.redaction import redact_text

        result = redact_text(str(text))
        cleaned = getattr(result, "text", result)
        return str(cleaned)[:_TEXT_CAP]
    except Exception:  # noqa: BLE001 — redaction fault → drop the text
        return None


def _prune_registry() -> None:
    cutoff = time.monotonic() - _REGISTRY_TTL_SECONDS
    stale = [k for k, v in _REGISTRY.items() if v.recorded_at < cutoff]
    for key in stale:
        _REGISTRY.pop(key, None)
        _FLAGGED.pop(key, None)
    while len(_REGISTRY) > _REGISTRY_MAX:
        key, _ = _REGISTRY.popitem(last=False)
        _FLAGGED.pop(key, None)


def remember_answer(reply_message_id: int, ctx: AnswerContext) -> None:
    """Remember a sent AI answer so a later 👎 / correction reply can
    recover the original Q&A (bounded + TTL'd)."""
    _prune_registry()
    _REGISTRY[reply_message_id] = ctx
    _REGISTRY.move_to_end(reply_message_id)


def lookup_answer(reply_message_id: int) -> AnswerContext | None:
    ctx = _REGISTRY.get(reply_message_id)
    if ctx is None:
        return None
    if ctx.recorded_at < time.monotonic() - _REGISTRY_TTL_SECONDS:
        _REGISTRY.pop(reply_message_id, None)
        return None
    return ctx


def already_flagged(reply_message_id: int, user_id: int) -> bool:
    return user_id in _FLAGGED.get(reply_message_id, set())


def _note_flagger(reply_message_id: int, user_id: int) -> None:
    _FLAGGED.setdefault(reply_message_id, set()).add(user_id)


def reset_registry_for_tests() -> None:
    _REGISTRY.clear()
    _FLAGGED.clear()


async def _record(actor_user_id: int, guild_id: int,
                  params: dict[str, Any]) -> int | None:
    """Run the audited record lane. Fail-safe: any error logs + None."""
    try:
        from sb.kernel.interaction.request import ActorRef
        from sb.kernel.workflow import engine
        from sb.kernel.workflow.context import WorkflowContext
        from sb.spec.refs import WorkflowRef

        actor = ActorRef(user_id=actor_user_id, is_guild_operator=False,
                         is_bot_owner=False, is_dm=False)
        result = await engine.run(
            WorkflowRef("ai.record_review_entry"),
            WorkflowContext(actor=actor, guild_id=guild_id, params=params))
        if result.ok:
            return int((result.after or {}).get("entry_id") or 0) or None
        return None
    except Exception:  # noqa: BLE001 — never disturb the reply path
        logger.debug("ai review: record failed", exc_info=True)
        return None


async def record_unknown(*, guild_id: int, channel_id: int, user_id: int,
                         message_id: int | None, reason_code: str,
                         task: str | None, route: str | None,
                         question: str | None, answer: str | None,
                         provider: str | None = None,
                         model: str | None = None) -> int | None:
    """The stage could not answer properly — record a reviewable row."""
    return await _record(user_id, guild_id, {
        "kind": KIND_UNKNOWN, "channel_id": channel_id,
        "user_id": user_id, "message_id": message_id,
        "reason_code": reason_code, "task": task, "route": route,
        "question": _redact(question), "answer": _redact(answer),
        "provider": provider, "model": model,
    })


async def record_correction(*, reply_message_id: int, corrected_by: int,
                            signal: str,
                            correction_text: str | None = None) -> int | None:
    """A member flagged one of the bot's AI answers (👎 or a correction
    reply). Uses the registry to recover the original Q&A; dedupes per
    (message, flagger)."""
    ctx = lookup_answer(reply_message_id)
    if ctx is None:
        return None
    if already_flagged(reply_message_id, corrected_by):
        return None
    _note_flagger(reply_message_id, corrected_by)
    return await _record(corrected_by, ctx.guild_id, {
        "kind": KIND_CORRECTION, "channel_id": ctx.channel_id,
        "user_id": ctx.user_id, "message_id": ctx.message_id,
        "reply_message_id": reply_message_id,
        "reason_code": signal, "task": ctx.task, "route": ctx.route,
        "question": ctx.question, "answer": ctx.answer,
        "correction": _redact(correction_text),
        "corrected_by": corrected_by,
        "provider": ctx.provider, "model": ctx.model,
    })
