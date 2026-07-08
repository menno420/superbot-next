-- 0008_ai_decision_audit.sql — the K10 NL decision audit (canonical plan
-- §2.1 K10 row: "decision audit" in the NL front-end).
--
-- Every NL-engine invocation produces exactly ONE row via
-- sb.kernel.ai.decision_audit.record — denial, skip, reply, degrade,
-- error. No raw message content is stored: the row holds the join key
-- (message_id) plus structured decision metadata (the shipped
-- ai_decision_audit posture; a redaction policy lifting raw text into the
-- row is deliberately deferred).
--
-- Sole writer: sb.kernel.ai (decision_audit.record).

CREATE TABLE IF NOT EXISTS ai_decision_audit (
    id                       BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id                 BIGINT      NOT NULL,
    channel_id               BIGINT      NOT NULL,
    category_id              BIGINT      NULL,
    user_id                  BIGINT      NOT NULL,
    message_id               BIGINT      NULL,
    task                     TEXT        NULL,          -- registered task id
    route                    TEXT        NULL,
    decision                 TEXT        NOT NULL,      -- allowed|denied|skipped|replied|degraded|errored
    reason_code              TEXT        NOT NULL,      -- PolicyDenialReason value ('none' on success)
    policy_snapshot_hash     TEXT        NULL,
    instruction_profile_ids  JSONB       NULL,
    provider                 TEXT        NULL,
    model                    TEXT        NULL,
    occurred_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The operator "why-no-response" view (newest-first per guild).
CREATE INDEX IF NOT EXISTS ai_decision_audit_guild_occurred_idx
    ON ai_decision_audit (guild_id, occurred_at DESC);

-- Per-user filtering (diagnostics + the erasure workflow's enumerate leg).
CREATE INDEX IF NOT EXISTS ai_decision_audit_guild_user_idx
    ON ai_decision_audit (guild_id, user_id, occurred_at DESC);
