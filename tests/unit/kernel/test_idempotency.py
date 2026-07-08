"""K3 idempotency-key contract tests (spec 05 §3.7)."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.db.idempotency import (
    OUTCOMES,
    IdempotencyKey,
    PriorOutcome,
    once,
    read_outcome,
    record_outcome,
)


def test_render_shape() -> None:
    key = IdempotencyKey("economy.daily", 42, "msg-123")
    assert key.render() == "economy.daily:42:msg-123"


def test_render_parse_roundtrip_with_colons_in_token() -> None:
    # Spec 08 §3.5: dedup tokens carry :{event_name}/:{emit_index} suffixes.
    key = IdempotencyKey("outbox", 7, "mut-1:xp.level_up")
    assert IdempotencyKey.parse(key.render()) == key


def test_parse_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        IdempotencyKey.parse("no-colons-here")
    with pytest.raises(ValueError):
        IdempotencyKey.parse("ns:not-an-int:token")


def test_key_validation() -> None:
    with pytest.raises(ValueError):
        IdempotencyKey("has:colon", 1, "t")
    with pytest.raises(ValueError):
        IdempotencyKey("", 1, "t")
    with pytest.raises(ValueError):
        IdempotencyKey("ns", 1, "")


def test_outcome_vocab_frozen() -> None:
    assert OUTCOMES == ("SUCCESS", "PARTIAL", "BLOCKED", "DECLINED", "DISCORD_FAILED")


class _Conn:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}   # key -> row
        self.executed: list[tuple[str, tuple]] = []

    async def fetchrow(self, query: str, *params: object):
        self.executed.append((query, params))
        if query.startswith("INSERT INTO idempotency_keys"):
            key, namespace, first_seen = params
            if key in self.rows:
                return None  # ON CONFLICT DO NOTHING
            self.rows[key] = {"key": key, "namespace": namespace,
                              "first_seen_at": first_seen, "outcome": None,
                              "result_ref": None}
            return {"key": key}
        if query.startswith("SELECT outcome"):
            row = self.rows.get(params[0])
            if row is None:
                return None
            return {"outcome": row["outcome"], "result_ref": row["result_ref"],
                    "first_seen_at": row["first_seen_at"]}
        raise AssertionError(f"unexpected fetchrow: {query}")

    async def execute(self, query: str, *params: object):
        self.executed.append((query, params))
        if query.startswith("UPDATE idempotency_keys"):
            key, outcome, result_ref = params
            row = self.rows[key]
            row["outcome"] = outcome
            row["result_ref"] = result_ref
            return "UPDATE 1"
        raise AssertionError(f"unexpected execute: {query}")


def test_once_then_conflict_then_outcome_readback() -> None:
    async def scenario() -> None:
        conn = _Conn()
        key = IdempotencyKey("economy.daily", 42, "interaction-9")
        assert await once(key, conn=conn) is True          # first sighting
        assert await once(key, conn=conn) is False         # replay no-ops
        assert await read_outcome(key, conn=conn) is None  # mid-flight: not recorded yet
        await record_outcome(key, "SUCCESS", result_ref="audit-1", conn=conn)
        prior = await read_outcome(key, conn=conn)
        assert isinstance(prior, PriorOutcome)
        assert prior.outcome == "SUCCESS"
        assert prior.result_ref == "audit-1"

    asyncio.run(scenario())


def test_record_outcome_rejects_unknown_vocab() -> None:
    async def scenario() -> None:
        conn = _Conn()
        key = IdempotencyKey("ns", 1, "t")
        await once(key, conn=conn)
        with pytest.raises(ValueError):
            await record_outcome(key, "OK", conn=conn)

    asyncio.run(scenario())
