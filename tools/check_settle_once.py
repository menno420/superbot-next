#!/usr/bin/env python3
"""check_settle_once — V010's settle-once architecture guard over the K7
money legs (contract c, warn-first).

Provenance / reliability header (per CLAUDE.md Q-0105 adopt-with-kill-switch):
- Why: sim-lab VERDICT 010 (sims/verdict-010-settle-once-architecture-guard
  @ 055245e9, approve) found no checker enforces the settle-once invariant;
  D-0078 (docs/decisions.md:577) PARKED it with a named successor and the
  admin-surface audit's consumption record
  (docs/review/admin-surface-audit-2026-07-12.md:380-396) fixed the terms:
  contract (c) — every money-moving op leg settles exactly once via
  {atomic consume of >=1 escrow row} OR {atomic check-and-set on a
  settle-flag row}, warn-first, with explicit re-arm for multi-stage
  settlement. Reference fence: the #133 ``tournament_flag.clear_active()``
  rowcount gate (sb/domain/rps/ops.py:394-417,
  sb/domain/blackjack/ops.py:590-613, merge 9923151).
- What it enforces, DB-free (pure AST over ``sb/domain`` source — never
  boots anything, never imports sb; the check_money_race machinery reused):
  1. root enumeration is DERIVED, never a file list (superbot's cogs/-drift
     lesson, audit:394-395): a ROOT = a function in the widened money
     fixpoint (seed: the five audited balance writers credit_coins /
     try_debit_coins / credit_treasury / try_debit_treasury / credit_karma,
     plus the wager boundary's public aliases; composites join by
     transitive closure) that carries a literal ``@workflow("...")``
     decorator — i.e. a registered K7 leg;
  2. every root classifies into a settle-once shape or WARNs:
     CW  conditional-write — money moves only through self-detecting
         one-statement conditional writes (try_debit_* / the debit
         composites that raise-or-None on shortfall);
     CAS check-and-set — the money mutation is dominated by a branch taken
         right after an atomic consume (delete rowcount / conditional-write
         result: the #133 clear_active gate, the gc_sweep delete-then-if
         shape, the try_debit-then-branch transfer shape);
     RC  row-consumption — a FOR-UPDATE/advisory-fenced load precedes the
         money call AND the txn consumes/rewrites gating state (row delete
         or state upsert reachable from the leg) — the escrow-settle and
         fenced read-settle-rearm shapes;
  3. money-fixpoint functions NOT reachable (name closure) from any leg
     are their own WARN class — an undeclared money path;
  4. multi-stage settlement re-arm sites are LEDGERED and verified
     (REARM_SITES: the named function must still call the named re-arm
     write) — a moved/renamed re-arm reds the ledger, not the tree.
- Posture (warn-first per Q-0105): classification misses PRINT and exit 0;
  RED (exit 1) is reserved for STRUCTURAL failures — a stale row in any
  ledger (the check_money_race stale-row hygiene: an excuse must never
  outlive the code it excused), overlapping ledgers, or a SETTLE_SITES
  trust anchor whose function no longer looks like what the ledger claims.
  The per-class telemetry line (``settle_once: N roots — RC:x CAS:y CW:z
  allowlisted:a known-risk:b warn:c``) is the warn->red graduation's
  evidence trail (the check_doc_cites rule-b playbook,
  tools/check_doc_cites.py:9-18).
- Deliberately pragmatic (documented false-negative surface, the
  check_money_race posture): resolution is name/import based; CAS
  dominance is approximated as "the FIRST branch after an atomic consume
  guards its surviving paths" (no dataflow — a rowcount bound ignored
  across an unrelated branch can fool it); a fence anywhere in a helper
  marks the caller's path fenced even if conditional in the helper; the
  RC "consumes gating state" test accepts any non-money DELETE/UPDATE/
  upsert reachable from the leg. The lint pins the PROVEN shapes (#133,
  gc_sweep, the wager composites, the #217 fenced loads); it is not a
  general concurrency analyzer.
- Added: 2026-07-12 (the D-0078 named successor slice).

Run: python3 tools/check_settle_once.py
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.check_money_race import (  # noqa: E402
    Analyzer,
    CallSite,
    DB_CALL_NAMES,
    FuncInfo,
    _call_qualifier_and_name,
    _calls_in,
    _strings_under,
    collect_sources,
)

# ------------------------------------------------------------------ money seed
# The widened seed (audit:387 "over the K7 op grammar"): the five audited
# balance writers, PLUS the wager boundary's PUBLIC ALIASES — module-level
# assignments (``credit_in_txn = _credit``, sb/domain/games/wager.py:148-149)
# the def-name fixpoint cannot see through. Every wager composite
# (escrow/settle/refund/enter/payout) joins by transitive closure.
MONEY_SEED = frozenset({
    "credit_coins",
    "try_debit_coins",
    "credit_treasury",
    "try_debit_treasury",
    "credit_karma",
    "credit_in_txn",
    "debit_in_txn",
})

# ------------------------------------------------------------ the four ledgers
# All four are stale-row-is-RED (the check_money_race idiom — no in-source
# annotations, the excuse lives HERE and dies with the code it excused).

#: The settle-guard trust anchors: (module, public name) -> (kind, why).
#: kinds: "consume"     — atomic check-and-set primitive whose result
#:                        (rowcount / None) callers branch on; ARMS the CAS
#:                        dominance test;
#:        "conditional" — self-detecting one-statement conditional money
#:                        write (also arms CAS for a following branch);
#:        "rc-composite"  — internally FOR-UPDATE-fenced row-consumption
#:                          settle (locks, gates on pot, consumes rows);
#:        "cas-composite" — internally fenced existence-check-then-act.
#: Every row verified against source at HEAD before being added.
SETTLE_SITES: dict[tuple[str, str], tuple[str, str]] = {
    ("sb/domain/economy/store.py", "try_debit_coins"): (
        "conditional",
        "one-statement decide-and-write (UPDATE ... WHERE coins >= $n "
        "RETURNING) — None on shortfall, can never over-debit"),
    ("sb/domain/treasury/store.py", "try_debit_treasury"): (
        "conditional",
        "one-statement decide-and-write (WHERE balance >= $n) — never "
        "overdraws the pool"),
    ("sb/domain/economy/store.py", "try_grant_unique_item"): (
        "consume",
        "conditional unique-grant upsert (ON CONFLICT ... WHERE quantity "
        "<= 0 RETURNING) — the shipped double-click double-charge closure; "
        "economy.record_buy branches on its bool"),
    ("sb/domain/games/store.py", "delete_checkpoint_by_id"): (
        "consume",
        "precise by-id DELETE returning the rowcount — the gc_sweep "
        "refund gate (credit ONLY when this txn removed the row)"),
    ("sb/domain/games/tournament_flag.py", "clear_active"): (
        "consume",
        "the #133 reference fence: atomic flag-row DELETE returning the "
        "rowcount — the tournament payout/free-consolation check-and-set"),
    ("sb/domain/games/wager.py", "debit_in_txn"): (
        "conditional",
        "public alias of _debit — try_debit_coins-backed, raises "
        "InsufficientFundsError (rolling the txn back) on shortfall"),
    ("sb/domain/games/wager.py", "debit_floor_in_txn"): (
        "conditional",
        "overdraft-tolerant floor debit — every branch is a conditional "
        "decide-and-write; detects its own race (the raced-to-zero arm)"),
    ("sb/domain/games/wager.py", "settle_pvp_in_txn"): (
        "rc-composite",
        "lock_rows_for_settlement (FOR UPDATE) + pot>0 gate + row delete "
        "in one txn — idempotent by row consumption"),
    ("sb/domain/games/wager.py", "refund_pvp_in_txn"): (
        "rc-composite",
        "same row-consumption guard as settle_pvp_in_txn, per-row refund"),
    ("sb/domain/games/wager.py", "payout_tournament_in_txn"): (
        "rc-composite",
        "locks + consumes ALL entry rows before paying the summed pot; "
        "the free-consolation arm relies on the caller's clear_active "
        "gate (the #133 shape — see the payout legs' CAS classification)"),
    ("sb/domain/games/wager.py", "enter_tournament_in_txn"): (
        "cas-composite",
        "advisory slot lock + fenced existence check BEFORE the fee debit "
        "(the #213/#221 fix, proven in "
        "tests/integration/test_tournament_entry_race.py)"),
}

#: Multi-stage settlement re-arm sites: (module, leg function, re-arm callee)
#: -> why. Verified: the function must still call the named callee.
REARM_SITES: dict[tuple[str, str, str], str] = {
    ("sb/domain/rps/ops.py", "_record_tournament_open", "set_active"):
        "re-arms the active_tournament flag row the payout/abort legs "
        "consume via clear_active (the #133 fence's arming half)",
    ("sb/domain/blackjack/ops.py", "_record_tournament_open", "set_active"):
        "re-arms the active_tournament flag row the payout/abort legs "
        "consume via clear_active (the #133 fence's arming half)",
    ("sb/domain/farm/ops.py", "_record_collect", "set_farm"):
        "self re-arm: eggs=0 under the same FOR-UPDATE fence restarts "
        "accrual — the next collect settles a fresh accumulation",
    ("sb/domain/economy/ops.py", "_record_daily", "set_daily_claim"):
        "re-arms the cooldown anchor (last_daily) on the row the leg "
        "loaded FOR UPDATE — the next claim settles a fresh window",
    ("sb/domain/economy/ops.py", "_record_work", "set_last_worked"):
        "re-arms the cooldown anchor (last_worked) on the row the leg "
        "loaded FOR UPDATE",
}

#: Roots VERIFIED SAFE against source despite missing every recognized
#: shape, each with its one-line justification. Suppressed (green).
ALLOWLIST: dict[tuple[str, str], str] = {
    ("sb/domain/rps/ops.py", "_record_solo_play"):
        "stateless single-leg quick play: no session row exists to settle "
        "twice — the win credit pays each INVOCATION once by design and "
        "the loss debit is debit_floor_in_txn (self-detecting conditional, "
        "sb/domain/rps/ops.py:102-148); nothing re-settles a prior stake",
}

#: Roots judged REAL members of the defect class — ledgered for a named
#: fix, printed loudly on every run, NOT red; never called safe. Fixing
#: the site without deleting its row reds the checker.
KNOWN_RISKS: dict[tuple[str, str], str] = {
    ("sb/domain/karma/ops.py", "_record_give"):
        "cooldown/cap reads are UNLOCKED plain SELECTs "
        "(store.recent_grant_count / grants_given_since) and credit_karma "
        "is an unconditioned upsert (sb/domain/karma/ops.py:138-229): two "
        "racing grants from the same giver both pass the window checks "
        "and both land — the cooldown/cap can over-admit under "
        "concurrency; needs a FOR-UPDATE anchor row or advisory fence "
        "(the ensure_and_get_economy shape)",
}

# The settle guards' STATE-WRITE signature (used to validate "consume"
# rows and to detect gating-state disarm writes; plain INSERT — a ledger
# append — deliberately does NOT match).
_WRITE_SQL = re.compile(
    r"\bDELETE\s+FROM\b|\bUPDATE\s+\w+[^;]*?\bSET\b|"
    r"\bON\s+CONFLICT\b[^;]*?\bDO\s+UPDATE\b",
    re.IGNORECASE | re.DOTALL)


# ------------------------------------------------------------------- results
@dataclass
class RootResult:
    module: str
    func: str
    lineno: int
    ref: str                       # the @workflow("<ref>") string
    klass: str                     # "rc" | "cas" | "cw" | "warn"
    warn_events: list[tuple[int, str]] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        return (self.module, self.func)


@dataclass
class SettleReport:
    roots: list[RootResult]
    undeclared: list[tuple[str, str, int]]     # (module, func, lineno)


# ------------------------------------------------------------------ analyzer
@dataclass
class _State:
    fenced: bool = False           # FOR-UPDATE / advisory fence on this path
    consume_seen: bool = False     # atomic consume result awaiting its branch
    cas: bool = False              # path dominated by a post-consume branch

    def copy(self) -> "_State":
        return _State(self.fenced, self.consume_seen, self.cas)


def _merge(survivors: list[_State]) -> _State:
    return _State(
        fenced=all(s.fenced for s in survivors),
        consume_seen=all(s.consume_seen for s in survivors),
        cas=all(s.cas for s in survivors),
    )


class SettleAnalyzer(Analyzer):
    """check_money_race's parse/resolve/fence machinery with the widened
    money seed, @workflow-leg root derivation and the settle-shape walk."""

    def __init__(self, sources: dict[str, str],
                 settle_sites: dict[tuple[str, str], tuple[str, str]]
                 | None = None):
        self._settle_sites = (SETTLE_SITES if settle_sites is None
                              else settle_sites)
        # name -> kind, derived from the ledger (names are load-bearing:
        # a renamed guard goes stale-RED instead of silently unarming).
        self.guard_kinds: dict[str, str] = {
            name: kind
            for (_, name), (kind, _) in self._settle_sites.items()
        }
        self.arming_names = {n for n, k in self.guard_kinds.items()
                             if k in ("consume", "conditional")}
        self.self_guarding = {
            n: {"conditional": "cw", "rc-composite": "rc",
                "cas-composite": "cas"}[k]
            for n, k in self.guard_kinds.items() if k != "consume"
        }
        super().__init__(sources)
        # decorator + module-alias scan (parse_module discards both)
        self.legs: dict[str, dict[str, str]] = {}       # module -> {fn: ref}
        self.assign_aliases: dict[str, dict[str, str]] = {}
        for path, source in sources.items():
            legs, aliases = _leg_scan(source)
            self.legs[path] = legs
            self.assign_aliases[path] = aliases
        self.disarm_names = self._disarm_fixpoint()

    # -- widened money fixpoint (same loop as the parent, this seed) --------
    def _money_fixpoint(self) -> set[str]:
        names = set(MONEY_SEED)
        changed = True
        while changed:
            changed = False
            for funcs in self.modules.values():
                for info in funcs.values():
                    if info.name in names:
                        continue
                    if any(c.name in names for c in info.calls):
                        names.add(info.name)
                        changed = True
        return names

    # -- gating-state writers (non-money DELETE/UPDATE/upsert), transitive --
    def _disarm_fixpoint(self) -> set[str]:
        names = {
            info.name
            for funcs in self.modules.values()
            for info in funcs.values()
            if info.name not in self.money_names
            and _WRITE_SQL.search("\n".join(_strings_under(info.node)))
        }
        changed = True
        while changed:
            changed = False
            for funcs in self.modules.values():
                for info in funcs.values():
                    if info.name in names:
                        continue
                    if any(c.name in names for c in info.calls):
                        names.add(info.name)
                        changed = True
        return names

    # -- roots ---------------------------------------------------------------
    def roots(self) -> list[FuncInfo]:
        out = []
        for path in sorted(self.modules):
            legs = self.legs.get(path, {})
            for info in sorted(self.modules[path].values(),
                               key=lambda f: f.lineno):
                if info.name in legs and info.name in self.money_names:
                    out.append(info)
        return out

    # -- the settle-shape walk -------------------------------------------------
    def classify_root(self, info: FuncInfo) -> RootResult:
        events: list[tuple[str | None, int, str]] = []   # (class|None, ln, nm)

        def event(call: CallSite, state: _State) -> None:
            name = call.name
            if (self._call_is_fence(info.module, call)
                    or name in self.fence_names):
                state.fenced = True
            if name in self.money_names and name not in DB_CALL_NAMES:
                if state.cas:
                    events.append(("cas", call.lineno, name))
                elif name in self.self_guarding:
                    events.append((self.self_guarding[name],
                                   call.lineno, name))
                elif state.fenced and info.name in self.disarm_names:
                    events.append(("rc", call.lineno, name))
                else:
                    events.append((None, call.lineno, name))
            if name in self.arming_names:
                state.consume_seen = True

        def run_calls(node: ast.AST | None, state: _State) -> None:
            for call in _calls_in(node):
                event(call, state)

        def walk(stmts: list[ast.stmt], state: _State) -> tuple[_State, bool]:
            for stmt in stmts:
                if isinstance(stmt, ast.If):
                    run_calls(stmt.test, state)
                    armed = state.consume_seen
                    body_state = state.copy()
                    else_state = state.copy()
                    if armed:
                        # the first branch after an atomic consume is
                        # treated as testing its result — both arms (and
                        # therefore any fall-through survivor) are
                        # check-and-set dominated; the consume is spent.
                        for s in (body_state, else_state):
                            s.cas, s.consume_seen = True, False
                    body_state, body_term = walk(stmt.body, body_state)
                    else_state, else_term = walk(stmt.orelse, else_state)
                    survivors = []
                    if not body_term:
                        survivors.append(body_state)
                    if not else_term:
                        survivors.append(else_state)
                    if not survivors:
                        return state, True
                    state = _merge(survivors)
                elif isinstance(stmt, ast.Try):
                    body_state, body_term = walk(stmt.body, state.copy())
                    survivors = [] if body_term else [body_state]
                    for handler in stmt.handlers:
                        h_state, h_term = walk(handler.body, state.copy())
                        if not h_term:
                            survivors.append(h_state)
                    if not survivors:
                        return state, True
                    state = _merge(survivors)
                    if stmt.finalbody:
                        state, final_term = walk(stmt.finalbody, state)
                        if final_term:
                            return state, True
                elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                    run_calls(stmt.iter, state)
                    body_state, _ = walk(stmt.body, state.copy())
                    state = _merge([state, body_state])
                elif isinstance(stmt, ast.While):
                    run_calls(stmt.test, state)
                    body_state, _ = walk(stmt.body, state.copy())
                    state = _merge([state, body_state])
                elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                    for item in stmt.items:
                        run_calls(item.context_expr, state)
                    state, term = walk(stmt.body, state)
                    if term:
                        return state, True
                elif isinstance(stmt, (ast.Return, ast.Raise)):
                    run_calls(getattr(stmt, "value", None) or
                              getattr(stmt, "exc", None), state)
                    return state, True
                elif isinstance(stmt, (ast.Break, ast.Continue)):
                    return state, True
                elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef,
                                       ast.Lambda)):
                    continue                    # nested def: runs later
                else:
                    run_calls(stmt, state)
            return state, False

        walk(list(info.node.body), _State())

        warn_events = [(ln, nm) for k, ln, nm in events if k is None]
        if warn_events or not events:
            klass = "warn"
            if not events:
                warn_events = [(info.lineno,
                                "money reached only through an unwalkable "
                                "scope (nested def / lambda)")]
        elif any(k == "cas" for k, _, _ in events):
            klass = "cas"
        elif any(k == "rc" for k, _, _ in events):
            klass = "rc"
        else:
            klass = "cw"
        ref = self.legs.get(info.module, {}).get(info.name, "")
        return RootResult(info.module, info.name, info.lineno, ref, klass,
                          warn_events)

    # -- undeclared money paths -------------------------------------------------
    def undeclared_money(self, roots: list[FuncInfo]) -> list[tuple[str, str, int]]:
        reachable = {r.name for r in roots}
        changed = True
        while changed:
            changed = False
            for funcs in self.modules.values():
                for info in funcs.values():
                    if info.name not in reachable:
                        continue
                    for call in info.calls:
                        if call.name not in reachable:
                            reachable.add(call.name)
                            changed = True
        out = []
        for path in sorted(self.modules):
            for info in sorted(self.modules[path].values(),
                               key=lambda f: f.lineno):
                if info.name in self.money_names and info.name not in reachable:
                    out.append((path, info.name, info.lineno))
        return out

    def report(self) -> SettleReport:
        roots = self.roots()
        return SettleReport(
            roots=[self.classify_root(info) for info in roots],
            undeclared=self.undeclared_money(roots),
        )


def _leg_scan(source: str) -> tuple[dict[str, str], dict[str, str]]:
    """-> ({function name: @workflow ref}, {module-level alias: def name})."""
    tree = ast.parse(source)
    legs: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                _, name = _call_qualifier_and_name(dec.func)
                if (name == "workflow" and dec.args
                        and isinstance(dec.args[0], ast.Constant)
                        and isinstance(dec.args[0].value, str)):
                    legs[node.name] = dec.args[0].value
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Name)):
            aliases[node.targets[0].id] = node.value.id
    return legs, aliases


def analyze_sources(sources: dict[str, str],
                    settle_sites: dict[tuple[str, str], tuple[str, str]]
                    | None = None) -> SettleReport:
    """The test seam: run the full pipeline over in-memory modules."""
    return SettleAnalyzer(sources, settle_sites).report()


# --------------------------------------------------------------------- driver
def run_check(analyzer: SettleAnalyzer, report: SettleReport, *,
              settle_sites: dict[tuple[str, str], tuple[str, str]]
              | None = None,
              rearm_sites: dict[tuple[str, str, str], str] | None = None,
              allowlist: dict[tuple[str, str], str] | None = None,
              known_risks: dict[tuple[str, str], str] | None = None,
              ) -> tuple[int, list[str]]:
    """-> (exit code, printable lines). RED only on structural failures."""
    settle_sites = SETTLE_SITES if settle_sites is None else settle_sites
    rearm_sites = REARM_SITES if rearm_sites is None else rearm_sites
    allowlist = ALLOWLIST if allowlist is None else allowlist
    known_risks = KNOWN_RISKS if known_risks is None else known_risks

    problems: list[str] = []
    lines: list[str] = []

    # -- structural: ledger hygiene ------------------------------------------
    for key in sorted(set(allowlist) & set(known_risks)):
        problems.append(f"LEDGER-OVERLAP {key[0]} [{key[1]}]: a site cannot "
                        f"be both verified-safe and a known risk")

    for (module, name), (kind, _why) in sorted(settle_sites.items()):
        funcs = analyzer.modules.get(module)
        if funcs is None:
            problems.append(f"STALE-ROW SETTLE_SITES {module} [{name}]: "
                            f"module not under the scan root — remove or "
                            f"re-point the row")
            continue
        target = name
        if target not in funcs:
            target = analyzer.assign_aliases.get(module, {}).get(name, "")
            if target not in funcs:
                problems.append(f"STALE-ROW SETTLE_SITES {module} [{name}]: "
                                f"no such function or module-level alias")
                continue
        info = funcs[target]
        if kind == "consume":
            own_sql = "\n".join(_strings_under(info.node))
            if not _WRITE_SQL.search(own_sql):
                problems.append(
                    f"STALE-ROW SETTLE_SITES {module} [{name}]: ledgered as "
                    f"an atomic consume but its SQL no longer carries an "
                    f"atomic write statement")
        elif target not in analyzer.money_names and \
                name not in analyzer.money_names:
            problems.append(
                f"STALE-ROW SETTLE_SITES {module} [{name}]: ledgered as a "
                f"money-guard composite but it is no longer in the money "
                f"fixpoint")

    for (module, func, callee), _why in sorted(rearm_sites.items()):
        info = analyzer.modules.get(module, {}).get(func)
        if info is None:
            problems.append(f"STALE-ROW REARM_SITES {module} [{func}]: no "
                            f"such function")
            continue
        if callee not in {c.name for c in info.calls}:
            problems.append(f"STALE-ROW REARM_SITES {module} [{func}]: no "
                            f"longer calls the re-arm write `{callee}`")

    # -- roots ------------------------------------------------------------------
    counts = {"rc": 0, "cas": 0, "cw": 0}
    allow_hits: set[tuple[str, str]] = set()
    risk_hits: set[tuple[str, str]] = set()
    warn_roots: list[RootResult] = []
    for root in report.roots:
        if root.klass != "warn":
            counts[root.klass] += 1
            continue
        if root.key in allowlist:
            allow_hits.add(root.key)
            continue
        if root.key in known_risks:
            risk_hits.add(root.key)
            lines.append(
                f"KNOWN-RISK (ledgered, NOT safe) {root.module}:"
                f"{root.lineno} [{root.func} -> {root.ref}] — "
                f"{known_risks[root.key]}")
            continue
        warn_roots.append(root)

    for key in sorted(set(allowlist) - allow_hits):
        problems.append(
            f"STALE-ROW ALLOWLIST {key[0]} [{key[1]}]: row matches no "
            f"warn-classified root — remove it (never let an excuse "
            f"outlive the code it excused)")
    for key in sorted(set(known_risks) - risk_hits):
        problems.append(
            f"STALE-ROW KNOWN_RISKS {key[0]} [{key[1]}]: row matches no "
            f"warn-classified root — the risk was fixed; delete the row")

    for root in warn_roots:
        for ln, nm in root.warn_events:
            lines.append(
                f"WARN {root.module}:{ln} [{root.func} -> {root.ref}] "
                f"money call `{nm}` matches no settle-once shape (no "
                f"check-and-set dominance, not a self-guarding composite, "
                f"no fenced-load-plus-consume) — verify and ledger it")
    for module, func, lineno in report.undeclared:
        lines.append(
            f"WARN {module}:{lineno} [{func}] undeclared money path — in "
            f"the money fixpoint but reachable from NO @workflow leg "
            f"(the cogs/-drift class): route it through a declared op or "
            f"remove it")

    lines.append(
        f"settle_once: {len(report.roots)} roots — RC:{counts['rc']} "
        f"CAS:{counts['cas']} CW:{counts['cw']} "
        f"allowlisted:{len(allow_hits)} known-risk:{len(risk_hits)} "
        f"warn:{len(warn_roots)}")

    if problems:
        for p in problems:
            lines.append(f"RED {p}")
        lines.append(f"check_settle_once: {len(problems)} structural "
                     f"problem(s)")
        return 1, lines
    lines.append("check_settle_once: OK")
    return 0, lines


def main(argv: list[str] | None = None) -> int:
    analyzer = SettleAnalyzer(collect_sources())
    code, lines = run_check(analyzer, analyzer.report())
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
