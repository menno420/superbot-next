-- 0047: mining equipped title — the equipped-title selection (slice 5 —
-- skills/skill/titles, oracle disbot/migrations/074_mining_equipped_title.sql,
-- imported NAME_STABLE).
--
-- A player's EARNED titles are DERIVED on read from existing progression (skill
-- allocation at cap, max depth, game level — sb/domain/mining/titles.py), so the
-- only thing that needs persisting is which earned title the player chose to
-- display. equipped_title is that choice (NULL = none equipped -> byte-identical
-- to the pre-titles Character card). It lives on mining_player_state (the
-- per-(user, guild) mining meta row) rather than a new table — purely additive.
--
-- The equipped-title WRITE (the 🏆 Titles panel select) rides the deferred panel
-- port (D-0043) — every imported sweep drove only the bare `!titles`, which
-- renders the "— none —" / 🔒 Locked (9) card off the store's NULL equipped_title
-- (goldens/mining/sweep_titles.json) — so mining_player_state stays a
-- declared-but-guard-only mining surface (depth.exemptions.mining, already held).
ALTER TABLE mining_player_state
    ADD COLUMN IF NOT EXISTS equipped_title TEXT;
