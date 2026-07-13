-- 0049: fishing rod tier (fishing depth slice 2 — the gear shops, oracle
-- disbot/migrations/087_fishing_rod.sql, imported NAME_STABLE).
--
-- The second, orthogonal fishing-progression axis (owner design Q-0175).
-- Fishing *level* (game_xp) gates which size bands you can catch; the
-- *rod* gates how well / which-within-band you catch them, via tuned
-- knobs that live in pure code (sb/domain/fishing/rods.py).
--
-- One additive per-(user, guild) row holding the owned rod tier (0 = the
-- starter "Bare Rod", up the ladder to diamond). Rods are bought with
-- coins through the audited fishing.rod_upgrade op (debit + tier bump in
-- ONE txn); this table just stores the tier. Absent row = tier 0, so
-- every existing player and every fresh row starts on the starter rod
-- (which still catches fine — rods only improve, never gate).
-- goldens/fishing/sweep_rod pins the fresh-player tier-0 shop read.
CREATE TABLE IF NOT EXISTS fishing_rod (
    user_id  BIGINT  NOT NULL,
    guild_id BIGINT  NOT NULL DEFAULT 0,
    tier     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
