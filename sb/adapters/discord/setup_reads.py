"""The setup-advisor guild READ ports, LIVE leg — the real installs
behind two guild-id-keyed seams the setup band reads:

* the deterministic advisor's channel index
  (``sb.domain.setup.plan.install_channel_index``) — the gateway guild
  cache's text-channel listing (the parity harness installs its
  capture-world twin instead, sb/adapters/parity/boot.py);
* the perms-bearing guild-snapshot source
  (``sb.domain.platform.guild_snapshot.install_snapshot_source``) — the
  channel-recommender's input (the oracle wizard called
  ``guild_snapshot.collect(guild)`` inline from its views; handler-side
  domain code here only carries guild_id, so this fill closes the
  bot.get_guild → collect gap).

Uninstalled, both seams degrade (advisor hints absent / the channels
section's recommender lane falls back to the advisor) — never a crash.
Duck-typed against discord.py like the sibling adapters — no discord
import (the ai_operator_ports precedent)."""

from __future__ import annotations

import logging

logger = logging.getLogger("sb.adapters.discord.setup_reads")

__all__ = ["install_setup_read_ports"]


def install_setup_read_ports(bot: object) -> None:
    """Composition-root wiring (after READY — the guild cache is warm)."""
    from sb.domain.platform.guild_snapshot import (
        collect,
        install_snapshot_source,
    )
    from sb.domain.setup.plan import GuildChannel, install_channel_index

    async def _channel_index(guild_id: int):
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            return ()
        return tuple(
            GuildChannel(id=int(c.id), name=str(c.name))
            for c in (getattr(guild, "text_channels", ()) or ()))

    async def _snapshot(guild_id: int):
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            return None
        try:
            return await collect(guild)
        except Exception:  # noqa: BLE001 — consumers degrade to fallback
            logger.exception("setup_reads: guild_snapshot.collect failed "
                             "for guild=%s", guild_id)
            return None

    install_channel_index(_channel_index)
    install_snapshot_source(_snapshot)
