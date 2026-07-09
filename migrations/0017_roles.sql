-- 0017: ROLE stores (band 5) — the shipped role-family tables on the
-- fresh chain: role_thresholds (bootstrap shape + old migrations 003/056
-- columns folded in), the legacy reaction_roles emoji surface, the
-- reaction-roles-overhaul tables (078/079/080/081), and the
-- role_automation_exemptions table (052).

CREATE TABLE IF NOT EXISTS role_thresholds (
    guild_id      BIGINT  NOT NULL,
    role_name     TEXT    NOT NULL,
    days_required INTEGER NOT NULL DEFAULT 0,
    level_required INTEGER DEFAULT NULL,          -- old 003: XP auto-assign
    xp_auto_assign BOOLEAN NOT NULL DEFAULT FALSE, -- old 003
    role_id       BIGINT  DEFAULT NULL,           -- old 056: id-first resolve
    display_name  TEXT    DEFAULT NULL,           -- old 056: stale diagnostics
    PRIMARY KEY (guild_id, role_name)
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id   BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    emoji      TEXT   NOT NULL,
    role_id    BIGINT NOT NULL,
    PRIMARY KEY (guild_id, message_id, emoji)
);

CREATE TABLE IF NOT EXISTS reaction_role_message_modes (
    guild_id   BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    mode       TEXT   NOT NULL DEFAULT 'normal',
    PRIMARY KEY (guild_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_reaction_role_modes_guild
    ON reaction_role_message_modes (guild_id);

CREATE TABLE IF NOT EXISTS role_menus (
    menu_id     BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id    BIGINT      NOT NULL,
    channel_id  BIGINT      NOT NULL,
    message_id  BIGINT,
    title       TEXT        NOT NULL DEFAULT 'Pick your roles',
    description TEXT,
    style       TEXT        NOT NULL DEFAULT 'dropdown',
    mode        TEXT        NOT NULL DEFAULT 'normal',
    max_roles   INTEGER     NOT NULL DEFAULT 0,
    theme       TEXT        NOT NULL DEFAULT 'default',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_role_menus_guild ON role_menus (guild_id);
CREATE INDEX IF NOT EXISTS idx_role_menus_message ON role_menus (message_id);

CREATE TABLE IF NOT EXISTS role_menu_options (
    menu_id  BIGINT  NOT NULL REFERENCES role_menus (menu_id) ON DELETE CASCADE,
    role_id  BIGINT  NOT NULL,
    emoji    TEXT,
    label    TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (menu_id, role_id)
);

CREATE TABLE IF NOT EXISTS role_grants (
    grant_id   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id   BIGINT      NOT NULL,
    member_id  BIGINT      NOT NULL,
    role_id    BIGINT      NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    granted_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (guild_id, member_id, role_id)
);
CREATE INDEX IF NOT EXISTS idx_role_grants_expiry ON role_grants (expires_at);
CREATE INDEX IF NOT EXISTS idx_role_grants_guild ON role_grants (guild_id);

CREATE TABLE IF NOT EXISTS role_menu_pickup_stats (
    guild_id       BIGINT      NOT NULL,
    role_id        BIGINT      NOT NULL,
    picked         INTEGER     NOT NULL DEFAULT 0,
    removed        INTEGER     NOT NULL DEFAULT 0,
    last_picked_at TIMESTAMPTZ,
    PRIMARY KEY (guild_id, role_id)
);
CREATE INDEX IF NOT EXISTS idx_role_pickup_stats_guild
    ON role_menu_pickup_stats (guild_id);

CREATE TABLE IF NOT EXISTS role_automation_exemptions (
    guild_id    BIGINT  NOT NULL,
    role_id     BIGINT  NOT NULL,
    exempt_xp   BOOLEAN NOT NULL DEFAULT FALSE,
    exempt_time BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (guild_id, role_id)
);
