-- 0040: mining_gear_wear — remaining durability of the "active" unit of each
-- gear item a player owns (oracle disbot/migrations/063_mining_gear_wear.sql,
-- imported NAME_STABLE). Keyed by item NAME, not equipment slot, so wear
-- survives unequip/re-equip; a row exists only while the item is worn (absence
-- = full durability; breaking or repairing deletes the row). user_id is TEXT
-- to match mining_inventory's legacy column type. Also reserves the shipped
-- "quick-craft the last item that broke" pointer on mining_player_state.
--
-- No golden drives a wear write (the guard-only slice-1 capture) — declared-
-- but-guard-only (depth.exemptions.mining guard-only-capture).
CREATE TABLE IF NOT EXISTS mining_gear_wear (
    user_id    TEXT        NOT NULL,
    guild_id   BIGINT      NOT NULL,
    item_name  TEXT        NOT NULL,
    durability INTEGER     NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, guild_id, item_name)
);

ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS last_broken_item TEXT;
