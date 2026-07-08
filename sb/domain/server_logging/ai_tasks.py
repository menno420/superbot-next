"""logs.triage — the band-2 legacy task-id claim (byte-identical,
tasks.LEGACY_TASK_IDS discipline)."""

from __future__ import annotations

from sb.kernel.ai import tasks

__all__ = ["register_ai_tasks"]


def register_ai_tasks() -> None:
    assert "logs.triage" in tasks.LEGACY_TASK_IDS
    tasks.register_task(tasks.AITaskSpec(
        task_id="logs.triage",
        owner_subsystem="logging",
        description="Summarize/triage operator log lines on request "
                    "(reads the routed history; advisory output only).",
        realtime=True,
    ))
