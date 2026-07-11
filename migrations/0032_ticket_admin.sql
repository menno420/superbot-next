-- 0032: ticket_config + ticket_blacklist — the shipped ticket admin
-- tables (old repo disbot/migrations/098_tickets.sql, imported
-- NAME_STABLE; DDL reconstructed fragment-by-fragment via search_code).
-- Consumers: the `!ticketlimit` config upsert (ticket.set_limit) and the
-- `!ticketblacklist add|remove` pair (ticket.blacklist_add/_remove) —
-- goldens/ticket/sweep_ticketlimit + sweep_ticketblacklist_add pin the
-- row shapes byte-for-byte. The oracle's third table (`tickets`, one row
-- per open/closed ticket) is NOT minted here: no golden touches it — it
-- lands with the channel-provisioning open-flow slice (the trap-15b
-- "declare only what the slice fully carries" rule).
CREATE TABLE IF NOT EXISTS ticket_config (
    guild_id           BIGINT  NOT NULL PRIMARY KEY,
    -- whether the subsystem is active in this guild (panel button + AI
    -- tool + `!ticket new` all refuse to open when false) — shipped
    -- default TRUE (098_tickets.sql verbatim).
    enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    -- the role granted view access to every ticket channel; NULL until setup
    staff_role_id      BIGINT,
    -- the category new ticket channels are created under
    category_id        BIGINT,
    log_channel_id     BIGINT,
    panel_channel_id   BIGINT,
    panel_message_id   BIGINT,
    -- max simultaneously-open tickets one member may hold (shipped
    -- default 1; `!ticketlimit` clamps 1-25)
    max_open_per_user  INT     NOT NULL DEFAULT 1,
    -- mention the staff role in a freshly-opened ticket channel
    ping_staff_on_open BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at         BIGINT  NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ticket_blacklist (
    guild_id   BIGINT      NOT NULL,
    user_id    BIGINT      NOT NULL,
    added_by   BIGINT,
    reason     TEXT,
    added_at   BIGINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);
