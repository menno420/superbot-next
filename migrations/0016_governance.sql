-- 0016: GOVERNANCE stores (band 5) — the shipped governance tables
-- (old migrations 004/006/009/010/011) on the fresh chain.
--
--  * subsystem_visibility: scope-chain overrides; enabled NULL = explicit
--    inherit; scope_type gained 'thread' in old migration 009 (RC-5).
--  * cleanup_policies: deliberately NON-thread CHECK (RC-5 — the writes
--    pipeline rejects thread scope before the DB).
--  * governance_audit_log: every governance mutation's audit row (the
--    shipped table, verbatim columns).
--  * capability_execution_overrides: per-guild capability revoke overlay.
--    Fresh-chain simplification (D-0039): the shipped runtime read
--    collapsed the scope columns (SELECT capability, allowed WHERE
--    guild_id=...), so the fresh shape keys on (guild_id, capability).
--  * governance_templates (+ applications): the ISSUE-034 template store.

CREATE TABLE IF NOT EXISTS subsystem_visibility (
    guild_id    BIGINT  NOT NULL,
    scope_type  TEXT    NOT NULL
        CHECK (scope_type IN ('guild', 'category', 'channel', 'thread', 'role')),
    scope_id    BIGINT  NOT NULL,
    subsystem   TEXT    NOT NULL,
    enabled     BOOLEAN,           -- NULL = inherit from parent scope
    PRIMARY KEY (guild_id, scope_type, scope_id, subsystem)
);

CREATE INDEX IF NOT EXISTS idx_sv_lookup
    ON subsystem_visibility (guild_id, scope_type, scope_id);

CREATE TABLE IF NOT EXISTS cleanup_policies (
    guild_id                BIGINT  NOT NULL,
    scope_type              TEXT    NOT NULL
        CHECK (scope_type IN ('guild', 'category', 'channel')),
    scope_id                BIGINT  NOT NULL,
    delete_invalid_commands BOOLEAN NOT NULL DEFAULT TRUE,
    delete_failed_commands  BOOLEAN NOT NULL DEFAULT TRUE,
    delete_after_seconds    INTEGER NOT NULL DEFAULT 5,
    PRIMARY KEY (guild_id, scope_type, scope_id)
);

CREATE TABLE IF NOT EXISTS governance_audit_log (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    guild_id    BIGINT      NOT NULL,
    actor_id    BIGINT      NOT NULL,
    action      TEXT        NOT NULL,
    scope_type  TEXT,
    scope_id    BIGINT,
    subsystem   TEXT,
    old_value   JSONB,
    new_value   JSONB
);

CREATE INDEX IF NOT EXISTS idx_governance_audit_guild
    ON governance_audit_log (guild_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS capability_execution_overrides (
    guild_id   BIGINT      NOT NULL,
    capability TEXT        NOT NULL,
    allowed    BOOLEAN     NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, capability)
);

CREATE TABLE IF NOT EXISTS governance_templates (
    template_id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                TEXT        NOT NULL,
    description         TEXT,
    created_by_guild_id BIGINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload             JSONB       NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS governance_template_applications (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id    BIGINT      NOT NULL,
    template_id BIGINT      NOT NULL
        REFERENCES governance_templates(template_id) ON DELETE CASCADE,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by  BIGINT,
    UNIQUE (guild_id, template_id)
);
