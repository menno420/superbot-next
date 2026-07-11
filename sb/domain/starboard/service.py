"""Starboard domain reads + the UNDER-PORT BOUNDARY (the `_unmapped`
starboard-family re-home; NEW subsystem birth).

What this slice ports (exactly what the goldens pin): the `!starboard`
config command group — the bare status read, the `#channel [threshold]`
configure lane, `off`, `selfstar`, `ignore`/`unignore` and the `panel`
config-panel open (goldens/starboard/sweep_starboard{,_ignore,_off,
_panel,_selfstar,_unignore}).

What deliberately does NOT ship here (the reaction-listener slice's
port): the starboard PIPELINE — the shipped ``on_raw_reaction_add/
remove`` listeners, ``handle_star_change`` (threshold/self-star/ignore
policy over live reactor lists), the hall-of-fame embed builder and the
``starboard_entries`` table (source→board message map; NOT minted — the
trap-15b "declare only what the slice fully carries" rule). No golden
pins a reaction step: reaction ingress is outside the imported corpus's
input vocabulary (sb/kernel/interaction/reactions.py names starboard a
successor reaction surface). The config this slice writes is REAL —
the reaction slice reads it when it lands.
"""

from __future__ import annotations

from sb.domain.starboard import store

__all__ = ["get_settings", "list_ignore_channels"]


async def get_settings(guild_id: int) -> dict | None:
    """The shipped ``starboard_service.get_settings`` read: the guild's
    config row, or None until `!starboard #channel` configures it."""
    return await store.get_settings_row(guild_id)


async def list_ignore_channels(guild_id: int) -> tuple[int, ...]:
    """The shipped ignore-list read (the config panel's ignored-channels
    field)."""
    return await store.list_ignore_channel_rows(guild_id)
