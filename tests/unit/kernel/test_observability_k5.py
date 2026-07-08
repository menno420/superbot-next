"""K5 observability fold tests: redaction port, findings seam, A-8 alert sink."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.observability.alerts import (
    AlertKind,
    LoggingAlertSink,
    NullAlertSink,
    OperatorAlert,
    OperatorAlertSink,
    prepare_alert,
)
from sb.kernel.observability.findings import (
    recent_findings,
    record_operator_finding,
    reset_for_tests,
)
from sb.kernel.observability.redaction import redact_payload, redact_text


@pytest.fixture(autouse=True)
def fresh_findings():
    reset_for_tests()
    yield
    reset_for_tests()


# --- redaction (ported verbatim from disbot/core/runtime/ai/redaction.py) ---

def test_redact_dsn_and_bearer() -> None:
    result = redact_text("dsn is postgres://user:pw@host:5432/db and Bearer abc.def")
    assert "postgres://" not in result.value
    assert "[database_url:redacted]" in result.value
    assert "[bearer_token:redacted]" in result.value
    assert result.replacements["database_url"] == 1


def test_redact_api_key_and_email() -> None:
    result = redact_text("key sk-proj-abcdefghijklm mail me@example.com")
    assert "[api_key_like:redacted]" in result.value
    assert "[email:redacted]" in result.value


def test_redact_url_secret_query_and_snowflake() -> None:
    result = redact_text("https://x.y/z?token=supersecret and id 123456789012345678")
    assert "token=[redacted]" in result.value
    assert "[discord_id:redacted]" in result.value


def test_redact_payload_recurses() -> None:
    result = redact_payload({"a": ["postgres://u:p@h/db"], "b": {"c": "clean"}})
    assert result.value["a"] == ["[database_url:redacted]"]
    assert result.value["b"]["c"] == "clean"
    assert result.replacements == {"database_url": 1}


# --- findings (the spec 08 §4 seam) ---

def test_record_finding_shape_and_redaction() -> None:
    finding = record_operator_finding(
        source="sb.kernel.outbox",
        severity="error",
        summary="outbox dead-letter: xp.awarded",
        detail="last error: cannot reach postgres://u:pw@db:5432/prod",
        correlation_id="mut-1",
    )
    assert finding.source == "sb.kernel.outbox"
    assert "postgres://" not in finding.detail        # redact obligation
    assert recent_findings()[-1] is finding


def test_unknown_severity_coerced() -> None:
    finding = record_operator_finding(
        source="x", severity="nonsense", summary="s", detail="d")
    assert finding.severity == "error"


# --- A-8 operator-alert sink spec ---

def test_prepare_alert_scrubs_every_text_surface() -> None:
    alert = OperatorAlert(
        kind=AlertKind.STARTUP,
        title="token MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM.XXXXXX.abcdefghijklmnopqrstuvwx",
        body="dsn postgres://u:pw@h/db",
        fields=(("Owner", "mail me@example.com"),),
    )
    prepared = prepare_alert(alert)
    assert "postgres://" not in prepared.body
    assert "[email:redacted]" in prepared.fields[0][1]
    assert "redacted" in prepared.title
    assert prepared.kind is AlertKind.STARTUP


def test_sinks_satisfy_the_port() -> None:
    assert isinstance(LoggingAlertSink(), OperatorAlertSink)
    assert isinstance(NullAlertSink(), OperatorAlertSink)
    alert = OperatorAlert(kind=AlertKind.TASK_DIED, title="task died: outbox:relay")
    asyncio.run(LoggingAlertSink().send(alert))
    asyncio.run(NullAlertSink().send(alert))


def test_alert_kinds_cover_the_shipped_feed() -> None:
    assert {k.value for k in AlertKind} >= {
        "startup", "startup_summary", "shutdown", "cog_fail", "task_died",
    }
