-- 0037_setup_session.sql — the setup wizard's per-guild session row
-- (the setup parity flip; ORACLE disbot/migrations/031_setup_session.sql,
-- reconstructed @befc6d0d via search_code fragments — column set is pinned
-- byte-for-byte by goldens/setup/sweep_slash_setup-hub.json +
-- sweep_slash_setup-advanced.json db_delta rows).
--
-- One row per guild (guild_id PK). Array columns mirror the oracle's
-- BIGINT[]/TEXT[] shapes so the snapshot serialization (asyncpg list)
-- renders the goldens' [] byte.
--
-- Forward-only and idempotent.

CREATE TABLE IF NOT EXISTS setup_session (
    guild_id              BIGINT       PRIMARY KEY,
    guild_name            TEXT         NOT NULL,
    owner_id              BIGINT       NOT NULL,
    setup_status          TEXT         NOT NULL DEFAULT 'pending',
    joined_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    setup_channel_id      BIGINT,
    setup_message_id      BIGINT,
    last_readiness_score  INT,
    current_step          TEXT,
    delegated_admins      BIGINT[]     NOT NULL DEFAULT '{}',
    skipped_sections      TEXT[]       NOT NULL DEFAULT '{}',
    acknowledged_sections TEXT[]       NOT NULL DEFAULT '{}',
    depth                 TEXT,
    purpose               TEXT,
    essential_message_id  BIGINT,
    essential_step        TEXT,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
