"""Domain policy-loader stored-value coercion sweep (band-2 subsystems).

Each `load_policy` reads its fields through the K7 `resolve` seam and then
defends against malformed / off-type stored rows: `int()`/`bool()` coercion
with a shipped-default fallback, `str(... or DEFAULT)` empty reverts, and a
mention-token parser. Removing any of those swallows would let a bad KV row
silently ship a WRONG policy — no existing test drives the present-malformed
leg (welcome/automod/counters `load_policy` are untested; moderation pins only
the all-default/`None` path). These tests pin the STORED-value coercion
behavior. Every assertion was verified against a live run of the real function
before commit.
"""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_settings():
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    yield
    ksettings.clear_for_tests()


def _install(subsystem: str, names: tuple[str, ...], store: dict) -> None:
    """Declare `names` under `subsystem` (default None) and install a
    per-guild reader backed by `store` (key ``"subsystem.name"`` -> value)."""
    from sb.kernel import settings as ksettings

    for name in names:
        ksettings.register_setting(
            ksettings.SettingDeclaration(subsystem=subsystem, name=name,
                                         default=None))

    async def reader(guild_id, key):
        if guild_id is not None and key in store:
            return store[key]
        return ksettings.UNSET

    ksettings.install_settings_reader(reader)


_WELCOME_KEYS = (
    "enabled", "join_enabled", "leave_enabled", "dm_enabled",
    "join_message", "leave_message", "dm_message", "delete_after_seconds",
)
_AUTOMOD_KEYS = (
    "enabled", "spam_enabled", "invites_enabled", "caps_enabled",
    "mentions_enabled", "cross_channel_spam_enabled", "duplicate_enabled",
    "spam_count", "spam_window_seconds", "caps_percent", "mentions_count",
    "cross_channel_spam_count", "duplicate_count",
    "exempt_roles", "exempt_channels",
)
_MODERATION_KEYS = (
    "warn_threshold", "warn_timeout_minutes", "warn_escalation_action",
    "dm_on_action", "dm_actions", "dm_template", "require_reason",
    "ban_delete_message_days", "max_timeout_minutes", "post_action_cleanup",
    "post_action_cleanup_limit", "public_log_actions",
)
_COUNTERS_KEYS = ("enabled", "total_template", "humans_template", "bots_template")


# --- welcome -----------------------------------------------------------------------

def test_welcome_load_policy_coerces_malformed_stored_values():
    from sb.domain.welcome import DEFAULT_JOIN_MESSAGE
    from sb.domain.welcome.service import load_policy

    _install("welcome", _WELCOME_KEYS, {
        "welcome.enabled": "garbage",             # unrecognized -> False (NOT fallback)
        "welcome.join_enabled": "nope",           # unrecognized -> False even though fallback True
        "welcome.delete_after_seconds": "not-int",  # int() ValueError -> fallback 0
        "welcome.join_message": "",               # empty -> str("" or DEFAULT) -> DEFAULT
    })

    p = run(load_policy(1))
    # A present bool-typed row that is neither truthy-token nor None resolves to
    # False regardless of the field's fallback (welcome `_as_bool` returns the
    # membership test for present values; fallback is the None-only leg).
    assert p.enabled is False
    assert p.join_enabled is False
    assert p.delete_after_seconds == 0            # malformed int reverts to fallback, not raised
    assert p.join_message == DEFAULT_JOIN_MESSAGE  # empty string reverts to shipped default


def test_welcome_load_policy_coerces_string_and_float_typed_values():
    from sb.domain.welcome.service import load_policy

    _install("welcome", _WELCOME_KEYS, {
        "welcome.enabled": "true",                # truthy token -> True
        "welcome.dm_enabled": True,               # real bool passes through
        "welcome.delete_after_seconds": " 45 ",   # stripped numeric string -> int 45
        "welcome.leave_message": "bye",           # non-empty preserved
    })

    p = run(load_policy(1))
    assert p.enabled is True
    assert p.dm_enabled is True
    assert p.delete_after_seconds == 45 and isinstance(p.delete_after_seconds, int)
    assert p.leave_message == "bye"


def test_welcome_as_int_rejects_float_string_to_fallback():
    """`_as_int` uses `int(str(value))`, so a float value (`3.9`) is NOT
    truncated to 3 — it raises `ValueError` and reverts to the fallback. This
    is the honest behavior of the coercion, not `int(float(...))`."""
    from sb.domain.welcome.service import _as_int

    assert _as_int(3.9, 7) == 7          # float -> "3.9" -> ValueError -> fallback
    assert _as_int(None, 7) == 7         # None  -> "None" -> ValueError -> fallback
    assert _as_int("12", 7) == 12
    assert _as_int(" 8 ", 7) == 8


# --- automod -----------------------------------------------------------------------

def test_automod_load_policy_coerces_malformed_stored_values():
    from sb.domain.automod.engine import load_policy

    _install("automod", _AUTOMOD_KEYS, {
        "automod.enabled": "garbage",       # unrecognized -> fallback False
        "automod.spam_enabled": "yes",      # truthy token -> True
        "automod.spam_count": "not-int",    # int() ValueError -> fallback 5
        "automod.caps_percent": [1, 2],     # int(str([1,2])) ValueError -> fallback 70
    })

    p = run(load_policy(1))
    assert p.enabled is False               # unrecognized token -> the fallback (d)
    assert p.spam_enabled is True
    assert p.spam_count == 5                # shipped default, not the bad string
    assert p.caps_percent == 70


def test_automod_as_bool_unrecognized_returns_fallback():
    """automod `_as_bool` differs from welcome/counters: an unrecognized present
    token returns the fallback `d`, not a hard False."""
    from sb.domain.automod.engine import _as_bool

    assert _as_bool("garbage", True) is True     # unrecognized -> fallback True
    assert _as_bool("garbage", False) is False   # unrecognized -> fallback False
    assert _as_bool("off", True) is False        # explicit false token wins over fallback
    assert _as_bool(True, False) is True         # real bool passes through


def test_automod_ids_parses_mixed_mention_tokens():
    from sb.domain.automod.engine import _ids

    assert _ids("<@&1>,2 ; 3") == frozenset({1, 2, 3})  # role-mention, comma, semicolon
    assert _ids(123) == frozenset({123})                # bare int stringifies then parses
    assert _ids("junk") == frozenset()                  # non-numeric -> dropped
    assert _ids(None) == frozenset()                    # None -> "" -> empty


# --- moderation --------------------------------------------------------------------

def test_moderation_load_policy_coerces_present_malformed_values():
    """The pre-existing moderation test pins only the all-default (`None`) path.
    This pins the present-but-off-type leg: a stored non-int reverts to the
    ModerationPolicy default, a stored non-bool token reverts to its fallback."""
    from sb.domain.moderation.service import ModerationPolicy, load_policy

    d = ModerationPolicy()
    _install("moderation", _MODERATION_KEYS, {
        "moderation.warn_threshold": "not-int",       # -> default 3
        "moderation.max_timeout_minutes": 12.5,        # int(str(12.5)) ValueError -> default
        "moderation.dm_on_action": "garbage",          # unrecognized -> fallback False
        "moderation.require_reason": "yes",            # truthy token -> True
        "moderation.warn_escalation_action": "",       # empty -> str("" or default) -> default
    })

    p = run(load_policy(1))
    assert p.warn_threshold == d.warn_threshold == 3
    assert p.max_timeout_minutes == d.max_timeout_minutes == 40320
    assert p.dm_on_action is False
    assert p.require_reason is True
    assert p.warn_escalation_action == d.warn_escalation_action


# --- counters ----------------------------------------------------------------------

def test_counters_load_policy_reverts_blank_templates_to_shipped_defaults():
    from sb.domain.counters.service import DEFAULT_TEMPLATES, load_policy

    _install("counters", _COUNTERS_KEYS, {
        "counters.enabled": "garbage",         # unrecognized present -> False (no fallback leg)
        "counters.total_template": "",         # blank -> DEFAULT_TEMPLATES['total']
        "counters.humans_template": "   ",     # whitespace-only -> stripped empty -> default
        "counters.bots_template": "Bots={count}",  # non-empty preserved
    })

    p = run(load_policy(1))
    assert p.enabled is False
    assert p.total_template == DEFAULT_TEMPLATES["total"]
    assert p.humans_template == DEFAULT_TEMPLATES["humans"]
    assert p.bots_template == "Bots={count}"


def test_counters_template_for_empty_falls_back_to_default():
    """`CounterPolicy.template_for` reverts an empty stored template to the
    shipped default at read time (`... or DEFAULT_TEMPLATES[kind]`)."""
    from sb.domain.counters.service import CounterPolicy, DEFAULT_TEMPLATES

    policy = CounterPolicy(enabled=True, total_channel_id=None,
                           humans_channel_id=None, bots_channel_id=None,
                           total_template="", humans_template="H={count}",
                           bots_template="")
    assert policy.template_for("total") == DEFAULT_TEMPLATES["total"]
    assert policy.template_for("humans") == "H={count}"
    assert policy.template_for("bots") == DEFAULT_TEMPLATES["bots"]
