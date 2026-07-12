#!/usr/bin/env python3
"""check_money_race — static money-race lint (the F-001/F-002 defect class,
fixed twice: PR #213 blackjack/rps checkpoint loads, PR #217 farm/mining).

DB-free by construction: pure AST/regex over the Python source + SQL string
literals under ``sb/domain``. Never boots anything, never imports sb.

The defect class (read-then-settle over an unlocked row / natural-key upsert
without a locking read): every game/economy K7 leg runs under
``IdempotencyPosture.NATURAL_KEY`` — "intrinsically once (ON CONFLICT / FOR
UPDATE)", spec 07 — which puts the WHOLE concurrency fence on the DB legs
themselves. A leg that (a) loads state with a plain SELECT and then moves
money on what it read, or (b) upserts caller-computed state by natural key
without any lock, lets two concurrent invocations both read the pre-mutation
row and both settle: a double credit / double payout / swallowed purchase.

Enforced rules (red = exit 1), per MONEY-BEARING txn function — a function
under ``sb/domain`` that directly or transitively calls one of the money
primitives (``wager.credit_in_txn`` / ``debit_in_txn`` / ``debit_floor_in_txn``
/ ``economy_store.credit_coins`` / ``try_debit_coins``):

  A  unlocked-read-then-settle — a read (SELECT without FOR UPDATE, resolved
     through the domain-store seam or issued directly, with no
     ``pg_advisory_xact_lock`` / FOR-UPDATE fence earlier in the function)
     is followed on a fall-through path by a money mutation. The pre-#217
     ``farm.collect`` / ``mining.sell`` shape. Reads on a TERMINATING branch
     (one that ends in ``raise``/``return`` — the error-copy ``get_coins``
     pattern) cannot leak into the settle path and are not flagged.
  B  unfenced natural-key upsert — an ``INSERT … ON CONFLICT … DO UPDATE``
     writing caller-computed values (not a self-referential atomic
     read-modify-write like ``coins = coins + $n``, not ``DO NOTHING``, not
     WHERE-guarded) occurs with no locking read / advisory fence earlier in
     the function. The pre-#217 ``farm.buy_chicken`` first-insert shape.

What counts as a FENCE (from the two shipped fixes):
  * a call passing ``for_update=True`` (the #217 store-seam idiom);
  * a call to a store function whose own SQL carries ``FOR UPDATE`` or
    ``pg_advisory_xact_lock`` unconditionally (``fetch_checkpoint``,
    ``lock_rows_for_settlement``, ``lock_new_checkpoint_slot``, …);
  * a direct ``execute/fetchone/fetchall`` whose SQL literal carries either
    marker;
  * a call to a same-tree function that itself fences (name fixpoint —
    ``_load_pending`` inherits ``fetch_checkpoint``'s lock).

Deliberately pragmatic (documented false-negative surface): resolution is
name/import based; ordering is source order with branch-aware termination
(no path-sensitivity beyond that); a fence anywhere in a helper marks the
helper fence-providing even if conditional; reads hidden behind helpers that
neither lock nor carry SQL are not seen. The lint pins the two PROVEN shapes;
it is not a general concurrency analyzer.

Two site ledgers (the committed-checker allowlist idiom — check_egress /
check_no_skip precedent), both keyed (file, function, rule):

  ALLOWLIST    — sites VERIFIED SAFE against source, each with its one-line
                 justification. Suppressed (green).
  KNOWN_RISKS  — sites judged REAL members of the defect class, ledgered for
                 a named fix. Printed loudly on every run, NOT red — but
                 never called safe. Fixing the site without deleting its row
                 reds the checker (stale-row hygiene), so the ledger cannot
                 outlive the bug.

A stale row in either table (no matching finding) is RED.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = "sb/domain"

# The money primitives (the audited coin boundary): the wager helpers every
# game leg composes, plus the two economy-store balance writes they wrap.
MONEY_SEED = frozenset({
    "credit_in_txn",
    "debit_in_txn",
    "debit_floor_in_txn",
    "credit_coins",
    "try_debit_coins",
})

# The K3 seam's raw executors — a call to one of these with an inline SQL
# literal is classified by that literal.
DB_CALL_NAMES = frozenset({
    "execute", "fetchone", "fetchall", "fetchrow", "fetchval", "fetch",
})

_LOCK_MARKERS = ("FOR UPDATE", "pg_advisory_xact_lock")

# ---------------------------------------------------------------- site ledgers
# (relative file, function, rule) -> one-line justification. Every row
# verified against source at HEAD before being added.
ALLOWLIST: dict[tuple[str, str, str], str] = {
    ("sb/domain/games/wager.py", "debit_floor_in_txn", "A"):
        "the get_coins read only sizes the retry amount for try_debit_coins "
        "— a one-statement conditional decide-and-write (WHERE coins >= $n) "
        "that detects the race itself (returns None; the raced-to-zero "
        "branch is handled), so a stale read can never over-debit",
    ("sb/domain/games/wager.py", "escrow_pvp_in_txn", "B"):
        "the PvP escrow rows: every caller fences first — both accept legs "
        "(blackjack/ops.py _record_pvp_accept, rps/ops.py _record_pvp_accept)"
        " load the pending challenge via _load_pending -> fetch_checkpoint "
        "(unconditional FOR UPDATE, the #213 fix) before escrowing, so two "
        "racing accepts serialize on the pending row's lock",
}

# Sites the checker judges REAL members of the defect class — ledgered, never
# whitelisted as safe. Loud on every run; red only when stale.
# (enter_tournament_in_txn's row cleared 2026-07-12: fixed with
# lock_new_checkpoint_slot + existence check before the debit — the #213
# solo_start precedent — proven red-then-green on real Postgres in
# tests/integration/test_tournament_entry_race.py.)
KNOWN_RISKS: dict[tuple[str, str, str], str] = {}


# ------------------------------------------------------------------- models
@dataclass
class CallSite:
    lineno: int
    col: int
    name: str                    # last attribute segment / bare name
    qualifier: str | None        # `store.get_farm` -> "store"
    for_update_true: bool
    sql: str                     # string literals inside THIS call's args


@dataclass
class FuncInfo:
    module: str                  # repo-relative posix path
    name: str
    lineno: int
    has_for_update_param: bool
    node: ast.AST = None         # the def node (analysis walks it)
    sql_reads: bool = False
    sql_locks: bool = False      # FOR UPDATE / advisory in own literals
    upsert_kind: str | None = None   # "value" | "atomic" | None
    calls: list[CallSite] = field(default_factory=list)


@dataclass
class Finding:
    module: str
    func: str
    rule: str                    # "A" | "B"
    lineno: int
    message: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.module, self.func, self.rule)


# ------------------------------------------------------------ SQL classifiers
def _strings_under(node: ast.AST) -> list[str]:
    out: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
        elif isinstance(sub, ast.JoinedStr):
            for part in sub.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    out.append(part.value)
    return out


def _has_lock_marker(sql: str) -> bool:
    return any(marker in sql for marker in _LOCK_MARKERS)


def _is_select(sql: str) -> bool:
    return bool(re.search(r"\bSELECT\b", sql)) and bool(re.search(r"\bFROM\b", sql))


def classify_upsert(sql: str) -> str | None:
    """None (no ON CONFLICT) | "atomic" (safe by construction) | "value".

    "value" = DO UPDATE SET writing caller-computed state ($n / EXCLUDED.*)
    with neither a self-referential read-modify-write (``tbl.col`` in the SET
    expression — atomic in SQL) nor a WHERE guard (conditional write).
    """
    upper = sql.upper()
    idx = upper.find("ON CONFLICT")
    if idx < 0:
        return None
    while idx >= 0:
        tail = sql[idx:]
        do_update = tail.upper().find("DO UPDATE")
        if do_update >= 0:
            set_clause = tail[do_update:]
            # a qualified own-table column (`mining_inventory.quantity`,
            # `economy_balances.coins`) = self-referential arithmetic;
            # EXCLUDED.* does NOT count (it is the caller's value).
            self_ref = any(
                not m.group(0).upper().startswith("EXCLUDED.")
                for m in re.finditer(r"\b[A-Za-z_][A-Za-z_0-9]*\.[A-Za-z_]", set_clause)
            )
            guarded = bool(re.search(r"\bWHERE\b", set_clause, re.IGNORECASE))
            if not self_ref and not guarded:
                return "value"
        idx = upper.find("ON CONFLICT", idx + 1)
    return "atomic"


# -------------------------------------------------------------------- parsing
def _dotted_to_path(dotted: str, modules: dict) -> str | None:
    candidate = dotted.replace(".", "/") + ".py"
    return candidate if candidate in modules else None


def _call_qualifier_and_name(func: ast.expr) -> tuple[str | None, str | None]:
    if isinstance(func, ast.Name):
        return None, func.id
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name):
            return base.id, func.attr
        return "<expr>", func.attr
    return None, None


def _call_site(node: ast.Call) -> CallSite | None:
    qualifier, name = _call_qualifier_and_name(node.func)
    if name is None:
        return None
    for_update_true = any(
        kw.arg == "for_update"
        and isinstance(kw.value, ast.Constant)
        and kw.value.value is True
        for kw in node.keywords
    )
    sql = "\n".join(s for arg in node.args for s in _strings_under(arg))
    return CallSite(node.lineno, node.col_offset, name, qualifier,
                    for_update_true, sql)


_SCOPE_BARRIERS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _calls_in(node: ast.AST | None, *, skip_self_barrier: bool = False) -> list[CallSite]:
    """Call sites lexically inside *node*, source order, NOT descending into
    nested function/lambda scopes (their calls run later, if ever)."""
    if node is None:
        return []
    out: list[CallSite] = []
    stack: list[ast.AST] = [node]
    first = True
    while stack:
        cur = stack.pop()
        if isinstance(cur, _SCOPE_BARRIERS) and not (first and skip_self_barrier):
            first = False
            continue
        first = False
        if isinstance(cur, ast.Call):
            site = _call_site(cur)
            if site is not None:
                out.append(site)
        stack.extend(ast.iter_child_nodes(cur))
    out.sort(key=lambda c: (c.lineno, c.col))
    return out


def parse_module(path: str, source: str):
    """-> (functions, module_aliases, func_aliases).

    module_aliases: local alias -> dotted module (`store` -> sb.domain.farm.store)
    func_aliases:   local alias -> (dotted module, name) for direct
                    `from sb.domain.x.store import get_coins` imports.
    """
    tree = ast.parse(source)
    functions: dict[str, FuncInfo] = {}
    module_aliases: dict[str, str] = {}
    func_aliases: dict[str, tuple[str, str]] = {}

    pkg_parts = path.rsplit("/", 1)[0].split("/")   # sb/domain/farm

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:                            # from . import store
                base = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                mod_parts = base + (node.module.split(".") if node.module else [])
            else:
                mod_parts = (node.module or "").split(".")
            dotted = ".".join(p for p in mod_parts if p)
            for alias in node.names:
                local = alias.asname or alias.name
                module_aliases[local] = (
                    f"{dotted}.{alias.name}" if dotted else alias.name
                )
                func_aliases[local] = (dotted, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                module_aliases[local] = alias.name

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args
        param_names = {a.arg for a in
                       args.posonlyargs + args.args + args.kwonlyargs}
        info = FuncInfo(module=path, name=node.name, lineno=node.lineno,
                        has_for_update_param="for_update" in param_names,
                        node=node)
        own_sql = "\n".join(_strings_under(node))
        info.sql_reads = _is_select(own_sql)
        info.sql_locks = _has_lock_marker(own_sql)
        info.upsert_kind = classify_upsert(own_sql)
        info.calls = _calls_in(node, skip_self_barrier=True)
        # last definition wins on duplicate names (matches runtime)
        functions[node.name] = info

    return functions, module_aliases, func_aliases


# ------------------------------------------------------------------ analysis
@dataclass
class _PathState:
    fenced: bool = False
    read: CallSite | None = None      # first leakable unlocked read

    def copy(self) -> "_PathState":
        return _PathState(self.fenced, self.read)


def _merge(survivors: list[_PathState]) -> _PathState:
    fenced = all(s.fenced for s in survivors)
    reads = [s.read for s in survivors if s.read is not None]
    read = min(reads, key=lambda c: (c.lineno, c.col)) if reads else None
    return _PathState(fenced, read)


class Analyzer:
    def __init__(self, sources: dict[str, str]):
        self.sources = sources
        self.modules: dict[str, dict[str, FuncInfo]] = {}
        self.module_aliases: dict[str, dict[str, str]] = {}
        self.func_aliases: dict[str, dict[str, tuple[str, str]]] = {}
        for path, source in sources.items():
            funcs, mod_aliases, fn_aliases = parse_module(path, source)
            self.modules[path] = funcs
            self.module_aliases[path] = mod_aliases
            self.func_aliases[path] = fn_aliases
        self.by_name: dict[str, list[FuncInfo]] = {}
        for funcs in self.modules.values():
            for info in funcs.values():
                self.by_name.setdefault(info.name, []).append(info)
        self.money_names = self._money_fixpoint()
        self.fence_names = self._fence_fixpoint()

    # -- name fixpoints -------------------------------------------------------
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

    def _fence_fixpoint(self) -> set[str]:
        names = {
            info.name
            for funcs in self.modules.values()
            for info in funcs.values()
            if info.sql_locks and not info.has_for_update_param
        }
        changed = True
        while changed:
            changed = False
            for funcs in self.modules.values():
                for info in funcs.values():
                    if info.name in names:
                        continue
                    if any(
                        c.name in names or self._call_is_fence(info.module, c)
                        for c in info.calls
                    ):
                        names.add(info.name)
                        changed = True
        return names

    # -- resolution ------------------------------------------------------------
    def resolve(self, module: str, call: CallSite) -> FuncInfo | None:
        funcs = self.modules.get(module, {})
        if call.qualifier is None:
            if call.name in funcs:
                return funcs[call.name]
            target = self.func_aliases.get(module, {}).get(call.name)
            if target:
                dotted, fname = target
                path = _dotted_to_path(dotted, self.modules)
                if path and fname in self.modules[path]:
                    return self.modules[path][fname]
        else:
            dotted = self.module_aliases.get(module, {}).get(call.qualifier)
            if dotted:
                path = _dotted_to_path(dotted, self.modules)
                if path and call.name in self.modules[path]:
                    return self.modules[path][call.name]
        candidates = self.by_name.get(call.name, [])
        if len(candidates) == 1:
            return candidates[0]
        return None

    # -- event classification ----------------------------------------------------
    def _call_is_fence(self, module: str, call: CallSite) -> bool:
        if call.for_update_true:
            return True
        if call.sql and _has_lock_marker(call.sql):
            return True
        resolved = self.resolve(module, call)
        return bool(resolved is not None and resolved.sql_locks
                    and not resolved.has_for_update_param)

    def classify(self, module: str, call: CallSite) -> str | None:
        """-> "money" | "fence" | "upsert" | "read" | None."""
        if call.name in self.money_names and call.name not in DB_CALL_NAMES:
            return "money"
        if self._call_is_fence(module, call) or call.name in self.fence_names:
            return "fence"
        resolved = self.resolve(module, call)
        if resolved is not None:
            if resolved.upsert_kind == "value":
                return "upsert"
            if resolved.sql_reads and not resolved.sql_locks:
                return "read"
            if resolved.has_for_update_param and resolved.sql_reads:
                return "read"      # lockable read called WITHOUT the lock
            return None
        if call.name in DB_CALL_NAMES and call.sql:
            kind = classify_upsert(call.sql)
            if kind == "value":
                return "upsert"
            if _is_select(call.sql):
                return "read"
        return None

    # -- rules ----------------------------------------------------------------
    def analyze_function(self, info: FuncInfo) -> list[Finding]:
        findings: list[Finding] = []
        seen_b: set[int] = set()
        a_done = False

        def event(call: CallSite, state: _PathState) -> None:
            nonlocal a_done
            kind = self.classify(info.module, call)
            if kind == "fence":
                state.fenced = True
            elif kind == "read":
                if not state.fenced and state.read is None:
                    state.read = call
            elif kind == "money":
                if state.read is not None and not a_done:
                    findings.append(Finding(
                        info.module, info.name, "A", call.lineno,
                        f"money mutation `{call.name}` at line {call.lineno} "
                        f"follows the unlocked read `{state.read.name}` at "
                        f"line {state.read.lineno} in the same txn scope (no "
                        f"FOR UPDATE / advisory fence before the read) — the "
                        f"F-001/F-002 read-then-settle shape"))
                    a_done = True
            elif kind == "upsert":
                if not state.fenced and call.lineno not in seen_b:
                    seen_b.add(call.lineno)
                    findings.append(Finding(
                        info.module, info.name, "B", call.lineno,
                        f"natural-key upsert `{call.name}` at line "
                        f"{call.lineno} writes caller-computed state with no "
                        f"preceding locking read / pg_advisory_xact_lock "
                        f"fence — the first-insert race shape "
                        f"(farm.buy_chicken, pre-#217)"))

        def run_calls(node: ast.AST | None, state: _PathState) -> None:
            for call in _calls_in(node):
                event(call, state)

        def walk(stmts: list[ast.stmt], state: _PathState) -> tuple[_PathState, bool]:
            """-> (fall-through state, terminated). A terminated block ends
            in raise/return/continue/break — nothing leaks past it."""
            for stmt in stmts:
                if isinstance(stmt, ast.If):
                    run_calls(stmt.test, state)
                    body_state, body_term = walk(stmt.body, state.copy())
                    else_state, else_term = walk(stmt.orelse, state.copy())
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
                        # an exception may fire before the body's effects —
                        # handlers start from the PRE-body state
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
                    state = _merge([state, body_state])  # 0-or-more runs
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
                elif isinstance(stmt, _SCOPE_BARRIERS):
                    continue                       # nested def: runs later
                else:
                    run_calls(stmt, state)
            return state, False

        walk(list(info.node.body), _PathState())
        return findings

    def analyze(self) -> list[Finding]:
        findings: list[Finding] = []
        for path in sorted(self.modules):
            for info in sorted(self.modules[path].values(),
                               key=lambda f: f.lineno):
                if info.name not in self.money_names:
                    continue
                findings.extend(self.analyze_function(info))
        return findings


def analyze_sources(sources: dict[str, str]) -> list[Finding]:
    """The test seam: run the full pipeline over in-memory modules."""
    return Analyzer(sources).analyze()


# --------------------------------------------------------------------- driver
def collect_sources(root: Path = REPO_ROOT) -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in sorted((root / SCAN_ROOT).rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        sources[rel] = path.read_text()
    return sources


def main(argv: list[str] | None = None) -> int:
    findings = analyze_sources(collect_sources())
    problems: list[str] = []
    warns: list[str] = []
    matched: set[tuple[str, str, str]] = set()
    for finding in findings:
        if finding.key in ALLOWLIST:
            matched.add(finding.key)
            continue
        if finding.key in KNOWN_RISKS:
            matched.add(finding.key)
            warns.append(
                f"KNOWN-RISK (ledgered, NOT safe) {finding.module}:"
                f"{finding.lineno} [{finding.func}] — "
                f"{KNOWN_RISKS[finding.key]}"
            )
            continue
        problems.append(
            f"{finding.rule} {finding.module}:{finding.lineno} "
            f"[{finding.func}] {finding.message}"
        )
    for key in sorted((set(ALLOWLIST) | set(KNOWN_RISKS)) - matched):
        table = "ALLOWLIST" if key in ALLOWLIST else "KNOWN_RISKS"
        problems.append(
            f"STALE-ROW {key[0]} [{key[1]}] rule {key[2]}: {table} row "
            f"matches no finding — remove it (never let an excuse outlive "
            f"the code it excused)"
        )
    for w in warns:
        print(w)
    if problems:
        for p in problems:
            print(f"RED {p}")
        print(f"check_money_race: {len(problems)} problem(s)")
        return 1
    print(
        f"check_money_race: OK — 0 violations under {SCAN_ROOT} "
        f"({len(ALLOWLIST)} allowlisted site(s), "
        f"{len(KNOWN_RISKS)} ledgered known-risk site(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
