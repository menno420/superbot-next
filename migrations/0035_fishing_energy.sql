-- 0035: fishing_energy — the per-(user, guild) cast-energy bar (old repo
-- disbot/migrations/088_fishing_energy.sql, imported NAME_STABLE; DDL
-- reconstructed fragment-by-fragment via search_code). Consumer: the
-- `!fish` cast open (fishing.cast_open settles then spends CAST_COST
-- before presenting the reel panel — goldens/fishing/sweep_fish pins the
-- spent row {energy: 58, energy_updated_at: <now>} byte-for-byte).
-- energy defaults to the full bar (60) and energy_updated_at to 0, so
-- every existing player and every fresh row starts with a full bar (a
-- huge elapsed-from-0 simply settles to the cap) — purely computed regen
-- (ADR-001/002 posture carried over: a stored value + a timestamp, never
-- a background ticker).
CREATE TABLE IF NOT EXISTS fishing_energy (
    user_id           BIGINT  NOT NULL,
    guild_id          BIGINT  NOT NULL DEFAULT 0,
    energy            INTEGER NOT NULL DEFAULT 60,
    energy_updated_at BIGINT  NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
