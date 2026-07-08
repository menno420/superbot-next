"""Feature-facts gather registry (K10) — B-1 contamination #2 cut.

The shipped ``_gather_feature_facts`` in
``disbot/core/runtime/ai/natural_language_stage.py`` hand-branched an
if-chain over domain tasks (PROJMOON → projmoon_context_service, BTD6 →
btd6_context_service, VIDEO → youtube_context_service). Here fact
gathering is a REGISTRY hook: a domain registers a gatherer for its task
ids at its port band; :func:`gather` dispatches; tasks without a gatherer
return empty facts and the gateway answers from the instruction stack
alone (the shipped default).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

__all__ = [
    "FeatureFactRequest",
    "FeatureFactsResult",
    "clear_gatherers_for_tests",
    "gather",
    "register_fact_gatherer",
    "registered_gatherer_tasks",
]

logger = logging.getLogger("sb.kernel.ai.feature_facts")


@dataclass(frozen=True)
class FeatureFactRequest:
    """Shipped shape (feature_facts.py @7f7628e1) with ``task`` as the
    registered id string."""

    task: str
    text: str
    guild_id: int | None
    channel_id: int | None
    author_id: int | None
    message_id: int | None
    # The router routed this turn via the conversation cue (a pronoun
    # follow-up) — the grounding layer then adds the carryover facts even
    # when the text itself grounds something.
    conversation_followup: bool = False


@dataclass(frozen=True)
class FeatureFactsResult:
    facts: tuple[str, ...]
    render_context: object | None = None
    error_reason: str | None = None


#: A gatherer returns the grounding facts for one request. It SHOULD be
#: fault-tolerant internally; the dispatcher additionally fail-safes so a
#: broken gatherer degrades to empty facts with an error_reason rather
#: than breaking the reply path.
FactGatherer = Callable[[FeatureFactRequest], Awaitable[FeatureFactsResult]]

_GATHERERS: dict[str, tuple[str, FactGatherer]] = {}


def register_fact_gatherer(
    task_id: str,
    gatherer: FactGatherer,
    *,
    owner_subsystem: str,
) -> None:
    """Register the fact gatherer for ``task_id``. One gatherer per task;
    a differing re-registration raises (two bands claiming one task's
    grounding is a build error). Idempotent for the same function."""
    prior = _GATHERERS.get(task_id)
    if prior is not None and prior != (owner_subsystem, gatherer):
        raise ValueError(
            f"fact gatherer for task {task_id!r} already registered by "
            f"{prior[0]!r}",
        )
    _GATHERERS[task_id] = (owner_subsystem, gatherer)


def registered_gatherer_tasks() -> tuple[str, ...]:
    return tuple(sorted(_GATHERERS))


def clear_gatherers_for_tests() -> None:
    _GATHERERS.clear()


_EMPTY = FeatureFactsResult(facts=())


async def gather(req: FeatureFactRequest) -> FeatureFactsResult:
    """Dispatch to the registered gatherer for ``req.task``; no gatherer →
    empty facts (the gateway answers from the instruction stack alone).
    Never raises."""
    entry = _GATHERERS.get(req.task)
    if entry is None:
        return _EMPTY
    owner, gatherer = entry
    try:
        return await gatherer(req)
    except Exception:  # noqa: BLE001 — grounding faults never break the reply path
        logger.warning(
            "feature facts: gatherer for task %s (owner %s) raised",
            req.task,
            owner,
            exc_info=True,
        )
        return FeatureFactsResult(facts=(), error_reason="fact_gatherer_error")
