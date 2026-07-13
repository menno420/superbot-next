-- 0054: command_routing_policy — per-scope per-cog enable/disable overrides
-- (oracle disbot/migrations/036_command_routing.sql shape @ f969b95; the
-- setup wizard's cog-routing section). The resolver
-- (sb/domain/server_management/routing.is_cog_enabled) walks
-- channel → category → guild → default-true, so absence of any policy row
-- never silently disables a cog (cogs are enabled by default; routing only
-- restricts — an empty table is the production default).
--
-- scope_type   guild / category / channel — mirrors the cleanup_policies
--              scope vocabulary. Threads inherit from their parent channel
--              and do not have their own scope here (oracle 036 comment).
-- scope_id     the category / channel id; NULL when scope_type='guild'.
-- cog_name     stable cog/subsystem key (the staged payload's vocabulary —
--              sb/domain/governance/registry.SUBSYSTEM_META keys, the
--              oracle utils.subsystem_registry names). Free-form TEXT so a
--              new cog needs no enum bump here (oracle posture).
-- enabled      True iff the cog is enabled in this scope.
-- actor_id     operator who set the policy; preserved for audit joins.
--
-- The UNIQUE index uses COALESCE on scope_id because PostgreSQL UNIQUE
-- treats NULL as distinct; without COALESCE every guild-scope row would
-- collide on (guild_id, scope_type, NULL, cog_name).
--
-- Rollback: DROP TABLE IF EXISTS command_routing_policy;  Nothing depends
-- on the data — the resolver returns enabled=True when no row exists.
-- Forward-only and idempotent.

CREATE TABLE IF NOT EXISTS command_routing_policy (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id      BIGINT       NOT NULL,
    scope_type    TEXT         NOT NULL,
    scope_id      BIGINT,
    cog_name      TEXT         NOT NULL,
    enabled       BOOLEAN      NOT NULL,
    actor_id      BIGINT,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (scope_type IN ('guild', 'category', 'channel'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_command_routing_policy_scope
    ON command_routing_policy (
        guild_id,
        scope_type,
        COALESCE(scope_id, -1),
        cog_name
    );

CREATE INDEX IF NOT EXISTS idx_command_routing_policy_guild_cog
    ON command_routing_policy (guild_id, cog_name);
