-- 0041: player_skills — a player's allocated skill-tree points (oracle
-- disbot/migrations/071_player_skills.sql, imported NAME_STABLE). One row per
-- (user, guild, branch) holding how many points the player has allocated into
-- that branch. Allocations map onto the shared EffectiveStats block
-- (sb/domain/mining/skills.py skill_stats), merged with equipped gear by
-- sb/domain/mining/character.py, so an EMPTY allocation is byte-identical to
-- gear-only stats (the additive safety property). user_id is BIGINT to match
-- game_xp (skills derive from the game-XP level), NOT mining_inventory's
-- legacy TEXT column.
--
-- No golden drives a skill write (the guard-only slice-1 capture) — declared-
-- but-guard-only (depth.exemptions.mining guard-only-capture).
CREATE TABLE IF NOT EXISTS player_skills (
    user_id   BIGINT  NOT NULL,
    guild_id  BIGINT  NOT NULL DEFAULT 0,
    branch    TEXT    NOT NULL,
    points    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, branch)
);
