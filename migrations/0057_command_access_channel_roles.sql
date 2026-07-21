-- 0057: PLATFORM-CONTROL — the D3 access-audit M1 per-channel role-set
-- store (D-0095: access granularity is M1 per-channel; per-command
-- deferred). Persists the OPTIONAL per-channel role-set constraint the K6
-- resolver already enforces (channel_access.py's channel_role_sets /
-- role_not_held gate, live since S9) but that had no DB truth — so the
-- snapshot's channel_role_sets always arrived as the default empty map.
--
-- A channel with one or more rows here admits only actors holding one of
-- the listed roles (usable under ANY AccessMode; NOT a 4th mode). Absence
-- of rows for a channel = unconstrained. Sole writer:
-- sb/domain/platform/command_access.py
-- (platform.record_set_channel_roles — atomic DELETE+re-INSERT per
-- (guild_id, channel_id)). FK CASCADE mirrors the 0018 channel allowlist:
-- the role-set rows die with the guild's policy row. Forward-only,
-- additive, idempotent.

CREATE TABLE IF NOT EXISTS guild_command_access_channel_roles (
    guild_id   BIGINT       NOT NULL
        REFERENCES guild_command_access_policy(guild_id) ON DELETE CASCADE,
    channel_id BIGINT       NOT NULL,
    role_id    BIGINT       NOT NULL,
    created_by BIGINT,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, channel_id, role_id)
);
