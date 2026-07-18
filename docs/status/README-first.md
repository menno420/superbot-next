# READ FIRST — how to read this repo's red

> **Status:** `reference` — the one-screen orientation the gen-1 retro named as
> its E4 prevention (`docs/retro/self-review-2026-07-09.md` §E4): a fresh
> no-history session's first misread is THE RED REPLAY NUMBERS.

## The report leg is GREEN now (2026-07-13) — red there is a real signal

- **`golden-parity` / `report` reached FULL-CORPUS PARITY on 2026-07-13**:
  484/484 goldens green across 51/51 ported subsystems, zero `_unmapped`
  (run 29238825392 on main; first green: run 29222893993, the fishing
  port slice 4, #350). The leg was born red-by-design — the owner's
  red-until-parity dashboard (`tools/run_golden_parity.py --report`),
  deliberately exiting 1 while any subsystem was unported — and stayed
  red from repo birth until that flip. **That doctrine is retired: a red
  `report` on main is now a REAL regression signal — investigate it like
  any other red.** The job remains non-required (`docs/decisions.md` —
  the parity-workflow entry's "never required" clause still stands); the
  **`gate` job stays the required leg**: ported subsystems must replay
  green; pending ones would be reported, not failing.
- **"0/465 green, 0/49 ported" was the ledgered starting state** (not a
  regression — historical context for old cards/retros citing it). Every
  replay red was *classified* into a named red-class
  (`docs/status/testing-report-2026-07-09.md`, red-class table); an
  unclassified red was — and now every report red is — an actual bug
  signal.
- **`ported` flips are a one-way door (A-16).** A subsystem row in
  `parity/parity.yml` flips `pending → ported` only with its depth roster
  satisfied (`tools/check_parity_depth.py`), and never flips back. The first
  flip is ⚑ gated on the owner's **flag-13** corpus-red disposition ruling
  (`control/status.md` OWNER-ACTION 1).

## Where live truth lives

- `control/status.md` — the live status ledger (blockers, owner actions, next lane).
- `docs/retro/archive-ready-2026-07-11.md` — the 2026-07-11 close-out's resume-here
  note (verified state snapshot, owner-actions, PR/branch sweep, re-arm recipe
  pointers) — start THERE when un-archiving.
- `docs/status/testing-report-2026-07-09.md` — the live-testing ledger (what has
  actually been driven in a real guild, band by band).
- `parity/parity.yml` — the port dashboard (49 subsystem rows).
- `docs/status/completeness-table-2026-07-13.md` — per-subsystem completeness
  inventory (core/admin/setup × every subsystem, ORDER 017 item 1).
- `docs/status/prod-readiness-backlog-2026-07-17.md` — the prioritized,
  cold-pickup-ready production-readiness backlog (owner-only ops cutover +
  the remaining declared-honest pending terminals, from the full-tree survey
  @ `1893d32`).
- `docs/decisions.md` — append-only decision ledger (D-entries).

The report leg is green (2026-07-13, run 29238825392) — a red there is no
longer expected: stop and root-cause the offending change before landing it.
Merges still gate on `ci.yml` + the `gate` leg (`report` stays non-required),
but never wave off a report red as "by design" again.
