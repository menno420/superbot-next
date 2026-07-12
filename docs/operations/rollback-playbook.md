# Backup / DR / rollback playbook

> **Status:** `reference` — the S14 ops artifact (frozen L0 spec 13). Grammar:
> `ForwardMapKind`/`RollbackClass` + `derive_rollback_class` in
> `sb/spec/versioning.py`; fence `tools/check_rollback_disposition.py`;
> reverse importer `tools/importer/reverse/`; verify profile
> `sb/app/verify_boot.py`; workflows `.github/workflows/backup-db.yml` +
> `restore-verify.yml`. The end-to-end cutover procedure that drives this
> playbook's rollback section is [cutover-runbook.md](cutover-runbook.md).

## Backup port — owner one-time steps (cutover runbook, spec 13 §2.1)

1. Re-create the `DATABASE_PUBLIC_URL` Actions secret in THIS repo
   (Railway → Postgres → Connect → public URL). Its lifecycle row lives in
   `CREDENTIAL_REGISTRY` (S13).
2. Raise repo Settings → Actions → General → *Artifact and log retention*
   to **400** — else the monthly tier is SILENTLY clamped to 90
   (`restore-verify.yml` asserts this and goes red if skipped).
3. Set the repo Actions variable `BACKUP_ENABLED=true` (the de-repo-bound
   guard replacing the old `github.repository ==` relic).

## The verified-restore proof (continuous, side-effect-free)

`restore-verify.yml` (weekly): latest backup artifact → fresh Postgres
service container → `SB_VERIFY_BOOT=true SB_DATA_PLANE=test
python3 -m sb.app.verify_boot` → **verified := boots AND the dry-run
invariant sweep is clean** (S12 `run_verify_import`, dossier 11's
definition consumed verbatim). No gateway, no token, no PollSupervisor, no
outbox relay — a stale snapshot's overdue timers can never fire into real
guilds (T-7). It emits `last_verified_restore_age` — the §5.4 scoreboard's
backup-health / RPO witness. A stale/red value = do not cut over.

## RPO contract (spec 13 §2.3 — honestly costed)

Under the built posture (daily `pg_dump` + monthly tier) EVERY store —
money/audit included — has **RPO ≤ 24 h**: the append-only `audit_log` is
co-located in the dumped Postgres and dies with it. Minutes-RPO requires
owner **Q1**: (B) build a continuous off-box `audit_log` export scoped to
the `bears_value` spine, or (C) buy Railway PITR (plan-gated). Neither is
free; (A) the 24 h floor is the honest default until Q1 rules.

## Rollback-data disposition (spec 13 §2.4; Q-D15 posture B built)

Every StoreSpec derives a `rollback_class` mechanically
(`forward_map_kind` invertibility × `bears_value`, SESSION ⇒ COLLAPSE
short-circuit, `store_retirements.yml` ⇒ DROP; `replay_intent` = the one
owner NARROWING override). The fence: unresolved stores and a reverse
importer whose covered set drifts from the derived `REVERSE_IMPORTABLE`
set are CI-red. All 8 kernel stores are `NEW_ONLY` ⇒ `DECLARED_LOSS`
(fresh-chain tables — no old-schema home; the new `audit_log` spine never
round-trips, it is the forensic + REPLAY_INTENT substrate only).

**The delta boundary** is `cutover_flip_ts` — the UTC instant the Railway
flip goes live (§5.4 step 4 end: freeze old bot → final import delta →
flip), written ONCE at the flip through the audited settings seam under
`platform.cutover_flip_ts` (`CUTOVER_FLIP_TS_KEY`), never `os.getenv`.

**Rollback procedure (CUT-3):**

1. Rollback decision (last resort — the default response to a post-cutover
   bug is a hotfix FORWARD; short N + the progressive ring bound the blast).
2. Freeze the new bot.
3. Export each store's post-`cutover_flip_ts` delta, bucketed by its
   DERIVED `rollback_class` (per-store walk — the generic `audit_log` has
   no store column and supplies only the whole-window cross-check total).
4. `tools/importer/reverse` into the OLD DB — LEDGER rows re-insert by
   `mutation_id` (`ON CONFLICT DO NOTHING`); AGGREGATE stores copy the NEW
   ABSOLUTE value by natural-key upsert (never per-mutation deltas). Both
   idempotent; machine-readable stop-codes
   (`cutover_flip_ts_unset` / `reverse_importer_coverage_gap` /
   `store_import_failed`).
5. Emit the `DECLARED_LOSS` manifest: **M1** (per-store counts — the owner
   reviews and SIGNS, SF-g rail) + **M2** (per-`(guild, user, store)`
   amounts — feeds the CUT-3 comms/compensation hook; fed, not owned).
6. Re-deploy the old worker on its untouched OLD DB (§5.2 topology).
7. Notify guild admins (M2-driven per-user, M1-driven per-store).

**Window N:** the mechanism reads N off the scoreboard's
`rollback_window_writes_by_class` line; the VALUE of N is the owner's
Stage-3 carry (Q3).

## Owner-gated (routed in the question router)

- **Q1** RPO target + source tier (A 24 h floor / B off-box export / C PITR).
- **Q2 leg i** verified-restore as a HARD CUT-3 gate (recommended HARD);
  leg ii (which invariants hard-block) is decided ONCE in spec 11's Q2.
- **Q3** rollback-data disposition + window N — posture **B** built
  (reverse-import the invertible-∧-value-bearing tier, declare the rest,
  short forward-fix-biased N, owner-signed M1/M2).
