# Dockerfile — the deployable superbot-next container image.
#
# ENTRYPOINT: `python3 -m sb` → sb/__main__.py → sb.app.main.cli() →
#   asyncio.run(run_app()). There is NO console_script and NO separate migrate
#   command — DB migrations run automatically inside pool.init(cfg) at boot.
#
# WHY `COPY . .` (whole repo, not just the installed package): pyproject.toml
#   packages only `sb*` and DELIBERATELY excludes migrations/, tools/, and
#   manifest.snapshot.json — but a real boot needs all three. So the image
#   carries the full checkout and runs from the repo root.
#
# INSTALL CONTRACT (docs/operations/credential-lifecycle.md):
#   pip install --require-hashes -r requirements.lock  (hash-pinned, S13).
#   The pinned set (asyncpg / aiohttp / pydantic-core / …) ships manylinux
#   wheels for cp311 — no compiler or -dev apt packages are needed.
#
# HEALTH: the app binds /ready on HEALTH_PORT (default 8080), HEALTH_HOST
#   default `::` (IPv6 dual-stack for Railway private networking). Boot FAILS
#   if /ready does not bind within 10s. The container HEALTHCHECK + the Railway
#   healthcheck both probe /ready on 8080.
#
# RUNTIME ENV (set at deploy time — NEVER baked into this image):
#   REQUIRED (FAIL_FAST at boot):
#     DISCORD_BOT_TOKEN_PRODUCTION  secret — the bot token
#     DATABASE_URL                  Postgres DSN (asyncpg)
#     SB_DATA_PLANE                 test | prod
#   OPTIONAL:
#     SB_PROD_ATTEST     presence ⇒ prod-attested (opaque, owner-set)
#     HEALTH_PORT=8080   HEALTH_HOST=::   BOT_PREFIX=!
#     SB_APPCMD_SYNC_GUILD_ID   test-only app-command guild sync
#     SB_VERIFY_BOOT=true       side-effect-free boot check (python3 -m sb.app.verify_boot)
#   Railway injects RAILWAY_SERVICE_NAME (='worker' in prod).

FROM python:3.11-slim

# Fail fast, no .pyc noise, unbuffered logs, no interactive apt.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HEALTH_PORT=8080

# curl is only for the container HEALTHCHECK below; ca-certificates for TLS
# egress (Discord / provider APIs). No build toolchain — the lock is all wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the hash-pinned runtime set FIRST (its own layer, cached across
# source-only changes). --require-hashes makes pip refuse any artifact whose
# hash is not in the lock; --no-cache-dir keeps the layer lean.
COPY requirements.lock ./
RUN pip install --require-hashes --no-cache-dir -r requirements.lock

# The whole repo — migrations/, tools/, manifest.snapshot.json included (see
# the COPY-. rationale in the header). .dockerignore trims the rest.
COPY . .

# Run as a non-root user. The app needs no write access to the image FS
# (state lives in the external Postgres), so a plain unprivileged user is enough.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Probe the readiness gate the app is contractually required to bind. curl
# --fail turns a non-2xx (e.g. 503-while-DRAINING) into a non-zero exit.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent http://localhost:8080/ready || exit 1

CMD ["python3", "-m", "sb"]
