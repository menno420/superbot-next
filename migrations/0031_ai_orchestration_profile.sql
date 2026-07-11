-- 0031_ai_orchestration_profile.sql — the tool-orchestration profile
-- columns (band 7, the orchestration-mutation slice — the D-0070 parked
-- tools profile pickers): the shipped migration 062 shape
-- (disbot migrations/062_ai_orchestration_profile.sql) NAME_STABLE on the
-- two typed override tables 0028 landed. The shipped ai_guild_policy
-- column ports as a `guild_settings` KV row (`ai_orchestration_profile`
-- — sb/domain/ai/policy_store.py, the D-0025 KV guild-policy port; the
-- ai_policy_generation precedent), so only channel/category carry a
-- typed column here.
--
-- Intentionally NO CHECK constraint on the value (the shipped 062
-- comment verbatim): the set of valid profile keys lives in the service
-- layer (sb/kernel/ai/orchestration.py's registered profiles), validated
-- by the audited ai.set_*_orchestration seam, so adding a preset never
-- needs a migration + CHECK bump.
--
-- Additive, nullable, idempotent (ADD COLUMN IF NOT EXISTS) — NULL means
-- "no override at this scope" (inherit the next layer).

ALTER TABLE ai_channel_policy
    ADD COLUMN IF NOT EXISTS orchestration_profile TEXT NULL;

ALTER TABLE ai_category_policy
    ADD COLUMN IF NOT EXISTS orchestration_profile TEXT NULL;
