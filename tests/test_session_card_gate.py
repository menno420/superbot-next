"""Born-red session-card hold — regression pin for the CI gate seam.

The bug this pins (PRs #466/#477): no required CI check graded the
session card a PR actually shipped — ci.yml's bare ``check --strict``
fell back to newest-by-mtime card selection, which a fresh CI checkout
flattens, so a PR whose OWN card said ``in-progress`` showed all-green
checks. The fix routes card enforcement through
``.github/workflows/substrate-gate.yml`` (installed byte-for-byte from
``.substrate/ci/substrate-gate.yml``), whose added-card lane invokes
exactly the CLI seam exercised here.

These tests drive that SAME seam via subprocess — ``python3
bootstrap.py check --strict --session-log
.sessions/__born-red-card-added__.md --added-card <card>`` with
cwd=repo root — so they fail if the hold regresses anywhere along it:
flag parsing, ``check_added_card``, or the exit-code wiring. Full
``check --strict`` runs in ~1-2 s here, so no narrower invocation is
needed. The temp cards live under pytest's tmp_path (never
``.sessions/``), and a fixture snapshots/restores the tracked
``.substrate/guard-fires.jsonl`` telemetry the finding loop appends
to, so the working tree stays byte-clean after a run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_FIRES = REPO_ROOT / ".substrate" / "guard-fires.jsonl"

BORN_RED_SENTINEL = ".sessions/__born-red-card-added__.md"

IN_PROGRESS_CARD = """\
# 2026-01-01 — test: born-red hold regression pin (in-progress)

> **Status:** `in-progress`

- **📊 Model:** `test-fixture` · regression pin, never a real session.

## Scope

Synthetic mid-flight card: the added-card lane must HOLD it red.
"""

COMPLETE_CARD = """\
# 2026-01-01 — test: born-red hold regression pin (complete)

> **Status:** `complete`

- **📊 Model:** `test-fixture` · regression pin, never a real session.

## Scope

Synthetic finished close-out card: the added-card lane must pass it.

## 💡 Session idea

None — synthetic fixture.

## ⟲ Previous-session review

None — synthetic fixture (previous-session review marker needle).
"""


@pytest.fixture()
def restore_guard_fires():
    """Snapshot/restore the tracked telemetry file the finding loop appends to."""
    before = GUARD_FIRES.read_bytes() if GUARD_FIRES.exists() else None
    yield
    if before is not None:
        GUARD_FIRES.write_bytes(before)
    elif GUARD_FIRES.exists():
        GUARD_FIRES.unlink()


def run_added_card_gate(card: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the exact CLI seam substrate-gate's added-card lane runs in CI."""
    return subprocess.run(
        [
            sys.executable,
            "bootstrap.py",
            "check",
            "--strict",
            "--session-log",
            BORN_RED_SENTINEL,
            "--added-card",
            str(card),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_added_in_progress_card_holds_red(tmp_path, restore_guard_fires):
    card = tmp_path / "2026-01-01-born-red-fixture.md"
    card.write_text(IN_PROGRESS_CARD, encoding="utf-8")
    result = run_added_card_gate(card)
    output = result.stdout + result.stderr
    assert result.returncode != 0, (
        "born-red hold REGRESSED: an added in-progress card passed the "
        f"added-card gate.\n{output}"
    )
    assert "born-red HOLD" in output, output
    assert "holds the merge red until the card flips complete" in output, output


def test_added_complete_card_passes(tmp_path, restore_guard_fires):
    card = tmp_path / "2026-01-01-complete-fixture.md"
    card.write_text(COMPLETE_CARD, encoding="utf-8")
    result = run_added_card_gate(card)
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        "a grammar-complete added card must pass the added-card gate "
        f"(exit {result.returncode}).\n{output}"
    )
    assert "born-red HOLD" not in output, output
