-- 0009_settings.sql — band 1 (settings subsystem): the scalar KV store and
-- the binding route-truth table (design-spec §4.1/§4.2/§4.5).
--
-- settings: the canonical persisted key vocabulary (compat item 5 — the
-- shipped utils.settings_keys strings, verbatim). guild_id = 0 is the
-- global row (COALESCE precedent, S10). Values are stored as text, exactly
-- like the shipped KV table; typing/coercion lives in the SettingSpec.
CREATE TABLE IF NOT EXISTS settings (
    guild_id    BIGINT      NOT NULL DEFAULT 0,
    key         TEXT        NOT NULL,
    value       TEXT        NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_id, key)
);

-- subsystem_bindings: the ONLY route-truth for Discord-pointer config
-- (§4.5 decision 3). slot supports multiplicity>1 bindings (0-based).
CREATE TABLE IF NOT EXISTS subsystem_bindings (
    guild_id    BIGINT      NOT NULL,
    subsystem   TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    slot        INTEGER     NOT NULL DEFAULT 0,
    kind        TEXT        NOT NULL,
    resource_id BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_id, subsystem, name, slot)
);

CREATE INDEX IF NOT EXISTS idx_subsystem_bindings_guild
    ON subsystem_bindings (guild_id, subsystem);
