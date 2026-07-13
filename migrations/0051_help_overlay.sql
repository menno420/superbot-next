-- 0051: guild Help presentation overlay (the D-0026 named-successor
-- lane — oracle disbot/migrations/064_help_overlay.sql, imported
-- NAME_STABLE; the Q-0059 home-message columns of oracle 067 ride the
-- home-builder successor slice).
--
-- Guild-scoped, presentation-only deviations from the Help defaults: a
-- hub (category) or subsystem row may be display-hidden, renamed, or
-- re-described **in Help surfaces only** (owner decisions Q-0055
-- hiding=display-only · Q-0056 names=Help-only · Q-0058 admin views
-- show custom+default+key). Execution stays governed by command access
-- / governance — nothing here is consulted by any admission path, and
-- per-scope subsystem visibility remains governance's tables (this
-- table must never grow policy fields).
--
-- Absence = inherit the registry default. A row exists only while at
-- least one override field is non-NULL (the audited mutation lane
-- deletes a row that becomes all-NULL — "store only deviations").
-- Full reset = delete the guild's rows.
--
-- entity_kind has a CHECK because the valid kinds are a *schema*
-- contract the projection joins on, not a service-tunable list;
-- widening it (a future 'home' entity for the Q-0059 builder, or
-- 'command' rows) is a deliberate later migration.
--
-- Field bounds match the tightest Discord surface that renders them
-- (select option label/description caps = 100); the mutation lane
-- enforces the same bounds before the write so the CHECK is the
-- backstop, not the UX.
--
-- Sole writer: sb/domain/help/overlay_ops.py (the audited K7 lanes)
-- through the help.overlay_store engine. Forward-only, additive,
-- idempotent.
CREATE TABLE IF NOT EXISTS help_overlay (
    guild_id       BIGINT      NOT NULL,
    entity_kind    TEXT        NOT NULL CHECK (entity_kind IN ('hub', 'subsystem')),
    entity_key     TEXT        NOT NULL,
    display_hidden BOOLEAN     NULL,
    display_name   TEXT        NULL CHECK (char_length(display_name) BETWEEN 1 AND 100),
    description    TEXT        NULL CHECK (char_length(description) BETWEEN 1 AND 100),
    updated_by     BIGINT      NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (guild_id, entity_kind, entity_key)
);
