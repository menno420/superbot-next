# Local verification — reproducible Postgres + env setup

> **Status:** `reference` — the local-Postgres env-drift hygiene runbook
> (NEXT-2 baton item 1 remainder, `control/status.md` @ `0a96960`:
> "local-Postgres env-drift hygiene"). One command provisions the local
> cluster to the CI-canonical shape; this page is the full verification
> path a fresh session runs before pushing. Values are DERIVED from the
> CI workflows (cited per step) — the workflows stay the source of truth;
> if they move, re-derive here.

**Audience:** any agent/operator session verifying changes locally.
**Companion script:** `tools/setup_local_env.py` (idempotent, never
destructive — creates roles/DBs only if missing, prints the env exports).

---

## 0. Why this exists (the drift class)

Local clusters drift; CI containers do not. Observed episodes:

- A session read **"11 failed"** unit/integration tests as a stable fact —
  "integration race tests + btd6_seed_data; local-Postgres environment
  state, pre-existing" (`.sessions/2026-07-12-treasury-karma-argv-fix.md`)
  — and the correction had to be carried forward by hand: "the '11
  known-red integration tests under local Postgres' note from #290's card
  was local provisioning state, not a stable fact — this session's
  provisioned cluster runs the full suite green"
  (`.sessions/2026-07-12-live-adapter-landing.md` ⟲ review).
- The ORDER-004 live-drive session found the "cluster was WIPED by a
  container restart — re-provisioned per the standing recovery:
  `pg_ctlcluster 16 main start` + role/DB creation matching the env DSN"
  (`.sessions/2026-07-12-order004-live-drive-evidence.md`) — a recovery
  that lived only in session-card prose until this runbook.

The fix: provision locally EXACTLY what CI declares, via one idempotent
command, and run the same verification ladder CI runs.

## 1. One-time setup

### 1.1 Python tooling (mirrors CI verbatim)

Two tiers, exactly as the workflows install them:

- **Unit tier** (enough for `pytest tests/` + the checker fleet; the
  kernel's guarded-import discipline means the suite passes WITHOUT
  runtime deps — that absence is itself under test, ci.yml:8-11):

  ```
  pip install pytest pyyaml
  ```

  (.github/workflows/ci.yml:32.)

- **Full tier** (adds golden replay + `tests/integration/` — the
  real-Postgres legs): the hash-pinned runtime lock, then the same test
  tooling:

  ```
  pip install --require-hashes -r requirements.lock
  pip install pytest pyyaml
  ```

  (.github/workflows/golden-parity.yml:60-63.)

### 1.2 Postgres

A local PostgreSQL server on `localhost:5432`. CI runs the `postgres:18`
service image (.github/workflows/golden-parity.yml:42); local sessions
have verified green on both 16 and 18 — the schema uses no
version-gated features, so the stock distro cluster is fine.

### 1.3 Provision roles/DBs + env (the one command)

```
python3 tools/setup_local_env.py
```

Creates, ONLY if missing (nothing is ever dropped):

| Object | Value | Source |
|---|---|---|
| role `parity` (password `parity`) | replay/login role | golden-parity.yml:44-45 (`POSTGRES_USER`/`POSTGRES_PASSWORD`) |
| DB `parity_replay` (owner `parity`) | replay DB | golden-parity.yml:46 (`POSTGRES_DB`) |
| role `superbot` / DB `superbot` | local runtime-boot DSN (live-drive, runtime smoke) | local convention, `.sessions/2026-07-12-order-016-runtime-smoke.md` — NOT a CI value |

then prints the CI-canonical env triple (golden-parity.yml:52-54, also
the harness default `_ENV_DEFAULTS`, sb/adapters/parity/boot.py:68-70):

```
export DATABASE_URL='postgresql://parity:parity@localhost:5432/parity_replay'
export SB_DATA_PLANE=test
export SB_TEST_DB_HOSTS=localhost
```

`--check` reports without mutating. The only mutation ever applied to a
PRE-existing object is a password re-align on the login role, and only
when the canonical DSN fails to authenticate (announced when it happens).
Migrations are NOT applied by the script — the parity harness applies and
truncates its own schema per replay boot; a runtime boot applies its own.

## 2. The verification ladder (what CI runs, in order)

Run from the repo root, with the §1.3 exports in the environment. Always
target `tests/` — never bare `pytest` at the repo root: repo-root
collection walks the kit machinery (`bootstrap.py`, `.substrate/`), which
is not the CI shape (ci.yml:34 runs `python3 -m pytest tests/ -q`).

| # | Command | CI twin | Expect |
|---|---|---|---|
| 1 | `python3 -m pytest tests/ -q` | ci.yml:34 | green; `tests/integration` auto-skips cleanly if Postgres/asyncpg absent |
| 2 | `python3 tools/manifest_compile.py` + the checker loop | ci.yml:44-63 | all green |
| 3 | `python3 bootstrap.py check --strict` | ci.yml:64-65 | "all checks passed" (advisory warnings never exit-affect) |
| 4 | `python3 tools/check_parity_depth.py` | golden-parity.yml:64-65 | `OK — …` |
| 5 | `python3 tools/run_golden_parity.py --gate` | golden-parity.yml:66-67 | `gate: GREEN — all N golden(s) … replay clean` |
| 6 | `python3 -m pytest tests/integration -q` | golden-parity.yml:72-73 | green (needs full tier + live DB — skips are an ENV signal here, not a pass) |

The `report` leg (`run_golden_parity.py --report`,
golden-parity.yml:100-101) is red-by-design until the owner-parked
`_unmapped` set lands — red there is NOT a local-environment problem
(`docs/status/README-first.md`).

## 3. Drift recovery

- **Container restart wiped the cluster** (the ORDER-004 episode): start
  it (`pg_ctlcluster <ver> main start` — `pg_lsclusters` names ver) and
  re-run `python3 tools/setup_local_env.py`; it re-creates whatever is
  missing. The script attempts the cluster start itself when
  `pg_ctlcluster` is available.
- **Unexplained replay/integration reds that CI does not show**: suspect
  the local cluster BEFORE suspecting the diff — re-run
  `tools/setup_local_env.py --check`, then re-run the ladder. The replay
  harness truncates and re-migrates `parity_replay` per boot, so stale
  ROWS cannot leak — but the migrations LEDGER can run ahead of your
  checkout: a gate run on a branch that adds `migrations/0049_*.sql`
  leaves `schema_migrations` at 49, and back on main every harness boot
  refuses with "Migration 0049 is recorded as applied but its file is
  absent on disk" (`sb/kernel/db/migrations.py:215`), which cascades
  (`tests/integration` all-skip, and the aborted boot leaves the pool
  global initialized, which reds
  `tests/unit/kernel/test_db_pool.py::test_get_raises_before_init` in a
  full-suite run). A drifted `parity_replay` is disposable replay state;
  recover either way:
  - non-destructively — point `DATABASE_URL` at a fresh sibling DB
    (`postgresql://parity:parity@localhost:5432/parity_replay_fresh`;
    create it with the script's own create-if-missing shape), or
  - `dropdb parity_replay` + re-run the script (the script itself never
    drops anything, by contract).
- **Auth failures on the canonical DSN**: the script re-aligns the role
  password to the CI value and says so; anything else it reports as
  `PROBLEM — …` with exit 1.
