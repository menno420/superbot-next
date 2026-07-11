# READ FIRST — how to read this repo's red

> **Status:** `reference` — the one-screen orientation the gen-1 retro named as
> its E4 prevention (`docs/retro/self-review-2026-07-09.md` §E4): a fresh
> no-history session's first misread is THE RED REPLAY NUMBERS.

## Red ≠ broken

- **`golden-parity` / `report` is BORN RED BY DESIGN.** It is the owner's
  red-until-parity dashboard over the full 465-golden corpus
  (`tools/run_golden_parity.py --report`), deliberately exits 1 while any
  subsystem is unported, and must **never** be marked a required check
  (`docs/decisions.md` — the parity-workflow entry and its "never required"
  clause). The **`gate` job is the required leg and is green**: ported
  subsystems must replay green; pending ones are reported, not failing.
- **"0/465 green, 0/49 ported" is the ledgered starting state**, not a
  regression. Every replay red is *classified* into a named red-class
  (`docs/status/testing-report-2026-07-09.md`, red-class table); an
  unclassified red is the thing that would actually be a bug.
- **`ported` flips are a one-way door (A-16).** A subsystem row in
  `parity/parity.yml` flips `pending → ported` only with its depth roster
  satisfied (`tools/check_parity_depth.py`), and never flips back. The first
  flip is ⚑ gated on the owner's **flag-13** corpus-red disposition ruling
  (`control/status.md` OWNER-ACTION 1).

## Where live truth lives

- `control/status.md` — the live status ledger (blockers, owner actions, next lane).
- `docs/status/testing-report-2026-07-09.md` — the live-testing ledger (what has
  actually been driven in a real guild, band by band).
- `docs/status/games-ai-cutover-risk-review-2026-07-11.md` — current cutover-risk review for games money races, golden-parity false-green risk, and AI operator-surface inertness.
- `parity/parity.yml` — the port dashboard (49 subsystem rows).
- `docs/decisions.md` — append-only decision ledger (D-entries).

Do not "fix" the report leg to green, and do not treat its red as a stop signal
for unrelated merges — merges gate on `ci.yml` + the `gate` leg only.
