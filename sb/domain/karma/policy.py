"""Karma policy — the config read model (services/karma_config.py
verbatim defaults) over the band-1 settings seam.

The canonical default constants are the single source of truth shared by
the manifest SettingSpecs and :func:`load_policy`'s fallbacks (the
shipped no-drift invariant, pinned by the band-4 tests).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_COOLDOWN_SECONDS",
    "DEFAULT_DAILY_CAP",
    "DEFAULT_ENABLED",
    "DEFAULT_REACTION_EMOJI",
    "MAX_COOLDOWN_SECONDS",
    "MAX_DAILY_CAP",
    "MAX_REACTION_EMOJI_LEN",
    "MIN_COOLDOWN_SECONDS",
    "MIN_DAILY_CAP",
    "KarmaPolicy",
    "load_policy",
]

DEFAULT_ENABLED = True            # karma is a friendly, opt-out feature

# Per-(giver -> receiver) cooldown (1 hour) — the primary anti-farm guard.
DEFAULT_COOLDOWN_SECONDS = 3600
MIN_COOLDOWN_SECONDS = 0
MAX_COOLDOWN_SECONDS = 604800     # one week

# Per-giver daily cap (rolling 24 h).
DEFAULT_DAILY_CAP = 10
MIN_DAILY_CAP = 1
MAX_DAILY_CAP = 1000

# React-to-thank trigger emoji; empty string = OFF (the safe default).
DEFAULT_REACTION_EMOJI = ""
MAX_REACTION_EMOJI_LEN = 64       # a unicode emoji or a <:name:id> form


@dataclass(frozen=True)
class KarmaPolicy:
    """Resolved karma behaviour for one guild (frozen: cache/compare-safe)."""

    enabled: bool = DEFAULT_ENABLED
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS
    daily_cap: int = DEFAULT_DAILY_CAP
    reaction_emoji: str = DEFAULT_REACTION_EMOJI


async def load_policy(guild_id: int) -> KarmaPolicy:
    """Compose the effective policy via the K7 resolve seam; a missing or
    malformed stored value transparently falls back to the default."""
    from sb.kernel import settings as ksettings

    async def _get(name: str, default):
        try:
            value = await ksettings.resolve(guild_id, "karma", name)
        except LookupError:
            return default
        return value

    enabled = await _get("enabled", DEFAULT_ENABLED)
    cooldown = await _get("cooldown_seconds", DEFAULT_COOLDOWN_SECONDS)
    daily_cap = await _get("daily_cap", DEFAULT_DAILY_CAP)
    emoji = await _get("reaction_emoji", DEFAULT_REACTION_EMOJI)
    try:
        cooldown = int(cooldown)      # type: ignore[arg-type]
    except (TypeError, ValueError):
        cooldown = DEFAULT_COOLDOWN_SECONDS
    try:
        daily_cap = int(daily_cap)    # type: ignore[arg-type]
    except (TypeError, ValueError):
        daily_cap = DEFAULT_DAILY_CAP
    return KarmaPolicy(
        enabled=bool(enabled),
        cooldown_seconds=cooldown,
        daily_cap=daily_cap,
        reaction_emoji=str(emoji or ""),
    )
