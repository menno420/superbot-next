-- 0038_bindings_oracle_shape.sql — re-shape `subsystem_bindings` to the
-- SHIPPED schema and add the shipped `binding_audit_log` audit ledger
-- (the economy `!setlogchannel` parity re-home; ORACLE
-- disbot/migrations/022_subsystem_bindings.sql, reconstructed @35ddf6ef
-- via search_code fragments — both column sets are pinned byte-for-byte
-- by goldens/economy/sweep_setlogchannel.json db_delta rows).
--
-- The 0009 shape (name/slot/resource_id/updated_at) was a port-side
-- invention with NO golden and no D-record behind it; the one golden that
-- carries the table pins the oracle columns (binding_name / target_id /
-- status / version / last_updated_at / last_validated_at). The slot
-- multiplicity column had no shipped counterpart (oracle PK is
-- (guild_id, subsystem, binding_name)) — slot-0 rows carry over, higher
-- slots are dropped (none exist outside tests; the multiplicity lane was
-- part of the same invention).
--
-- Forward-only and idempotent.

-- 1. subsystem_bindings → the oracle 022 shape.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'subsystem_bindings'
                 AND column_name = 'name') THEN
        DELETE FROM subsystem_bindings WHERE slot <> 0;
        ALTER TABLE subsystem_bindings
            DROP CONSTRAINT IF EXISTS subsystem_bindings_pkey;
        ALTER TABLE subsystem_bindings RENAME COLUMN name TO binding_name;
        ALTER TABLE subsystem_bindings RENAME COLUMN resource_id TO target_id;
        ALTER TABLE subsystem_bindings
            RENAME COLUMN updated_at TO last_updated_at;
        ALTER TABLE subsystem_bindings DROP COLUMN slot;
        ALTER TABLE subsystem_bindings ALTER COLUMN target_id DROP NOT NULL;
        ALTER TABLE subsystem_bindings
            ADD COLUMN status TEXT NOT NULL DEFAULT 'unresolved',
            ADD COLUMN last_validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
        -- pre-reshape rows were only ever written bound (NOT NULL target).
        UPDATE subsystem_bindings SET status = 'bound'
            WHERE target_id IS NOT NULL;
        ALTER TABLE subsystem_bindings
            ADD PRIMARY KEY (guild_id, subsystem, binding_name);
    END IF;
END $$;

-- 2. binding_audit_log — the shipped append-only bind/clear audit trail
--    (mutation_id is UUID so the parity snapshot normalizes the cell to
--    the goldens' `<uuid>`; actor_id is NOT NULL — actor_type is the
--    system/user discriminator, oracle docstring semantics).
CREATE TABLE IF NOT EXISTS binding_audit_log (
    id             BIGSERIAL    PRIMARY KEY,
    mutation_id    UUID         NOT NULL,
    guild_id       BIGINT       NOT NULL,
    subsystem      TEXT         NOT NULL,
    binding_name   TEXT         NOT NULL,
    actor_type     TEXT         NOT NULL,
    actor_id       BIGINT       NOT NULL,
    action         TEXT         NOT NULL,
    old_target_id  BIGINT,
    new_target_id  BIGINT,
    old_status     TEXT,
    new_status     TEXT,
    at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (action IN ('set', 'clear', 'backfill'))
);

CREATE INDEX IF NOT EXISTS idx_binding_audit_log_guild_at
    ON binding_audit_log (guild_id, at);
CREATE INDEX IF NOT EXISTS idx_binding_audit_log_mutation
    ON binding_audit_log (mutation_id);
