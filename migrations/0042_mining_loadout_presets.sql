-- 0042: mining_loadout_presets — named saved gear loadouts per player (oracle
-- disbot/migrations/101_mining_loadout_presets.sql, imported NAME_STABLE). A
-- player can save their current equipped gear under a name (e.g. `mining`,
-- `combat`, `fishing`) and swap their whole loadout back to it later. One row
-- per (user_id, guild_id, name, slot) — a preset is the set of rows sharing a
-- (user_id, guild_id, name). user_id is TEXT to match mining_equipment /
-- mining_inventory's legacy column type. CRUD is DELETE-then-INSERT per slot
-- (sb/domain/mining/store.py save_loadout).
--
-- No golden drives an argful !loadout save/apply (the imported sweep pinned
-- only the bare "no saved loadouts yet" guard, goldens/mining/sweep_loadout) —
-- declared-but-guard-only (depth.exemptions.mining guard-only-capture).
CREATE TABLE IF NOT EXISTS mining_loadout_presets (
    user_id    TEXT        NOT NULL,
    guild_id   BIGINT      NOT NULL,
    name       TEXT        NOT NULL,
    slot       TEXT        NOT NULL,
    item_name  TEXT        NOT NULL,
    saved_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, guild_id, name, slot)
);
