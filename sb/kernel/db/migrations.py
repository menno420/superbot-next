"""Fresh-chain migration runner with checksum integrity (K3, spec 05 §3.6).

Ported from shipped `disbot/utils/db/migrations.py` (superbot main 7f7628e1)
with the spec-05 changes:

  - FRESH chain `0001+` (design-spec §5.2 decision 8): NNNN_<snake>.sql, no
    legacy bootstrap DDL (`create_tables` is NOT ported — there is no
    pre-migration schema in this repo; every table ships as a migration);
  - `schema_migrations` gains `checksum TEXT NOT NULL` (sha256 of the file
    bytes) — the ONE change to the ledger shape;
  - `verify_applied_checksums()` runs at boot AFTER applying pending files:
    an edited/absent applied migration raises MigrationDrift -> refuse boot,
    never auto-repair (fork 3: DB != source-of-record is the corruption path);
  - the shipped `pg_advisory_lock` dual-instance serialization is preserved.

CI twin: `tools/check_migrations.py` (numbering + immutability against the
committed `migrations/checksums.json` manifest) catches an edit in the PR,
before it can reach a deploy.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from collections.abc import Iterable
from pathlib import Path

from sb.kernel.db import pool

logger = logging.getLogger("sb.db.migrations")

__all__ = [
    "MigrationDrift",
    "MigrationError",
    "applied_migration_versions",
    "ensure_migrations_table",
    "migration_versions_on_disk",
    "run_migrations",
    "verify_applied_checksums",
]

# Repo-root migrations/ (sb/kernel/db/migrations.py -> parents[3] == repo root).
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"

# Stable 64-bit key for pg_advisory_lock — "sb-next" interpreted as int.
_MIGRATION_ADVISORY_LOCK = 0x73625F6E_65787431

# NNNN_<snake_name>.sql — the fresh-chain contract (0001+), pinned by
# tools/check_migrations.py. group(1)=version, group(2)=name.
_MIGRATION_NAME_RE = re.compile(r"^(\d{4})_([a-z][a-z0-9_]*)\.sql$")


class MigrationError(RuntimeError):
    """The migrations directory is structurally invalid.

    Raised BEFORE any migration runs, so a malformed set fails fast instead
    of silently skipping a file (shipped RC-6 fix, preserved).
    """


class MigrationDrift(RuntimeError):
    """A recorded migration's checksum no longer matches its file on disk —
    an applied migration was edited (or its file is absent). Correctness
    hazard (DB != source-of-record). Refuse boot; never auto-repair.
    """


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ordered_migration_versions(filenames: Iterable[str]) -> list[tuple[int, str]]:
    """Validate `*.sql` migration filenames; return (version, filename) sorted.

    Raises MigrationError when a .sql file does not match NNNN_<snake>.sql,
    when two files share a leading version, or when the chain is not
    contiguous from 0001 (fresh chain — spec 05 §3.6 gate 1). Non-.sql files
    are ignored.
    """
    seen: dict[int, str] = {}
    ordered: list[tuple[int, str]] = []
    for filename in sorted(filenames):
        if not filename.endswith(".sql"):
            continue
        match = _MIGRATION_NAME_RE.match(filename)
        if match is None:
            raise MigrationError(
                f"Migration file does not match NNNN_<snake_name>.sql: {filename!r}",
            )
        version = int(match.group(1))
        if version in seen:
            raise MigrationError(
                f"Duplicate migration version {version:04d}: "
                f"{seen[version]!r} and {filename!r} — the second would never "
                "apply (forward-only; rename, do not duplicate).",
            )
        seen[version] = filename
        ordered.append((version, filename))
    ordered.sort()
    for index, (version, filename) in enumerate(ordered, start=1):
        if version != index:
            raise MigrationError(
                f"Migration chain not contiguous from 0001: expected {index:04d}, "
                f"found {version:04d} ({filename!r}).",
            )
    return ordered


def migration_versions_on_disk() -> set[int]:
    """Versions present as NNNN_*.sql files (diagnostic N/N reporting)."""
    if not MIGRATIONS_DIR.is_dir():
        return set()
    return {
        version
        for version, _ in _ordered_migration_versions(
            p.name for p in MIGRATIONS_DIR.iterdir()
        )
    }


async def applied_migration_versions() -> set[int]:
    """Versions recorded in schema_migrations (applied on this DB)."""
    rows = await pool.fetchall("SELECT version FROM schema_migrations", ())
    return {r["version"] for r in rows}


async def ensure_migrations_table() -> None:
    await pool.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            applied_at  BIGINT  NOT NULL,
            description TEXT    NOT NULL,
            checksum    TEXT    NOT NULL
        )""",
    )


async def run_migrations() -> None:
    """Apply pending migrations under a PostgreSQL advisory lock.

    The session-scoped advisory lock ensures concurrent instances starting
    simultaneously (merge=deploy overlap) do not race to apply the same
    migration — only one process holds the lock; others wait, then see the
    consistent ledger (spec 05 §6 dual-instance rule, shipped behavior).
    """
    if not MIGRATIONS_DIR.is_dir():
        return

    ordered = _ordered_migration_versions(p.name for p in MIGRATIONS_DIR.iterdir())
    p = pool.get()
    async with p.acquire() as conn:
        await conn.execute("SELECT pg_advisory_lock($1)", _MIGRATION_ADVISORY_LOCK)
        try:
            applied = {
                r["version"]
                for r in await conn.fetch(
                    "SELECT version FROM schema_migrations ORDER BY version",
                )
            }
            for version, filename in ordered:
                if version in applied:
                    continue
                data = (MIGRATIONS_DIR / filename).read_bytes()
                sql = data.decode("utf-8")
                description = filename[5:].removesuffix(".sql").replace("_", " ")
                try:
                    async with conn.transaction():
                        await conn.execute(sql)
                        await conn.execute(
                            "INSERT INTO schema_migrations "
                            "(version, applied_at, description, checksum) "
                            "VALUES ($1, $2, $3, $4)",
                            version,
                            int(time.time()),
                            description,
                            _checksum(data),
                        )
                    logger.info("Applied migration %04d: %s", version, description)
                except Exception as exc:
                    logger.error(
                        "Migration %04d failed: %s", version, exc, exc_info=True,
                    )
                    raise
        finally:
            await conn.execute(
                "SELECT pg_advisory_unlock($1)", _MIGRATION_ADVISORY_LOCK,
            )


async def verify_applied_checksums() -> None:
    """Boot integrity gate (spec 05 §3.6): for every recorded version,
    sha256(file_bytes) == stored checksum; mismatch => MigrationDrift.
    A version recorded-but-file-absent => MigrationDrift (a squashed or
    renamed applied file). Runs AFTER applying pending files, BEFORE
    init() returns; MigrationDrift maps to FAILED_STARTUP (§3.9).
    """
    on_disk = {
        version: filename
        for version, filename in (
            _ordered_migration_versions(p.name for p in MIGRATIONS_DIR.iterdir())
            if MIGRATIONS_DIR.is_dir()
            else []
        )
    }
    rows = await pool.fetchall(
        "SELECT version, checksum FROM schema_migrations ORDER BY version", (),
    )
    for row in rows:
        version = row["version"]
        filename = on_disk.get(version)
        if filename is None:
            raise MigrationDrift(
                f"Migration {version:04d} is recorded as applied but its file "
                "is absent on disk (squashed/renamed applied migration).",
            )
        actual = _checksum((MIGRATIONS_DIR / filename).read_bytes())
        if actual != row["checksum"]:
            raise MigrationDrift(
                f"Migration {version:04d} ({filename!r}) was edited after being "
                f"applied: recorded {row['checksum']}, on disk {actual}.",
            )
