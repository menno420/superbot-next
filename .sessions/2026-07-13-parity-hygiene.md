# 2026-07-13 — parity: golden flavor conformance + dead-ref/orphan hygiene

> **Status:** `in-progress`

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

(fills as items land)
