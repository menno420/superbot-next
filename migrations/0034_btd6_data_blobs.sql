-- 0034: btd6_data_blobs — the shipped BTD6 deterministic-data blob store
-- (old repo disbot/migrations/054_btd6_data_blobs.sql, imported NAME_STABLE;
-- DDL reconstructed fragment-by-fragment via search_code at oracle head
-- b0713fcd — the corpus pin stays 7f7628e1, this table predates it: the
-- oracle's `!btd6 ops seed-data` admin terminal wrote it since PR #676).
-- Consumer: the audited `btd6.seed_data` op (sb/domain/btd6/ops.py) — the
-- `!btd6 ops seed-data` / legacy `!btd6ops seed-data` terminals upsert every
-- committed sb/domain/btd6/data/*.json fixture (+ the stats tree) here,
-- sha256-stamped over the canonical JSON dump, idempotently ("Safe to re-run
-- any time (it upserts)" — the shipped receipt's own words). The SERVING lane
-- in this build stays the committed files (the capture world's file backend —
-- goldens/btd6 pin the `local:` data-source label); the postgres-serving
-- provider (oracle BTD6_DATA_BACKEND=postgres) rides the D-0046 ingestion
-- successor with content_drift's non-None lane.
CREATE TABLE IF NOT EXISTS btd6_data_blobs (
    name        TEXT PRIMARY KEY,
    body        JSONB NOT NULL,
    sha256      TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
