"""The shipped ``utils.settings_keys`` vocabulary, harvested VERBATIM from
the frozen oracle (menno420/superbot @ 7f7628e1, disbot/utils/settings_keys/
— 17 modules, 124 constants).

These key strings are the CANONICAL PERSISTED VOCABULARY (design-spec §4.5
rule 5 / compat item 5): the `settings` table row keys stay these exact
strings across the cutover import. The constant->string map is data here;
each owning subsystem's manifest claims its slice via
``SettingSpec.settings_key`` / ``SettingSpec.legacy_keys`` /
``BindingSpec.legacy_settings_key_aliases`` as its band ports (the 17
modules "collapse into the manifests" — this module is the collapse's
single verbatim source, and the completeness oracle for the CI check that
every key observed in the production dump has exactly one owning spec).

NOTE the four non-key constants in the logging module (DEFAULT_*_NAME are
channel-NAME defaults, not KV keys) are carried verbatim too — the logging
band decides their new home; dropping them here would lose the vocabulary.
"""

from __future__ import annotations

#: module-of-origin -> {CONSTANT_NAME: persisted key string} (verbatim)
LEGACY_SETTINGS_KEYS: dict[str, dict[str, str]] = {
    "ai": {
        "AI_ENABLED": "ai_enabled",
        "AI_NATURAL_LANGUAGE_ENABLED": "ai_natural_language_enabled",
        "AI_DEFAULT_PROVIDER": "ai_default_provider",
        "AI_DEFAULT_MODEL": "ai_default_model",
        "AI_MINIMUM_LEVEL_DEFAULT": "ai_minimum_level_default",
        "AI_COOLDOWN_SECONDS": "ai_cooldown_seconds",
        "AI_FRESH_USER_MENTION_ALLOWANCE": "ai_fresh_user_mention_allowance",
        "AI_GUILD_INSTRUCTION_PROFILE": "ai_guild_instruction_profile",
        "AI_MEMORY_WINDOW_MINUTES": "ai_memory_window_minutes",
        "AI_MEMORY_CHANNEL_SCAN_ENABLED": "ai_memory_channel_scan_enabled",
        "AI_REVIEW_CHANNEL": "ai_review_channel",
    },
    "automod": {
        "AUTOMOD_ENABLED": "automod_enabled",
        "AUTOMOD_SPAM_ENABLED": "automod_spam_enabled",
        "AUTOMOD_INVITES_ENABLED": "automod_invites_enabled",
        "AUTOMOD_CAPS_ENABLED": "automod_caps_enabled",
        "AUTOMOD_MENTIONS_ENABLED": "automod_mentions_enabled",
        "AUTOMOD_CROSS_CHANNEL_SPAM_ENABLED": "automod_cross_channel_spam_enabled",
        "AUTOMOD_DUPLICATE_ENABLED": "automod_duplicate_enabled",
        "AUTOMOD_SPAM_COUNT": "automod_spam_count",
        "AUTOMOD_SPAM_WINDOW_SECONDS": "automod_spam_window_seconds",
        "AUTOMOD_CAPS_PERCENT": "automod_caps_percent",
        "AUTOMOD_MENTIONS_COUNT": "automod_mentions_count",
        "AUTOMOD_CROSS_CHANNEL_SPAM_COUNT": "automod_cross_channel_spam_count",
        "AUTOMOD_DUPLICATE_COUNT": "automod_duplicate_count",
        "AUTOMOD_EXEMPT_ROLES": "automod_exempt_roles",
        "AUTOMOD_EXEMPT_CHANNELS": "automod_exempt_channels",
    },
    "btd6": {
        "BTD6_STRATEGY_SUBMISSION_CHANNEL": "btd6_strategy_submission_channel",
        "BTD6_CT_GROUP_ID": "btd6_ct_group_id",
        "BTD6_VERSION_ANNOUNCEMENT_CHANNEL": "btd6_version_announcement_channel",
    },
    "btd6_cache": {
        "BTD6_CACHE_DEFAULT_INTERVAL_SECONDS": "btd6_cache_default_interval_seconds",
        "BTD6_CACHE_CIRCUIT_BREAKER_THRESHOLD": "btd6_cache_circuit_breaker_threshold",
        "BTD6_CACHE_FRESHNESS_WARNING_HOURS": "btd6_cache_freshness_warning_hours",
    },
    "cleanup": {
        "CLEANUP_SPAM_WINDOW_SECONDS": "cleanup_spam_window_seconds",
    },
    "counters": {
        "COUNTERS_ENABLED": "counters_enabled",
        "COUNTERS_TOTAL_CHANNEL": "counters_total_channel",
        "COUNTERS_HUMANS_CHANNEL": "counters_humans_channel",
        "COUNTERS_BOTS_CHANNEL": "counters_bots_channel",
        "COUNTERS_TOTAL_TEMPLATE": "counters_total_template",
        "COUNTERS_HUMANS_TEMPLATE": "counters_humans_template",
        "COUNTERS_BOTS_TEMPLATE": "counters_bots_template",
    },
    "economy": {
        "ECONOMY_LOG_CHANNEL": "economy_log_channel",
    },
    "games": {
        "ACTIVE_TOURNAMENT": "active_tournament",
        "RPS_DEFAULT_ENTRY_FEE": "rps_default_entry_fee",
        "BLACKJACK_DEFAULT_ENTRY_FEE": "blackjack_default_entry_fee",
        "DEATHMATCH_TURN_TIMEOUT": "deathmatch_turn_timeout",
    },
    "governance": {
        "GOVERNANCE_VERSION": "governance_version",
        "TRUSTED_TIER_ROLE_ID": "trusted_tier_role_id",
        "MODERATOR_TIER_ROLE_ID": "moderator_tier_role_id",
    },
    "image_moderation": {
        "IMAGE_MODERATION_ENABLED": "image_moderation_enabled",
        "IMAGE_MODERATION_SEXUAL_ENABLED": "image_moderation_sexual_enabled",
        "IMAGE_MODERATION_VIOLENCE_ENABLED": "image_moderation_violence_enabled",
        "IMAGE_MODERATION_HARASSMENT_ENABLED": "image_moderation_harassment_enabled",
        "IMAGE_MODERATION_HATE_ENABLED": "image_moderation_hate_enabled",
        "IMAGE_MODERATION_THRESHOLD_PERCENT": "image_moderation_threshold_percent",
        "IMAGE_MODERATION_EXEMPT_ROLES": "image_moderation_exempt_roles",
        "IMAGE_MODERATION_EXEMPT_CHANNELS": "image_moderation_exempt_channels",
    },
    "karma": {
        "KARMA_ENABLED": "karma_enabled",
        "KARMA_COOLDOWN": "karma_cooldown",
        "KARMA_DAILY_CAP": "karma_daily_cap",
        "KARMA_REACTION_EMOJI": "karma_reaction_emoji",
    },
    "logging": {
        "LOGGING_ENABLED": "logging_enabled",
        "LOGGING_MOD_CHANNEL": "logging_mod_channel",
        "LOGGING_CLEANUP_CHANNEL": "logging_cleanup_channel",
        "LOGGING_AUTO_CREATE_CHANNELS": "logging_auto_create_channels",
        "DEFAULT_MOD_CHANNEL_NAME": "bot-mod-log",
        "DEFAULT_CLEANUP_CHANNEL_NAME": "bot-cleanup-log",
        "LOGGING_MESSAGES_ENABLED": "logging_messages_enabled",
        "LOGGING_MEMBERS_ENABLED": "logging_members_enabled",
        "LOGGING_ROLES_ENABLED": "logging_roles_enabled",
        "LOGGING_MODERATION_ENABLED": "logging_moderation_enabled",
        "LOGGING_CHANNELS_ENABLED": "logging_channels_enabled",
        "LOGGING_SERVER_ENABLED": "logging_server_enabled",
        "LOGGING_VOICE_ENABLED": "logging_voice_enabled",
        "LOGGING_EVENT_ROUTING": "logging_event_routing",
        "LOGGING_IGNORED_CHANNELS": "logging_ignored_channels",
        "LOGGING_IGNORED_USERS": "logging_ignored_users",
        "DEFAULT_EVENTS_CHANNEL_NAME": "bot-event-log",
        "DEFAULT_MESSAGE_LOG_CHANNEL_NAME": "bot-message-log",
        "DEFAULT_MEMBER_LOG_CHANNEL_NAME": "bot-member-log",
        "DEFAULT_ROLE_LOG_CHANNEL_NAME": "bot-role-log",
    },
    "moderation": {
        "WARN_THRESHOLD": "warn_threshold",
        "WARN_TIMEOUT_MINS": "warn_timeout_minutes",
        "MOD_DM_ON_ACTION": "moderation_dm_on_action",
        "MOD_DM_ACTIONS": "moderation_dm_actions",
        "MOD_DM_TEMPLATE": "moderation_dm_template",
        "MOD_REQUIRE_REASON": "moderation_require_reason",
        "MOD_BAN_DELETE_MESSAGE_DAYS": "moderation_ban_delete_message_days",
        "MOD_MAX_TIMEOUT_MINUTES": "moderation_max_timeout_minutes",
        "MOD_WARN_ESCALATION_ACTION": "moderation_warn_escalation_action",
        "MOD_POST_ACTION_CLEANUP": "moderation_post_action_cleanup",
        "MOD_POST_ACTION_CLEANUP_LIMIT": "moderation_post_action_cleanup_limit",
        "MOD_PUBLIC_LOG_CHANNEL": "moderation_public_log_channel",
        "MOD_PUBLIC_LOG_ACTIONS": "moderation_public_log_actions",
    },
    "role": {
        "SKIP_ROLES": "skip_roles",
        "TIME_ROLES_STACK": "time_roles_stack",
        "XP_ROLES_STACK": "xp_roles_stack",
        "REACTION_ROLES_ENABLED": "reaction_roles_enabled",
    },
    "security": {
        "SECURITY_ENABLED": "security_enabled",
        "SECURITY_RAID_ENABLED": "security_raid_enabled",
        "SECURITY_RAID_JOIN_COUNT": "security_raid_join_count",
        "SECURITY_RAID_WINDOW_SECONDS": "security_raid_window_seconds",
        "SECURITY_RAID_SLOWMODE_SECONDS": "security_raid_slowmode_seconds",
        "SECURITY_RAID_LOCKDOWN_SECONDS": "security_raid_lockdown_seconds",
        "SECURITY_RAID_SLOWMODE_CHANNEL": "security_raid_slowmode_channel",
        "SECURITY_AGE_ENABLED": "security_age_enabled",
        "SECURITY_AGE_MIN_DAYS": "security_age_min_days",
        "SECURITY_AGE_ACTION": "security_age_action",
        "SECURITY_ALERT_CHANNEL": "security_alert_channel",
    },
    "welcome": {
        "WELCOME_ENABLED": "welcome_enabled",
        "WELCOME_JOIN_ENABLED": "welcome_join_enabled",
        "WELCOME_LEAVE_ENABLED": "welcome_leave_enabled",
        "WELCOME_CHANNEL": "welcome_channel",
        "WELCOME_JOIN_MESSAGE": "welcome_join_message",
        "WELCOME_LEAVE_MESSAGE": "welcome_leave_message",
        "WELCOME_ENTRY_ROLE": "welcome_entry_role",
        "WELCOME_DM_ENABLED": "welcome_dm_enabled",
        "WELCOME_DM_MESSAGE": "welcome_dm_message",
        "WELCOME_CARD_ENABLED": "welcome_card_enabled",
        "WELCOME_MIN_ACCOUNT_AGE_DAYS": "welcome_min_account_age_days",
        "WELCOME_DELETE_AFTER_SECONDS": "welcome_delete_after_seconds",
    },
    "xp": {
        "XP_MIN": "xp_min",
        "XP_MAX": "xp_max",
        "XP_COOLDOWN": "xp_cooldown",
        "XP_ANNOUNCE_CHANNEL": "xp_announce_channel",
    },
}


#: every persisted key string (flat, sorted) — the orphan-audit denominator
ALL_LEGACY_KEYS: tuple[str, ...] = tuple(sorted(
    key
    for module_keys in LEGACY_SETTINGS_KEYS.values()
    for key in module_keys.values()
))


def owning_module(key: str) -> str | None:
    """The settings_keys module that minted a persisted key (None = not a
    shipped key — a net-new declaration)."""
    for module, keys in LEGACY_SETTINGS_KEYS.items():
        if key in keys.values():
            return module
    return None

