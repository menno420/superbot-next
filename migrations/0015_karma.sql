-- 0015: KARMA stores (band 4) — the shipped karma aggregate + the
-- append-only karma_audit_log (the audit log doubles as the anti-abuse
-- source of truth: cooldown + daily cap read it, INV-K's runtime half).
-- mutation_id is the ADDITIVE S14 ledger-reinsert conflict key (the
-- economy_audit_log precedent, D-0031): the CUT-2 alias map adds the
-- column + unique index old-side before any rollback window opens.

CREATE TABLE IF NOT EXISTS karma (
    user_id        BIGINT NOT NULL,
    guild_id       BIGINT NOT NULL,
    karma_points   BIGINT NOT NULL DEFAULT 0 CHECK (karma_points >= 0),
    received_count BIGINT NOT NULL DEFAULT 0,
    given_count    BIGINT NOT NULL DEFAULT 0,
    last_received  TIMESTAMPTZ,
    PRIMARY KEY (user_id, guild_id)
);

-- board ordering: points desc, oldest last_received breaks ties
CREATE INDEX IF NOT EXISTS idx_karma_guild_points
    ON karma (guild_id, karma_points DESC, last_received ASC);

CREATE TABLE IF NOT EXISTS karma_audit_log (
    id          BIGSERIAL PRIMARY KEY,
    mutation_id TEXT NOT NULL UNIQUE,
    guild_id    BIGINT NOT NULL,
    from_user   BIGINT NOT NULL,
    to_user     BIGINT NOT NULL,
    delta       INT NOT NULL,
    source      TEXT NOT NULL,
    reason      TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- the per-(giver -> receiver) cooldown read
CREATE INDEX IF NOT EXISTS idx_karma_audit_pair
    ON karma_audit_log (guild_id, from_user, to_user, occurred_at);
-- the per-giver daily-cap read
CREATE INDEX IF NOT EXISTS idx_karma_audit_giver
    ON karma_audit_log (guild_id, from_user, occurred_at);
-- the INV-K reconciliation read
CREATE INDEX IF NOT EXISTS idx_karma_audit_recipient
    ON karma_audit_log (guild_id, to_user);
