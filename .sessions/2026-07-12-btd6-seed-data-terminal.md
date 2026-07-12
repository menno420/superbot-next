# 2026-07-12 — btd6 `!btd6 ops seed-data` terminal (band 7, the LAST #144 parked domain item's bounded core)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

Of the two remaining #144 parked domain candidates (boss estimator ·
seed-data terminals; CT-team guided-set stays NK-live-gated), this slice
takes **seed-data** — the bounded one: the boss estimator is
deterministic on the committed data (oracle
`services/btd6_estimator_service.py`'s own docstring — no NK-live
dependency) but NOT one slice, because it needs the full per-crosspath
combat-stats derivation `sb/domain/btd6/stats.py` explicitly parks as a
named successor ("the full tower/hero normal-view derivation … the
upgrade-detail resolver"), i.e. a multi-service reconstruction (oracle
PRs #1574/#1578). Seed-data is one migration + one store + one audited
op + one handler + two receipt cards, its alias routing was already
ratified at #218 (both `!btd6 ops seed-data` and legacy
`!btd6ops seed-data` route `btd6.cmd_ops_seed`; the #218 @codex
question, comment 4949189321, drew the "alias-faithful is right, the
terminal itself is inert" verdict — this slice makes the terminal
real), and it has NO EFFECT leg (DB-only + in-process cache reload), so
the D-0030 compensator-ruling class never engages and the allowlist
stays EMPTY.

## Oracle reconstruction (trap 24 ledger)

search_code fragments returned ref **1ecc2113** first, then
**b0713fcd** for the whole reconstruction window (the default branch
churned again past the #225-ledgered 1ecc2113; corpus pin stays
`7f7628e1` — seed-data predates it, shipped since oracle PR #676).
Sources reconstructed: `disbot/services/btd6_data_service.py`
(`seed_postgres_from_files` — the FileRawProvider loop, the
`manifest.json` bucket-artifact skip, sha256 over
`json.dumps(body, sort_keys=True, ensure_ascii=False)`, the
`if seeded: warm_provider(); reset_cache()` reload tail;
`content_drift` — None for the file backend),
`disbot/utils/db/btd6_data.py` (`upsert_blob` — the
ON CONFLICT (name) DO UPDATE bytes), `disbot/migrations/
054_btd6_data_blobs.sql` (the four-column DDL verbatim),
`disbot/cogs/btd6/_ops_helpers.py` (`seed_embed` — drift-before-seed
ordering, the orange zero-files card, the green receipt: "Upserted
**{count}** blobs …", `**Now serving:** game version`, the #1263
"Applied N changed file(s)" 8-shown/+N-more report, the Railway
first-time paragraph, "Safe to re-run any time (it upserts)"),
`disbot/cogs/btd6_ops_cog.py` + `disbot/cogs/btd6/_unified.py` (the
`is_administrator_member`-or-ADMIN_DENIED gate on both prefix forms).
Trap-28 check re-run: BOTH command forms are `_sweep_skips.json` rows
("bulk data seed — the golden would embed the whole versioned BTD6
dataset (6.8MB) …") — the skip-listed-but-declared posture (#226) holds:
declared, no golden, sweep entry documents why.

## What shipped

1. **migrations/0034_btd6_data_blobs.sql** — oracle migration 054
   imported NAME_STABLE (name PK / body JSONB / sha256 / updated_at);
   checksums.json entry same PR.
2. **sb/domain/btd6/store.py** — `BTD6_DATA_BLOBS_STORE` StoreSpec
   (sole_writer the existing `btd6.store` marker, DataClass.NONE,
   bears_value False) + `upsert_data_blob` (oracle SQL verbatim,
   `$2::jsonb`) + `count_data_blobs` / `get_data_blob_row` readers.
3. **sb/domain/btd6/ops.py** — `btd6.record_seed_data` DB leg (the
   shipped seed loop verbatim: every `dataset.list_blob_names()` name,
   manifest.json skip carried, canonical-dump sha256, one upsert per
   blob; count on the ctx.params side-channel — the karma 16a lane) +
   `SEED = btd6.seed_data` op, audit verb `btd6_data_seeded`,
   **authority "administrator"** (the shipped ADMIN_DENIED gate mapped
   onto the K6 floor — the diagnostic.backfill_dry_run precedent; the
   command rows keep their #144/#218 compat-pinned "staff" tier, so a
   staff-not-admin invoker gets the K6 deny, kernel copy, unpinned
   path).
4. **sb/domain/btd6/oracle_cards.py** — `seed_empty_card` (orange,
   zero-files bytes) + `seed_receipt_card` (green; serving/changed
   lines byte-per-byte incl. the structurally-empty changed line under
   the file backend).
5. **sb/domain/btd6/oracle_surface.py** — `cmd_ops_seed` goes real:
   shipped ordering (content_drift BEFORE the seed), the ONE audited op,
   zero-files orange arm, post-commit "applies immediately" reload
   (file-backend flavor: `dataset.reset_cache()` +
   `stats.reset_stats_cache()`), the receipt with the committed
   dataset's real `game_version` (55.1). The inert BLOCKED pending
   terminal deleted; `sb/domain/btd6/dataset.py` grows the
   `content_drift()` file-backend arm (None, docstring names the
   D-0046 postgres-serving successor).
6. **sb/domain/btd6/service.py** — the module-docstring ledger sentence
   retired: seed-data moves out of the PENDING TERMINALS list (the
   D-0071/72/74/#208/#225 retirement-loop discipline, sixth
   application).
7. **parity/parity.yml** — ONE depth exemption `table:btd6_data_blobs`
   under the EXISTING **`dataset-scale`** class ("golden would embed a
   pinned bulk dataset" — the class's own definition matches the sweep
   skip verbatim; first exemptions use of the class, zero vocabulary
   growth, no new decision record needed).
8. **sb/manifest/btd6.py** — stores +1; `manifest_compile --write`
   (snapshot hash moved). Zero new commands/panels/modals/events/
   settings — compat pin, sim-gate locks, HUB labels all untouched
   (verified: full checker fleet green).
9. **Tests** — `tests/unit/band7/test_band7_btd6_seed_data.py` (14: the
   seed-loop semantics incl. the manifest.json quirk + canonical sha +
   idempotent re-run, the op-spec administrator/one-DB-leg pins, the
   card byte pins incl. the changed-report 8/+N bytes, the handler
   sequence incl. the zero-files and refusal arms) +
   `tests/integration/test_btd6_seed_data.py` (real Postgres through
   the REAL K7 engine: K6 deny for a plain member writes NOTHING, the
   seed lands all 74 committed blobs with verified sha256/body
   round-trip, re-run idempotent, 2 `btd6_data_seeded` audit_log rows).

## Ladder (serial, real Postgres — trap 25)

units **1606 passed / 2 skipped** (+14 unit +1 integration over the
#232-window 1591/2); gate **GREEN 346/346 across 45 ported** (btd6
103/103); report **352/471 green, 471/471 replayable** — the slice
mints zero goldens and moves zero gate/report counts, as designed;
`check_parity_depth` OK (50 subsystems, 44 ported, kernel ported, 471
goldens); `--write-ratchet` byte-stable (btd6 stays
{events: 1, tables: 4, settings: 1} — covered-side counts, the new
table is declared-and-exempt, never covered); full 15-checker fleet
green incl. check_migrations (34) and check_money_race (0 violations);
`bootstrap.py check --strict` green.

## Parked (honest)

The **boss estimator** is now the last non-gated #144 domain item —
its prerequisite is the stats normal-view derivation slice (named in
stats.py's docstring). CT-team guided-set stays NK-live-gated. The
postgres-SERVING provider for btd6_data_blobs (oracle
`BTD6_DATA_BACKEND=postgres` + `PostgresRawProvider` + non-None
`content_drift` + auto-seed-on-boot Q-0077(b)) rides D-0046 with the
rest of live ingestion — this build keeps the capture world's file
backend, which is what goldens/btd6 pin (`local:` data-source label).
The oracle's `scripts/seed_btd6_data.py` CLI twin: not carried (no
operator surface asked for it; the op is the one write path).

## 💡 Session idea

The `dataset-scale` reason class sat unused in the closed vocabulary
for weeks while its exact use-case (seed-data) waited in the parked
list — the sweep-skip reasons and the depth-exemption classes are the
SAME taxonomy seen from two sides, so when a parked item's skip entry
already names a vocabulary class verbatim, the exemption text writes
itself and the flip-risk drops to zero. Successor pick: the boss
estimator should start by shipping the stats normal-view derivation as
its OWN slice (it unblocks tower/hero card depth too), then the
estimator service rides it.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-btd6-freeplay-moab-scaling.md`, #225.)
Its "publish-your-own-anchors" fidelity check transferred: seed-data's
equivalent was the oracle's own receipt copy quoting its mechanics
("it upserts", the sha provenance the skip entry cites) — three
independent oracle sources (service, db util, migration) agreed with
the reconstruction before any code was written. Its parked list was
accurate and priced this pick correctly by naming seed-data a
"terminal" (one write lane), which is exactly what it turned out to
be. One under-call: it did not flag that the #218 codex exchange had
already settled the seed-data ROUTING question — a successor map that
carries "the alias question is closed, only the terminal body remains"
would have saved this session the re-derivation.
