"""help.answer — the band-1 legacy task-id claim (byte-identical,
tasks.LEGACY_TASK_IDS discipline)."""

from __future__ import annotations

from sb.kernel.ai import tasks

__all__ = ["register_ai_tasks"]


def register_ai_tasks() -> None:
    assert "help.answer" in tasks.LEGACY_TASK_IDS
    tasks.register_task(tasks.AITaskSpec(
        task_id="help.answer",
        owner_subsystem="help",
        description="Answer 'how do I / what can the bot do' questions from "
                    "the manifest-generated capabilities overview.",
        realtime=True,
    ))
