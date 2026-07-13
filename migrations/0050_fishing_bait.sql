-- 0050: fishing bait loadout (fishing depth slice 2 — the gear shops,
-- oracle disbot/migrations/091_fishing_bait.sql, imported NAME_STABLE).
--
-- The optional second pre-cast economy knob (owner design Q-0175 §4):
-- bait is a coin-bought pack of charges that, while held, biases each
-- cast toward rarer fish. Bait is bought with coins through the audited
-- fishing.bait_buy op (debit + load in ONE txn).
--
-- One additive per-(user, guild) row holding the player's currently-
-- loaded bait key + remaining charges (a player loads at most one bait
-- at a time). The bait knob values + the purchase policy live in pure
-- code (sb/domain/fishing/bait.py); this table just stores the active
-- loadout. Absent row (or charges = 0) = no bait, so every existing
-- player and every fresh row fishes bait-less (which catches fine —
-- bait only improves, never gates).
-- goldens/fishing/sweep_bait pins the fresh-player bait-less shop read.
CREATE TABLE IF NOT EXISTS fishing_bait (
    user_id  BIGINT  NOT NULL,
    guild_id BIGINT  NOT NULL DEFAULT 0,
    bait_key TEXT    NOT NULL DEFAULT '',
    charges  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
