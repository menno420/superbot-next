# Cutover runbook — CUT-2 / CUT-3 end-to-end

> **Status:** `reference` — the consolidated production cutover procedure
> (design-spec steps 15/17; `rebuild-completion-report-2026-07-09.md` §3(d)
> items 32–33). Consumes: rollback `docs/operations/rollback-playbook.md`;
> credentials `docs/operations/credential-lifecycle.md`; census
> `tools/permission_census.py`; verify-import `sb/app/verify_boot.py`
> (S12 `run_verify_import`); coverage-debt `tools/check_verified_live.py`;
> reverse importer `tools/importer/reverse/`; delta boundary
> `platform.cutover_flip_ts` (`CUTOVER_FLIP_TS_KEY`).

This runbook takes the bot from **test-plane, live-proven** (CUT-1 done) to
**production live on the new worker** (CUT-3), with a bounded rollback
window. It is the single authority for CUT-2 and CUT-3; the scattered
checklist rows it replaces are marked SUPERSEDED in the completion report's
§3(d). Every step is tagged **⚑ OWNER** (an irreducible human touch — real
secrets, token custody, repo visibility, retention/vars, cutover timing,
`SB_PROD_ATTEST`) or **AGENT** (dry-runs, verify, census generation,
debt-list). The ownership table at the end is the authoritative index; ⚑
in-line marks the owner-gated legs so they cannot be skimmed past.

Prod boot contract (FAIL_FAST, `sb/spec/config.py`): a production worker
requires `DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`, `SB_DATA_PLANE=prod`,
and `SB_PROD_ATTEST` present to attest prod. Entry is `python3 -m sb`;
migrations auto-run in `pool.init`. All live evidence to date is
`SB_DATA_PLANE=test` — CUT-3 is the first `prod` boot.

---

## 0. Preconditions — HARD GATES (all must be green before CUT-2 opens)

Each gate has an exact check. A red or stale value means **do not proceed**.

1. **⚑ Verified-restore is fresh green** (S14 Q2(i), ruled a HARD CUT-3 gate
   in PR #30; see `rollback-playbook.md` §Owner-gated Q2 leg i).
   `restore-verify.yml` must have a recent successful run and emit a
   fresh `last_verified_restore_age`. As of this writing the workflow has
   **ZERO runs** (`program-review-2026-07-12.md` §Q4 item 3) — this gate is
   UNSATISFIED. The rollback playbook's own rule: *a stale/red restore
   witness = do not cut over* (`rollback-playbook.md` §"The verified-restore
   proof"). Check: the workflow's latest conclusion is `success` and its
   `last_verified_restore_age` is within cadence.
   - Local re-check of the same proof (no CI): against a restored snapshot,
     `SB_VERIFY_BOOT=true SB_DATA_PLANE=test DATABASE_URL=<restored> python3 -m sb.app.verify_boot`
     exits 0 (see §CUT-2 verify-import).

2. **⚑ Backup is actually running** (spec 13 §2.1 owner one-time setup). All
   four scheduled backup runs to date concluded `skipped` (§Q4 item 3). Owner
   must, in THIS repo:
   - Re-create the `DATABASE_PUBLIC_URL` Actions **secret** (Railway →
     Postgres → Connect → public URL); its row lives in `CREDENTIAL_REGISTRY`
     (S13).
   - Raise Settings → Actions → General → *Artifact and log retention* to
     **400** (else the monthly tier is silently clamped to 90 and
     `restore-verify.yml` goes red).
   - Set the repo Actions **variable** `BACKUP_ENABLED=true`.
   - Check: `backup-db.yml`'s next scheduled run concludes `success` (not
     `skipped`) and produces an artifact.

3. **⚑ Deploy packaging merged.** CUT-3 deploys a container, so the sibling
   deploy-packaging PR (`deploy/container-packaging`) must be merged FIRST:
   `Dockerfile`, `docker-compose.yml`, `railway.json`, and
   `.github/workflows/release.yml` (builds + tags to
   `ghcr.io/menno420/superbot-next`; **no auto-deploy** — the flip is manual,
   §CUT-3). Check: the four paths exist on `main` and `release.yml` has a
   green tagged build. (Zero deploy packaging is §Q4 item 2.)

4. **⚑ `SB_PROD_ATTEST` custody resolved** (CL-5b, OPEN — SF-d). The prod
   attestation credential's durable custody SOURCE (plain env vs sealed vs
   OIDC) is un-ruled (`credential-lifecycle.md` §Owner-gated). Only its
   rotation ROW lives in `CREDENTIAL_REGISTRY`; the actual custody model is an
   owner call and must be decided before a prod boot. Check: CL-5b is ruled in
   `docs/decisions.md` and the attest value is provisioned in the production
   Railway service under the ruled custody model.

5. **⚑ Same Discord application-id confirmed** (PG-5, confirmed
   NON-NEGOTIABLE cutover constraint, ruled in PR #30). CUT-3 is a TOKEN swap
   on the SAME application id —
   NEVER a new app id. This is what preserves guild admins' per-command
   permission overrides through re-registration (§CUT-2 census). Check: the
   production bot token belongs to the same application id the census was
   captured against.

6. **Supply-chain lock is fresh** (AGENT-checkable). Deploy installs
   `pip install --require-hashes -r requirements.lock`
   (`credential-lifecycle.md` §Supply-chain). Check: `check_lockfile_fresh`
   is green in CI.

---

## CUT-2 — prod-data staging + permission census + visibility flip

CUT-2 stages the migration and captures the Discord-side security config; it
performs **no** live token swap. Ordering matters: **the public→private repo
flip happens BEFORE any artifacts carry real balances** (item 3).

### C2.1 — Prod-data import DRY-RUN  ·  AGENT (generation) / ⚑ OWNER (prod DSN)

The forward importer (`tools/importer/`, prod DB → new-chain DB) **lands with
the CUT-2 build** — `tools/importer/` today ships only `reverse/` (see its
`__init__.py`: "the forward importer lands with the CUT-2 build"). Until it
exists, the dry-run is owner/CUT-2-build-gated. When built, run it
**dry-run only, NEVER a live write**, against a RESTORED snapshot (never the
live prod DB), producing the row-count/mapping report the verify-import
(C2.4) then validates. ⚑ The prod/restored `DATABASE_URL` is an owner secret.

### C2.2 — Published reaction-capture window  ·  ⚑ OWNER

Announce and open the reaction-capture window on the OLD bot (design-spec
§2.10.4 Phase-0.5 telemetry sidecar; completion-report item 31). This is a
comms + timing act on the live old bot — owner-owned. Its output feeds the
sim runs (item 21) and the A-18(3) reaction-window debt publication (C3.4).

### C2.3 — Live permission census  ·  AGENT (partition/verify) / ⚑ OWNER (GET sweep)

Guild admins' per-command Server-Settings overrides are a SECOND security
config DB living in Discord: **bot-token-READABLE but bot-token-UN-WRITABLE**
(the PUT needs an admin OAuth2 Bearer — there is NO automated replay;
`tools/permission_census.py` module docstring; PG-4). Preservation = id
stability under the SAME application id (PG-5); the RENAMED/DROPPED remainder
gets an admin-notice.

- **⚑ Capture (the live GET sweep) — OWNER-GATED.** One GET per guild:
  `GET /applications/{app}/guilds/{g}/commands/permissions`, bot-token
  authorization. This needs the production bot token and network to Discord;
  it is **not implemented in-tool** and is **not test-plane runnable** (the
  tool consumes a captured JSON — it has no network code). Owner captures the
  sweep into a census JSON of schema
  `{guild_id: [{"command_id", "command_name", "permissions": [{"id","type","permission"}]}]}`.
- **Partition (AGENT).** With the captured census and the Q-0224 rename map:
  ```
  python3 tools/permission_census.py --census census.json --rename-map rename-map.json
  ```
  Prints `N override(s) — P preserved, R renamed, D dropped` plus one
  `NOTICE` admin-notice line per RENAMED/DROPPED override with the exact
  re-apply overlay. `--json` emits the machine-readable partition +
  `admin_notice` lines for the CUT-3 comms plan. (PG-5(b) would pass
  `--new-application-id`, forcing EVERY override into the admin-notice —
  which is exactly why same-app-id is non-negotiable.)
- **Carry-verify (AGENT, post-swap, runs in CUT-3).** After re-registration,
  read the census back (bot-token GET) and assert every PRESERVED override
  survived:
  ```
  python3 tools/permission_census.py --census census.json --verify post-swap-census.json
  ```
  Exit 1 = a PRESERVED override vanished/changed = **cutover-blocking**
  copy-fidelity failure (FJ §4 #7).

### C2.4 — verify-import  ·  AGENT (drive) / ⚑ OWNER (restored DSN)

Verify-import is the side-effect-free boot profile (`sb/app/verify_boot.py`,
consuming S12 `run_verify_import` verbatim): boots to readiness with no
gateway/token, PollSupervisor and outbox relay never built, plane-fenced to
test, then runs the dry-run invariant sweep. Against a restored snapshot:
```
SB_VERIFY_BOOT=true SB_DATA_PLANE=test DATABASE_URL=<restored> python3 -m sb.app.verify_boot
```
Exit 0 = verified (boots AND sweep clean); non-zero prints machine-readable
stop codes and the failing stage. ⚑ The restored `DATABASE_URL` (and the
Postgres/`asyncpg` runtime) are owner-provisioned — without a real DB the run
stops at `db_init` (see §Tooling-wiring outcomes). This is the SAME proof
`restore-verify.yml` runs weekly; a green here on the migration target is the
import's correctness witness.

### C2.5 — Repo public→private flip  ·  ⚑ OWNER  (BEFORE artifacts)

Flip repo visibility public→private **before** any CI artifact can carry real
balances (item 3). This precedes CUT-3 so no prod-data-bearing artifact is
ever produced under public visibility. Owner-only (repo admin).

---

## CUT-3 — token swap + flip + rollback window + debt publication

CUT-3 is the live flip. It is a token swap on the SAME application id (PG-5);
the composition root's global app-command sync goes from compare-only ("the
remote GLOBAL set is still the OLD bot's until CUT-3", `sb/app/main.py`) to
authoritative.

### C3.1 — Freeze → final delta → same-app-id token swap  ·  ⚑ OWNER

Sequence (`rollback-playbook.md` §5.4 step 4): **freeze the old bot → run the
final import delta → flip**. The swap replaces `DISCORD_BOT_TOKEN_PRODUCTION`
with the production token of the SAME application id (PG-5 — never a new app
id, or every permission override is lost). The swap of a `WORKER_ENV`
credential auto-redeploys the worker (merge/var change = deploy = restart,
Q-0193). The new worker boots `python3 -m sb` with `SB_DATA_PLANE=prod` +
`SB_PROD_ATTEST`; migrations auto-run in `pool.init`.

### C3.2 — Write `platform.cutover_flip_ts` ONCE  ·  ⚑ OWNER (flip op)

At the flip, the runbook flip op writes `platform.cutover_flip_ts`
(`CUTOVER_FLIP_TS_KEY`) **exactly once**, through the audited settings seam
(NEVER `os.getenv`) — the UTC instant the Railway service goes live. This is
the write-once delta boundary every rollback export is bucketed around
(`tools/importer/reverse/core.py`). If it is unset at rollback time the
reverse importer stops with `cutover_flip_ts_unset`.

### C3.3 — Post-swap census carry-verify  ·  AGENT

Immediately after re-registration, run the C2.3 carry-verify
(`--verify post-swap-census.json`). Any PRESERVED override loss is
cutover-blocking. Emit the admin-notice lines (`--json`) as the comms-plan
remainder for RENAMED/DROPPED overrides.

### C3.4 — A-18 coverage-debt publication  ·  AGENT

Publish the coverage-debt list (A-18(3)/Q-0244 — the CUT-2/CUT-3
reaction-window publication; **published, NEVER a CUT-3 blocker**: unsigned
human-tier rows never block the flip):
```
python3 tools/check_verified_live.py --debt-list
```
Exit 0. Commit the output to the dated status artifact
[status/coverage-debt-2026-07-12.md](../status/coverage-debt-2026-07-12.md)
(this build's run: **0 rows** — see that file for the verbatim output and
reading).

### C3.5 — Rollback window (N = 7d)  ·  ⚑ OWNER (decision) / AGENT (mechanism)

The rollback window is **N = 7d** (`platform.cutover_flip_ts` + 7d; Q-D15
default, carried until the owner's Stage-3 Q3 override). During the window the
default response to a post-cutover bug is a **hotfix FORWARD**, not a
rollback — a short N and the progressive ring bound the blast
(`rollback-playbook.md` §Rollback procedure step 1). The mechanism reads N off
the scoreboard's `rollback_window_writes_by_class` line; the VALUE of N is the
owner's carry.

### C3.6 — Day-8–10 checklist (A-20)  ·  ⚑ OWNER

After the window closes (day 8–10): confirm prod healthy on the new creds and
new DB; decommission/retire the OLD-bot standby per topology (the old worker
stays deployable on its untouched OLD DB THROUGH day 7); close the rollback
window; and record the cutover as complete. Owner-owned (production timing +
teardown).

---

## ROLLBACK  (last resort — reference `rollback-playbook.md`)

Rollback is the last resort; the biased response inside N is a forward hotfix
(C3.5). If the owner rules a rollback (`rollback-playbook.md` §"Rollback
procedure (CUT-3)"):

1. **⚑ Rollback decision** (owner, last resort).
2. Freeze the new bot.
3. Export each store's post-`platform.cutover_flip_ts` delta, bucketed by its
   DERIVED `rollback_class` (per-store walk — the generic `audit_log` has no
   store column, it supplies only the whole-window cross-check total).
4. **AGENT** `tools/importer/reverse` into the OLD DB: LEDGER rows re-insert by
   `mutation_id` (`ON CONFLICT DO NOTHING`); AGGREGATE stores copy the NEW
   ABSOLUTE value by natural-key upsert (never per-mutation deltas). Both
   idempotent; machine-readable stop-codes (`cutover_flip_ts_unset` /
   `reverse_importer_coverage_gap` / `store_import_failed`). The delta
   boundary is `platform.cutover_flip_ts`.
5. **⚑ OWNER-SIGNED** `DECLARED_LOSS` manifest: M1 (per-store counts — owner
   reviews and SIGNS, SF-g rail) + M2 (per-`(guild,user,store)` amounts —
   feeds the comms/compensation hook).
6. Re-deploy the old worker on its untouched OLD DB (§5.2 topology).
7. **⚑ OWNER** notify guild admins (M2-driven per-user, M1-driven per-store).

All 8 kernel stores are `NEW_ONLY` ⇒ `DECLARED_LOSS` (fresh-chain tables, no
old-schema home) — the new `audit_log` spine never round-trips.

---

## Step ownership table  (⚑ = OWNER-GATED — irreducible human touch)

| # | Step | Owner | Exact check / command |
|---|---|---|---|
| G1 | Verified-restore fresh green | **⚑ OWNER** | `restore-verify.yml` latest = `success`, `last_verified_restore_age` fresh |
| G2 | Backup running | **⚑ OWNER** | `DATABASE_PUBLIC_URL` secret + retention **400** + `BACKUP_ENABLED=true`; next `backup-db.yml` = `success` |
| G3 | Deploy packaging merged | **⚑ OWNER** | `Dockerfile`/`docker-compose.yml`/`railway.json`/`release.yml` on `main`; green tagged build to `ghcr.io/menno420/superbot-next` |
| G4 | `SB_PROD_ATTEST` custody | **⚑ OWNER** | CL-5b ruled in `docs/decisions.md`; attest provisioned |
| G5 | Same application-id (PG-5) | **⚑ OWNER** | prod token belongs to the censused app id |
| G6 | Lockfile fresh | AGENT | `check_lockfile_fresh` green |
| C2.1 | Prod-data import dry-run | AGENT / **⚑ OWNER** DSN | forward importer (CUT-2 build) dry-run vs restored snapshot |
| C2.2 | Reaction-capture window | **⚑ OWNER** | window announced/opened on old bot |
| C2.3a | Census GET sweep | **⚑ OWNER** | `GET /applications/{app}/guilds/{g}/commands/permissions` per guild (prod token) |
| C2.3b | Census partition | AGENT | `permission_census.py --census census.json --rename-map rename-map.json` |
| C2.3c | Census carry-verify | AGENT | `permission_census.py --census census.json --verify post-swap-census.json` |
| C2.4 | verify-import | AGENT / **⚑ OWNER** DSN | `SB_VERIFY_BOOT=true SB_DATA_PLANE=test DATABASE_URL=<restored> python3 -m sb.app.verify_boot` |
| C2.5 | Public→private flip | **⚑ OWNER** | repo visibility private BEFORE artifacts |
| C3.1 | Freeze → delta → token swap | **⚑ OWNER** | swap `DISCORD_BOT_TOKEN_PRODUCTION` (same app id); `python3 -m sb` `SB_DATA_PLANE=prod` |
| C3.2 | `cutover_flip_ts` write-once | **⚑ OWNER** | audited settings seam writes `platform.cutover_flip_ts` once |
| C3.3 | Post-swap carry-verify | AGENT | `permission_census.py --verify` (blocking on loss) |
| C3.4 | Coverage-debt publication | AGENT | `python3 tools/check_verified_live.py --debt-list` → `docs/status/coverage-debt-2026-07-12.md` |
| C3.5 | Rollback window N=7d | **⚑ OWNER** value / AGENT mechanism | window = `cutover_flip_ts` + 7d; forward-fix biased |
| C3.6 | Day-8–10 checklist (A-20) | **⚑ OWNER** | health confirm + old-standby teardown + close window |
| R1–R7 | Rollback | **⚑ OWNER** decision/sign/notify · AGENT `reverse` | `tools/importer/reverse`; owner-signed M1/M2 |
