-- 0004_due_queue.sql — the K9 durable due-queue (frozen L0 spec 09 §5).
-- Net-new (fresh chain; automation_runs is superseded by the lease, never imported).
--
-- Sole writer: sb.kernel.db.scheduler. One live slot per recurring task via
-- the COALESCE(guild_id, 0) partial unique index — a GLOBAL task stores
-- guild_id = NULL and Postgres treats NULLs as DISTINCT in a plain UNIQUE,
-- so bare (task_key, guild_id) would double-arm GLOBAL tasks on every boot
-- (the GLOBAL slot-key double-arm, closed here). One-shots are free-multi.

CREATE TABLE IF NOT EXISTS sb_due_queue (
    task_id              UUID        PRIMARY KEY,
    task_key             TEXT        NOT NULL,               -- ManagedTaskSpec.name (namespace task_prefix)
    guild_id             BIGINT      NULL,                   -- NULL = GLOBAL scope
    trigger_kind         TEXT        NOT NULL,               -- interval | cron | one_shot | condition
    fire_at              TIMESTAMPTZ NOT NULL,
    payload_json         JSONB       NOT NULL DEFAULT '{}',
    payload_version      INT         NOT NULL DEFAULT 1,
    recurring            BOOLEAN     NOT NULL,               -- advance fire_at vs delete after fire
    -- misfire / trigger params (denormalized from the spec at arm time)
    misfire_policy       TEXT        NOT NULL,
    catch_up             BOOLEAN     NOT NULL DEFAULT TRUE,
    grace_s              INT         NOT NULL DEFAULT 0,
    max_catchup          INT         NOT NULL DEFAULT 1,
    interval_seconds     INT         NULL,                   -- set iff trigger_kind='interval'
    cron_expr            TEXT        NULL,                   -- set iff trigger_kind='cron'
    error_policy         TEXT        NOT NULL,
    -- lease / attempts / lifecycle
    status               TEXT        NOT NULL DEFAULT 'pending',  -- pending | claimed | dead | cancelled
    claimed_by           TEXT        NULL,
    lease_expires_at     TIMESTAMPTZ NULL,
    attempts             INT         NOT NULL DEFAULT 0,     -- transient re-claims for the CURRENT fire_epoch
    consecutive_failures INT         NOT NULL DEFAULT 0,     -- non-retryable failures across slots
    created_at           TIMESTAMPTZ NOT NULL,
    updated_at           TIMESTAMPTZ NOT NULL
);

-- claim_due / select_overdue hot path.
CREATE INDEX IF NOT EXISTS sb_due_queue_pending_fire_idx
    ON sb_due_queue (status, fire_at);

-- reap_expired_leases.
CREATE INDEX IF NOT EXISTS sb_due_queue_lease_idx
    ON sb_due_queue (status, lease_expires_at) WHERE status = 'claimed';

-- cancel_scope (guild-leave reclaim).
CREATE INDEX IF NOT EXISTS sb_due_queue_guild_idx
    ON sb_due_queue (guild_id) WHERE guild_id IS NOT NULL;

-- ONE live slot per recurring task (GLOBAL-collision-proof: COALESCE folds
-- NULL -> 0 so the slot key AGREES with the fire key's `guild_id or 0`).
CREATE UNIQUE INDEX IF NOT EXISTS sb_due_queue_recurring_slot
    ON sb_due_queue (task_key, COALESCE(guild_id, 0))
    WHERE recurring;
