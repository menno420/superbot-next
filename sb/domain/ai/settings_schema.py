"""The declared ai.* settings schema (band 7) — the shipped
AI_CONFIG_SCHEMA (cogs/ai/schemas.py @7f7628e1) as SettingSpec/BindingSpec
facets. Lives in the DOMAIN (not the manifest module) so the settings
panel can read the shipped roster without a manifest↔panels import cycle;
``sb/manifest/ai.py`` declares exactly these facets.
"""

from __future__ import annotations

from sb.spec.settings import Activation, BindingKind, BindingSpec, SettingSpec

__all__ = ["AI_SETTINGS_FACETS", "SHIPPED_SCHEMA_SETTINGS"]

_CAPABILITY = "ai.settings.configure"


def _bool_setting(name: str, key: str, default: bool, hint: str) -> SettingSpec:
    return SettingSpec(name=name, value_type=bool, default=default,
                       settings_key=key, hint=hint,
                       capability_required=_CAPABILITY,
                       activation=Activation.OFF_UNTIL_OPT_IN)


#: the shipped AI_CONFIG_SCHEMA scalars VERBATIM (names, keys, value types,
#: DEFAULTS, declaration order) — the `!ai settings` page renders exactly
#: this roster with these defaults (goldens/ai/sweep_ai_settings pins every
#: byte: default='deterministic', min level 2, cooldown 30, allowance 1).
SHIPPED_SCHEMA_SETTINGS: tuple[SettingSpec, ...] = (
    _bool_setting("enabled", "ai_enabled", False,
                  "Master switch for the AI platform in this server."),
    _bool_setting("natural_language_enabled", "ai_natural_language_enabled",
                  False,
                  "Allow the bot to answer natural-language mentions."),
    SettingSpec(name="default_provider", value_type=str,
                default="deterministic",
                settings_key="ai_default_provider",
                capability_required=_CAPABILITY,
                hint="Default provider used by AI tasks that don't specify "
                     "their own ('deterministic' keeps responses local).",
                allowed_values=("deterministic", "openai", "anthropic")),
    SettingSpec(name="default_model", value_type=str, default="",
                settings_key="ai_default_model",
                capability_required=_CAPABILITY,
                hint="Per-server model overlay (must match the provider "
                     "family; empty = routing default)."),
    SettingSpec(name="minimum_level_default", value_type=int, default=2,
                settings_key="ai_minimum_level_default",
                capability_required=_CAPABILITY,
                hint="Minimum member level for NL replies.",
                bounds=(0, 1000)),
    SettingSpec(name="cooldown_seconds", value_type=int, default=30,
                settings_key="ai_cooldown_seconds",
                capability_required=_CAPABILITY,
                hint="Per-user NL reply cooldown in seconds (0 = none).",
                bounds=(0, 86400)),
    SettingSpec(name="fresh_user_mention_allowance", value_type=int,
                default=1,
                settings_key="ai_fresh_user_mention_allowance",
                capability_required=_CAPABILITY,
                hint="Replies a below-level user may still get by "
                     "mentioning the bot (spent per delivered reply).",
                bounds=(0, 100)),
    SettingSpec(name="guild_instruction_profile", value_type=str,
                default="",
                settings_key="ai_guild_instruction_profile",
                capability_required=_CAPABILITY,
                hint="Named instruction/orchestration profile key for "
                     "this server (empty = compatible default)."),
    SettingSpec(name="memory_window_minutes", value_type=int, default=0,
                settings_key="ai_memory_window_minutes",
                capability_required=_CAPABILITY,
                hint="Conversation-memory window (0/15/30/60/120; 0 = "
                     "floor-only memory).",
                allowed_values=(0, 15, 30, 60, 120)),
    _bool_setting("memory_channel_scan_enabled",
                  "ai_memory_channel_scan_enabled", False,
                  "Seed memory from recent channel history on a cold "
                  "buffer (bodies are never persisted)."),
)

#: everything the manifest declares: the shipped schema roster PLUS
#: ai_review_channel (a shipped KV key OUTSIDE the subsystem schema —
#: utils/settings_keys.ai carried it, cogs/ai/schemas.py did not; the
#: `!aireview channel/off` lane wrote it directly and the settings page
#: never listed it: goldens/ai/sweep_ai_settings renders 10 scalars,
#: goldens/_unmapped/sweep_aireview_off carries the KV write. Declared
#: because §4.1 bans raw-KV reads — but excluded from the shipped page
#: roster) PLUS the shipped audit_log_channel binding.
AI_SETTINGS_FACETS: tuple[object, ...] = SHIPPED_SCHEMA_SETTINGS + (
    SettingSpec(name="review_channel", value_type=int, default=0,
                settings_key="ai_review_channel",
                capability_required=_CAPABILITY,
                hint="Channel the AI answer-review feed posts to "
                     "(0 = off).",
                input_hint="channel"),
    # the shipped audit_log_channel binding (cogs/ai/schemas.py
    # AI_BINDINGS, verbatim shape) — the settings page's Bindings row
    # (goldens/ai/sweep_ai_settings pins the line).
    BindingSpec(name="audit_log_channel", kind=BindingKind.CHANNEL,
                required=False,
                hint="Channel where AI Platform writes audit entries "
                     "(policy changes, denials, kill-switch flips, "
                     "decision-audit summaries).",
                capability_required=_CAPABILITY),
)
