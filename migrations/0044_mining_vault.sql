-- 0044: mining vault — a per-player "safe stash" separate from the active
-- mining pack (slice 3 — vault/stash/unstash/vaultupgrade, oracle
-- disbot/migrations/070_mining_vault.sql, imported NAME_STABLE).
--
-- Depositing moves items OUT of mining_inventory and into this protected store;
-- withdrawing moves them back. The shape mirrors mining_inventory exactly so a
-- deposit/withdraw is a symmetric pair of clamped item deltas: guild-scoped,
-- user_id TEXT to match mining_inventory's legacy column type, one row per item,
-- quantity clamped at >= 0. Purely additive — no existing play changes.
--
-- The item-bearing deposit (`!stash <owned item> [n]`) writes a row, but every
-- imported sweep drove only the bare `!stash` usage guard (goldens/mining/
-- sweep_stash pins the usage byte with no row), so mining_vault is a
-- declared-but-guard-only mining surface (depth.exemptions.mining
-- guard-only-capture).
CREATE TABLE IF NOT EXISTS mining_vault (
    user_id    TEXT    NOT NULL,
    guild_id   BIGINT  NOT NULL DEFAULT 0,
    item_name  TEXT    NOT NULL,
    quantity   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, item_name)
);
