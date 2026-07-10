"""Panel-anchor persistence (the shipped ``panel_anchors`` registry).

The shipped bot recorded every CHANNEL-SENT panel message in
``panel_anchors`` (migration 0025) so later refresh/stale-marking could find
it; ephemeral interaction responses were never anchored — no editable
channel message exists. The parity goldens pin both sides of that rule
(``parity/goldens/help/help_panel_open.json`` carries the row; the slash
twin carries none).

This module is the Postgres implementation of the engine's anchor-store
port (``sb.kernel.panels.engine.install_panel_anchor_store``) — composition
roots install it once the pool is initialized; the port left uninstalled is
a no-op (DB-free environments).
"""

from __future__ import annotations

import uuid

__all__ = ["record_anchor"]


async def record_anchor(*, guild_id: int | None, channel_id: int | None,
                        message_id: int, subsystem: str,
                        user_id: int | None) -> None:
    """Insert one anchor row for a freshly sent channel panel message."""
    from sb.kernel.db import pool

    await pool.execute(
        """
        INSERT INTO panel_anchors
            (anchor_id, guild_id, channel_id, message_id, subsystem, user_id)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (channel_id, message_id) DO UPDATE
            SET last_updated_at = NOW(), is_stale = FALSE
        """,
        (uuid.uuid4(), int(guild_id or 0), int(channel_id or 0),
         int(message_id), subsystem, user_id),
    )
