-- 0014: XP store (band 4) — the shipped `xp` table shape MINUS the coins
-- column (band 3 extracted it into economy_balances, D-0031 RENAME split).
-- level is DERIVED state (level_progress(xp)) guarded by the INV-G
-- level-consistency invariant; last_xp is the unix-epoch cooldown stamp.

CREATE TABLE IF NOT EXISTS xp (
    user_id  BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    xp       BIGINT NOT NULL DEFAULT 0,
    level    INT    NOT NULL DEFAULT 0,
    messages BIGINT NOT NULL DEFAULT 0,
    last_xp  BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- leaderboard / rank ordering
CREATE INDEX IF NOT EXISTS idx_xp_guild_xp ON xp (guild_id, xp DESC);
