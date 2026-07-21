"""Real-Postgres coverage for `ai/policy_store.get_generation`'s malformed
stored-value swallow — the last untested branch of the domain-coercion sweep.

`get_generation` reads the `ai_policy_generation` KV row and coerces it with
`int(str(row["value"]) or 0)` under `except ValueError: return 0`. A corrupt
row (a non-numeric string a stray write or a hand-edit could leave) MUST fold
to the shipped `0` — "degrade, never raise" — rather than blow up the read.
The write twin (`bump_generation`) only ever mints numeric text, so no
DB-free/unit path exercises the malformed leg; this drives it through the
store's OWN pool seam against real Postgres. Skips cleanly without asyncpg /
Postgres exactly like its `tests/integration` siblings (see conftest).

Every assertion was verified against a live run of the real function before
commit.
"""

from __future__ import annotations

import asyncio

from tests.integration.conftest import boot_harness  # noqa: E402

run = asyncio.run

_GID = 900000000000000424


async def _seed(value: str) -> None:
    """Write a raw `ai_policy_generation` row for `_GID` through the store's own
    pool seam (upsert so the helper can be called repeatedly in one body)."""
    from sb.domain.ai.policy_store import AI_POLICY_GENERATION_KEY
    from sb.kernel.db import pool as db

    await db.execute(
        "INSERT INTO guild_settings (guild_id, key, value) VALUES ($1, $2, $3) "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value = EXCLUDED.value",
        (_GID, AI_POLICY_GENERATION_KEY, value))


async def _body() -> None:
    from sb.domain.ai.policy_store import get_generation

    # No row at all -> None (the "no scoped write ever landed" state), NOT 0.
    assert await get_generation(_GID) is None

    # A malformed stored value hits `except ValueError` and folds to 0 — the
    # branch this test exists for. Removing the swallow would raise here.
    await _seed("not-a-number")
    assert await get_generation(_GID) == 0

    # An empty string rides the `str("") or 0` leg -> int(0) -> 0 (distinct from
    # the ValueError leg; both land on 0).
    await _seed("")
    assert await get_generation(_GID) == 0

    # Contrast: a well-formed numeric row reads straight through `int()`, so the
    # swallow above is genuinely the malformed-only path, not a blanket zero.
    await _seed("7")
    assert await get_generation(_GID) == 7


def test_get_generation_folds_malformed_and_empty_rows_to_zero():
    async def _run() -> None:
        harness = await boot_harness()
        try:
            await _body()
        finally:
            await harness.close()

    run(_run())
