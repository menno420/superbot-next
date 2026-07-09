"""The live COMPONENT FEED adapter (CUT-1, completion-report flag 30 —
the interaction band's twin of sb/adapters/discord/message_feed.py):
gateway ``on_interaction`` → ``dispatch_component`` → ``resolve()``.

Before this feed, buttons/selects had NO live path at all: the panel
runtime's ``PanelRuntimeView`` deliberately carries no per-item callbacks
("every child click dispatches through the registered component adapter",
sb/adapters/discord/panel_view.py) and ``main()`` armed only the slash
callbacks (PR #61) — so every nav:* / panel-component / ``sb.confirm:``
click died silently in the view's no-op default. The replay harness has
always driven this exact seam (sb/adapters/parity/boot.py ``click`` →
``dispatch_component``); this module is the same wiring against the real
gateway, honoring the spec 02 §7 no-skip fence.

Scope (the ONE armed interaction-band consumer beyond slash): component
interactions only — buttons and select menus (Discord wire
``InteractionType.component`` = 3). Modal submits keep their dormant
successor (sb/kernel/interaction/adapters/modal.py has no live caller yet);
application-command interactions belong to the command tree's callbacks.

Invoker lock: a LIVE ``PanelRuntimeView`` already enforces it in
``interaction_check`` (denial sent view-side), so this feed mirrors the
same ``may_interact`` read and SKIPS locked-out clicks instead of racing a
second response. Stale panels (post-restart: no session, no view) pass the
lock by design and fall through to the §3.4 router's polite-expiry
terminal.

Duck-typed against discord.py (no discord import — the interaction object
arrives from the gateway at runtime), like the message feed; the listener
is additive (``bot.add_listener``), never replacing the Bot's own event.
"""

from __future__ import annotations

import logging

from sb.adapters.discord.responders import InteractionResponder
from sb.kernel.interaction.adapters.component import dispatch_component
from sb.kernel.interaction.errors import from_exception
from sb.kernel.interaction.request import Surface
from sb.kernel.panels.engine import may_interact, session_for

logger = logging.getLogger("sb.adapters.discord.component_feed")

__all__ = [
    "COMPONENT_INTERACTION_TYPE",
    "arm_component_feed",
    "handle_component_interaction",
    "is_component_interaction",
]

#: Discord wire value for ``InteractionType.component`` (buttons + selects).
COMPONENT_INTERACTION_TYPE = 3


def is_component_interaction(interaction: object) -> bool:
    """True only for the component band (wire type 3). Application commands
    (2) belong to the command tree; autocomplete (4) and modal submits (5)
    stay dormant successors — never consumed here."""
    itype = getattr(interaction, "type", None)
    return getattr(itype, "value", itype) == COMPONENT_INTERACTION_TYPE


def _custom_id(interaction: object) -> str:
    data = getattr(interaction, "data", None) or {}
    if isinstance(data, dict):
        return str(data.get("custom_id", ""))
    return str(getattr(data, "custom_id", ""))


async def handle_component_interaction(interaction: object) -> object | None:
    """One inbound gateway interaction: component clicks dispatch through
    the real spine (custom_id → target index / §3.4 panel router →
    ``resolve()`` / the panel engine). Returns the resolve() Result, or
    None when not consumed. Never raises — a dispatch fault renders the K8
    error envelope (spec 02 §6)."""
    if not is_component_interaction(interaction):
        return None
    message_key = str(getattr(getattr(interaction, "message", None), "id", ""))
    user_id = getattr(getattr(interaction, "user", None), "id", None)
    if not may_interact(session_for(message_key), user_id):
        # the live view's interaction_check owns the denial copy — one
        # response per click, never two racing writers.
        return None
    responder = InteractionResponder(interaction, surface=Surface.COMPONENT)
    try:
        return await dispatch_component(interaction, responder=responder)
    except Exception as exc:  # noqa: BLE001 — the feed never breaks the event loop
        envelope = from_exception(exc, surface=Surface.COMPONENT, target=None)
        try:
            if not responder.is_acked():
                await responder.deny(envelope.user_message, ephemeral=True)
        except Exception:  # noqa: BLE001
            logger.warning("component feed: error render failed", exc_info=True)
        logger.warning("component feed: dispatch fault on %r",
                       _custom_id(interaction), exc_info=True)
        return None


def arm_component_feed(bot: object) -> None:
    """Register the on_interaction listener (``bot.add_listener`` —
    additive, never replaces the Bot's own event). No intent gate: the
    interaction band needs no privileged intent (unlike the message feed)."""

    async def on_interaction(interaction: object) -> None:
        await handle_component_interaction(interaction)

    bot.add_listener(on_interaction, "on_interaction")
