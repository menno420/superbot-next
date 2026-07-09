"""Band-5 K10 claims — the three legacy task ids the band map assigns to
platform/control (tasks.LEGACY_TASK_IDS, byte-identical):
platform.explain_status / platform.explain_consistency /
code_context.explain — plus fact gatherers reading the band-1
diagnostic surface and the band-5 consistency report.
"""

from __future__ import annotations

__all__ = ["register_platform_tasks"]


def register_platform_tasks() -> None:
    """Idempotent (register_task tolerates identical re-registration)."""
    from sb.kernel.ai import feature_facts, tasks

    tasks.register_task(tasks.AITaskSpec(
        task_id="platform.explain_status",
        owner_subsystem="platform",
        description="Explain the bot's current platform status: lifecycle "
                    "phase, findings, declared surfaces, recent decisions.",
        realtime=True,
    ))
    tasks.register_task(tasks.AITaskSpec(
        task_id="platform.explain_consistency",
        owner_subsystem="platform",
        description="Explain the platform consistency report: which "
                    "sections are clean/warning/fatal and what blocks "
                    "rollout readiness.",
        realtime=True,
    ))
    tasks.register_task(tasks.AITaskSpec(
        task_id="code_context.explain",
        owner_subsystem="platform",
        description="Explain how a platform surface is wired (manifest "
                    "declarations, compiled snapshot facts).",
        realtime=False,
    ))

    feature_facts.register_fact_gatherer(
        "platform.explain_status", _status_facts,
        owner_subsystem="platform")
    feature_facts.register_fact_gatherer(
        "platform.explain_consistency", _consistency_facts,
        owner_subsystem="platform")


async def _status_facts(rctx) -> dict:
    from sb.domain.diagnostic.service import platform_status

    return {"platform_status": platform_status()}


async def _consistency_facts(rctx) -> dict:
    from sb.domain.platform.consistency import collect_report

    report = await collect_report()
    return {"consistency_report": report.to_dict()}
