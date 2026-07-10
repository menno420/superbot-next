-- 0026: game_state timestamps back to the SHIPPED column types.
--
-- The shipped table (old-repo migration 015_game_state.sql) declared
-- created_at/updated_at TIMESTAMPTZ; 0019 carried them as BIGINT epochs — a
-- silent dialect deviation the blackjack gating golden exposed: the parity
-- db_delta pins `created_at: "<ts>"` (the Normalizer's datetime symbol),
-- which a BIGINT column can never produce. Convert in place; the store keeps
-- its epoch-int API and converts at the SQL boundary (to_timestamp).
ALTER TABLE game_state
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING to_timestamp(created_at),
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING to_timestamp(updated_at);
