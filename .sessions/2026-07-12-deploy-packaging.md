# 2026-07-12 — deploy packaging (container image + release workflow)

> **Status:** `complete`

- **📊 Model:** Opus 4.8 · high · deploy packaging (Q-0194 / ORDER 012)

## Scope

Program-review Q4 blocker #2: the repo has **zero deploy packaging**. There
is no way to build a runnable container of the bot, and no release path that
publishes an image an owner can cut over to. This session delivers the
container packaging + a build/tag release workflow in ONE PR (production
lane, owner-directed 2026-07-12), no deploy/cutover step (that stays a
manual owner action per the cutover runbook, which a sibling lane authors in
parallel).

Deliverables (exact paths — the runbook lane references them):
`Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example`,
`railway.json`, a `build-image` CI job in `.github/workflows/ci.yml`, and
`.github/workflows/release.yml` (build+tag to GHCR, no deploy).

## Boot contract the image must honour (recon HARD FACTS, not re-derived)

- Entrypoint `python3 -m sb` → `sb/__main__.py` → `sb.app.main.cli()` →
  `asyncio.run(run_app())`. No console_script, no separate migrate command —
  migrations run inside `pool.init(cfg)` at boot step 4.
- `requires-python >=3.11`; base `python:3.11-slim`.
- Install contract (docs/operations/credential-lifecycle.md):
  `pip install --require-hashes -r requirements.lock`.
- The container needs the FULL repo checkout, not just the `sb*` package —
  `pyproject.toml` deliberately excludes `migrations/`, `tools/`,
  `manifest.snapshot.json`, all of which a real boot needs. So `COPY . .`.
- Health server binds `/ready` on `HEALTH_PORT` (default 8080), `HEALTH_HOST`
  default `::`; boot FAILS if `/ready` doesn't bind within 10s. Container +
  Railway healthcheck use `/ready` on 8080.
- FAIL_FAST env at boot: `DISCORD_BOT_TOKEN_PRODUCTION` (secret),
  `DATABASE_URL` (DSN), `SB_DATA_PLANE` (`test`|`prod`). Never baked into the
  image — set at deploy/runtime. Host target: Railway.

## Plan

1. Session card (this file) born-red + telemetry row (Q-0194).
2. `Dockerfile` — 3.11-slim, non-root, `COPY . .`, `--require-hashes` install,
   `EXPOSE 8080`, HEALTHCHECK on `/ready`, `CMD python3 -m sb`.
3. `.dockerignore` — drop `.git`/tests/docs/caches, KEEP migrations/tools/
   manifest.snapshot.json/sb/requirements*/pyproject.
4. `docker-compose.yml` + `.env.example` — LOCAL dev (postgres:16 + app).
5. `railway.json` — DOCKERFILE builder, `/ready` healthcheck.
6. CI `build-image` job (non-required) + `release.yml` (GHCR build+tag).
7. Green `pytest tests/` + `check --strict`; push; open READY PR; flip card
   complete.

## Shipped (PR #266, branch `deploy/container-packaging`)

Files added: `Dockerfile`, `.dockerignore`, `docker-compose.yml`,
`.env.example`, `railway.json`, `.github/workflows/release.yml`. Files
changed: `.github/workflows/ci.yml` (added a non-required `build-image` job;
existing jobs untouched), `.gitignore` (ignore local `.env`, keep the
template), this card + its telemetry row.

## Evidence

- `pytest tests/ -q` = **1727 passed, 8 skipped** (matches the CI-shape run;
  the runtime-dep suites skip without asyncpg/aiohttp/discord installed).
- `manifest_compile` green (48 manifests); the full committed checker fleet
  (20 checkers) green; `bootstrap.py check --strict` green apart from this
  card's own designed born-red hold while `in-progress` (now flipped).
- **Local `docker build` validated** (the sandbox proxy CA had to be plumbed
  into the build to reach PyPI — that plumbing is validation-only, never
  committed): the image built cleanly and `pip install --require-hashes
  --no-cache-dir -r requirements.lock` pulled ALL manylinux wheels
  (asyncpg / pydantic-core / yarl / multidict / propcache — cp311), so NO
  compiler or `-dev` apt package is needed. The built image runs as `appuser`
  from `/app`, carries `migrations/` + `tools/` + `manifest.snapshot.json` +
  `curl`, and `python3 -m sb` (with `SB_VERIFY_BOOT=true`) boots through
  config → data-plane → `db_init`, failing only because no Postgres was
  reachable in the test — proving the entrypoint, import graph, and config
  parsing all work inside the image.

## ⚑ Owner-gated (flagged, not self-applied)

- GHCR package `ghcr.io/menno420/superbot-next` visibility + deploy
  pull-access (inherits repo visibility on first release push).
- Railway project / service variables / first deploy — no deploy step is
  automated; cutover stays a manual owner action per the runbook.

## 💡 Session idea

The boot contract (entrypoint, health port/path, FAIL_FAST env set) lives in
prose across recon notes and docs/operations. A tiny machine-readable
`deploy/boot-contract.json` (or a checker `tools/check_deploy_contract.py`
that greps the Dockerfile/compose/railway.json against `sb.app` constants)
would make the packaging drift-detectable — today a rename of `HEALTH_PORT`
or the entrypoint would silently rot the Dockerfile with nothing red.

## ⟲ Previous-session review

The previous-session review: the recon that fed this lane handed over HARD
FACTS (entrypoint chain, health-port bind-or-die, the pyproject
package-exclusion trap that forces `COPY . .`, the require-hashes install
contract) already verified against source — that pricing was accurate and
saved re-deriving the boot path from `sb/__main__.py`. What it could not
settle and left to this lane: whether the hashed lock needs native build
deps (psycopg/asyncpg) — checked here by reading the lock (asyncpg ships
manylinux wheels; no `libpq`/build-essential needed for the pinned set).
