# 2026-07-13 — night stamp dedupe: completeness table double-cites D-0043/D-0046

> **Status:** `complete`

- **📊 Model:** `fable-5` · night lane worker · mandate: remediation slice — `bootstrap.py check --strict` red on main after #436 ([stamp] D-0043 + D-0046 each cited from both `docs/status/completeness-table-2026-07-13.md` and their stamp home `docs/status/rebuild-completion-report-2026-07-09.md`)

## Scope

PR #436 (fishing cast-leg true-up) added a `D-0043` citation to the
completeness table's fishing row and Top-gaps item 1, and the earlier btd6
row carries a `D-0046` token — but both decisions are already stamped in
`docs/status/rebuild-completion-report-2026-07-09.md`. The stamp checker
(`check_stamp_discipline`, bootstrap.py) counts ANY bare `\bD-\d{3,}\b`
token in a doc under `docs/` as a citation, so the only permitted form is
to drop the tokens from the table entirely. Reword the three sites to
refer to the parked work descriptively (service PENDING-roster note,
`sb/domain/fishing/service.py:1032`; "stamped in that module" pointer for
btd6) without the decision-id tokens. Do NOT touch the stamp home. Keep
the #373/#387/#410 facts intact.

## Previous-session review

#436's true-up was accurate on the facts (cast leg live, minigame rung
parked) but stamped its evidence with the raw `D-0043` token in a doc
that isn't the decision's home — the exact drift risk `check_stamp_
discipline` exists to catch, and it took `--strict` red for every branch
cut after the merge. The btd6 row's `D-0046` had been sitting latent the
same way. The lesson generalizes: status docs should point at the stamp
home ("stamped in that module" / the PENDING-roster note), never repeat
the id.

## What shipped

PR #439, branch `claude/night-stamp-dedupe`. One doc touched:
`docs/status/completeness-table-2026-07-13.md` — three token sites
reworded (fishing row + Top-gaps item 1: "the parked real-time minigame
rung", pointer to `sb/domain/fishing/service.py:1032` kept; btd6 row:
"stay a ledger-parked decision, stamped in that module"). Stamp home
`docs/status/rebuild-completion-report-2026-07-09.md` untouched.
Verification: `bootstrap.py check --strict` exit 0 (both [stamp]
findings gone; only pre-existing never-exit-affecting claims advisories
remain); `pytest tests/ -q` 2911 passed / 15 skipped (one order-dependent
flake in `test_no_skip_fence_is_clean_and_catches_a_bypass` on the first
run, green in isolation and on the full rerun — docs-only diff cannot
touch it).

## 💡 Session idea

The stamp checker's `\bD-\d{3,}\b` regex makes every decision id a
single-home token, but nothing tells a writer where that home IS at the
moment they cite. A tiny `bootstrap.py stamp-home D-0043` lookup (or a
pre-commit hint that prints the existing home when a new doc introduces
an already-stamped id) would have stopped #436's double-cite at write
time instead of after merge.
