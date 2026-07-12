# 2026-07-12 — local-Postgres env-drift hygiene: reproducible local verification

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · adapter-lane baton item (NEXT-2 item 1, `control/status.md` @ `0a96960`)

## Scope

The last open adapter-lane baton item ("local-Postgres env-drift hygiene",
`control/status.md` NEXT-2 baton @ `0a96960`): make local verification
reproducible. The observed drift class: the local Postgres cluster's
provisioning state varies across sessions/containers — #290's session read
11 red integration/btd6_seed_data tests as a stable fact when it was "local
provisioning state" (corrected in
`.sessions/2026-07-12-live-adapter-landing.md` ⟲ review); the ORDER-004
live-drive session found the cluster "WIPED by a container restart" and
re-derived the recovery by hand
(`.sessions/2026-07-12-order004-live-drive-evidence.md`). Every fresh
session pays a re-derivation tax to stand up roles/DBs/env that CI gets
declaratively from its workflow files.

Deliverable: one idempotent provisioning script (`tools/setup_local_env.py`,
never destructive) + one runbook (`docs/operations/local-verification.md`)
that mirror the CI workflows' canonical values exactly
(`.github/workflows/golden-parity.yml` / `named-gates.yml` / `ci.yml`).

## What shipped

(filled at close-out)

## Evidence

(filled at close-out)

## 💡 Session idea

(filled at close-out)

## ⟲ previous-session review

(filled at close-out)
