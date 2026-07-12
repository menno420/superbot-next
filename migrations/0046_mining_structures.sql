-- 0046: mining structures — per-player built structure levels (slice 4 —
-- forge/repair/quickcraft/cook/use, oracle disbot/migrations/072_mining_
-- structures.sql, imported NAME_STABLE).
--
-- One row per (user, guild, structure) holding the structure's built level;
-- absent row = level 0 (not built). Generic on purpose: the Forge (gates
-- gold/diamond gear crafting) and the Campfire (gates cooking fish into food)
-- are its two slice-4 structures, and the later Home backdrop reuses this same
-- table. user_id is BIGINT to match player_skills / game_xp (player-progression
-- identity), NOT mining_inventory's legacy TEXT column.
--
-- Purely additive — an EMPTY table is byte-identical to today's crafting (the
-- forge level required to craft a recipe is derived in pure code from its gear
-- tier; bronze/iron/silver gear, tools, and structures need level 0). The
-- row-bearing build write (`!forge` 🔥 Build / `!build campfire`) rides the
-- deferred structures BUILD system (the `!build` command stays a pending
-- terminal this slice), and every imported sweep drove only the bare `!forge`
-- — which renders the not-built card off the store's no-row level 0
-- (goldens/mining/sweep_forge.json) — so mining_structures is a
-- declared-but-guard-only mining surface (depth.exemptions.mining
-- guard-only-capture).
CREATE TABLE IF NOT EXISTS mining_structures (
    user_id   BIGINT  NOT NULL,
    guild_id  BIGINT  NOT NULL DEFAULT 0,
    structure TEXT    NOT NULL,
    level     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id, structure)
);
