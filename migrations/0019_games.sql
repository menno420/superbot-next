-- 0019: GAMES substrate (band 6 slice 1) — the shared game-state checkpoint
-- table and the cross-game progression track, shipped shapes carried forward.
--
-- `game_state` (shipped migration 015 + 018) is the restart-safe checkpoint
-- store for in-flight game state (blackjack hands, RPS matches, escrow rows,
-- tournament entry rows). One row per (guild, user, channel, subsystem);
-- SESSION checkpoint class — restart-lossy BY DESIGN (design-spec §3.4:
-- money-safety rides the refund/recovery paths, never session resurrection).
-- Escrow/entry rows carry the staked amount under the `bet` payload key —
-- the GC-refund convention shared with the session_gc sweep.
--
-- `game_xp` (shipped migration 065) is the shared cross-game progression
-- track: per-game attribution + per-game daily soft caps; the player's
-- SHARED level derives from SUM(xp) through the ONE chat-XP curve —
-- deliberately NO stored level column.

CREATE TABLE IF NOT EXISTS game_state (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id     BIGINT NOT NULL,
    user_id      BIGINT NOT NULL,
    channel_id   BIGINT NOT NULL,
    subsystem    TEXT   NOT NULL,
    state        TEXT   NOT NULL,
    version      INTEGER NOT NULL DEFAULT 1,
    created_at   BIGINT NOT NULL,
    updated_at   BIGINT NOT NULL,
    CONSTRAINT uq_game_state UNIQUE (guild_id, user_id, channel_id, subsystem)
);

CREATE INDEX IF NOT EXISTS idx_game_state_subsystem
    ON game_state (subsystem, guild_id);
CREATE INDEX IF NOT EXISTS idx_game_state_user
    ON game_state (guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_game_state_updated
    ON game_state (updated_at);

CREATE TABLE IF NOT EXISTS game_xp (
    user_id    BIGINT  NOT NULL,
    guild_id   BIGINT  NOT NULL,
    game       TEXT    NOT NULL,
    xp         BIGINT  NOT NULL DEFAULT 0,
    day        TEXT,
    day_xp     INTEGER NOT NULL DEFAULT 0,
    updated_at BIGINT  NOT NULL,
    PRIMARY KEY (user_id, guild_id, game)
);

CREATE INDEX IF NOT EXISTS idx_game_xp_guild ON game_xp (guild_id, xp DESC);
