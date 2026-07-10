-- 0027: the shipped guild_settings KV table (old-repo utils/db/migrations.py
-- baseline), imported NAME_STABLE for the ONE runtime key the game bands
-- write: active_tournament (the shipped tournament_state_service home — PR
-- B' classified it "runtime tournament state, not guild configuration", so
-- it never joined the band-1 settings table; the rpsregister golden pins the
-- row shape {guild_id, key, value} byte-for-byte). Durable guild
-- CONFIGURATION stays in `settings` (band 1) — this table is the runtime
-- tournament flag's verbatim home, nothing else writes it.
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT NOT NULL,
    key      TEXT   NOT NULL,
    value    TEXT   NOT NULL,
    PRIMARY KEY (guild_id, key)
);
