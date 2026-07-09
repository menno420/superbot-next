-- 0022: PvP stat stores (band 6 slice 4) — shipped shapes carried
-- forward (deathmatch_stats + rps_players, both widened to
-- (user_id, guild_id) by shipped migration 005-era fixes; rps name
-- captured at game time per the shipped leaderboard query).

CREATE TABLE IF NOT EXISTS deathmatch_stats (
    user_id  BIGINT  NOT NULL,
    guild_id BIGINT  NOT NULL DEFAULT 0,
    wins     INTEGER NOT NULL DEFAULT 0,
    losses   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS rps_players (
    user_id  BIGINT NOT NULL,
    guild_id BIGINT NOT NULL DEFAULT 0,
    name     TEXT    NOT NULL,
    wins     INTEGER NOT NULL DEFAULT 0,
    losses   INTEGER NOT NULL DEFAULT 0,
    ties     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);
