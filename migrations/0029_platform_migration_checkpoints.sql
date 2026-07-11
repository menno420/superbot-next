-- 0029: platform_migration_checkpoints — the shipped generic logical-
-- migration checkpoint table (old repo disbot/migrations/026, imported
-- NAME_STABLE; DDL reconstructed fragment-by-fragment via search_code at
-- the corpus posture — only 'dry_run_complete' is golden-pinned:
-- goldens/diagnostic/sweep_platform_backfill pins the `!platform backfill`
-- dry-run row byte-for-byte, id/name/guild_id/status/version/started_at/
-- completed_at/summary_json). First (and so far only) consumer is the
-- binding-backfill dry run (diagnostic.backfill_dry_run).
CREATE TABLE IF NOT EXISTS platform_migration_checkpoints (
    id              BIGSERIAL    PRIMARY KEY,
    name            TEXT         NOT NULL,
    guild_id        BIGINT,
    status          TEXT         NOT NULL
        CHECK (status IN ('pending', 'dry_run_complete', 'in_progress',
                          'complete', 'failed')),
    version         INTEGER      NOT NULL DEFAULT 1,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    summary_json    JSONB
);
