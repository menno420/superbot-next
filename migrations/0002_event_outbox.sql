-- 0002_event_outbox.sql — the K4 durable-delivery ledger
-- (frozen L0 spec 08 §5.1). Net-new (no legacy table to import).
--
-- Sole writer: sb.kernel.outbox (INV-OUTBOX-SOLE-WRITER); the operator
-- dashboard is a read-only projection. Retention delivered:7d / dead:90d is
-- enforced by OutboxReaperLane.prune.

CREATE TABLE IF NOT EXISTS event_outbox (
    outbox_id          UUID        PRIMARY KEY,               -- the row's own id
    dedup_key          TEXT        NOT NULL,                  -- IdempotencyKey.render() — exactly-once capture key
    event_name         TEXT        NOT NULL,                  -- a KNOWN_EVENTS literal
    payload            JSONB       NOT NULL,                  -- JSON-native emit kwargs (§6.5 codec)
    guild_id           BIGINT      NULL,
    created_at         TIMESTAMPTZ NOT NULL,                  -- == the commit fact
    available_at       TIMESTAMPTZ NOT NULL,                  -- claim/lease/backoff cursor
    claims             INT         NOT NULL DEFAULT 0,        -- leases taken (crash-loop signal; does NOT gate DEAD)
    delivery_attempts  INT         NOT NULL DEFAULT 0,        -- bus-level failures; MAX_ATTEMPTS gates DEAD on THIS
    status             TEXT        NOT NULL DEFAULT 'pending', -- 'pending' | 'delivered' | 'dead'
    delivered_at       TIMESTAMPTZ NULL,
    last_error         TEXT        NULL,
    correlation_id     UUID        NULL                        -- the producing mutation_id / audit_log link
);

-- The exactly-once capture guard (INSERT … ON CONFLICT (dedup_key) DO NOTHING).
CREATE UNIQUE INDEX IF NOT EXISTS event_outbox_dedup_key_uq
    ON event_outbox (dedup_key);

-- The relay claim/due poll (small and hot).
CREATE INDEX IF NOT EXISTS event_outbox_pending_available_idx
    ON event_outbox (available_at) WHERE status = 'pending';

-- The OutboxReaperLane prune scan.
CREATE INDEX IF NOT EXISTS event_outbox_terminal_idx
    ON event_outbox (status, delivered_at) WHERE status IN ('delivered', 'dead');

-- Trace an event back to its audit_log row.
CREATE INDEX IF NOT EXISTS event_outbox_correlation_idx
    ON event_outbox (correlation_id) WHERE correlation_id IS NOT NULL;
