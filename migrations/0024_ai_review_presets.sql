-- 0024: AI answer review loop (band 7 final slice) — the shipped
-- migrations 100 (ai_review_log) + 102 (ai_answer_presets) shapes
-- carried forward. The review feed channel is the declared
-- ai.review_channel setting (band-1 KV rails), not a column here.

CREATE TABLE IF NOT EXISTS ai_review_log (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id         BIGINT      NOT NULL,
    channel_id       BIGINT      NOT NULL,
    user_id          BIGINT      NOT NULL,
    message_id       BIGINT,
    reply_message_id BIGINT,
    kind             VARCHAR(16) NOT NULL,
    reason_code      TEXT,
    task             TEXT,
    route            TEXT,
    question         TEXT,
    answer           TEXT,
    correction       TEXT,
    corrected_by     BIGINT,
    provider         TEXT,
    model            TEXT,
    reviewed         BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_review_log_guild_created
    ON ai_review_log (guild_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_review_log_guild_unreviewed
    ON ai_review_log (guild_id, reviewed)
    WHERE reviewed = FALSE;

CREATE TABLE IF NOT EXISTS ai_answer_presets (
    id            BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id      BIGINT      NOT NULL,
    question_key  TEXT        NOT NULL,
    question      TEXT        NOT NULL,
    answer        TEXT        NOT NULL,
    task          TEXT,
    source        TEXT,
    enabled       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_by    BIGINT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_answer_presets_guild_key
    ON ai_answer_presets (guild_id, question_key);
