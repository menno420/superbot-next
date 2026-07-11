-- 0028_ai_policy.sql — the typed AI policy OVERRIDE tables (band 7, the
-- policy-mutation slice): the shipped migration 039 shapes for the three
-- sparse override scopes (disbot migrations/039_ai_policy.sql @7f7628e1),
-- NAME_STABLE. The shipped ai_guild_policy row stays the KV settings port
-- (sb/domain/settings/ai_readers.py — D-0025; the per-guild policy
-- GENERATION counter rides a guild_settings row, the ai_review_channel
-- precedent), and ai_instruction_profile ports with the instruction-profile
-- slice, so instruction_profile_id is carried as a plain nullable column
-- (no FK target yet) — the shipped column set otherwise verbatim.

-- 1) Per-channel override --------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_channel_policy (
    guild_id                       BIGINT NOT NULL,
    channel_id                     BIGINT NOT NULL,
    mode                           TEXT   NOT NULL
        CHECK (mode IN ('inherit', 'always_reply', 'mention_only', 'disabled')),
    min_level                      INTEGER NULL,
    cooldown_seconds               INTEGER NULL,
    instruction_profile_id         BIGINT  NULL,
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by                     BIGINT  NULL,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE INDEX IF NOT EXISTS ai_channel_policy_guild_idx
    ON ai_channel_policy (guild_id);

-- 2) Per-category override -------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_category_policy (
    guild_id                       BIGINT NOT NULL,
    category_id                    BIGINT NOT NULL,
    mode                           TEXT   NOT NULL
        CHECK (mode IN ('inherit', 'always_reply', 'mention_only', 'disabled')),
    min_level                      INTEGER NULL,
    cooldown_seconds               INTEGER NULL,
    instruction_profile_id         BIGINT  NULL,
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by                     BIGINT  NULL,
    PRIMARY KEY (guild_id, category_id)
);

CREATE INDEX IF NOT EXISTS ai_category_policy_guild_idx
    ON ai_category_policy (guild_id);

-- 3) Role policy -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_role_policy (
    guild_id                       BIGINT NOT NULL,
    role_id                        BIGINT NOT NULL,
    decision                       TEXT   NOT NULL
        CHECK (decision IN ('allow', 'deny', 'inherit')),
    min_level_override             INTEGER NULL,
    bypass_cooldown                BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by                     BIGINT  NULL,
    PRIMARY KEY (guild_id, role_id)
);

CREATE INDEX IF NOT EXISTS ai_role_policy_guild_idx
    ON ai_role_policy (guild_id);
