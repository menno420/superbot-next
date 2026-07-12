"""tools/check_settle_once — the V010 settle-once guard (contract c),
pinned red-then-green against the PROVEN shapes: the pre-#133 tournament
free-branch credit without the ``clear_active`` rowcount gate, the
gc-refund credit not gated on the delete count, and the shipped fixed
shapes verbatim (the #133 check-and-set, the gc delete-then-if, the
fenced-load row-consumption settle). Plus the ledger hygiene pins
(stale-row-is-RED) and the telemetry-line format the warn->red
graduation will rely on. Hermetic: in-memory fixture sources through the
analyze seam — never imports sb, never touches a DB, no manifest imports.
"""

from __future__ import annotations

import re

import pytest

from tools.check_money_race import collect_sources
from tools.check_settle_once import (
    ALLOWLIST,
    KNOWN_RISKS,
    REARM_SITES,
    SETTLE_SITES,
    SettleAnalyzer,
    analyze_sources,
    run_check,
)

# --------------------------------------------------------------- fixtures
# Minimal stand-ins for the real seams: names and lock/write markers match
# HEAD (the checker resolves by name and classifies by SQL markers).
FLAG_STUB = '''
async def set_active(conn, *, guild_id, game):
    await execute(
        "INSERT INTO guild_settings (guild_id, key, value) VALUES ($1,$2,$3) "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value = EXCLUDED.value",
        (guild_id, "active_tournament", game), conn=conn)


async def clear_active(conn, *, guild_id):
    result = await execute(
        "DELETE FROM guild_settings WHERE guild_id = $1 AND key = $2",
        (guild_id, "active_tournament"), conn=conn)
    return int(str(result).rsplit(" ", 1)[-1])
'''

GAMES_STORE_STUB = '''
async def fetch_user_checkpoint(guild_id, user_id, subsystem, conn=None):
    return await fetchone(
        "SELECT id, state FROM game_state WHERE guild_id=$1 AND user_id=$2 "
        "AND subsystem=$3 FOR UPDATE",
        (guild_id, user_id, subsystem), conn=conn)


async def delete_user_checkpoint(conn, *, guild_id, user_id, subsystem):
    await execute(
        "DELETE FROM game_state WHERE guild_id=$1 AND user_id=$2 "
        "AND subsystem=$3", (guild_id, user_id, subsystem), conn=conn)


async def delete_checkpoint_by_id(conn, *, row_id):
    result = await execute(
        "DELETE FROM game_state WHERE id = $1", (row_id,), conn=conn)
    return int(str(result).rsplit(" ", 1)[-1])
'''

ECON_STORE_STUB = '''
async def credit_coins(conn, *, user_id, guild_id, amount):
    row = await fetchone(
        "INSERT INTO economy_balances (user_id, guild_id, coins) "
        "VALUES ($1, $2, GREATEST(0, $3)) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "coins = GREATEST(0, economy_balances.coins + $3) RETURNING coins",
        (user_id, guild_id, amount), conn=conn)
    return int(row["coins"]) if row else 0
'''

WAGER_STUB = '''
from sb.domain.economy import store as economy_store


async def credit_in_txn(conn, *, guild_id, user_id, amount, reason,
                        actor_id):
    return await economy_store.credit_coins(
        conn, user_id=user_id, guild_id=guild_id, amount=amount)
'''

# The pre-#133 defect shape: the free-branch consolation credit runs with
# NO gate on the atomic flag consume (clear_active's rowcount unused) —
# two racing champion resolutions both pay.
PAYOUT_PRE_133 = '''
from sb.domain.games import tournament_flag, wager
from sb.spec.refs import workflow


@workflow("demo.record_tournament_payout")
async def _record_tournament_payout(conn, ctx):
    gid = int(ctx.guild_id or 0)
    winner = int(ctx.params["winner_id"])
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=winner, amount=100,
        reason="demo:tournament_free_reward", actor_id=winner)
    await tournament_flag.clear_active(conn, guild_id=gid)
    return balance
'''

# The shipped #133 fix shape verbatim: the flag-row delete runs FIRST and
# the settle keys on its atomic row-deletion count.
PAYOUT_POST_133 = '''
from sb.domain.games import tournament_flag, wager
from sb.spec.refs import workflow


@workflow("demo.record_tournament_payout")
async def _record_tournament_payout(conn, ctx):
    gid = int(ctx.guild_id or 0)
    winner = int(ctx.params["winner_id"])
    cleared = await tournament_flag.clear_active(conn, guild_id=gid)
    if not cleared:
        return 0
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=winner, amount=100,
        reason="demo:tournament_free_reward", actor_id=winner)
    return balance
'''

# The gc-refund defect twin: credit NOT gated on the delete count.
GC_UNGATED = '''
from sb.domain.games import store, wager
from sb.spec.refs import workflow


@workflow("demo.record_gc_sweep_row")
async def _record_gc_sweep_row(conn, ctx):
    row = dict(ctx.params["row"])
    bet = int((row.get("state") or {}).get("bet", 0) or 0)
    deleted = await store.delete_checkpoint_by_id(conn,
                                                  row_id=int(row["id"]))
    balance = await wager.credit_in_txn(
        conn, guild_id=int(row["guild_id"]), user_id=int(row["user_id"]),
        amount=bet, reason="games:gc_refund", actor_id=int(row["user_id"]))
    return balance
'''

# The shipped gc_sweep shape: delete FIRST, credit ONLY when this txn
# removed the row.
GC_GATED = '''
from sb.domain.games import store, wager
from sb.spec.refs import workflow


@workflow("demo.record_gc_sweep_row")
async def _record_gc_sweep_row(conn, ctx):
    row = dict(ctx.params["row"])
    bet = row.get("state", {}).get("bet")
    deleted = await store.delete_checkpoint_by_id(conn,
                                                  row_id=int(row["id"]))
    if deleted and isinstance(bet, int) and bet > 0:
        await wager.credit_in_txn(
            conn, guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]), amount=bet,
            reason="games:gc_refund", actor_id=int(row["user_id"]))
    return deleted
'''

# The fenced row-consumption settle (the blackjack solo shape): FOR-UPDATE
# load via the store seam, settle, row delete in the SAME function.
SOLO_RC = '''
from sb.domain.games import store, wager
from sb.spec.refs import workflow


async def _load_solo(conn, gid, uid):
    row = await store.fetch_user_checkpoint(gid, uid, "demo_solo",
                                            conn=conn)
    if row is None:
        raise ValidatorError("expired")
    return row["state"]


@workflow("demo.record_solo_stand")
async def _record_solo_stand(conn, ctx):
    uid, gid = int(ctx.actor.user_id), int(ctx.guild_id or 0)
    state = await _load_solo(conn, gid, uid)
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=int(state["bet"]),
        reason="demo:solo_win", actor_id=uid)
    await store.delete_user_checkpoint(conn, guild_id=gid, user_id=uid,
                                       subsystem="demo_solo")
    return balance
'''

# The unfenced twin of SOLO_RC (no FOR-UPDATE load): must NOT pass as RC.
SOLO_UNFENCED = '''
from sb.domain.games import store, wager
from sb.spec.refs import workflow


async def _load_solo_plain(conn, gid, uid):
    row = await fetchone(
        "SELECT id, state FROM game_state WHERE guild_id=$1 AND user_id=$2",
        (gid, uid), conn=conn)
    return row["state"]


@workflow("demo.record_solo_stand")
async def _record_solo_stand(conn, ctx):
    uid, gid = int(ctx.actor.user_id), int(ctx.guild_id or 0)
    state = await _load_solo_plain(conn, gid, uid)
    balance = await wager.credit_in_txn(
        conn, guild_id=gid, user_id=uid, amount=int(state["bet"]),
        reason="demo:solo_win", actor_id=uid)
    await store.delete_user_checkpoint(conn, guild_id=gid, user_id=uid,
                                       subsystem="demo_solo")
    return balance
'''

# A tournament-open leg (no money) whose set_active call is the ledgered
# re-arm site.
OPEN_LEG = '''
from sb.domain.games import tournament_flag
from sb.spec.refs import workflow


@workflow("demo.record_tournament_open")
async def _record_tournament_open(conn, ctx):
    await tournament_flag.set_active(conn, guild_id=int(ctx.guild_id or 0),
                                     game="demo")
    return True
'''

# A money-fixpoint helper reachable from NO @workflow leg — the
# undeclared-money-path (cogs/-drift) class.
ORPHAN_MONEY = '''
from sb.domain.games import wager


async def _pay_bonus(conn, *, guild_id, user_id):
    return await wager.credit_in_txn(
        conn, guild_id=guild_id, user_id=user_id, amount=10,
        reason="demo:bonus", actor_id=user_id)
'''


def _modules(ops_src: str, *, ops_path: str = "sb/domain/demo/ops.py",
             extra: dict[str, str] | None = None) -> dict[str, str]:
    mods = {
        "sb/domain/games/tournament_flag.py": FLAG_STUB,
        "sb/domain/games/store.py": GAMES_STORE_STUB,
        "sb/domain/games/wager.py": WAGER_STUB,
        "sb/domain/economy/store.py": ECON_STORE_STUB,
        ops_path: ops_src,
    }
    if extra:
        mods.update(extra)
    return mods


# Fixture-scoped settle-site trust anchors (the real ledger points at the
# real tree; run_check over fixtures needs rows that resolve there).
FIX_SETTLE_SITES = {
    ("sb/domain/games/tournament_flag.py", "clear_active"):
        ("consume", "flag-row delete returning the rowcount (#133)"),
    ("sb/domain/games/store.py", "delete_checkpoint_by_id"):
        ("consume", "by-id delete returning the rowcount (gc gate)"),
}


def _root(report, func):
    matches = [r for r in report.roots if r.func == func]
    assert matches, f"no root {func!r} derived — enumeration broke"
    return matches[0]


# --------------------------------------------------------- RED (pre-fix shapes)
class TestRedOnProvenPreFixShapes:
    def test_pre_133_free_branch_credit_warns(self):
        report = analyze_sources(_modules(PAYOUT_PRE_133), FIX_SETTLE_SITES)
        root = _root(report, "_record_tournament_payout")
        assert root.klass == "warn", (
            "the pre-#133 shape (consolation credit with the clear_active "
            "rowcount unused) MUST classify warn")
        assert any(nm == "credit_in_txn" for _, nm in root.warn_events)

    def test_gc_refund_not_gated_on_delete_count_warns(self):
        report = analyze_sources(_modules(GC_UNGATED), FIX_SETTLE_SITES)
        root = _root(report, "_record_gc_sweep_row")
        assert root.klass == "warn", (
            "a gc refund credit not dominated by a branch on the delete "
            "rowcount MUST classify warn")

    def test_unfenced_load_then_settle_warns(self):
        report = analyze_sources(_modules(SOLO_UNFENCED), FIX_SETTLE_SITES)
        root = _root(report, "_record_solo_stand")
        assert root.klass == "warn", (
            "a plain-SELECT load before the settle must NOT pass as "
            "row-consumption — the fence is the point")

    def test_unledgered_warn_prints_but_exits_zero(self):
        sources = _modules(PAYOUT_PRE_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist={}, known_risks={})
        assert code == 0, "warn-first: classification misses never red"
        assert any(line.startswith("WARN ") and "credit_in_txn" in line
                   for line in lines)


# ------------------------------------------------------- GREEN (shipped shapes)
class TestGreenOnShippedShapes:
    def test_post_133_check_and_set_classifies_cas(self):
        report = analyze_sources(_modules(PAYOUT_POST_133), FIX_SETTLE_SITES)
        root = _root(report, "_record_tournament_payout")
        assert root.klass == "cas"
        assert root.warn_events == []

    def test_gc_delete_then_if_classifies_cas(self):
        report = analyze_sources(_modules(GC_GATED), FIX_SETTLE_SITES)
        assert _root(report, "_record_gc_sweep_row").klass == "cas"

    def test_fenced_load_plus_consume_classifies_rc(self):
        report = analyze_sources(_modules(SOLO_RC), FIX_SETTLE_SITES)
        assert _root(report, "_record_solo_stand").klass == "rc"

    def test_green_tree_exits_zero_with_clean_summary(self):
        sources = _modules(PAYOUT_POST_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist={}, known_risks={})
        assert code == 0
        assert not any(line.startswith(("WARN ", "RED ")) for line in lines)
        assert lines[-1] == "check_settle_once: OK"


# ----------------------------------------------------------- root derivation
class TestRootDerivation:
    def test_undecorated_money_helper_is_not_a_root(self):
        report = analyze_sources(_modules(SOLO_RC), FIX_SETTLE_SITES)
        assert not any(r.func == "_load_solo" for r in report.roots)

    def test_orphan_money_function_is_an_undeclared_path(self):
        report = analyze_sources(
            _modules(PAYOUT_POST_133,
                     extra={"sb/domain/demo/bonus.py": ORPHAN_MONEY}),
            FIX_SETTLE_SITES)
        assert ("sb/domain/demo/bonus.py", "_pay_bonus") in {
            (m, f) for m, f, _ in report.undeclared}
        analyzer = SettleAnalyzer(
            _modules(PAYOUT_POST_133,
                     extra={"sb/domain/demo/bonus.py": ORPHAN_MONEY}),
            FIX_SETTLE_SITES)
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist={}, known_risks={})
        assert code == 0                       # warn-first
        assert any("undeclared money path" in line for line in lines)


# --------------------------------------------------------------- re-arm ledger
class TestRearmLedger:
    def test_matching_rearm_row_is_green(self):
        sources = _modules(PAYOUT_POST_133,
                           extra={"sb/domain/demo/open.py": OPEN_LEG})
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        rearm = {("sb/domain/demo/open.py", "_record_tournament_open",
                  "set_active"): "re-arms the demo flag row"}
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites=rearm, allowlist={}, known_risks={})
        assert code == 0
        assert not any("STALE-ROW REARM_SITES" in line for line in lines)

    def test_stale_rearm_row_is_red(self):
        sources = _modules(PAYOUT_POST_133,
                           extra={"sb/domain/demo/open.py": OPEN_LEG})
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        rearm = {("sb/domain/demo/open.py", "_record_tournament_open",
                  "set_farm"): "names a callee the leg never calls"}
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites=rearm, allowlist={}, known_risks={})
        assert code == 1
        assert any("STALE-ROW REARM_SITES" in line and "set_farm" in line
                   for line in lines)


# --------------------------------------------------------------- ledger hygiene
class TestLedgerHygiene:
    def test_stale_allowlist_row_is_red(self):
        sources = _modules(PAYOUT_POST_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        stale = {("sb/domain/demo/ops.py", "_record_tournament_payout"):
                 "matches a GREEN root, not a warn — must go stale"}
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist=stale, known_risks={})
        assert code == 1
        assert any("STALE-ROW ALLOWLIST" in line for line in lines)

    def test_fixed_known_risk_row_is_red(self):
        sources = _modules(PAYOUT_POST_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        stale = {("sb/domain/demo/ops.py", "_record_tournament_payout"):
                 "the risk was fixed by the #133 shape — row must die"}
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist={}, known_risks=stale)
        assert code == 1
        assert any("STALE-ROW KNOWN_RISKS" in line for line in lines)

    def test_ledgered_known_risk_prints_loud_but_green(self):
        sources = _modules(PAYOUT_PRE_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        risks = {("sb/domain/demo/ops.py", "_record_tournament_payout"):
                 "the pre-#133 shape, ledgered for a named fix"}
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist={}, known_risks=risks)
        assert code == 0
        assert any(line.startswith("KNOWN-RISK (ledgered, NOT safe)")
                   for line in lines)

    def test_stale_settle_site_row_is_red(self):
        sources = _modules(PAYOUT_POST_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        sites = dict(FIX_SETTLE_SITES)
        sites[("sb/domain/games/store.py", "no_such_guard")] = (
            "consume", "points at nothing")
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=sites,
            rearm_sites={}, allowlist={}, known_risks={})
        assert code == 1
        assert any("STALE-ROW SETTLE_SITES" in line for line in lines)


# ------------------------------------------------------------------- telemetry
_SUMMARY = re.compile(
    r"^settle_once: \d+ roots — RC:\d+ CAS:\d+ CW:\d+ "
    r"allowlisted:\d+ known-risk:\d+ warn:\d+$")


class TestTelemetryLine:
    def test_summary_line_format_pin(self):
        sources = _modules(PAYOUT_POST_133)
        analyzer = SettleAnalyzer(sources, FIX_SETTLE_SITES)
        code, lines = run_check(
            analyzer, analyzer.report(), settle_sites=FIX_SETTLE_SITES,
            rearm_sites={}, allowlist={}, known_risks={})
        summary = [line for line in lines if _SUMMARY.match(line)]
        assert len(summary) == 1, lines
        assert summary[0] == ("settle_once: 1 roots — RC:0 CAS:1 CW:0 "
                              "allowlisted:0 known-risk:0 warn:0")


# ------------------------------------------------------- real-tree baseline
class TestRealTreeBaseline:
    def test_every_root_is_guarded_or_ledgered_at_head(self):
        report = analyze_sources(collect_sources())
        warn_keys = {r.key for r in report.roots if r.klass == "warn"}
        dispositioned = set(ALLOWLIST) | set(KNOWN_RISKS)
        assert warn_keys <= dispositioned, sorted(warn_keys - dispositioned)
        assert dispositioned <= warn_keys, sorted(dispositioned - warn_keys)

    def test_no_undeclared_money_paths_at_head(self):
        report = analyze_sources(collect_sources())
        assert report.undeclared == []

    def test_every_rearm_site_resolves_at_head(self):
        analyzer = SettleAnalyzer(collect_sources())
        for (module, func, callee) in REARM_SITES:
            info = analyzer.modules.get(module, {}).get(func)
            assert info is not None, (module, func)
            assert callee in {c.name for c in info.calls}, (module, func,
                                                            callee)

    def test_ledger_tables_disjoint_and_justified(self):
        assert not (set(ALLOWLIST) & set(KNOWN_RISKS))
        for reason in (list(ALLOWLIST.values()) + list(KNOWN_RISKS.values())
                       + list(REARM_SITES.values())
                       + [why for _, why in SETTLE_SITES.values()]):
            assert isinstance(reason, str) and len(reason) > 20

    def test_main_exit_zero_on_head(self, capsys):
        from tools.check_settle_once import main
        assert main([]) == 0
        out = capsys.readouterr().out
        assert "check_settle_once: OK" in out
        # karma record_give is the ONE ledgered known risk at HEAD — loud
        # on every run, never silently green.
        assert "KNOWN-RISK (ledgered, NOT safe) sb/domain/karma/ops.py" in out
        summary = [line for line in out.splitlines() if _SUMMARY.match(line)]
        assert len(summary) == 1
        assert summary[0].endswith("known-risk:1 warn:0")
