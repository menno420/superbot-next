-- 0012: ECONOMY stores (band 3 slice 1) — shipped shapes carried forward.
--
-- `economy_balances` is the per-user coin aggregate. In the shipped bot the
-- balance lived as `xp.coins` (one column on the XP table); the rebuild
-- de-couples the money aggregate from the XP band into its own table —
-- forward_map_kind=RENAME (pure bijection: xp(user_id,guild_id).coins →
-- economy_balances(user_id,guild_id).coins).
--
-- `economy_audit_log` is the money ledger (shipped table, NAME_STABLE — the
-- hottest audit table imports name-stable at CUT-2). The ADDITIVE
-- `mutation_id` column is the ledger-reinsert conflict key the S14 reverse
-- importer keys on (tools/importer/reverse ledger_reinsert_sql); minted per
-- movement at write time.
--
-- `economy` is the shipped daily/work tracking row (streaks, cooldown
-- anchors), `job_progress` the shipped per-job mastery counter, `inventory`
-- the shipped per-guild unique-item table (the shop's grant target).

CREATE TABLE IF NOT EXISTS economy_balances (
    user_id  BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    coins    BIGINT NOT NULL DEFAULT 0 CHECK (coins >= 0),
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS economy_audit_log (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mutation_id TEXT        NOT NULL,
    guild_id    BIGINT      NOT NULL,
    user_id     BIGINT      NOT NULL,
    actor_id    BIGINT,
    delta       BIGINT      NOT NULL,
    new_balance BIGINT      NOT NULL,
    reason      TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_economy_audit_mutation
    ON economy_audit_log (mutation_id);
CREATE INDEX IF NOT EXISTS idx_economy_audit_guild_time
    ON economy_audit_log (guild_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_economy_audit_guild_reason
    ON economy_audit_log (guild_id, reason);

CREATE TABLE IF NOT EXISTS economy (
    user_id      BIGINT  NOT NULL,
    guild_id     BIGINT  NOT NULL,
    last_daily   BIGINT  NOT NULL DEFAULT 0,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    daily_count  INTEGER NOT NULL DEFAULT 0,
    last_worked  BIGINT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS job_progress (
    user_id      BIGINT  NOT NULL,
    guild_id     BIGINT  NOT NULL,
    job_name     TEXT    NOT NULL,
    times_worked INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, job_name)
);

CREATE TABLE IF NOT EXISTS inventory (
    user_id   BIGINT  NOT NULL,
    guild_id  BIGINT  NOT NULL,
    item_name TEXT    NOT NULL,
    quantity  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, item_name)
);
