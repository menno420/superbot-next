"""The operator-alert sink spec (K5 — amendment A-8).

A-8: the shipped WebhookReporter operator-alert feed (startup / shutdown /
cog-fail / task-died embeds, `disbot/services/webhook_reporter.py`) lands as
a K5/observability SINK SPEC carrying its `redact_text` secret-redaction
obligation. This module is that spec: the `OperatorAlertSink` port, the
`OperatorAlert` shape, and the redaction obligation enforced at the ONE
choke point (`prepare_alert`) every implementation must route through.

THE OBLIGATION (frozen): every text surface of an alert (title, body, every
field name + value) passes through `redact_text` immediately before egress —
secret-looking substrings (tokens, API keys, postgres:// DSNs, bearer
tokens, emails, secret query params) never reach the operator channel.

Implementations here: `LoggingAlertSink` (always available) and
`NullAlertSink`. The Discord `WebhookReporter` twin (aiohttp + embed
rendering + `DISCORD_WEBHOOK_URL`) is an ADAPTER that ports at the operator
band — it consumes this port and `prepare_alert`; flagged for owner only in
that its webhook URL is a SecretSpec the owner provisions.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field, replace
from typing import Protocol, runtime_checkable

from sb.kernel.observability.redaction import redact_text

logger = logging.getLogger("sb.alerts")

__all__ = [
    "AlertKind",
    "LoggingAlertSink",
    "NullAlertSink",
    "OperatorAlert",
    "OperatorAlertSink",
    "prepare_alert",
]


class AlertKind(str, enum.Enum):
    """The shipped WebhookReporter feed, named (A-8)."""

    STARTUP = "startup"                  # "Bot Online" embed
    STARTUP_SUMMARY = "startup_summary"  # LP-7 deterministic phase summary
    SHUTDOWN = "shutdown"
    COG_FAIL = "cog_fail"
    TASK_DIED = "task_died"
    CLOSE_TIMEOUT = "close_timeout"      # the wedged-close force-exit branch
    ERROR = "error"                      # generic operator error embed


@dataclass(frozen=True)
class OperatorAlert:
    kind: AlertKind
    title: str
    body: str = ""
    fields: tuple[tuple[str, str], ...] = ()   # (name, value) pairs
    created_at: float = field(default_factory=time.time)


@runtime_checkable
class OperatorAlertSink(Protocol):
    """The sink port. Implementations MUST send `prepare_alert(alert)`,
    never the raw alert — that is where the A-8 redaction obligation lives."""

    async def send(self, alert: OperatorAlert) -> None: ...


def prepare_alert(alert: OperatorAlert) -> OperatorAlert:
    """Scrub every text surface through `redact_text` (the A-8 obligation).

    Mirrors the shipped `_redact_embed` walk (title, description, field
    names + values) on the port shape. Returns a NEW alert; replacement
    counts are logged at debug like the shipped reporter.
    """
    counts: dict[str, int] = {}

    def scrub(text: str) -> str:
        result = redact_text(text)
        for key, n in result.replacements.items():
            counts[key] = counts.get(key, 0) + n
        return result.value

    prepared = replace(
        alert,
        title=scrub(alert.title),
        body=scrub(alert.body),
        fields=tuple((scrub(name), scrub(value)) for name, value in alert.fields),
    )
    if counts:
        logger.debug("operator alert redacted: %s", counts)
    return prepared


class LoggingAlertSink:
    """v1 sink: structured log lines (always available, no Discord)."""

    async def send(self, alert: OperatorAlert) -> None:
        prepared = prepare_alert(alert)
        logger.warning(
            "operator alert [%s] %s — %s %s",
            prepared.kind.value, prepared.title, prepared.body,
            dict(prepared.fields) if prepared.fields else "",
        )


class NullAlertSink:
    """Explicitly discards alerts (test / alerts-disabled composition)."""

    async def send(self, alert: OperatorAlert) -> None:
        return None
