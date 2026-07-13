-- 0048: fishing venue (fishing depth slice 1 — forecast/sail, oracle
-- disbot/migrations/094_fishing_venue.sql, imported NAME_STABLE).
--
-- Which water the player is fishing (owner design Q-0175 §5). Shore is the
-- relaxed default; setting sail in the boat opens the deepwater venue, with
-- its own boat-only species pool and a tougher minigame (the numbers live in
-- pure code, sb/domain/fishing/venue.py).
--
-- One additive per-(user, guild) row holding the current venue string. An
-- absent row reads as 'shore', so every existing player and every fresh row
-- starts on the shore (the ⛵ Set sail / 🏖️ Dock toggle flips it). Venue is
-- plain game state — set through the fishing.sail_route handler and read by
-- the hub/cast renders; no audit (like rod tier / energy).
-- goldens/fishing/sweep_sail pins the deepwater row this table's first
-- write mints.
CREATE TABLE IF NOT EXISTS fishing_venue (
    user_id  BIGINT NOT NULL,
    guild_id BIGINT NOT NULL DEFAULT 0,
    venue    TEXT   NOT NULL DEFAULT 'shore',
    PRIMARY KEY (user_id, guild_id)
);
