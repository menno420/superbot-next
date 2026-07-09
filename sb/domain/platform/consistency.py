"""Unified platform consistency & readiness diagnostics (band 5) —
services/platform_consistency.py compiled: the frozen severity contract
(CLEAN/WARNING/FATAL/SKIPPED, informational never promotes), the
fail-isolated section-collector registry, collect_report / get_last_report
/ iter_blocking_sections, and sb-native collectors for the surfaces that
exist today (migrations, lifecycle, manifests, governance, scheduler,
findings). Later bands register more collectors.
"""

from __future__ import annotations

import dataclasses
import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger("sb.domain.platform.consistency")

__all__ = [
    "ConsistencyReport",
    "SectionResult",
    "SectionStatus",
    "collect_report",
    "get_last_report",
    "iter_blocking_sections",
    "register_collector",
    "reset_collectors_for_tests",
]


class SectionStatus(str, Enum):
    CLEAN = "clean"
    WARNING = "warning"
    FATAL = "fatal"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SectionResult:
    kind: str
    status: SectionStatus
    summary: str
    details: tuple[str, ...] = ()
    informational: bool = False


@dataclass(frozen=True)
class ConsistencyReport:
    sections: tuple[SectionResult, ...]
    overall_status: SectionStatus
    collected_at: str

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status.value,
            "collected_at": self.collected_at,
            "sections": [
                {**dataclasses.asdict(s), "status": s.status.value}
                for s in self.sections],
        }


Collector = Callable[[], Awaitable[SectionResult]]

_COLLECTORS: dict[str, Collector] = {}
_last_report: ConsistencyReport | None = None


def register_collector(kind: str, collector: Collector) -> None:
    _COLLECTORS[kind] = collector


def _promote(sections: tuple[SectionResult, ...]) -> SectionStatus:
    """The shipped promotion contract: FATAL > WARNING > all-SKIPPED >
    CLEAN; informational sections never promote."""
    operative = [s for s in sections if not s.informational]
    if any(s.status is SectionStatus.FATAL for s in operative):
        return SectionStatus.FATAL
    if any(s.status is SectionStatus.WARNING for s in operative):
        return SectionStatus.WARNING
    if operative and all(s.status is SectionStatus.SKIPPED for s in operative):
        return SectionStatus.SKIPPED
    return SectionStatus.CLEAN


async def collect_report() -> ConsistencyReport:
    """Run every registered collector, each fail-isolated: an unknown
    raise becomes a FATAL section, never a blank report (shipped)."""
    global _last_report
    sections: list[SectionResult] = []
    for kind, collector in sorted(_COLLECTORS.items()):
        try:
            sections.append(await collector())
        except Exception as exc:  # noqa: BLE001 — the shipped isolation rule
            logger.exception("consistency collector %s raised", kind)
            sections.append(SectionResult(
                kind=kind, status=SectionStatus.FATAL,
                summary=f"collector raised: {type(exc).__name__}: {exc}"))
    report = ConsistencyReport(
        sections=tuple(sections),
        overall_status=_promote(tuple(sections)),
        collected_at=datetime.datetime.now(
            tz=datetime.timezone.utc).isoformat())
    _last_report = report
    return report


def get_last_report() -> ConsistencyReport | None:
    return _last_report


def iter_blocking_sections(report: ConsistencyReport) -> tuple[SectionResult, ...]:
    """Non-informational, non-CLEAN/SKIPPED sections (rollout blockers)."""
    return tuple(s for s in report.sections
                 if not s.informational
                 and s.status in (SectionStatus.WARNING, SectionStatus.FATAL))


# --- sb-native collectors --------------------------------------------------------------

async def _collect_migrations() -> SectionResult:
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "migrations"
    try:
        recorded = json.loads((root / "checksums.json").read_text())
    except Exception as exc:  # noqa: BLE001
        return SectionResult("migrations", SectionStatus.FATAL,
                             f"checksums.json unreadable: {exc}")
    drift = []
    for name, digest in recorded.items():
        path = root / name
        if not path.exists():
            drift.append(f"{name}: file missing")
            continue
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            drift.append(f"{name}: checksum drift")
    if drift:
        return SectionResult("migrations", SectionStatus.FATAL,
                             f"{len(drift)} migration problem(s)",
                             details=tuple(drift))
    return SectionResult("migrations", SectionStatus.CLEAN,
                         f"{len(recorded)} migration(s) checksum-clean")


async def _collect_lifecycle() -> SectionResult:
    try:
        from sb.kernel.lifecycle import get_phase

        phase = get_phase()
        name = getattr(phase, "name", str(phase))
        status = (SectionStatus.CLEAN if name == "RUNNING"
                  else SectionStatus.WARNING)
        return SectionResult("lifecycle", status, f"phase={name}")
    except Exception:  # noqa: BLE001 — headless test context has no lifecycle
        return SectionResult("lifecycle", SectionStatus.SKIPPED,
                             "lifecycle not initialised")


async def _collect_manifests() -> SectionResult:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "manifest.snapshot.json"
    try:
        snap = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        return SectionResult("manifests", SectionStatus.FATAL,
                             f"manifest.snapshot.json unreadable: {exc}")
    subsystems = snap.get("subsystems", {})
    return SectionResult("manifests", SectionStatus.CLEAN,
                         f"{len(subsystems)} compiled manifest(s), "
                         f"hash {snap.get('stable_hash', '?')[:16]}…")


async def _collect_governance() -> SectionResult:
    from sb.domain.governance import registry

    try:
        registry.validate_registry()
    except Exception as exc:  # noqa: BLE001
        return SectionResult("governance", SectionStatus.FATAL,
                             f"registry invalid: {exc}")
    return SectionResult(
        "governance", SectionStatus.CLEAN,
        f"{len(registry.SUBSYSTEM_META)} subsystems, "
        f"{len(registry.CAPABILITY_TO_SUBSYSTEM)} capabilities, "
        f"registry v{registry.REGISTRY_VERSION}")


async def _collect_scheduler() -> SectionResult:
    from sb.kernel.scheduler.due_queue import declared_tasks

    tasks = declared_tasks()
    return SectionResult("scheduler", SectionStatus.CLEAN,
                         f"{len(tasks)} declared task(s)",
                         details=tuple(t.name for t in tasks))


async def _collect_findings() -> SectionResult:
    try:
        from sb.kernel.observability.findings import recent_findings

        findings = recent_findings()
        fatal = [f for f in findings
                 if getattr(f, "severity", "") == "fatal"]
        if fatal:
            return SectionResult("findings", SectionStatus.FATAL,
                                 f"{len(fatal)} fatal finding(s)")
        if findings:
            return SectionResult("findings", SectionStatus.WARNING,
                                 f"{len(findings)} operator finding(s)")
        return SectionResult("findings", SectionStatus.CLEAN, "no findings")
    except Exception:  # noqa: BLE001 — findings ring may not expose reads
        return SectionResult("findings", SectionStatus.SKIPPED,
                             "findings engine not readable")


def _register_builtin_collectors() -> None:
    register_collector("migrations", _collect_migrations)
    register_collector("lifecycle", _collect_lifecycle)
    register_collector("manifests", _collect_manifests)
    register_collector("governance", _collect_governance)
    register_collector("scheduler", _collect_scheduler)
    register_collector("findings", _collect_findings)


def reset_collectors_for_tests() -> None:
    global _last_report
    _COLLECTORS.clear()
    _last_report = None
    _register_builtin_collectors()


_register_builtin_collectors()
