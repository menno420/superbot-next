-- 0053: wordfilter_config — the per-guild prohibited-word filter "strict"
-- (anti-evasion) opt-in (oracle disbot/migrations/097_wordfilter_strict.sql
-- shape @ 9776401). When ON, a message is also checked against a
-- de-obfuscated view of its text (leet / unicode-confusable / fullwidth /
-- zero-width & invisible-character / spaced-letter evasion). Default: a
-- guild with no row (or strict = FALSE) behaves exactly as today — only the
-- exact \bword\b match runs. Kept as its own table (mirroring
-- prohibited_words, 0011) rather than a settings KV row — the oracle's own
-- posture ("stays clear of the settings-key declaration/mutation
-- invariants and needs no SettingSpec"). Consumer: the words manager's
-- 🛡️ Anti-evasion toggle (sb/domain/cleanup); the message-pipeline
-- anti-evasion PASS stays the automod/message-stage slice's port.
--
-- Rollback: DROP TABLE IF EXISTS wordfilter_config;  Forward-only and
-- idempotent.

CREATE TABLE IF NOT EXISTS wordfilter_config (
    guild_id BIGINT PRIMARY KEY,
    strict   BOOLEAN NOT NULL DEFAULT FALSE
);
