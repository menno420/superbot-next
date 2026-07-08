-- 0005_drafts.sql — the K9 producer-agnostic draft primitive (frozen L0
-- spec 06 §5). Net-new: live setup_draft_operations rows are transient
-- staging, never imported (drafts open at cutover are re-staged).
--
-- Sole writer: sb.kernel.db.draft. Op identity is (draft_id, op_seq) —
-- position in the draft, NEVER a slot key (the L-7 10-channel collapse fix).

CREATE TABLE IF NOT EXISTS sb_drafts (
    draft_id             UUID        PRIMARY KEY,
    producer             TEXT        NOT NULL,               -- Producer enum value
    owner_guild_id       BIGINT      NOT NULL,
    owner_actor_id       BIGINT      NULL,                   -- NULL for system/backfill (IS NOT DISTINCT FROM)
    status               TEXT        NOT NULL,               -- DraftStatus enum value
    accept_authority_ref TEXT        NOT NULL,               -- derived DISPLAY floor (gate = per-ref AND)
    correlation_id       UUID        NOT NULL,               -- = draft_id
    verification_json    JSONB       NULL,                   -- VerificationContext | NULL
    created_at           TIMESTAMPTZ NOT NULL,
    updated_at           TIMESTAMPTZ NOT NULL,
    expires_at           TIMESTAMPTZ NULL                    -- NULL = no TTL
);

CREATE INDEX IF NOT EXISTS sb_drafts_open_idx
    ON sb_drafts (owner_guild_id, owner_actor_id, status);

CREATE INDEX IF NOT EXISTS sb_drafts_expiry_idx
    ON sb_drafts (status, expires_at);

CREATE TABLE IF NOT EXISTS sb_draft_operations (
    draft_id      UUID   NOT NULL REFERENCES sb_drafts(draft_id) ON DELETE CASCADE,
    op_seq        INT    NOT NULL,                            -- 1-based order; the 10-channel fix
    op_kind       TEXT   NOT NULL,                            -- the OpKindRegistry key
    subsystem     TEXT   NOT NULL,
    authority_ref TEXT   NOT NULL,
    payload_json  JSONB  NOT NULL,
    label         TEXT   NOT NULL,
    dedup_token   TEXT   NOT NULL,                            -- default f"{draft_id}:{op_seq}"
    PRIMARY KEY (draft_id, op_seq)
);
