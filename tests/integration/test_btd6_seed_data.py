"""Real-Postgres leg for the `!btd6 ops seed-data` terminal — the audited
``btd6.seed_data`` op against the migration-0034 ``btd6_data_blobs`` table.

No golden can drive this lane (parity/goldens/_sweep_skips.json pins the
capture skip: the golden would embed the whole 6.8MB dataset), so this is
the table's behavior evidence: the REAL K7 engine runs the registered op
over the REAL committed dataset and the rows land — every bundled name
(fixtures + the stats tree), sha256 over the canonical dump, and the
"Safe to re-run any time (it upserts)" idempotency the shipped receipt
promises (second run rewrites, never grows).

Whole body under ONE ``asyncio.run()`` — see conftest.py's note on
asyncpg pools binding to their creating loop.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_777_000_000_001
ADMIN = 900_000_777_000_000_101


def _ctx(params: dict, tier: str = "administrator"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=ADMIN, actor_type="user",
                              member_tier=tier),
        guild_id=GID, request_id="seed-r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(1_000_000,
                                                tz=dt.timezone.utc))


async def _seed_twice_and_verify() -> None:
    from sb.domain.btd6 import dataset
    from sb.domain.btd6 import store as btd6_store
    from sb.kernel.db.pool import fetchone
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import WorkflowRef

    names = dataset.list_blob_names()
    assert len(names) > 20

    # the K6 administrator floor (the shipped ADMIN_DENIED gate mapped
    # onto leg-0): a plain member is refused and NOTHING lands.
    denied = await engine.run(WorkflowRef("btd6.seed_data"),
                              _ctx({}, tier="member"))
    assert denied.outcome != SUCCESS
    assert await btd6_store.count_data_blobs() == 0

    params: dict = {}
    result = await engine.run(WorkflowRef("btd6.seed_data"), _ctx(params))
    assert result.outcome == SUCCESS, result
    assert params["_seed_count"] == len(names)
    assert await btd6_store.count_data_blobs() == len(names)

    # sha256 provenance: the stored digest is the canonical-dump digest.
    row = await btd6_store.get_data_blob_row("towers.json")
    assert row is not None
    body = dataset.read_blob("towers.json")
    want = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"),
    ).hexdigest()
    assert row["sha256"] == want
    # the JSONB body round-trips the committed file.
    stored = row["body"]
    if isinstance(stored, str):
        stored = json.loads(stored)
    assert stored == body

    # "Safe to re-run any time (it upserts)": same names, no growth.
    params2: dict = {}
    result2 = await engine.run(WorkflowRef("btd6.seed_data"), _ctx(params2))
    assert result2.outcome == SUCCESS, result2
    assert params2["_seed_count"] == len(names)
    assert await btd6_store.count_data_blobs() == len(names)

    # one audited row per run on the K7 central audit spine.
    audit = await fetchone(
        "SELECT count(*) AS n FROM audit_log WHERE mutation_type=$1",
        ("btd6_data_seeded",))
    assert int(audit["n"]) == 2


def test_seed_data_op_writes_and_reruns_idempotently():
    async def _body():
        h = await boot_harness()
        try:
            await _seed_twice_and_verify()
        finally:
            await h.close()

    asyncio.run(_body())
