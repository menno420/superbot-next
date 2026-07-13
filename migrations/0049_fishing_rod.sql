-- 0049: fishing rod (fishing depth slice 2 — rod/rodrecipes/craftrod,
-- oracle disbot/migrations/087_fishing_rod.sql, imported NAME_STABLE).
--
-- The rod is the second, orthogonal fishing-progression axis (owner design
-- Q-0175): fishing *level* (game_xp) gates which size bands you can catch;
-- the *rod* gates how well / which-within-band you catch them, via five
-- tuned knobs (window bonus, bite speed, rarity pull, escape resist,
-- premature grace) that live in pure code (sb/domain/fishing/rods.py).
--
-- One additive per-(user, guild) row holding the owned rod tier (0 = the
-- starter "Bare Rod", up the ladder to diamond). An absent row reads as
-- tier 0, so every existing player and every fresh row starts on the
-- starter rod (which still catches fine — rods only improve, never gate).
-- Rods are bought with coins through the audited fishing.buy_rod op (the
-- coin debit audits itself on the economy ledger) or crafted from caught
-- fish through fishing.craft_rod; this table just stores the tier — plain
-- game state, no audit of its own (like venue / energy).
-- goldens/fishing/sweep_rod + sweep_rodrecipes pin the tier-0 shop /
-- recipe-browser renders and sweep_craftrod the not-enough-fish guard
-- (all pure reads — the first row-bearing golden lands with a funded
-- argful capture; depth.exemptions.fishing guard-only-capture).
CREATE TABLE IF NOT EXISTS fishing_rod (
    user_id  BIGINT  NOT NULL,
    guild_id BIGINT  NOT NULL DEFAULT 0,
    tier     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
