# O — Ops: migration + backup/restore + rollback drill, proven green in CI

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase — a NEW
> production-readiness track *beyond* the D1–D6 forward lanes, opening the
> "Beyond D1–D6" series on `docs/design/README.md`. This is a PLAN, not built
> work — the owner reacts and prioritizes; the code and `docs/decisions.md` win
> once slices land. Evidence citations are `file:line` at HEAD `cae15f8` unless
> noted.

## TL;DR

superbot-next's recoverability is **asymmetric and half-proven**. The *forward*
path is genuinely hardened — a forward-only fresh migration chain
(`migrations/0001..0055`), a checksum boot gate that refuses boot on drift
(`verify_applied_checksums`, `sb/kernel/db/migrations.py:192-224`), a daily +
monthly backup with a non-empty floor (`.github/workflows/backup-db.yml`), and a
weekly verified-restore proof (`.github/workflows/restore-verify.yml`). But the
*reverse* path is **prose that has never been exercised**: `restore-verify.yml`
has **zero runs** (`docs/operations/cutover-runbook.md:41`), the migration runner
has **no down-migrations at all** (forward-only by design), and the rollback
procedure is a seven-step reverse-importer walk (`rollback-playbook.md`
§Rollback) that has never round-tripped against a real database. An untested
restore is a hope, not a recovery plan; recoverability only counts once the full
loop — **migrate → backup → restore → rollback → deploy(Railway)** — has gone
green *unattended*. This doc proposes three CI/ops+docs slices to close that gap,
with **minimal-to-no `sb/` change**.

## Problem

Every piece of the recovery loop exists. **None of the reverse legs has been
observed green end-to-end.** Four grounded gaps.

### P1 — The migration chain is forward-only; "rollback" is not schema-down

The runner is a fresh-chain, forward-only applier: it validates
`NNNN_<snake>.sql` names, requires the chain contiguous from `0001`, applies
pending files under a `pg_advisory_lock`, and records a sha256 checksum per file
(`sb/kernel/db/migrations.py:140-189`). There is **no down-migration mechanism**
anywhere — the design is explicitly forward-only ("forward-only; rename, do not
duplicate", `sb/kernel/db/migrations.py:96-97`), and an edited/absent applied
file raises `MigrationDrift` → refuse boot, never auto-repair
(`sb/kernel/db/migrations.py:63-67,192-224`). Fifty-five migrations ship today
(`migrations/0001_idempotency_keys.sql … 0055_automation_rules.sql`) with a
committed `migrations/checksums.json` manifest and a CI twin
`tools/check_migrations.py` (numbering + immutability) named in the runner
docstring (`sb/kernel/db/migrations.py:16-18`).

The consequence for this design: **"rollback" in this repo is a data-plane
reverse-import into the OLD database, not a schema down-migration.** The rollback
playbook is explicit — every store is `NEW_ONLY ⇒ DECLARED_LOSS`, the reverse
importer re-inserts LEDGER rows by `mutation_id` (`ON CONFLICT DO NOTHING`) and
upserts AGGREGATE stores by natural key, bucketed around the write-once
`platform.cutover_flip_ts` delta boundary (`rollback-playbook.md:44-81`,
`cutover-runbook.md:252-277`). A rollback "drill" therefore cannot mean "reverse
the DDL" — it must mean "prove the forward chain applies cleanly onto a restored
snapshot AND the reverse importer round-trips a delta with row-level integrity".
That distinction is currently undocumented as a *drill* and unproven in CI.

### P2 — The restore proof exists but has never run (zero-run trapdoor)

`restore-verify.yml` is a real, well-shaped reliability job: it downloads the
latest daily backup artifact, restores it into a fresh `postgres:18` service
container, and boots the bot in `SB_VERIFY_BOOT=true SB_DATA_PLANE=test` mode to
run the dry-run invariant sweep — green **iff** it boots AND the sweep is clean
(`.github/workflows/restore-verify.yml:26-124`). It even asserts the monthly
artifact's 400-day retention was not silently clamped
(`restore-verify.yml:88-100`) and emits `last_verified_restore_age` as the RPO
witness (`restore-verify.yml:82-87`).

Three gaps make it a proof-on-paper today:

1. **Zero runs.** The workflow "has ZERO runs" and the cutover gate that depends
   on it is UNSATISFIED (`cutover-runbook.md:41-46`, G1 in the ownership table
   `cutover-runbook.md:284`). A restore that has never been observed green is
   indistinguishable from no backup at all.
2. **Scheduled-only, not PR-visible.** It fires on `schedule: '0 5 * * 1'`
   (weekly) + `workflow_dispatch` (`restore-verify.yml:28-31`) and is *not* one
   of the six required named gates (`.github/workflows/named-gates.yml`). So a
   change that breaks restorability is invisible until the next Monday, if the
   backup vars are even set.
3. **It asserts boot+sweep, not row-level integrity.** The sweep proves the bot
   *boots clean* on the restored schema and the invariant sweep passes; it does
   **not** assert that a known set of rows survived the dump→restore round-trip
   (counts per store, a checksum of representative economy/audit rows). "Boots
   clean" and "the money rows are all there" are different claims.

Its guard is `if: vars.BACKUP_ENABLED == 'true'` (`restore-verify.yml:45`) and
all of this is owner-gated on the backup setup (P3), so on a fork or the
pre-setup repo it simply does not run.

### P3 — Backup is armed in code but skipped in practice; and it is the ONLY layer

`backup-db.yml` is complete: daily `02:00 UTC` + monthly `1st 03:00 UTC`
`pg_dump` (PGDG client, `--no-owner --no-acl`), a **non-empty floor** of ≥10
`CREATE TABLE` statements, 90-day daily / 400-day monthly artifact retention, and
a failure-issue (`.github/workflows/backup-db.yml:28-159`). Its own header is
honest that the floor "proves the dump is NON-EMPTY, NOT that it is RESTORABLE"
(`backup-db.yml:16-17`) — restorability is P2's job.

But: all four scheduled backup runs to date concluded `skipped`
(`cutover-runbook.md:48-58`, G2), because it is guarded on three owner one-time
steps — the `DATABASE_PUBLIC_URL` secret, the retention-400 raise, and
`BACKUP_ENABLED=true` (`backup-db.yml:22-26`, `rollback-playbook.md:11-20`). This
is exactly the open item in `docs/NEXT-TASKS.md` §5 ("Turn on the data safety
net. Set `BACKUP_ENABLED=true` … confirm `restore-verify.yml` goes green"). And
this artifact backup is the **only** backup layer — Railway-native volume backups
are plan-gated (`backup-db.yml:33-36`), so the whole RPO ≤ 24 h contract
(`rollback-playbook.md:33-40`) rides on this one workflow actually running.

### P4 — No single verified runbook ties the loop to the deploy

The ops knowledge is spread across three good-but-separate docs — the backup/DR
grammar and RPO contract (`rollback-playbook.md`), the end-to-end cutover
(`cutover-runbook.md`), and credential rotation (`credential-lifecycle.md`) — and
two workflows. What is missing is a **single consolidated runbook that ties
migrate → backup → restore → rollback → deploy into one procedure whose every leg
has a green CI witness**. The deploy leg matters here: on this repo **a merge to
`main` deploys** — "merge/var change = deploy = restart, Q-0193"
(`credential-lifecycle.md:20-21`, `cutover-runbook.md:199-200`) via Railway,
which packages from the root `Dockerfile` / `railway.json` (both present on
`main`; `cutover-runbook.md:60-66`). So a bad migration merged to `main` deploys
itself, and the *only* recovery is the unrehearsed reverse path above. The loop
needs one authority that an operator (or the owner) can follow under pressure,
with each step pointing at the CI job that proves it.

## Proposed design

Three slices, ordered cheapest-highest-signal first. This is **CI/ops + docs**
work — it respects the layer rules in `.claude/CLAUDE.md` with **no `sb/` code
change** in slices 1 and 3, and at most a tiny test-only helper in slice 2 (the
drill drives existing entrypoints — `run_migrations`, `sb.app.verify_boot`, the
reverse importer — it does not add kernel surface).

### O.1 — Restore-verify with row-level integrity (turn the data-safety-net ON)

Harden `restore-verify.yml` from "boots + sweep clean" into "boots + sweep clean
+ **known rows survived**", and make it observable per-PR, not weekly-only.

- **Assert row-level integrity.** After the `psql` restore step
  (`restore-verify.yml:107-113`), add a step that runs a fixed integrity query
  set against the restored `restore_target` DB: per-store row counts for the
  value-bearing stores (economy/treasury/xp/karma — `migrations/0012..0015`), the
  `schema_migrations` count = 55 (chain fully applied), and a stable checksum
  (e.g. `md5(string_agg(... ORDER BY id))`) over a representative append-only
  slice of `audit_log` (`migrations/0003_audit_spine.sql`). Compare against
  expected values captured from the pre-dump source (or, for the ephemeral drill
  variant, from a seeded fixture — see O.2). This upgrades P2's "boots clean" to
  "the money and audit rows are all there".
- **Make it PR-visible on the paths that can break it.** Add a `pull_request`
  trigger scoped to `paths: [migrations/**, sb/kernel/db/**,
  .github/workflows/restore-verify.yml]` **using a seeded ephemeral fixture**
  (not the real backup artifact, which stays weekly + `workflow_dispatch`) — so a
  migration or runner change that breaks restore-round-trip goes red *in the PR*,
  while the real-artifact proof stays the scheduled reliability witness. Keep the
  existing `vars.BACKUP_ENABLED` guard only on the real-artifact leg.
- **Seams changed:** `.github/workflows/restore-verify.yml` only (add integrity
  step + a PR-scoped seeded-fixture job). No `sb/` change. The verify-boot
  entrypoint it already drives is `sb/app/verify_boot.py` (unchanged).

### O.2 — A rehearsed migrate + rollback drill on ephemeral Postgres

A new CI job — `rollback-drill.yml` (or a job inside the ops workflow) — that
rehearses the reverse path against a throwaway Postgres service container, honest
to the forward-only reality (P1): it proves the **reverse importer round-trips**,
not that migrations reverse (they cannot).

1. **Forward-apply the whole chain** onto a fresh `postgres:18` service
   container: drive `sb.kernel.db.migrations.run_migrations()` (the real
   entrypoint) → assert `schema_migrations` = 55 and `verify_applied_checksums()`
   passes (chain applies clean + checksum gate holds).
2. **Checksum-drift assertion.** Tamper one applied migration file byte-for-byte
   and assert `verify_applied_checksums()` raises `MigrationDrift`
   (`sb/kernel/db/migrations.py:219-223`) — proving the boot integrity gate
   actually fires, not just that it exists.
3. **Seed → dump → restore → integrity** (the O.1 fixture path, shared): seed
   representative rows into the value-bearing stores, `pg_dump | gzip`, restore
   into a *second* fresh container, assert the O.1 integrity query set matches.
4. **Reverse-importer round-trip** (the actual "rollback"): stand up an OLD-DB
   container, set a `platform.cutover_flip_ts` delta boundary, write a small
   post-flip delta, run `tools/importer/reverse` into the OLD DB, and assert the
   documented semantics hold — LEDGER rows idempotent by `mutation_id`
   (`ON CONFLICT DO NOTHING`), AGGREGATE stores at the NEW absolute value by
   natural-key upsert, run twice to prove idempotency
   (`rollback-playbook.md:66-70`, `cutover-runbook.md:263-268`). Assert the
   machine-readable stop-codes (`cutover_flip_ts_unset` /
   `reverse_importer_coverage_gap` / `store_import_failed`) on the error paths.
   *(The forward importer `tools/importer/` ships only `reverse/` today — the
   forward leg "lands with the CUT-2 build" (`cutover-runbook.md:116-124`); the
   drill exercises whichever legs exist and is a placeholder-skip for the
   not-yet-built forward importer, flagged in Open Questions.)*
- **Seams changed:** a new workflow + a small `tools/`-level or `tests/`-level
  drill driver script that calls existing entrypoints. **No kernel surface** —
  the drill imports `sb.kernel.db.migrations` and the reverse importer as they
  are. Respects the layer map (a CI harness driving the composition entrypoints,
  like `restore-verify.yml` already does with `sb.app.verify_boot`).

### O.3 — Consolidated ops runbook (one verified recovery procedure)

A new `docs/operations/recovery-drill-runbook.md` (or a top section folded into
the existing cutover runbook — see Open Questions) that ties the loop into a
single procedure, each step pinned to the CI job that proves it:

- **migrate** — forward-only chain + checksum gate (O.2 step 1–2;
  `sb/kernel/db/migrations.py`, `tools/check_migrations.py`).
- **backup** — daily/monthly `pg_dump` artifact + non-empty floor (P3;
  `backup-db.yml`), with the three owner one-time steps surfaced as a checklist.
- **restore** — verified restore + row-level integrity (O.1; `restore-verify.yml`).
- **rollback** — reverse-importer round-trip + `DECLARED_LOSS` manifest
  (O.2 step 4; `rollback-playbook.md` §Rollback) — explicitly noting rollback is
  data-plane reverse-import, **not** schema-down (P1).
- **deploy(Railway)** — merge=deploy (`credential-lifecycle.md:20-21`), the
  `Dockerfile`/`railway.json` package, and **deploy rollback** as an open scope
  question (redeploy a prior image vs data rollback).

This slice is pure docs — it cross-links the existing three ops docs rather than
duplicating them, and adds the one thing none of them is: a single ordered
procedure with a green-CI witness beside every leg. No layer-rule surface.

## Affected surfaces

| Band | Files | Slice |
|---|---|---|
| CI / restore | `.github/workflows/restore-verify.yml` (row-level integrity step + PR-scoped seeded-fixture job) | O.1 |
| CI / drill | new `.github/workflows/rollback-drill.yml` + a `tools/`- or `tests/`-level drill driver (calls existing entrypoints) | O.2 |
| CI / backup | `.github/workflows/backup-db.yml` (unchanged code; its owner one-time steps surfaced in the runbook) | O.3 |
| kernel / db | `sb/kernel/db/migrations.py` — **driven, not changed** (`run_migrations`, `verify_applied_checksums`) | O.2 |
| tooling | `tools/importer/reverse/` — **driven, not changed**; `tools/check_migrations.py` cross-referenced | O.2 |
| ops / docs | new `docs/operations/recovery-drill-runbook.md`; cross-links `rollback-playbook.md` / `cutover-runbook.md` / `credential-lifecycle.md` | O.3 |
| design index | `docs/design/README.md` (this doc's index row) | — |

No `sb/domain/*`, no `sb/spec/*`, no kernel behavior change in any slice — the
surface is CI workflows + a drill driver + docs, consistent with the layer map
(a harness driving existing composition entrypoints).

## Rough size + suggested PR slicing

- **O.1 — restore-verify + row-level integrity** — **S–M**. A row-integrity step
  plus a PR-scoped seeded-fixture job on an existing, well-shaped workflow.
  Highest signal for the cost (turns the data-safety-net from paper into a
  per-PR green witness). Land first, standalone.
- **O.2 — migrate + rollback drill** — **M**. A new workflow + a driver script
  calling existing entrypoints; the reverse-importer round-trip is the larger,
  more invasive leg (needs the OLD-DB + delta fixtures). Shares the seeded fixture
  with O.1. Land second.
- **O.3 — consolidated recovery runbook** — **S**, pure docs; can land anytime
  but reads best after O.1/O.2 exist so each step can cite a *green* job rather
  than a planned one.

Suggested landing order: **O.1 → O.2 → O.3**.

## Open questions for the owner

1. **Backup source + cadence.** Stay on the GitHub-Actions `pg_dump` artifact
   (daily + monthly, the only layer today because Railway volume backups are
   plan-gated — `backup-db.yml:33-36`), or is a Railway managed-backup / PITR
   tier (`rollback-playbook.md` §RPO Q1) now in budget? This decides whether O.1's
   real-artifact leg keeps pointing at the Actions artifact or a Railway source.
2. **Where the throwaway restore DB runs.** The drill uses a CI **service
   container** (`postgres:18`, as `restore-verify.yml:46-56` already does) — is a
   free ephemeral container the intended target, or should the drill run against a
   dedicated Railway scratch DB for higher fidelity to prod Postgres?
3. **Drill cadence — per-PR vs nightly.** O.1/O.2 propose a **PR-scoped seeded
   fixture leg** (fast, deterministic, gates migration/runner changes) plus the
   **real-artifact proof staying weekly**. Is per-PR the right cost, or should the
   full drill be nightly + `workflow_dispatch` only, keeping PRs light? And should
   the restore proof become a **HARD CUT-3 gate** (recommended in
   `rollback-playbook.md` Q2 leg i)?
4. **Rollback scope — schema vs data.** Confirm the design premise (P1): rollback
   is **data-plane reverse-import**, and the migration chain is forward-only with
   no down-migrations. Is that the intended permanent posture, or does the owner
   eventually want reversible/down migrations (a much larger change to
   `sb/kernel/db/migrations.py` and every `migrations/*.sql`)?
5. **Deploy rollback in scope?** Since **merge = deploy** on Railway
   (`credential-lifecycle.md:20-21`), is *deploy* rollback (Railway redeploy of a
   prior GHCR image / prior commit — `release.yml` tags to
   `ghcr.io/menno420/superbot-next`, `cutover-runbook.md:60-66`) part of this loop,
   or is deploy rollback strictly the owner's Railway-console action and only
   **data** rollback is drilled here?
6. **Integrity fixture ownership.** O.1/O.2 need a seeded row fixture + expected
   integrity values (counts + audit-slice checksum). Should that fixture live
   under `tests/fixtures/` and be owner-reviewable, and which stores are the
   mandatory value-bearing set beyond economy/treasury/xp/karma
   (`migrations/0012..0015`)?
