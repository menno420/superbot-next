# 2026-07-13 — parity: golden flavor conformance + dead-ref/orphan hygiene

> **Status:** `complete`

- **📊 Model:** fable-5 · parity-hygiene lane (claim
  `control/claims/parity-hygiene-flavor-orphans.md`, PR #417; branch
  `claude/parity-hygiene` off main @ d085a67)

## Scope

Three coordinator-ruled hygiene items, all decide-and-flag (PL-001),
provenance PRs #415/#416:

1. **Golden flavor conformance** — the coordinator ruled the canonical
   minted-golden byte-form is the stripped D-0073 flavor (disposed doc,
   no kernel spine). Two goldens are stored RAW
   (`parity/goldens/creature/creature_battle_accept.json`,
   `parity/goldens/cleanup/cleanup_policies_open.json`); re-mint both
   via `tools/mint_golden.py <case> --write --force`. Expected diff per
   golden: `db_delta` loses `audit_log` + `event_outbox`,
   `command.dispatched` entries vanish from step events — everything
   else byte-identical. Corpus stays 494, every count pin byte-stable.
2. **Dead harness ref** — `parity/harness/runner.apply_isolation_resets`
   loads `tests/_isolation.py`, which no longer exists in the tree
   (FileNotFoundError on live use; found-and-flagged by the #416 card).
   Remove the def, its `__all__` entry, its `capture_case` call, the
   now-unused `importlib.util` import, and the stale
   `parity/README.md` description; add a loadability pin test in
   `tests/unit/parity_gate/`. parity/harness is imported-harness code —
   this removal is coordinator-ruled (dead-ref hygiene), flagged here
   as decide-and-flag rather than re-routed.
3. **Orphan baseline prune (8 dead, 1 live)** — per-row oracle verdicts
   (superbot @ a724e9d): the blackjack (2), rps (3), and btd6 (3)
   pending orphans are DEAD — their features landed in next under other
   refs (blackjack tournament `_route` handlers, rps tournament
   `_route` handlers, live `btd6.cmd_events_*`/`cmd_ops_*`/`cmd_ct`).
   Delete the dead `_register_pending()` defs/rows in
   `sb/domain/blackjack/handlers.py`, `sb/domain/rps/handlers.py`,
   `sb/domain/btd6/service.py` (keeping `_INGESTION_PENDING`), re-point
   the roster canaries in
   `tests/unit/invariants/test_composition_parity.py`, prune
   `tools/check_orphan_pendings.py::_KNOWN_ORPHANS` to the single LIVE
   row `settings.group_pending` (real future port target: per-group
   scalar edit + reset, settings-mutation slice, write-seam-gated), and
   shrink the pinned list in `tests/unit/app/test_orphan_pendings.py`.

## Verification

Shipped as PR #420 (`claude/parity-hygiene` off main @ d085a67):

- Item 1: both re-mints dry-run first, then `--write --force` via the
  #416 tool (Postgres provisioned by `tools/setup_local_env.py`). Diffs
  are PURE DELETIONS (0 added lines): only `audit_log`/`event_outbox`
  db_delta tables + `command.dispatched` step events drop (cleanup also
  pops one now-empty `events` list). Corpus stays 494 on disk; zero
  diff to parity/parity.yml + both pin test files.
  `python3 tools/run_golden_parity.py --gate`: **GREEN — all 494
  golden(s) across 50 ported subsystem(s) replay clean** (run again
  post-Item-3, same line).
- Item 3: `python3 tools/check_orphan_pendings.py`: **OK — 15
  registered *_pending handler(s) (14 referenced, 1 on the burn-down
  baseline); 882 handler ref(s) walked, 0 dangling, 0 new orphans**.
  `manifest.snapshot.json` recompiled (`tools/manifest_compile.py
  --write`); its diff is exactly the 8 dead handler registration rows.
- `python3 -m pytest tests/ -q` (Postgres DOWN — the unit-env posture):
  **2856 passed, 15 skipped, 1 warning in 64.54s**.
- `python3 bootstrap.py check --strict`: green modulo this card's
  designed born-red hold (flips with this commit) + three pre-existing
  claims advisories (never exit-affecting; the claims-duplicate pair —
  completeness-remainders.md vs parity-hygiene-flavor-orphans.md both
  claiming `tests/` — was on main before this branch).
- Found en route (NOT fixed — out of scope): `tests/unit/parity_gate/
  test_check_parity_depth.py::TestGateDriver::
  test_report_leg_prints_full_corpus_banner` asserts
  `run_report() == 1` on the assumption that no replay binding exists
  in the unit env — with a LIVE local Postgres the binding probe
  succeeds, the full corpus replays green, `run_report()` returns 0
  and the test reds. Pre-existing (byte-identical on main), purely
  env-sensitive; the Postgres-DOWN full-suite run above is green.

## 💡 Session idea

`test_report_leg_prints_full_corpus_banner` pins the ENVIRONMENT, not
the behavior: it needs `_replay_binding()` to fail, so any session with
a live local Postgres (increasingly the norm now that
`tools/setup_local_env.py` makes provisioning one-command) reds the
unit suite for a non-defect. Monkeypatching
`tools.run_golden_parity._replay_binding` to return `(None, reason)`
inside the test — the exact seam its sibling
`test_gate_leg_reds_on_silently_dropped_ported_golden` already
monkeypatches in the other direction — would make the banner assertion
env-independent and retire the Postgres-up/Postgres-down verification
split this session had to route around.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-port-tooling-mint.md`, PR #416.) The
single most useful handoff in this lane's history: its found-and-fixed
note WAS Item 2's spec (dead ref, exact sites, the loadability-pin
recipe followed verbatim), its 💡 flavor-drift idea WAS Item 1, and the
tool it shipped executed both re-mints with every count pin as a
machine-verified no-op — the only friction was its Verification
claim of a full-suite green WITH Postgres up, which this session could
not reproduce (the report-leg banner test reds when the binding
succeeds; see the found-en-route note above).
