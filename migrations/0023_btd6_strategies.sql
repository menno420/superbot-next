-- 0023: BTD6 strategy memory (band 7 slice 1) — the shipped migration
-- 041 table shape carried forward (visibility/approval lifecycle,
-- nullable submitter identity so anonymisation detaches attribution
-- without deleting the row). The shipped btd6_strategy_audit side
-- table FOLDS into the K7 central audit lane (one-write discipline,
-- D-0046); the live btd6_facts / source-registry / ingestion tables
-- ride the named ingestion successor port.

CREATE TABLE IF NOT EXISTS btd6_strategies (
    id                              BIGSERIAL PRIMARY KEY,
    origin_guild_id                 BIGINT NOT NULL,
    current_guild_id                BIGINT NULL,
    visibility                      TEXT NOT NULL
        CHECK (visibility IN ('guild', 'published')),
    approval_status                 TEXT NOT NULL
        CHECK (approval_status IN ('draft', 'pending', 'approved',
                                   'rejected', 'unpublished')),
    approved_by                     TEXT NULL
        CHECK (approved_by IN ('ai', 'staff')),
    approved_by_id                  BIGINT NULL,
    approval_provider               TEXT NULL,
    approval_model                  TEXT NULL,
    title                           TEXT NOT NULL,
    summary                         TEXT NOT NULL,
    map                             TEXT NULL,
    mode                            TEXT NULL,
    difficulty                      TEXT NULL,
    hero                            TEXT NULL,
    towers                          JSONB NOT NULL DEFAULT '[]'::jsonb,
    upgrade_paths                   JSONB NOT NULL DEFAULT '[]'::jsonb,
    round_range                     JSONB NULL,
    steps                           JSONB NOT NULL DEFAULT '[]'::jsonb,
    common_failures                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_links                    JSONB NOT NULL DEFAULT '[]'::jsonb,
    submitted_by                    BIGINT NULL,
    submitter_display_snapshot      TEXT NULL,
    submitter_identity_state        TEXT NOT NULL DEFAULT 'present'
        CHECK (submitter_identity_state IN ('present', 'anonymized',
                                            'deleted')),
    origin_metadata                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version                         INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS btd6_strategies_origin_guild_idx
    ON btd6_strategies (origin_guild_id);

CREATE INDEX IF NOT EXISTS btd6_strategies_current_guild_idx
    ON btd6_strategies (current_guild_id)
    WHERE current_guild_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS btd6_strategies_visibility_idx
    ON btd6_strategies (visibility, approval_status);

CREATE INDEX IF NOT EXISTS btd6_strategies_submitter_idx
    ON btd6_strategies (submitted_by)
    WHERE submitted_by IS NOT NULL;
