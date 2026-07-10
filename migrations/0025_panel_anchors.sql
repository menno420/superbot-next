-- 0025: panel anchors — the shipped panel-message registry (help port PR;
-- goldens pin the row shape: parity/goldens/help/help_panel_open.json).
-- The old bot recorded every channel-sent panel message here so live-update
-- refresh and stale-marking could find it later; ephemeral interaction
-- responses are never anchored (no editable channel message exists).
-- Column set is the shipped shape, verbatim: the golden db_delta carries
-- exactly these nine columns.

CREATE TABLE IF NOT EXISTS panel_anchors (
    anchor_id       UUID        PRIMARY KEY,
    guild_id        BIGINT      NOT NULL,
    channel_id      BIGINT      NOT NULL,
    message_id      BIGINT      NOT NULL,
    subsystem       TEXT        NOT NULL,
    user_id         BIGINT,
    is_stale        BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_panel_anchors_guild_subsystem
    ON panel_anchors (guild_id, subsystem);

CREATE UNIQUE INDEX IF NOT EXISTS idx_panel_anchors_message
    ON panel_anchors (channel_id, message_id);
