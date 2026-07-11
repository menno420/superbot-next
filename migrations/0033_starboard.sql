-- 0033: starboard_settings + starboard_ignore_channels — the shipped
-- starboard config tables (old repo disbot/migrations/083_starboard.sql +
-- 084_starboard_pr2.sql, imported NAME_STABLE; DDL reconstructed
-- fragment-by-fragment via search_code). Consumers: the `!starboard
-- #channel [threshold]` configure upsert (starboard.configure), the
-- `!starboard off`/`selfstar` UPDATE lanes (starboard.disable /
-- starboard.set_self_star — pure UPDATEs, shipped: a no-op over an
-- unconfigured guild, exactly what goldens/starboard/sweep_starboard_off
-- + sweep_starboard_selfstar pin) and the `!starboard ignore|unignore`
-- pair (starboard.ignore_add/_remove) —
-- goldens/starboard/sweep_starboard_ignore pins the ignore-row shape
-- byte-for-byte. The oracle's third table (`starboard_entries`, one row
-- per boarded message) is NOT minted here: no golden touches it — it
-- lands with the reaction-listener slice (the trap-15b "declare only
-- what the slice fully carries" rule; sb/domain/starboard/service.py
-- module docstring carries the under-port boundary).
CREATE TABLE IF NOT EXISTS starboard_settings (
    guild_id   BIGINT  NOT NULL PRIMARY KEY,
    -- the hall-of-fame channel
    channel_id BIGINT  NOT NULL,
    -- stars needed to enter (shipped default 3; configure clamps >= 1)
    threshold  INTEGER NOT NULL DEFAULT 3,
    -- the trigger emoji (the shipped default '⭐')
    emoji      TEXT    NOT NULL DEFAULT '⭐',
    enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    -- count the author's own star toward the threshold? (084: default OFF)
    self_star  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS starboard_ignore_channels (
    guild_id   BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);
