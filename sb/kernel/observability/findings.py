"""Operator findings — the minimal K5 fold of the findings/diagnostics engine.

The canonical plan folds the findings engine into K5 (F-3.4). Strand-2 specs
consume exactly ONE seam from it today: `record_operator_finding(*, source,
severity, summary, detail, correlation_id)` — the shape spec 08 §4 states as
its consumes-assumption (the outbox DEAD path) and spec 09 §3.8 routes
`ErrorPolicy.ESCALATE_FINDING` through. This module provides that seam as a
durable-enough v1: structured log + bounded in-memory ring the diagnostics
surfaces read. A persisted findings store + operator projection grows here
later (S12's sweep log is separate, spec 11).

Findings are scrubbed through `redact_text` before recording — a finding's
detail often embeds an exception string, and exception strings embed DSNs.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from sb.kernel.observability.redaction import redact_text

logger = logging.getLogger("sb.findings")

__all__ = ["OperatorFinding", "recent_findings", "record_operator_finding",
           "reset_for_tests"]

_BUFFER_SIZE = 256

SEVERITIES = ("info", "warning", "error", "critical")


@dataclass(frozen=True)
class OperatorFinding:
    source: str                    # the recording module ("sb.kernel.outbox", ...)
    severity: str                  # one of SEVERITIES
    summary: str                   # one-line, redacted
    detail: str                    # redacted
    correlation_id: object | None  # audit/mutation link when there is one
    recorded_at: float = field(default_factory=time.time)


_findings: deque[OperatorFinding] = deque(maxlen=_BUFFER_SIZE)


def record_operator_finding(
    *,
    source: str,
    severity: str,
    summary: str,
    detail: str,
    correlation_id: object | None = None,
) -> OperatorFinding:
    """Record one persistent operator finding (the spec 08 §4 seam)."""
    if severity not in SEVERITIES:
        severity = "error"
    finding = OperatorFinding(
        source=source,
        severity=severity,
        summary=redact_text(summary).value,
        detail=redact_text(detail).value,
        correlation_id=correlation_id,
    )
    _findings.append(finding)
    log = getattr(logger, severity if severity != "critical" else "critical",
                  logger.error)
    log("finding [%s] %s: %s", finding.source, finding.summary, finding.detail)
    return finding


def recent_findings(limit: int = 50) -> list[OperatorFinding]:
    """Most recent findings, newest last (diagnostics read surface)."""
    if limit <= 0:
        return []
    return list(_findings)[-limit:]


def reset_for_tests() -> None:
    """Test-only: clear the ring."""
    _findings.clear()
