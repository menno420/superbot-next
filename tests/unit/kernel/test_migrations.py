"""K3 migration runner + CI gate structure tests (spec 05 §3.6)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sb.kernel.db.migrations import (
    MIGRATIONS_DIR,
    MigrationDrift,
    MigrationError,
    _ordered_migration_versions,
    migration_versions_on_disk,
)

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import check_migrations  # noqa: E402


def test_ordered_versions_happy_path() -> None:
    ordered = _ordered_migration_versions(
        ["0002_b.sql", "0001_a.sql", "README.md"],
    )
    assert ordered == [(1, "0001_a.sql"), (2, "0002_b.sql")]


def test_bad_filename_rejected() -> None:
    with pytest.raises(MigrationError):
        _ordered_migration_versions(["001_three_digit.sql"])
    with pytest.raises(MigrationError):
        _ordered_migration_versions(["0001-dash.sql"])
    with pytest.raises(MigrationError):
        _ordered_migration_versions(["0001_CamelCase.sql"])


def test_duplicate_version_rejected() -> None:
    with pytest.raises(MigrationError):
        _ordered_migration_versions(["0001_a.sql", "0001_b.sql"])


def test_gap_rejected() -> None:
    with pytest.raises(MigrationError):
        _ordered_migration_versions(["0001_a.sql", "0003_c.sql"])


def test_chain_must_start_at_0001() -> None:
    with pytest.raises(MigrationError):
        _ordered_migration_versions(["0002_b.sql"])


def test_committed_chain_is_valid() -> None:
    versions = migration_versions_on_disk()
    assert versions == set(range(1, len(versions) + 1))
    assert 1 in versions  # 0001_idempotency_keys.sql shipped at S4


def test_committed_manifest_matches_disk() -> None:
    assert check_migrations.check() == []


def test_checker_flags_edited_file(tmp_path: Path) -> None:
    mig = tmp_path / "0001_a.sql"
    mig.write_text("CREATE TABLE a (x INT);\n", encoding="utf-8")
    manifest = tmp_path / "checksums.json"
    manifest.write_text(json.dumps({
        "0001_a.sql": "sha256:" + hashlib.sha256(b"different bytes").hexdigest(),
    }), encoding="utf-8")
    problems = check_migrations.check(tmp_path, manifest)
    assert any("checksum mismatch" in p for p in problems)


def test_checker_flags_unmanifested_and_missing_files(tmp_path: Path) -> None:
    mig = tmp_path / "0001_a.sql"
    mig.write_text("SELECT 1;\n", encoding="utf-8")
    manifest = tmp_path / "checksums.json"
    manifest.write_text(json.dumps({"0002_gone.sql": "sha256:00"}), encoding="utf-8")
    problems = check_migrations.check(tmp_path, manifest)
    assert any("not in checksums.json" in p for p in problems)
    assert any("absent on disk" in p for p in problems)
    assert any("chain gap" not in p or "0001" not in p for p in problems)


def test_drift_error_types() -> None:
    assert issubclass(MigrationDrift, RuntimeError)
    assert issubclass(MigrationError, RuntimeError)
    assert MIGRATIONS_DIR.name == "migrations"
