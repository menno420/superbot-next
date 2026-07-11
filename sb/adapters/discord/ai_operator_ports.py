"""The AI operator-surface environment ports, LIVE leg (band 7) — the
real installs behind :mod:`sb.domain.ai.operator_cards`'s two ports:

* runtime identity — the support report's ``# python: X on Y`` +
  ``# bot_user_id`` lines (the interpreter's own version/system plus the
  gateway bot id, available at READY);
* channel permission probe — the readiness scan's ``bot_permissions``
  link (the shipped ``channel.permissions_for(guild.me)`` read);
* guild scope roster — the policy scope pickers' channel/category/role
  option rosters (the shipped native ChannelSelect/RoleSelect enumerated
  these server-side; the engine's string selects enumerate through this
  port — sb/domain/ai/policy_widgets.py).

The parity harness installs its capture-world twins instead
(sb/adapters/parity/boot.py). Duck-typed against discord.py like the
sibling adapters — no discord import."""

from __future__ import annotations

import logging
import platform
import sys

logger = logging.getLogger("sb.adapters.discord.ai_operator_ports")

__all__ = ["install_ai_operator_ports"]


def install_ai_operator_ports(bot: object) -> None:
    """Composition-root wiring (after READY — ``bot.user`` must exist)."""
    from sb.domain.ai.operator_cards import (
        RuntimeIdentity,
        install_channel_permission_probe,
        install_runtime_identity,
    )

    bot_user_id = getattr(getattr(bot, "user", None), "id", None)
    install_runtime_identity(RuntimeIdentity(
        python_version=sys.version.split()[0],
        system=platform.system(),
        bot_user_id=int(bot_user_id) if bot_user_id else None))

    async def _probe(guild_id: int, channel_id: int,
                     scan_enabled: bool) -> list[str] | None:
        guild = bot.get_guild(int(guild_id))
        me = getattr(guild, "me", None) if guild is not None else None
        channel = (guild.get_channel(int(channel_id))
                   if guild is not None else None)
        if me is None or channel is None:
            return None                      # → the shipped skipped finding
        try:
            perms = channel.permissions_for(me)
        except Exception:  # noqa: BLE001 — probe failure = cannot run
            logger.debug("ai permission probe failed", exc_info=True)
            return None
        missing: list[str] = []
        if not getattr(perms, "view_channel", False):
            missing.append("view_channel")
        if not getattr(perms, "send_messages", False):
            missing.append("send_messages")
        if scan_enabled and not getattr(perms, "read_message_history", False):
            missing.append("read_message_history")
        return missing

    install_channel_permission_probe(_probe)

    from sb.domain.ai.policy_widgets import (
        GuildScopeRoster,
        install_guild_scope_roster,
    )

    async def _scope_roster(guild_id: int) -> GuildScopeRoster | None:
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            return None
        text_channels = tuple(
            (int(c.id), str(c.name),
             int(c.category_id) if getattr(c, "category_id", None) else None)
            for c in (getattr(guild, "text_channels", ()) or ()))
        categories = tuple(
            (int(c.id), str(c.name))
            for c in (getattr(guild, "categories", ()) or ()))
        roles = tuple(
            (int(r.id), str(r.name))
            for r in (getattr(guild, "roles", ()) or ())
            if int(r.id) != int(guild_id))          # skip @everyone
        return GuildScopeRoster(text_channels=text_channels,
                                categories=categories, roles=roles)

    install_guild_scope_roster(_scope_roster)
