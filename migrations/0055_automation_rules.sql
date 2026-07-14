-- 0055: automation_rules — the per-guild automation rule store (oracle
-- disbot/migrations/032_automation_rules.sql shape @ f969b95). Each row is
-- one operator-configured behaviour ("post a welcome message when a new
-- member joins", ...). This slice ports the WRITE seam only (the K7
-- ``automation.add_rule`` op behind the K9 ``add_automation_rule`` kind —
-- rules insert DISABLED); the runtime consumer (the oracle's poll-based
-- AutomationScheduler + executor, 1,658 LOC across 4 service files, plus
-- the ``automation_runs`` companion table, oracle migration 033) is the
-- NAMED SUCCESSOR — the oracle itself persists member_join rules nothing
-- consumes yet, so the rows are inert while disabled.
--
-- enabled       master switch. Defaults FALSE so a freshly-created rule
--               never runs until the operator explicitly turns it on.
-- trigger/action CHECK constraints mirror the oracle's documented kind
--               enums, so a future code change adding a kind must also
--               bump a migration (oracle posture, verbatim lists).
-- schedule      cron-like string for trigger_kind='scheduled_time' — that
--               kind is blocked for new rules at the service boundary
--               (oracle UNSUPPORTED_INSTALLABLE_TRIGGER_KINDS) until a
--               cron parser ships.
--
-- Rollback: DROP TABLE IF EXISTS automation_rules;  Forward-only and
-- idempotent.

CREATE TABLE IF NOT EXISTS automation_rules (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id        BIGINT       NOT NULL,
    name            TEXT         NOT NULL,
    enabled         BOOLEAN      NOT NULL DEFAULT FALSE,
    trigger_kind    TEXT         NOT NULL CHECK (
        trigger_kind IN (
            'scheduled_time',
            'interval',
            'member_join',
            'setup_readiness_below',
            'binding_missing',
            'channel_inactive',
            'manual'
        )
    ),
    trigger_config  JSONB        NOT NULL DEFAULT '{}'::JSONB,
    action_kind     TEXT         NOT NULL CHECK (
        action_kind IN (
            'send_message',
            'assign_role',
            'remove_role',
            'post_readiness_summary',
            'post_leaderboard_summary',
            'bind_channel',
            'create_channel',
            'notify_owner'
        )
    ),
    action_config   JSONB        NOT NULL DEFAULT '{}'::JSONB,
    schedule        TEXT,
    timezone        TEXT         NOT NULL DEFAULT 'UTC',
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    failure_count   INT          NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_by      BIGINT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (guild_id, name)
);

CREATE INDEX IF NOT EXISTS automation_rules_next_run_idx
    ON automation_rules (next_run_at)
    WHERE enabled;
