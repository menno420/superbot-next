"""Band-1 K10 seam installs (the progress-log band map): the REAL readers
behind sb.kernel.ai's installable ports, backed by DECLARED ai.* settings
through THE K7 resolve seam (§4.1 one declaration path).

The ai.* SettingSpec declarations themselves belong to the `ai` manifest
(band 7 owns that subsystem's keys — the shipped `utils.settings_keys.ai`
vocabulary is carried in sb/domain/settings/keys.py). Until band 7 declares
them, every read falls back CLOSED (LookupError -> safe default: AI off,
window 0) — the reader seams are band 1's deliverable, not the ai data.

v1 scope (D-0025): the shipped typed `ai_guild_policy` +
channel/category/role policy + instruction-profile TABLES are settings-band
data (K10 D-0022 note) but port in a band-1 follow-up slice — this module
serves the guild-level policy from the declared KV settings (one of the
shipped truth sources, §4.3), with empty channel/category/role overlays and
a None profile body. The reader seams are the contract; widening them to
the typed tables changes no caller.
"""

from __future__ import annotations

import logging

from sb.kernel import settings as ksettings

logger = logging.getLogger("sb.domain.settings.ai_readers")

__all__ = ["install_ai_readers"]

_SUBSYSTEM = "ai"


async def _resolve(guild_id: int, name: str, fallback: object) -> object:
    try:
        value = await ksettings.resolve(guild_id, _SUBSYSTEM, name)
    except LookupError:
        return fallback
    return fallback if value is None else value


def _to_int(value: object, fallback: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback


def _to_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("1", "true", "yes", "on"):
        return True
    if token in ("0", "false", "no", "off"):
        return False
    return fallback


async def _policy_bundle(guild_id: int):
    from sb.kernel.ai.policy import PolicyBundle

    enabled = _to_bool(await _resolve(guild_id, "enabled", False), False)
    nl = _to_bool(await _resolve(guild_id, "natural_language_enabled", False), False)
    policy = {
        "enabled": enabled,
        "natural_language_enabled": nl,
        "minimum_level_default": _to_int(
            await _resolve(guild_id, "minimum_level_default", 0), 0),
        "cooldown_seconds": _to_int(
            await _resolve(guild_id, "cooldown_seconds", 60), 60),
        "guild_instruction_profile_id": await _resolve(
            guild_id, "guild_instruction_profile", None) or None,
        "fresh_user_mention_allowance": _to_int(
            await _resolve(guild_id, "fresh_user_mention_allowance", 0), 0),
        "generation": 0,
    }
    # channel/category/role overlays ride the typed-table follow-up slice.
    return PolicyBundle(policy=policy, channel={}, category={}, role={})


async def _memory_settings(guild_id: int) -> tuple[int, bool]:
    window = _to_int(await _resolve(guild_id, "memory_window_minutes", 0), 0)
    scan = _to_bool(await _resolve(guild_id, "memory_channel_scan_enabled", False), False)
    return window, scan


async def _profile_key(guild_id: int, channel_id: int,
                       category_id: int | None):
    # (channel_key, category_key, guild_key) — channel/category overlays
    # arrive with the typed-table slice; the guild-level key serves now.
    guild_key = await _resolve(guild_id, "guild_instruction_profile", None)
    return None, None, (str(guild_key) if guild_key else None)


async def _profile_body(profile_id: int):
    # Instruction-profile BODIES live in the typed-table follow-up slice.
    return None


def install_ai_readers() -> None:
    """Composition-root wiring (after install_ai_config): band 1's four
    K10 reader installs."""
    from sb.kernel.ai import instructions, memory, orchestration, policy

    policy.install_policy_bundle_reader(_policy_bundle)
    memory.install_memory_settings_reader(_memory_settings)
    orchestration.install_profile_key_reader(_profile_key)
    instructions.install_profile_reader(_profile_body)
