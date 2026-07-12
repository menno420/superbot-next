-- 0045: mining vault capacity tier — the upgradeable vault (slice 3 —
-- vaultupgrade, oracle disbot/migrations/072_mining_vault_capacity.sql,
-- imported NAME_STABLE).
--
-- vault_level is the per-player capacity tier: the vault holds
-- BASE_VAULT_CAP + level * VAULT_SLOTS_PER_LEVEL distinct item-types
-- (sb/domain/mining/capacity.py). Level 0 is the base default, so this column
-- is purely additive — every existing vault keeps its base capacity and no play
-- changes. It lives on mining_player_state (the per-(user,guild) mining meta
-- row) rather than a new table; the `!vaultupgrade` sink spends coins through
-- the audited economy lane (sb/domain/mining/ops.py).
--
-- The funded upgrade that writes it exists in no imported golden — the ONLY
-- pinned vaultupgrade path is the insufficient-funds refusal (a pure read;
-- goldens/mining/sweep_vaultupgrade), so mining_player_state stays guard-only.
ALTER TABLE mining_player_state
    ADD COLUMN IF NOT EXISTS vault_level INTEGER NOT NULL DEFAULT 0;
