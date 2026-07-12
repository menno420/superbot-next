-- 0039: mining_equipment — which item a player has equipped in each slot
-- (oracle disbot/migrations/060_mining_equipment.sql, imported NAME_STABLE).
-- Direct-lane game state in the oracle, re-homed onto the audited K7 mining
-- write boundary here (sb/domain/mining/ops.py record_equip / record_unequip);
-- the sole writer is the mining.store engine. One row per (user_id, guild_id,
-- slot); user_id is TEXT to match mining_inventory's legacy column type.
--
-- No golden drives an argful !equip (every imported sweep pinned only the bare
-- guard byte, goldens/mining/sweep_equip) — the table is a declared-but-
-- guard-only mining surface (depth.exemptions.mining guard-only-capture).
CREATE TABLE IF NOT EXISTS mining_equipment (
    user_id     TEXT        NOT NULL,
    guild_id    BIGINT      NOT NULL,
    slot        TEXT        NOT NULL,
    item_name   TEXT        NOT NULL,
    equipped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, guild_id, slot)
);
