-- 0030_ai_instruction_profile.sql — the shipped instruction-profile
-- CATALOG (band 7, the behavior-preset slice — D-0071): the FK target
-- migration 0028 deliberately carried as "a plain nullable column (no FK
-- target yet)".
--
-- ORACLE shapes, NAME_STABLE (reconstructed via search_code fragments —
-- full-file oracle reads stay denied):
--   * disbot migrations/039_ai_policy.sql — the ai_instruction_profile
--     CREATE (id/guild_id/name/body/scope/feature_key/created_at/
--     created_by/updated_at + UNIQUE (guild_id, scope, name));
--   * disbot migrations/043_ai_instruction_profile_preset.sql — the
--     is_preset flag (folded into the CREATE here: a fresh chain needs no
--     two-step ALTER);
--   * disbot migrations/044_ai_instruction_profile_seed.sql — the SEVEN
--     system preset rows VERBATIM (guild_id IS NULL, scope='system',
--     is_preset=TRUE). The oracle seeded with ON CONFLICT … DO UPDATE for
--     re-run idempotency; the K3 runner applies a migration exactly once,
--     so a plain INSERT lands the identical state.
--
-- The 0028 override tables' instruction_profile_id columns gain the
-- shipped FK (039: REFERENCES ai_instruction_profile(id) ON DELETE SET
-- NULL). Guild-authored profiles (the oracle ai_instruction_mutation
-- surface) are NOT this slice — every row here is the system seed.

CREATE TABLE IF NOT EXISTS ai_instruction_profile (
    id              BIGSERIAL PRIMARY KEY,
    guild_id        BIGINT  NULL,
    name            TEXT    NOT NULL,
    body            TEXT    NOT NULL,
    scope           TEXT    NOT NULL
        CHECK (scope IN ('guild', 'channel', 'category', 'feature', 'system')),
    feature_key     TEXT    NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      BIGINT  NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_preset       BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (guild_id, scope, name)
);

ALTER TABLE ai_channel_policy
    ADD CONSTRAINT ai_channel_policy_instruction_profile_fk
    FOREIGN KEY (instruction_profile_id)
    REFERENCES ai_instruction_profile(id) ON DELETE SET NULL;

ALTER TABLE ai_category_policy
    ADD CONSTRAINT ai_category_policy_instruction_profile_fk
    FOREIGN KEY (instruction_profile_id)
    REFERENCES ai_instruction_profile(id) ON DELETE SET NULL;

-- The seven shipped system presets (oracle migration 044, bodies verbatim).

INSERT INTO ai_instruction_profile
    (guild_id, name, body, scope, feature_key, is_preset, created_at, updated_at)
VALUES
    (NULL, 'disabled',
     'AI replies are disabled. The assistant does not respond to natural-language messages in this scope.',
     'system', NULL, TRUE, NOW(), NOW()),
    (NULL, 'mention_only_helper',
     'Reply only when explicitly mentioned. Keep answers concise, polite, and to the point. Decline gracefully when out of scope.',
     'system', NULL, TRUE, NOW(), NOW()),
    (NULL, 'helpful_channel',
     'Engage helpfully in natural-language messages within this scope. Answer questions, surface relevant context, and use the configured natural-language level gate as the only eligibility check.',
     'system', NULL, TRUE, NOW(), NOW()),
    (NULL, 'btd6_focused',
     'Prioritise BTD6 grounding. When a message resolves to a BTD6 intent, cite the grounding facts. Defer to the BTD6 response builder before composing free-form text.',
     'system', NULL, TRUE, NOW(), NOW()),
    (NULL, 'quiet_btd6_focused',
     'Reply only when explicitly mentioned. Prefer BTD6 grounding for resolved intents; for other messages, decline gracefully.',
     'system', NULL, TRUE, NOW(), NOW()),
    (NULL, 'staff_diagnostics',
     'Operator-facing diagnostics scope. Surface audit-quality detail (route, provider, model, policy_snapshot_hash) when asked about the assistant. Intended for channels gated by a staff role policy.',
     'system', NULL, TRUE, NOW(), NOW()),
    (NULL, 'support_triage',
     'Neutral, factual triage style for support contexts. Avoid speculation; cite recent audit context when relevant. Used by the PR-H draft surface.',
     'system', NULL, TRUE, NOW(), NOW());
