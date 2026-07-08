"""Domain-registered AI task registry — REPLACES the closed ``AITask`` enum.

Canonical plan §2.4 B-1 contamination #1: shipped
``disbot/core/runtime/ai/contracts.py:30-38`` hardcoded domain members
(``BTD6_ANSWER``, ``PROJMOON_ANSWER``, ``VIDEO_*``) into a closed kernel
enum. Here a task is a REGISTERED :class:`AITaskSpec`; domains mint their
own tasks at their port band (the ``response_renderer_registry`` pattern,
proven next to the shipped enum).

Compat constraint (K1 ``ai_task`` namespace-kind discipline): the shipped
enum's VALUE strings are frozen in :data:`LEGACY_TASK_IDS`. They remain
claimable VERBATIM by their owning bands — a registration that collides
with a legacy id under normalisation but differs textually is refused, so
the metrics / audit / routing vocabulary stays byte-stable across cutover.

The kernel itself seeds only the domain-agnostic fallback task
(``general.nl_answer``): every other shipped id waits for its band.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "AITaskSpec",
    "KERNEL_TASK_GENERAL_NL",
    "LEGACY_TASK_IDS",
    "clear_tasks_for_tests",
    "get_task",
    "register_task",
    "registered_task_ids",
    "require_task",
    "task_registered",
]

# The 17 shipped AITask values (disbot/core/runtime/ai/contracts.py @7f7628e1),
# frozen verbatim. Owning band noted for the port workers.
LEGACY_TASK_IDS: frozenset[str] = frozenset(
    {
        "setup.suggest",  # band 1 (setup wizard)
        "setup.explain",  # band 1
        "platform.explain_status",  # band 5
        "platform.explain_consistency",  # band 5
        "logs.triage",  # band 2
        "settings.explain",  # band 1
        "settings.propose",  # band 1
        "help.answer",  # band 1
        "code_context.explain",  # band 5
        "moderation.assist",  # band 2
        "btd6.answer",  # band 7
        "general.nl_answer",  # KERNEL (seeded below)
        "projmoon.answer",  # band 7
        "btd6.strategy_review",  # band 7
        "video.describe",  # band 7 (shared media ingestion)
        "video.compare",  # band 7
        "video.qa",  # band 7
    },
)

_TASK_ID_RE = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$")


@dataclass(frozen=True)
class AITaskSpec:
    """One registered AI task — the unit of routing, gating, and audit.

    ``task_id`` is the stable dot-namespaced identifier used by metrics
    labels, decision-audit rows, routing tables, and per-task kill
    switches. ``owner_subsystem`` names the registering domain (``kernel``
    for the seeds). ``realtime`` is the routing hint the shipped model
    tables encoded implicitly (a user is waiting → fast model default).
    ``description`` is operator-facing.
    """

    task_id: str
    owner_subsystem: str
    description: str = ""
    realtime: bool = False
    # Forward-looking metadata for band-7 eval gates (A-17): a knowledge
    # domain marks its answer tasks so the deterministic eval harness can
    # enumerate them. Advisory today; consumed by the eval suite runner.
    knowledge_domain: str | None = None
    extra: dict[str, object] = field(default_factory=dict)


_REGISTRY: dict[str, AITaskSpec] = {}


class TaskIdInvalid(ValueError):
    """Raised for a malformed or legacy-colliding task id."""


class TaskCollision(ValueError):
    """Raised when a task id is registered twice with differing specs."""


def _validate_task_id(task_id: str) -> None:
    if not _TASK_ID_RE.match(task_id):
        raise TaskIdInvalid(
            f"task id {task_id!r} must be dot-namespaced lowercase "
            "([a-z0-9_]+(.[a-z0-9_]+)+)",
        )
    # Legacy-verbatim rule: an id that normalises onto a frozen legacy id
    # but is not byte-identical is a compat break (e.g. "BTD6.Answer",
    # "btd6.answers"). Case folding is already forced by the regex; guard
    # the near-miss class explicitly so the failure is descriptive.
    if task_id not in LEGACY_TASK_IDS:
        collapsed = task_id.replace("_", "").rstrip("s")
        for legacy in LEGACY_TASK_IDS:
            if collapsed == legacy.replace("_", "").rstrip("s"):
                raise TaskIdInvalid(
                    f"task id {task_id!r} collides with frozen legacy id "
                    f"{legacy!r}; legacy ids must be claimed verbatim",
                )


def register_task(spec: AITaskSpec) -> AITaskSpec:
    """Register ``spec``; idempotent for an identical re-registration.

    A differing re-registration raises :class:`TaskCollision` (two bands
    claiming one id is a build error, never a silent overwrite).
    """
    _validate_task_id(spec.task_id)
    prior = _REGISTRY.get(spec.task_id)
    if prior is not None and prior != spec:
        raise TaskCollision(
            f"task {spec.task_id!r} already registered by "
            f"{prior.owner_subsystem!r} with a differing spec",
        )
    _REGISTRY[spec.task_id] = spec
    return spec


def task_registered(task_id: str) -> bool:
    return task_id in _REGISTRY


def get_task(task_id: str) -> AITaskSpec | None:
    return _REGISTRY.get(task_id)


def require_task(task_id: str) -> AITaskSpec:
    """Return the spec or raise ``KeyError`` — gateway admission uses the
    non-raising :func:`task_registered`; this is for build-time wiring."""
    spec = _REGISTRY.get(task_id)
    if spec is None:
        raise KeyError(f"AI task {task_id!r} is not registered")
    return spec


def registered_task_ids() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def _seed_kernel_tasks() -> AITaskSpec:
    return register_task(
        AITaskSpec(
            task_id="general.nl_answer",
            owner_subsystem="kernel",
            description="Domain-agnostic natural-language fallback answer.",
            realtime=True,
        ),
    )


KERNEL_TASK_GENERAL_NL = _seed_kernel_tasks()


def clear_tasks_for_tests() -> None:
    """Reset the registry to the kernel seed (test seam)."""
    _REGISTRY.clear()
    _seed_kernel_tasks()
