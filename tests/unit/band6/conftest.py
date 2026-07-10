"""Band-6 fakes — in-memory games checkpoint store + economy wallet,
monkeypatched over the sole-writer store modules (the band-3/4 pattern).
"""

from __future__ import annotations

import pytest


class FakeEconomy:
    """In-memory wallet + ledger over sb.domain.economy.store."""

    def __init__(self, balances: dict | None = None):
        self.balances = dict(balances or {})   # (user, guild) -> coins
        self.audit: list[dict] = []

    def install(self, monkeypatch):
        from sb.domain.economy import store as econ

        async def get_coins(user_id, guild_id, conn=None):
            return self.balances.get((user_id, guild_id), 0)

        async def credit_coins(conn, *, user_id, guild_id, amount):
            key = (user_id, guild_id)
            self.balances[key] = max(0, self.balances.get(key, 0) + amount)
            return self.balances[key]

        async def try_debit_coins(conn, *, user_id, guild_id, amount):
            key = (user_id, guild_id)
            held = self.balances.get(key, 0)
            if held < amount:
                return None
            self.balances[key] = held - amount
            return self.balances[key]

        async def insert_economy_audit(conn, *, guild_id, user_id, actor_id,
                                       delta, new_balance, reason,
                                       mutation_id=None):
            self.audit.append({"guild_id": guild_id, "user_id": user_id,
                               "actor_id": actor_id, "delta": delta,
                               "new_balance": new_balance, "reason": reason})

        monkeypatch.setattr(econ, "get_coins", get_coins)
        monkeypatch.setattr(econ, "credit_coins", credit_coins)
        monkeypatch.setattr(econ, "try_debit_coins", try_debit_coins)
        monkeypatch.setattr(econ, "insert_economy_audit",
                            insert_economy_audit)
        return self


class FakeGamesStore:
    """In-memory game_state + game_xp over sb.domain.games.store."""

    def __init__(self):
        self.rows: dict[tuple, dict] = {}      # natural key -> row
        self.xp: dict[tuple, dict] = {}        # (user, guild, game) -> row
        self._next_id = 1

    def install(self, monkeypatch):
        from sb.domain.games import store as gs

        def _key(guild_id, user_id, channel_id, subsystem):
            return (guild_id, user_id, channel_id, subsystem)

        async def upsert_checkpoint(conn, *, guild_id, user_id, channel_id,
                                    subsystem, state, version, now):
            key = _key(guild_id, user_id, channel_id, subsystem)
            row = self.rows.get(key)
            rid = row["id"] if row else self._next_id
            if row is None:
                self._next_id += 1
            self.rows[key] = {"id": rid, "guild_id": guild_id,
                              "user_id": user_id, "channel_id": channel_id,
                              "subsystem": subsystem, "state": dict(state),
                              "version": version, "updated_at": now}

        async def fetch_checkpoint(guild_id, user_id, channel_id, subsystem,
                                   conn=None):
            row = self.rows.get(_key(guild_id, user_id, channel_id,
                                     subsystem))
            return dict(row["state"]) if row else None

        async def delete_checkpoint(conn, *, guild_id, user_id, channel_id,
                                    subsystem):
            return 1 if self.rows.pop(
                _key(guild_id, user_id, channel_id, subsystem), None) else 0

        async def fetch_user_checkpoint(guild_id, user_id, subsystem,
                                        conn=None):
            for row in self.rows.values():
                if (row["guild_id"] == guild_id
                        and row["user_id"] == user_id
                        and row["subsystem"] == subsystem):
                    return dict(row, state=dict(row["state"]))
            return None

        async def delete_user_checkpoint(conn, *, guild_id, user_id,
                                         subsystem):
            removed = 0
            for key, row in list(self.rows.items()):
                if (row["guild_id"] == guild_id
                        and row["user_id"] == user_id
                        and row["subsystem"] == subsystem):
                    del self.rows[key]
                    removed += 1
            return removed

        async def delete_checkpoint_by_id(conn, *, row_id):
            for key, row in list(self.rows.items()):
                if row["id"] == row_id:
                    del self.rows[key]
                    return 1
            return 0

        async def lock_rows_for_settlement(conn, *, guild_id, subsystem,
                                           channel_id=None, user_ids=None):
            out = []
            for row in self.rows.values():
                if row["guild_id"] != guild_id:
                    continue
                if row["subsystem"] != subsystem:
                    continue
                if channel_id is not None and row["channel_id"] != channel_id:
                    continue
                if user_ids and row["user_id"] not in user_ids:
                    continue
                out.append(dict(row, state=dict(row["state"])))
            return out

        async def list_active(subsystem, *, guild_id=None, conn=None):
            return [dict(r, state=dict(r["state"]))
                    for r in self.rows.values()
                    if r["subsystem"] == subsystem
                    and (guild_id is None or r["guild_id"] == guild_id)]

        async def list_stale(*, now, cutoff_hours=24, conn=None):
            cutoff = now - cutoff_hours * 3600
            return [dict(r, state=dict(r["state"]))
                    for r in self.rows.values()
                    if r["updated_at"] < cutoff]

        async def add_game_xp(conn, *, user_id, guild_id, game, amount, day,
                              day_xp_add, now):
            key = (user_id, guild_id, game)
            row = self.xp.setdefault(key, {"xp": 0, "day": None, "day_xp": 0})
            row["xp"] += amount
            row["day_xp"] = (row["day_xp"] + day_xp_add
                             if row["day"] == day else day_xp_add)
            row["day"] = day
            return row["xp"]

        async def day_xp_for(user_id, guild_id, game, day, conn=None):
            row = self.xp.get((user_id, guild_id, game))
            if row is None or row["day"] != day:
                return 0
            return row["day_xp"]

        async def total_game_xp(user_id, guild_id, conn=None):
            return sum(r["xp"] for (u, g, _), r in self.xp.items()
                       if u == user_id and g == guild_id)

        async def game_xp_rows(user_id, guild_id, conn=None):
            return [{"game": game, "xp": r["xp"], "day": r["day"],
                     "day_xp": r["day_xp"]}
                    for (u, g, game), r in sorted(
                        self.xp.items(), key=lambda kv: -kv[1]["xp"])
                    if u == user_id and g == guild_id]

        for name, fn in list(locals().items()):
            if callable(fn) and hasattr(gs, name):
                monkeypatch.setattr(gs, name, fn)
        return self


@pytest.fixture
def fake_economy(monkeypatch):
    return FakeEconomy().install(monkeypatch)


@pytest.fixture
def fake_games_store(monkeypatch):
    return FakeGamesStore().install(monkeypatch)
