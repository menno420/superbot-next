"""setup.suggest / setup.explain — band-1 legacy task-id claims."""

from __future__ import annotations

from sb.kernel.ai import tasks

__all__ = ["register_ai_tasks"]


def register_ai_tasks() -> None:
    for task_id, desc in (
        ("setup.suggest", "Suggest next setup steps from the section "
                          "registry + current guild config."),
        ("setup.explain", "Explain a setup section: what it configures and "
                          "which draft ops it stages."),
    ):
        assert task_id in tasks.LEGACY_TASK_IDS
        tasks.register_task(tasks.AITaskSpec(
            task_id=task_id, owner_subsystem="setup",
            description=desc, realtime=True))
