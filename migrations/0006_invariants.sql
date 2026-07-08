-- 0006_invariants.sql — the S12 quarantine + sweep-log stores (frozen L0
-- spec 11 §3). Fresh chain; net-new.
--
-- sb_quarantine: evidence-preserving, never-destroy — the disposition
-- (repair | carry_as_is | declared_loss) is OWNER-SIGNED (the SF-g pattern).
-- sb_invariant_sweep_log: kernel-internal observability, NOT an auditable
-- domain mutation (the 09 §7 bookkeeping posture).

CREATE TABLE IF NOT EXISTS sb_quarantine (
    quarantine_id  UUID        PRIMARY KEY,
    invariant_id   TEXT        NOT NULL,
    primary_store  TEXT        NOT NULL,        -- Violation.primary_store — the named target
    stores         TEXT[]      NOT NULL,        -- the full span (cross-store violations)
    row_id         TEXT        NOT NULL,        -- canonical PK (composite ":"-joined)
    guild_id       BIGINT      NULL,
    snapshot_json  JSONB       NOT NULL,        -- the preserved row payload (evidence)
    quarantined_at TIMESTAMPTZ NOT NULL,
    disposition    TEXT        NULL             -- owner-signed: repair | carry_as_is | declared_loss
);

CREATE INDEX IF NOT EXISTS sb_quarantine_invariant_idx
    ON sb_quarantine (invariant_id, quarantined_at DESC);
CREATE INDEX IF NOT EXISTS sb_quarantine_guild_idx
    ON sb_quarantine (guild_id) WHERE guild_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS sb_invariant_sweep_log (
    run_id            UUID        PRIMARY KEY,
    invariant_id      TEXT        NOT NULL,
    cadence_epoch     BIGINT      NOT NULL,     -- the once()-guarded window
    started_at        TIMESTAMPTZ NOT NULL,
    finished_at       TIMESTAMPTZ NULL,         -- NULL => crashed mid-run (boot re-runs)
    enforce_effective BOOLEAN     NOT NULL,
    guilds_scanned    INT         NOT NULL DEFAULT 0,
    rows_read         INT         NOT NULL DEFAULT 0,
    violations_found  INT         NOT NULL DEFAULT 0,
    repairs_applied   INT         NOT NULL DEFAULT 0,
    quarantined       INT         NOT NULL DEFAULT 0,
    alerts            INT         NOT NULL DEFAULT 0,
    breaker_tripped   BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS sb_invariant_sweep_log_idx
    ON sb_invariant_sweep_log (invariant_id, started_at DESC);
