-- 0003_audit_spine.sql — the K7 central audit row (frozen L0 spec 07 §5).
-- Net-new (no legacy table to import). One CompoundOpSpec invocation ==
-- exactly one row; the N legs ride `detail` JSONB — NEVER N rows.
--
-- Sole writer: sb.kernel.workflow (emit_central_audit). Domain ledger tables
-- (e.g. economy_audit_log at their port bands) remain the domain money
-- trails — this is the generic spine row, not their replacement.
--
-- correlation_id = WorkflowContext.correlation_id (= draft_id when the draft
-- pipeline invokes N ops as one apply) — correlation homes on THIS DB spine;
-- the frozen 11-field bus payload never grows a 12th field (spec 07 §5).

CREATE TABLE IF NOT EXISTS audit_log (
    mutation_id     UUID        PRIMARY KEY,       -- once()-guarded upstream; PK is belt-and-braces
    subsystem       TEXT        NOT NULL,
    mutation_type   TEXT        NOT NULL,          -- op.audit_verb
    target          TEXT        NOT NULL,
    scope           TEXT        NOT NULL,          -- 'global' | 'guild'
    guild_id        BIGINT      NULL,
    prev_value      TEXT        NULL,              -- rollup of leg before-states
    new_value       TEXT        NULL,              -- rollup of leg after-states
    actor_id        BIGINT      NULL,
    actor_type      TEXT        NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    detail          JSONB       NOT NULL DEFAULT '{}',  -- per-leg StepResults + FieldChanges
    correlation_id  UUID        NULL               -- draft-apply grouping (spec 07 §8 fork B)
);

-- The operator log (newest-first per guild).
CREATE INDEX IF NOT EXISTS audit_log_guild_occurred_idx
    ON audit_log (guild_id, occurred_at DESC);

-- Forensics by subsystem + verb.
CREATE INDEX IF NOT EXISTS audit_log_subsystem_type_idx
    ON audit_log (subsystem, mutation_type, occurred_at DESC);

-- Draft-apply grouping.
CREATE INDEX IF NOT EXISTS audit_log_correlation_idx
    ON audit_log (correlation_id) WHERE correlation_id IS NOT NULL;
