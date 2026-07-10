"""Hermes command handlers — `/bugreport` + `/dispatch` (band: hermes).

Shipped shape (disbot/cogs/hermes_cog.py): defer ephemeral, then try the
work-order fire; an unconfigured bridge answers the red missing-config
embed (the parity-pinned path). The configured transmit lane (outbound
POST to the Claude Code Routine ``/fire`` endpoint) is un-ported egress —
an honest pending terminal, never a silent success.
"""

from __future__ import annotations

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["ensure_handler_refs"]

_TRANSMIT_PENDING = (
    "📮 The Hermes→Claude dispatch bridge is keyed but its transmit lane "
    "is not armed in this build yet — the work order was NOT sent."
)


async def _bridge_reply(req) -> Reply:
    """The shared defer-then-reply leg: unconfigured -> the shipped
    missing-config embed (panel render on the deferred followup)."""
    from sb.domain.hermes.service import bridge_configured

    if not bridge_configured():
        from sb.domain.hermes.panels import BRIDGE_UNCONFIGURED_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(BRIDGE_UNCONFIGURED_PANEL_ID), req)
        return Reply(SUCCESS, None)
    return Reply(BLOCKED, _TRANSMIT_PENDING)


def _register() -> None:
    """Registered at MODULE IMPORT (declaring IS reserving — the
    sb/domain/rps/handlers.py posture)."""
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("hermes.bugreport")):
        return

    @handler("hermes.bugreport")
    async def bugreport(req) -> Reply:
        """/bugreport <title> <description> [notes]."""
        return await _bridge_reply(req)

    @handler("hermes.dispatch")
    async def dispatch(req) -> Reply:
        """/dispatch <work_order>."""
        return await _bridge_reply(req)


def ensure_handler_refs() -> None:
    _register()


_register()
