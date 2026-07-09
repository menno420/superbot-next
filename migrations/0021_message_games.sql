-- 0021: MESSAGE-GAME stores (band 6 slice 3) — shipped shapes carried
-- forward (inlined-baseline counting_state JSONB blob per guild;
-- chain_channels one row per channel).

CREATE TABLE IF NOT EXISTS counting_state (
    guild_id BIGINT PRIMARY KEY,
    state    JSONB  NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS chain_channels (
    channel_id  BIGINT  PRIMARY KEY,
    guild_id    BIGINT  NOT NULL,
    word        TEXT    NOT NULL DEFAULT '',
    word_limit  INTEGER NOT NULL DEFAULT 0,
    chain_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chain_channels_guild
    ON chain_channels (guild_id);
