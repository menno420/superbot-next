# 2026-07-11 — substrate-kit upgrade v1.9.0 → v1.10.0 (distribution wave)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable 5 · high · maintenance (Q-0194)

## Scope

Kit-seat distribution session (owner directive Q-0261.3): upgrade the
vendored substrate-kit from v1.9.0 to v1.10.0 using the pinned,
sha256-verified release asset (tag v1.10.0 @ kit commit 1b5db16, release
run 29142780212, sha256 ba69fc5c…c2f3b5a4 — three-way verified before
staging). Kit-owned files only; no domain work, no control/inbox or
control/status edits.

About to do: stage `bootstrap.py.new` + `release.json`, run the canonical
upgrade (including `--apply-docs`), verify the v1.10.0 payload
(session-card-hold gate path, retroactive model-doctrine append,
exactly-one-new-backup, carve-out section survival), run
`check --strict` + `--simulate-added-card` + the test suite, then flip
this card complete as the deliberate last commit.
