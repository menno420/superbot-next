"""moderation.assist — the band-2 legacy task-id claim (byte-identical,
tasks.LEGACY_TASK_IDS discipline). ADVISORY ONLY per the K10 band map
(D-0022 note): AI moderation output is an AISuggestion for the operator —
it NEVER routes to a typed K7 op until explicitly converted by a human."""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.ai import tasks

__all__ = ["AISuggestion", "register_ai_tasks"]


@dataclass(frozen=True)
class AISuggestion:
    """The advisory contract: a suggested action + rationale, rendered to
    the operator; the human clicks the REAL command surface to act."""

    action: str          # "warn" | "timeout" | "kick" | "ban" | "none"
    target_id: int
    rationale: str
    confidence: float = 0.0


def register_ai_tasks() -> None:
    assert "moderation.assist" in tasks.LEGACY_TASK_IDS
    tasks.register_task(tasks.AITaskSpec(
        task_id="moderation.assist",
        owner_subsystem="moderation",
        description="Advisory moderation suggestions (AISuggestion) for the "
                    "operator — never auto-executes a moderation action.",
        realtime=True,
    ))
