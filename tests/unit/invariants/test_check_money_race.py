"""tools/check_money_race — the F-001/F-002 money-race lint, pinned
red-then-green against the two PROVEN pre-#217 shapes (farm.collect /
farm.buy_chicken and mining.sell) and their shipped post-#217 fixes.

The fixtures below are the parent-of-`ed8eed34` code, verbatim-ish (only
docstrings trimmed): if the checker ever stops flagging the pre-fix shapes
(RED half) or starts flagging the fixed shapes (GREEN half), these tests
fail — the lint's detection power is itself under regression pin. DB-free:
the checker walks source strings, never imports sb or touches a DB.
"""

from __future__ import annotations

import pytest

from tools.check_money_race import (
    ALLOWLIST,
    KNOWN_RISKS,
    analyze_sources,
    classify_upsert,
    collect_sources,
)

# --------------------------------------------------------------- fixtures
# The pre-#217 farm store: plain-SELECT get_farm (no for_update seam), the
# natural-key set_farm upsert writing caller-computed absolute values.
FARM_STORE_PRE = '''
from sb.kernel.db.pool import execute, fetchall, fetchone


async def get_farm(user_id, guild_id, conn=None):
    row = await fetchone(
        "SELECT chickens, eggs, eggs_updated_at, coop_level FROM "
        "chicken_farm WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    if row is None:
        return 1, 0, 0, 0
    return (int(row["chickens"]), int(row["eggs"]),
            int(row["eggs_updated_at"]), int(row["coop_level"]))


async def set_farm(conn, *, user_id, guild_id, chickens, eggs, now,
                   coop_level):
    await execute(
        "INSERT INTO chicken_farm (user_id, guild_id, chickens, eggs, "
        "eggs_updated_at, coop_level) VALUES ($1,$2,$3,$4,$5,$6) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET chickens=$3, "
        "eggs=$4, eggs_updated_at=$5, coop_level=$6",
        (user_id, guild_id, chickens, eggs, now, coop_level), conn=conn)
'''

# The post-#217 farm store: for_update seam — advisory slot lock on the
# upsert's own natural key + FOR UPDATE on the row itself.
FARM_STORE_POST = '''
from sb.kernel.db.pool import execute, fetchall, fetchone


async def get_farm(user_id, guild_id, conn=None, *, for_update=False):
    if for_update:
        if conn is None:
            raise ValueError("for_update=True requires the caller's conn")
        await execute(
            "SELECT pg_advisory_xact_lock(hashtext($1))",
            (f"farm:slot:{guild_id}:{user_id}",), conn=conn)
    row = await fetchone(
        "SELECT chickens, eggs, eggs_updated_at, coop_level FROM "
        "chicken_farm WHERE user_id=$1 AND guild_id=$2"
        + (" FOR UPDATE" if for_update else ""),
        (user_id, guild_id), conn=conn)
    if row is None:
        return 1, 0, 0, 0
    return (int(row["chickens"]), int(row["eggs"]),
            int(row["eggs_updated_at"]), int(row["coop_level"]))


async def set_farm(conn, *, user_id, guild_id, chickens, eggs, now,
                   coop_level):
    await execute(
        "INSERT INTO chicken_farm (user_id, guild_id, chickens, eggs, "
        "eggs_updated_at, coop_level) VALUES ($1,$2,$3,$4,$5,$6) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET chickens=$3, "
        "eggs=$4, eggs_updated_at=$5, coop_level=$6",
        (user_id, guild_id, chickens, eggs, now, coop_level), conn=conn)
'''

# A minimal wager module so `wager.credit_in_txn` resolves as the money seed
# does at HEAD (the seed also matches by NAME, but keep the import real).
WAGER_STUB = '''
async def credit_in_txn(conn, *, guild_id, user_id, amount, reason,
                        actor_id):
    return 0


async def debit_in_txn(conn, *, guild_id, user_id, amount, reason,
                       actor_id):
    return 0
'''

FARM_OPS_PRE_COLLECT = '''
from sb.domain.farm import core, store
from sb.domain.games import wager


async def _record_collect(conn, ctx):
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn)
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    if settled.eggs <= 0:
        raise ValidatorError("empty coop")
    payout = core.collect_value(settled.eggs)
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=payout,
        reason="farm:collect", actor_id=uid)
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens, eggs=0, now=now,
                         coop_level=settled.coop_level)
    return balance


async def _record_buy_chicken(conn, ctx):
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn)
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    price = core.chicken_price(chickens)
    balance = await wager.debit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=price,
        reason="farm:buy_chicken", actor_id=uid)
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens + 1, eggs=settled.eggs,
                         now=now, coop_level=settled.coop_level)
    return balance
'''

FARM_OPS_POST_COLLECT = '''
from sb.domain.farm import core, store
from sb.domain.games import wager


async def _record_collect(conn, ctx):
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn,
                                                    for_update=True)
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    if settled.eggs <= 0:
        raise ValidatorError("empty coop")
    payout = core.collect_value(settled.eggs)
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=payout,
        reason="farm:collect", actor_id=uid)
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens, eggs=0, now=now,
                         coop_level=settled.coop_level)
    return balance


async def _record_buy_chicken(conn, ctx):
    uid, gid, now = _ids(ctx)
    chickens, eggs, ts, coop = await store.get_farm(uid, gid, conn=conn,
                                                    for_update=True)
    settled = core.settle(_stored(now, chickens, eggs, ts, coop), now)
    price = core.chicken_price(chickens)
    balance = await wager.debit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=price,
        reason="farm:buy_chicken", actor_id=uid)
    await store.set_farm(conn, user_id=uid, guild_id=gid,
                         chickens=settled.chickens + 1, eggs=settled.eggs,
                         now=now, coop_level=settled.coop_level)
    return balance
'''

# The pre-#217 mining store + sell leg: plain-SELECT holdings load, the
# GREATEST(0, …) decrement floor absorbing the loser's decrement, credit via
# the local _sell_rows helper (money reached TRANSITIVELY).
MINING_STORE_PRE = '''
from sb.kernel.db.pool import execute, fetchall, fetchone


async def get_mining_inventory(user_id, guild_id, conn=None):
    rows = await fetchall(
        "SELECT item_name, quantity FROM mining_inventory WHERE "
        "user_id=$1 AND guild_id=$2 AND quantity > 0",
        (str(user_id), guild_id), conn=conn)
    return {str(r["item_name"]): int(r["quantity"]) for r in rows}


async def update_mining_item(conn, *, user_id, guild_id, item, delta):
    row = await fetchone(
        "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
        "quantity) VALUES ($1,$2,$3,GREATEST(0,$4)) "
        "ON CONFLICT (user_id, guild_id, item_name) DO UPDATE SET "
        "quantity = GREATEST(0, mining_inventory.quantity + $4) "
        "RETURNING quantity",
        (str(user_id), guild_id, item, delta), conn=conn)
    return int(row["quantity"]) if row else 0
'''

MINING_STORE_POST = '''
from sb.kernel.db.pool import execute, fetchall, fetchone


async def get_mining_inventory(user_id, guild_id, conn=None, *,
                               for_update=False):
    if for_update and conn is None:
        raise ValueError("for_update=True requires the caller's conn")
    rows = await fetchall(
        "SELECT item_name, quantity FROM mining_inventory WHERE "
        "user_id=$1 AND guild_id=$2 AND quantity > 0"
        + (" ORDER BY item_name FOR UPDATE" if for_update else ""),
        (str(user_id), guild_id), conn=conn)
    return {str(r["item_name"]): int(r["quantity"]) for r in rows}


async def update_mining_item(conn, *, user_id, guild_id, item, delta):
    row = await fetchone(
        "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
        "quantity) VALUES ($1,$2,$3,GREATEST(0,$4)) "
        "ON CONFLICT (user_id, guild_id, item_name) DO UPDATE SET "
        "quantity = GREATEST(0, mining_inventory.quantity + $4) "
        "RETURNING quantity",
        (str(user_id), guild_id, item, delta), conn=conn)
    return int(row["quantity"]) if row else 0
'''

MINING_OPS_PRE_SELL = '''
from sb.domain.games import wager
from sb.domain.mining import market, store


async def _sell_rows(conn, ctx, rows):
    uid, gid, _ = _ids(ctx)
    total = 0
    for name, qty, price in rows:
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=name, delta=-qty)
        total += qty * price
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=total,
        reason="mining:sell_ore", actor_id=uid)
    return {"earned": total, "balance": balance}


async def _record_sell(conn, ctx):
    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    qty = _qty_from(ctx)
    price = market.sell_price(item)
    held = (await store.get_mining_inventory(uid, gid,
                                             conn=conn)).get(item, 0)
    if held < qty:
        raise ValidatorError("not enough")
    after = await _sell_rows(conn, ctx, [(item, qty, price)])
    return after
'''

MINING_OPS_POST_SELL = '''
from sb.domain.games import wager
from sb.domain.mining import market, store


async def _sell_rows(conn, ctx, rows):
    uid, gid, _ = _ids(ctx)
    total = 0
    for name, qty, price in rows:
        await store.update_mining_item(conn, user_id=uid, guild_id=gid,
                                       item=name, delta=-qty)
        total += qty * price
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=total,
        reason="mining:sell_ore", actor_id=uid)
    return {"earned": total, "balance": balance}


async def _record_sell(conn, ctx):
    uid, gid, _ = _ids(ctx)
    item = _item_from(ctx)
    qty = _qty_from(ctx)
    price = market.sell_price(item)
    held = (await store.get_mining_inventory(
        uid, gid, conn=conn, for_update=True)).get(item, 0)
    if held < qty:
        raise ValidatorError("not enough")
    after = await _sell_rows(conn, ctx, [(item, qty, price)])
    return after
'''


def _farm_modules(store_src: str, ops_src: str) -> dict[str, str]:
    return {
        "sb/domain/farm/store.py": store_src,
        "sb/domain/farm/ops.py": ops_src,
        "sb/domain/games/wager.py": WAGER_STUB,
    }


def _mining_modules(store_src: str, ops_src: str) -> dict[str, str]:
    return {
        "sb/domain/mining/store.py": store_src,
        "sb/domain/mining/ops.py": ops_src,
        "sb/domain/games/wager.py": WAGER_STUB,
    }


# ------------------------------------------------------------ RED (pre-#217)
class TestRedOnProvenPreFixShapes:
    def test_farm_collect_pre_fix_flags_read_then_settle(self):
        findings = analyze_sources(
            _farm_modules(FARM_STORE_PRE, FARM_OPS_PRE_COLLECT))
        collect = [f for f in findings
                   if f.func == "_record_collect" and f.rule == "A"]
        assert collect, (
            "the pre-#217 farm.collect double-credit shape (plain-SELECT "
            "get_farm -> credit_in_txn) MUST be flagged rule A"
        )
        assert "unlocked read `get_farm`" in collect[0].message

    def test_farm_buy_chicken_pre_fix_flags_unfenced_upsert(self):
        findings = analyze_sources(
            _farm_modules(FARM_STORE_PRE, FARM_OPS_PRE_COLLECT))
        buy = {(f.func, f.rule) for f in findings}
        # the first-insert race: debit + set_farm natural-key upsert with
        # neither a locking read nor an advisory fence
        assert ("_record_buy_chicken", "B") in buy
        assert ("_record_buy_chicken", "A") in buy

    def test_mining_sell_pre_fix_flags_transitive_credit(self):
        findings = analyze_sources(
            _mining_modules(MINING_STORE_PRE, MINING_OPS_PRE_SELL))
        sell = [f for f in findings
                if f.func == "_record_sell" and f.rule == "A"]
        assert sell, (
            "the pre-#217 mining.sell double-payout shape (plain-SELECT "
            "holdings -> credit via the local _sell_rows helper) MUST be "
            "flagged rule A — money is reached transitively"
        )
        assert "get_mining_inventory" in sell[0].message


# ---------------------------------------------------------- GREEN (post-#217)
class TestGreenOnShippedFixes:
    def test_farm_post_fix_is_clean(self):
        findings = analyze_sources(
            _farm_modules(FARM_STORE_POST, FARM_OPS_POST_COLLECT))
        assert findings == [], [f.message for f in findings]

    def test_mining_post_fix_is_clean(self):
        findings = analyze_sources(
            _mining_modules(MINING_STORE_POST, MINING_OPS_POST_SELL))
        assert findings == [], [f.message for f in findings]

    def test_atomic_self_referential_upsert_never_flags(self):
        # credit_coins' `coins = GREATEST(0, economy_balances.coins + $3)`
        # is an atomic read-modify-write — rule B must not fire on it.
        assert classify_upsert(
            "INSERT INTO economy_balances (user_id, guild_id, coins) "
            "VALUES ($1, $2, GREATEST(0, $3)) "
            "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
            "coins = GREATEST(0, economy_balances.coins + $3) RETURNING coins"
        ) == "atomic"

    def test_value_carrying_upsert_classifies_value(self):
        assert classify_upsert(
            "INSERT INTO chicken_farm (user_id, guild_id, chickens) "
            "VALUES ($1,$2,$3) "
            "ON CONFLICT (user_id, guild_id) DO UPDATE SET chickens=$3"
        ) == "value"

    def test_do_nothing_upsert_classifies_atomic(self):
        assert classify_upsert(
            "INSERT INTO economy (user_id, guild_id) VALUES ($1, $2) "
            "ON CONFLICT DO NOTHING"
        ) == "atomic"


# ------------------------------------------------------- real-tree baseline
class TestRealTreeBaseline:
    def test_head_findings_are_all_dispositioned(self):
        """Every finding at HEAD is either ALLOWLIST (verified safe) or
        KNOWN_RISKS (ledgered, never called safe) — and no row is stale."""
        findings = analyze_sources(collect_sources())
        keys = {f.key for f in findings}
        dispositioned = set(ALLOWLIST) | set(KNOWN_RISKS)
        assert keys <= dispositioned, sorted(keys - dispositioned)
        assert dispositioned <= keys, sorted(dispositioned - keys)

    def test_allow_and_risk_tables_are_disjoint_and_justified(self):
        assert not (set(ALLOWLIST) & set(KNOWN_RISKS))
        for reason in list(ALLOWLIST.values()) + list(KNOWN_RISKS.values()):
            assert isinstance(reason, str) and len(reason) > 20

    def test_main_exit_zero_on_head(self, capsys):
        from tools.check_money_race import main
        assert main([]) == 0
        out = capsys.readouterr().out
        assert "check_money_race: OK" in out
        # the KNOWN_RISKS ledger is EMPTY at HEAD (the
        # enter_tournament_in_txn row was fixed and cleared — advisory
        # slot lock + existence check before the debit, proven
        # red-then-green in tests/integration/test_tournament_entry_race
        # .py); a fixed site must never leave a loud line behind.
        assert "0 ledgered known-risk site(s)" in out
        assert "KNOWN-RISK (ledgered, NOT safe)" not in out
