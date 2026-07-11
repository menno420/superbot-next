"""Real-Postgres integration fixtures — guarded-absence (D-0003 discipline):
these tests need asyncpg + a reachable Postgres and SKIP cleanly without
either, exactly like `tests/unit/kernel/test_db_pool.py`'s guarded pool
tests. `code-quality`'s required gate installs no runtime deps (asyncpg
absent) so this whole directory reports skipped there by design — the
`golden-parity` named gate DOES install the full lock + provision a real
Postgres service container, so that job is where these tests actually run
(see the `pytest tests/integration -q` step added alongside the existing
`run_golden_parity.py --gate` step).

NOTE: every test in this directory drives its ENTIRE body — harness boot,
work, close — through exactly ONE `asyncio.run()` call. asyncpg pools bind
to the event loop that created them; a fixture that boots the pool under
one `asyncio.run()` and a test body that touches it under another leaves
the pool holding a connection to an already-closed loop (asyncpg then
raises `InterfaceError: another operation is in progress`). A plain async
helper awaited from inside the test's own `asyncio.run()` sidesteps that
entirely — no pytest-asyncio dependency needed.
"""

from __future__ import annotations

import pytest

try:
    import asyncpg  # noqa: F401 — presence probe only, see ASYNCPG_AVAILABLE
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

# NOT `pytest.importorskip("asyncpg")` at module level (found in adversarial
# review): a conftest.py loaded as pytest's "initial conftest" — which is
# exactly what happens when the collection target NAMES this directory
# directly (`pytest tests/integration -q`, the CI invocation this repo's
# workflows use) — is imported through a path that does NOT catch the
# `Skipped` exception `importorskip` raises. Reproduced directly: that
# invocation aborts with a bare traceback and exit code 1, zero tests
# reported — not the clean single-line skip the module previously claimed.
# Collected normally (`pytest tests/ -q`, code-quality's actual invocation)
# the same conftest loads through the ordinary path that DOES catch it, so
# the bug was invisible there — only a direct `pytest tests/integration`
# run (exactly the golden-parity CI steps, and the natural way to verify
# this suite by hand) trips it. The guard now lives INSIDE boot_harness(),
# a plain function call during normal test execution — always caught.


async def boot_harness():
    """A booted, real-Postgres NEW-bot harness — migrations applied, every
    table truncated fresh. Skips (not fails) when asyncpg or Postgres is
    unavailable, matching `run_golden_parity.py`'s own `_replay_binding`
    posture: an environment gap is not a behavior regression. Caller awaits
    `.close()` — always reached: this function closes on ITS OWN failure
    after a successful boot, so a caller's `try/finally: await
    harness.close()` never runs against a harness that was never fully
    opened, and a raised exception here never leaks the pool/global seams
    `Harness.start()` installed."""
    if not ASYNCPG_AVAILABLE:
        pytest.skip("asyncpg not installed — real-Postgres integration "
                    "tests need the full runtime lock (requirements.lock)")

    from sb.adapters.parity.boot import Harness, HarnessBootError

    try:
        h = await Harness.start(require_db=True)
    except HarnessBootError as exc:
        pytest.skip(f"Postgres unavailable for integration tests: {exc}")
        raise AssertionError("unreachable")  # pragma: no cover

    try:
        from parity.harness.dbsnap import reset_database
        from sb.kernel.db import pool as db_pool

        await reset_database(db_pool)
    except Exception:
        await h.close()
        raise
    return h
