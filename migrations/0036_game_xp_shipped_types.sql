-- 0036: game_xp column types to the SHIPPED shapes (old repo
-- disbot/migrations/065_game_xp.sql: `day DATE`, `updated_at TIMESTAMPTZ
-- NOT NULL DEFAULT now()`) — the band-6 port landed them as TEXT/BIGINT
-- (migration 0019), a drift no golden could catch while every game_xp
-- writer sat on a pending row. The mining flip's re-homed goldens
-- (goldens/mining/sweep_fastmine + sweep_chop + sweep_explore) pin the
-- shipped rows byte-for-byte (`day`/`updated_at` normalize to `<ts>` —
-- parity/harness/dbsnap.py normalizes date/datetime cells only), so the
-- columns go to the shipped types here. Values convert losslessly
-- (day was written as 'YYYY-MM-DD' text, updated_at as epoch seconds).
ALTER TABLE game_xp
    ALTER COLUMN day TYPE DATE USING day::date;
ALTER TABLE game_xp
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ
        USING to_timestamp(updated_at);
ALTER TABLE game_xp
    ALTER COLUMN updated_at SET DEFAULT now();
