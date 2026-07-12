-- 0043: mining world seed + descent record (slice 2 — descend/ascend/mineworld,
-- oracle disbot/migrations/085_mining_grid.sql + 061_mining_player_state.sql
-- max_depth, imported NAME_STABLE).
--
-- One shared procedural world per guild (Q-0173: "ONE shared grid per seed").
-- A guild with no row defaults to seed = guild_id in the read layer
-- (store.get_world_seed), so this table only ever holds an explicit owner
-- re-seed (`!mineworld <seed>`) — the bare `!mineworld` read never writes it,
-- so it is a declared-but-guard-only mining surface (depth.exemptions.mining
-- guard-only-capture; goldens/mining/sweep_mineworld pins the default-seed read
-- byte with no row).
CREATE TABLE IF NOT EXISTS mining_world (
    guild_id   BIGINT      PRIMARY KEY,
    seed       BIGINT      NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The deepest band a player has ever reached (0 = never left Surface) — the
-- one-time depth_record game-XP award fires when a descend beats it. The
-- shipped GEARED descent that writes it (depth_access > 0) exists in no
-- imported golden; the bare `!descend` refuses at the Surface with no write
-- (goldens/mining/sweep_descend), so mining_player_state stays guard-only.
ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS max_depth INTEGER NOT NULL DEFAULT 0;
