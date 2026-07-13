-- 0050: fishing bait (fishing depth slice 3 — bait/craftbait/craftpearl/
-- craftcharm, oracle disbot/migrations/091_fishing_bait.sql, imported
-- NAME_STABLE).
--
-- Bait is the optional *second* pre-cast economy knob (owner design
-- Q-0175 §4): fishing *level* (game_xp) gates which size bands you can
-- catch and the *rod* is the permanent how-well axis; *bait* is the
-- consumable how-well axis — a coin-bought (or fish/pearl-crafted) pack
-- of charges that, while held, biases each cast toward rarer fish and/or
-- quicker bites. The knob values live in pure code
-- (sb/domain/fishing/bait.py); the purchase/craft policy in the audited
-- fishing ops (sb/domain/fishing/ops.py).
--
-- One additive per-(user, guild) row holding the player's currently-
-- loaded bait key + remaining charges (a player loads at most one bait
-- at a time). An absent row (or charges = 0) reads as no bait, so every
-- existing player and every fresh row fishes bait-less (which catches
-- fine — bait only improves, never gates). Bait is bought with coins
-- through the audited fishing.buy_bait op (the coin debit audits itself
-- on the economy ledger) or crafted from caught fish / pearls through
-- fishing.craft_bait / fishing.craft_pearl_bait; this table just stores
-- the active loadout — plain game state, no audit of its own (like
-- venue / energy / rod).
-- goldens/fishing/sweep_bait + sweep_craftbait pin the fresh bait-less
-- shop render and sweep_craftpearl the no-pearls guard (all pure reads —
-- the first row-bearing golden lands with a funded/stocked argful
-- capture; depth.exemptions.fishing guard-only-capture).
CREATE TABLE IF NOT EXISTS fishing_bait (
    user_id  BIGINT  NOT NULL,
    guild_id BIGINT  NOT NULL DEFAULT 0,
    bait_key TEXT    NOT NULL DEFAULT '',
    charges  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
