-- 0013: TREASURY store (band 3 slice 2) — the shipped guild_treasury shape
-- (old migration 092) carried forward NAME_STABLE: one row per guild holding
-- the server-owned coin pool. `updated_at` is the shipped unix-epoch stamp.

CREATE TABLE IF NOT EXISTS guild_treasury (
    guild_id   BIGINT NOT NULL PRIMARY KEY,
    balance    BIGINT NOT NULL DEFAULT 0 CHECK (balance >= 0),
    updated_at BIGINT NOT NULL DEFAULT 0
);
