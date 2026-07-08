-- 0010: MODERATION stores (band 2 slice 1) — shipped shapes carried forward.
--
-- `mod_logs` is the canonical moderation history (shipped table, imported
-- NAME_STABLE at CUT-2; timestamp already TIMESTAMPTZ per the shipped
-- migration 006 part B fix). `warnings` is the per-member warn counter the
-- escalation ladder reads (shipped shape verbatim).

CREATE TABLE IF NOT EXISTS mod_logs (
    id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp    TIMESTAMPTZ NOT NULL,
    guild_id     BIGINT      NOT NULL,
    action       TEXT        NOT NULL,
    target_id    BIGINT      NOT NULL,
    moderator_id BIGINT      NOT NULL,
    reason       TEXT        NOT NULL DEFAULT 'No reason provided'
);

CREATE INDEX IF NOT EXISTS idx_mod_logs_guild_target
    ON mod_logs (guild_id, target_id, id DESC);

CREATE TABLE IF NOT EXISTS warnings (
    user_id  BIGINT  NOT NULL,
    guild_id BIGINT  NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
