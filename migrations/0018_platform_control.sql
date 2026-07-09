-- 0018: PLATFORM-CONTROL stores (band 5) — the command-access policy
-- (old migration 050, the K8 admission resolver's DB truth), and the
-- proof-channel timed-lock recovery rows (old migration 104, bug #8).

CREATE TABLE IF NOT EXISTS guild_command_access_policy (
    guild_id   BIGINT       PRIMARY KEY,
    mode       TEXT         NOT NULL,
    updated_by BIGINT,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (mode IN ('all_channels', 'selected_channels',
                    'disabled_except_bootstrap'))
);

CREATE TABLE IF NOT EXISTS guild_command_access_channels (
    guild_id   BIGINT       NOT NULL
        REFERENCES guild_command_access_policy(guild_id) ON DELETE CASCADE,
    channel_id BIGINT       NOT NULL,
    created_by BIGINT,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS proof_channel_locks (
    guild_id   BIGINT      NOT NULL,
    channel_id BIGINT      NOT NULL,
    winner_id  BIGINT      NOT NULL,
    unlock_at  TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, channel_id)
);

CREATE INDEX IF NOT EXISTS idx_proof_channel_locks_unlock_at
    ON proof_channel_locks (unlock_at);
