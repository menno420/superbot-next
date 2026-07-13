-- 0056: mining grid — lateral position + fog of war for the grid Mine
-- navigator (curation rework rows 45/59; oracle disbot/migrations/
-- 085_mining_grid.sql semantics @ 9c16365).
--
-- pos_x / pos_y land on the EXISTING mining_player_state meta row exactly as
-- shipped (the oracle put position on mining_player_state too; (x, y, depth)
-- is the full player position — z is the existing depth column).
ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS pos_x INTEGER NOT NULL DEFAULT 0;
ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS pos_y INTEGER NOT NULL DEFAULT 0;

-- FLAGGED DEVIATION (PR #434): the oracle keeps fog of war in a dedicated
-- mining_discovered table (one row per visited (z, x, y), windowed reads).
-- Here the visited-cell set rides a JSONB column on mining_player_state
-- ({"z:x:y": 1} keys; single-statement `discovered || $new::jsonb` merge —
-- idempotent and concat-race-safe, matching the oracle's ON CONFLICT DO
-- NOTHING posture). Why: a NEW declared store table on the already-ported
-- mining subsystem needs a parity/parity.yml depth-exemption row
-- (check_parity_depth R2), and parity.yml is owned by the wp-stack
-- reconcile lane tonight. Columns on an existing covered store ride free
-- (the 0052 energy-columns precedent). Graduating fog of war to the oracle
-- table shape (mining_discovered + StoreSpec + erasure workflow + depth
-- exemption) is the named follow-up for whoever holds the parity.yml pen.
-- mining.erase_subject_state already erases these columns with the row.
ALTER TABLE mining_player_state ADD COLUMN IF NOT EXISTS discovered JSONB NOT NULL DEFAULT '{}'::jsonb;
