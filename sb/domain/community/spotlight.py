"""Community Spotlight core (band 4) — the live server-activity
dashboard's data half (cogs/community_spotlight_cog.py, headless).

The level-up feed is the ``xp.level_up → community_spotlight`` wiring,
now a DECLARED event consumption (the band-4 contract): ``subscribe(bus)``
caches a human-readable blurb per guild in a bounded deque, exactly the
shipped EventBus pattern. Names render as mentions headlessly (the
shipped member_display cache read is live-adapter presentation).
"""

from __future__ import annotations

from collections import deque

__all__ = [
    "levelup_feed",
    "overview_fields",
    "provider_board_text",
    "reset_feed_for_tests",
    "subscribe",
]

MEDALS = ["🥇", "🥈", "🥉"]              # shipped verbatim
_MAX_LEVELUP_ENTRIES = 5

# guild_id -> deque of recent level-up strings, populated via the bus
_levelup_feed: dict[int, deque[str]] = {}


async def _on_level_up(**payload: object) -> None:
    guild_id = int(payload.get("guild_id", 0) or 0)
    user_id = int(payload.get("user_id", 0) or 0)
    new_level = int(payload.get("new_level", 0) or 0)
    entry = f"**<@{user_id}>** reached Level **{new_level}**"
    feed = _levelup_feed.setdefault(guild_id,
                                    deque(maxlen=_MAX_LEVELUP_ENTRIES))
    feed.append(entry)


def subscribe(bus: object) -> None:
    """Arm the feed on THE bus (composition-root / harness obligation —
    the shipped cog_load bus.on(xp.level_up) analog)."""
    bus.on("xp.level_up", _on_level_up)


def levelup_feed(guild_id: int) -> list[str]:
    return list(_levelup_feed.get(guild_id, []))


def reset_feed_for_tests() -> None:
    _levelup_feed.clear()


def _medal(i: int) -> str:
    return MEDALS[i] if i < 3 else f"`#{i + 1}`"


async def overview_fields(
        guild_id: int,
        member_count: int | None = None) -> tuple[tuple[str, str], ...]:
    """The shipped main-embed field set (server at a glance / XP leaders /
    richest / recent level-ups — cogs/community_spotlight_cog.py
    verbatim, incl. the per-field empty states the golden pins:
    XP Leaders → "*No activity yet*", Richest → "*No coins earned yet*").
    ``member_count`` prepends the shipped 👥 line when the caller has a
    guild-directory read (the panel renderer does; a headless caller
    omits it)."""
    from sb.domain.community.rank_providers import get_provider
    from sb.domain.xp.store import get_guild_xp_totals
    from sb.kernel.db.pool import fetchone

    total_xp = await get_guild_xp_totals(guild_id)
    row = await fetchone(
        "SELECT COALESCE(SUM(coins), 0)::bigint AS total "
        "FROM economy_balances WHERE guild_id=$1", (guild_id,))
    total_coins = int(row["total"]) if row else 0

    glance_lines = []
    if member_count is not None:
        glance_lines.append(f"👥 **{member_count:,}** members")
    glance_lines += [f"⭐ **{total_xp:,}** XP earned",
                     f"🪙 **{total_coins:,}** coins in circulation"]
    fields = [("📊 Server at a Glance", "\n".join(glance_lines))]

    for provider_name, title, empty in (
            ("xp", "🏆 XP Leaders", "*No activity yet*"),
            ("coins", "💰 Richest Members", "*No coins earned yet*")):
        provider = get_provider(provider_name)
        lines: list[str] = []
        if provider is not None:
            entries = await provider.top(guild_id)
            lines = [f"{_medal(i)} {e.label}"
                     for i, e in enumerate(entries[:3])]
        fields.append((title, "\n".join(lines) if lines else empty))

    feed = levelup_feed(guild_id)
    feed_text = ("\n".join(f"• {entry}" for entry in reversed(feed[-5:]))
                 if feed else "*Waiting for the next level-up…*")
    fields.append(("🎉 Recent Level-Ups", feed_text))
    return tuple(fields)


async def provider_board_text(name: str, guild_id: int) -> str:
    """A full top-10 board for the named provider (shipped embed body)."""
    from sb.domain.community.rank_providers import get_provider

    provider = get_provider(name)
    if provider is None:
        return f"Unknown category `{name}`."
    entries = await provider.top(guild_id)
    if not entries:
        return f"{provider.display_title}\n{provider.empty_hint}"
    lines = [provider.display_title]
    lines += [f"{_medal(i)} {e.label}" for i, e in enumerate(entries)]
    return "\n".join(lines)
