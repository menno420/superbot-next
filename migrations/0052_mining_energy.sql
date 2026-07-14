-- 0052: mining energy — the per-(user, guild) dig-energy fuel columns on the
-- existing mining_player_state meta row (oracle disbot/migrations/
-- 086_mining_energy.sql shape @ 87bbe1d; energy lives on the player-state
-- table, NOT a dedicated table — contrast fishing's 0035 fishing_energy).
-- Consumers arrive in later slices (docs/scoping/energy-system-scope.md):
-- slice 2 wires !cook/!use, slice 3 (owner-gated, after WP-3) the !fastmine
-- dig spend. This migration + the store get_energy/set_energy pair is slice 1.
--
-- DEFAULT 0/0 is the faithful oracle missing-row posture: get_energy returns
-- (0, 0) for a row-less player, and utils.mining.energy.settle reads that as
-- "0 energy as of the epoch" — the huge elapsed clamps to MAX_ENERGY, so every
-- fresh AND every pre-energy depth-player starts with a full bar (purely
-- computed lazy regen: a stored value + a timestamp, never a background
-- ticker — the ADR-001/002 posture, same as 0035).
ALTER TABLE mining_player_state
    ADD COLUMN IF NOT EXISTS energy            INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS energy_updated_at BIGINT  NOT NULL DEFAULT 0;
