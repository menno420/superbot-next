"""Mining energy persistence (slice 1) — ``get_energy``/``set_energy`` on the
existing ``mining_player_state`` store + migration 0052.

DB-free (the ``_RecordingConn`` SQL-shape pin from
``tests/unit/band6/test_band6_games_substrate.py``): inspects the SQL a fake
connection actually receives, plus a tiny in-memory upsert double for the
round-trip. Oracle semantics: ``disbot/utils/db/games/mining_player_state.py``
@ ``87bbe1d`` — missing row reads ``(0, 0)`` (settles to a full bar); the
write is a PLAIN non-audited/non-money upsert (the fishing-energy posture,
no lock). NO new store row — energy rides ``MINING_PLAYER_STATE_STORE``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

run = asyncio.run

GID, P1 = 1, 42

MIGRATION = Path(__file__).resolve().parents[3] / "migrations" / "0052_mining_energy.sql"


class _RecordingConn:
    """A bare conn double that remembers the SQL + params it was asked to
    run (mirrors tests/unit/band6/test_band6_games_substrate.py)."""

    def __init__(self, row: dict | None = None):
        self.row = row
        self.queries: list[str] = []
        self.params: list[tuple] = []

    async def fetchrow(self, query: str, *params: object):
        self.queries.append(query)
        self.params.append(params)
        return self.row

    async def execute(self, query: str, *params: object):
        self.queries.append(query)
        self.params.append(params)
        return "OK"


class _UpsertConn:
    """An in-memory (user_id, guild_id) -> row upsert double — just enough
    of the 0052 shape for a set/get round-trip."""

    def __init__(self):
        self.rows: dict[tuple, dict] = {}

    async def fetchrow(self, query: str, *params: object):
        return self.rows.get(params[:2])

    async def execute(self, query: str, *params: object):
        user_id, guild_id, energy, updated_at = params
        self.rows[(user_id, guild_id)] = {
            "energy": energy, "energy_updated_at": updated_at}
        return "OK"


# --- get_energy ----------------------------------------------------------------


def test_get_energy_missing_row_reads_zero_zero():
    """Oracle-verbatim missing-row posture: (0, 0) — settle() turns the
    epoch-0 stamp into a full bar, so a fresh player starts full without
    the store knowing MAX_ENERGY."""
    from sb.domain.mining import store

    conn = _RecordingConn(row=None)
    assert run(store.get_energy(P1, GID, conn=conn)) == (0, 0)


def test_get_energy_returns_the_stored_pair_as_ints():
    from sb.domain.mining import store

    conn = _RecordingConn(row={"energy": 59, "energy_updated_at": 1_000})
    assert run(store.get_energy(P1, GID, conn=conn)) == (59, 1_000)


def test_get_energy_is_a_plain_unlocked_text_id_read():
    """Non-money lane: no FOR UPDATE (fishing-energy posture); user ids are
    TEXT on the shipped mining tables (NAME_STABLE)."""
    from sb.domain.mining import store

    conn = _RecordingConn(row=None)
    run(store.get_energy(P1, GID, conn=conn))
    assert len(conn.queries) == 1
    assert "FOR UPDATE" not in conn.queries[0]
    assert "mining_player_state" in conn.queries[0]
    assert conn.params[0] == (str(P1), GID)


# --- set_energy ----------------------------------------------------------------


def test_set_energy_upserts_both_columns():
    from sb.domain.mining import store

    conn = _RecordingConn()
    run(store.set_energy(P1, GID, 59, 1_000, conn=conn))
    (query,) = conn.queries
    assert "INSERT INTO mining_player_state" in query
    assert "ON CONFLICT (user_id, guild_id)" in query
    assert "energy=$3" in query and "energy_updated_at=$4" in query
    assert conn.params[0] == (str(P1), GID, 59, 1_000)


def test_set_energy_never_touches_the_bigint_updated_at():
    """The target's updated_at is a BIGINT epoch (band convention, the
    set_depth precedent) — the oracle's updated_at=now() touch must NOT
    carry over."""
    from sb.domain.mining import store

    conn = _RecordingConn()
    run(store.set_energy(P1, GID, 59, 1_000, conn=conn))
    assert "now()" not in conn.queries[0]


def test_energy_round_trip():
    """set then get returns the settled pair (spend-then-persist shape:
    energy.spend keeps updated_at at the last whole regen tick)."""
    from sb.domain.mining import energy, store

    conn = _UpsertConn()
    spent = energy.spend(energy.EnergyState(60, 0), 1_000)
    run(store.set_energy(P1, GID, spent.current, spent.updated_at, conn=conn))
    assert run(store.get_energy(P1, GID, conn=conn)) == (59, 1_000)
    # a second write overwrites, never accumulates rows
    run(store.set_energy(P1, GID, 60, 2_000, conn=conn))
    assert run(store.get_energy(P1, GID, conn=conn)) == (60, 2_000)
    assert len(conn.rows) == 1


# --- migration 0052 (the DDL pin) ------------------------------------------------


def test_migration_0052_adds_both_energy_columns_default_zero():
    """DEFAULT 0/0 = the faithful missing-row posture on the EXISTING
    mining_player_state table (oracle migration 086 shape) — every
    pre-energy depth-player settles to a full bar on first read."""
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "ALTER TABLE mining_player_state" in sql
    assert "ADD COLUMN IF NOT EXISTS energy            INTEGER NOT NULL DEFAULT 0" in sql
    assert "ADD COLUMN IF NOT EXISTS energy_updated_at BIGINT  NOT NULL DEFAULT 0" in sql


def test_no_new_store_row_energy_rides_mining_player_state():
    """Energy registers NO new StoreSpec — it rides the existing
    MINING_PLAYER_STATE_STORE (erasure already covered by
    mining.erase_subject_state)."""
    from sb.domain.mining import store

    assert store.MINING_PLAYER_STATE_STORE.table == "mining_player_state"
    assert not hasattr(store, "MINING_ENERGY_STORE")
