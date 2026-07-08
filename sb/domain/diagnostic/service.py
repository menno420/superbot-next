"""Diagnostics service (band 1) — ports the shipped diagnostics_service
aggregation shape onto the new kernel seams (read-only, no store)."""

from __future__ import annotations

from typing import Any

__all__ = ["ai_diagnostics", "platform_status", "recent_decisions"]


def platform_status() -> dict[str, Any]:
    """The one status snapshot the hub renders (sync, in-process truth)."""
    from sb.kernel import lifecycle
    from sb.kernel import settings as ksettings
    from sb.kernel.ai.diagnostics import get_default_collector
    from sb.kernel.observability.findings import recent_findings

    findings = recent_findings(limit=10)
    decls = ksettings.iter_declarations()
    subsystems = sorted({d.subsystem for d in decls})
    return {
        "phase": lifecycle.get_phase().name,
        "declared_settings": len(decls),
        "declared_subsystems": subsystems,
        "recent_findings": [
            {"source": f.source, "severity": f.severity, "summary": f.summary}
            for f in findings
        ],
        "ai": ai_diagnostics(),
    }


def ai_diagnostics() -> dict[str, Any]:
    """The /ai diagnostics read: the K10 collector snapshot (the band-map
    obligation: diagnostics.get_default_collector().snapshot())."""
    from sb.kernel.ai.diagnostics import get_default_collector

    snap = get_default_collector().snapshot()
    out: dict[str, Any] = {}
    for field in ("provider_requested", "provider_active", "enabled",
                  "degraded", "last_error_type", "last_fallback_reason",
                  "requests_observed", "failures_observed"):
        if hasattr(snap, field):
            out[field] = getattr(snap, field)
    return out


async def recent_decisions(guild_id: int, limit: int = 20) -> list[dict]:
    """decision_audit.query passthrough (the /ai diagnostics second leg)."""
    from sb.kernel.db.ai_audit import query_decisions

    return await query_decisions(guild_id, limit=limit)
