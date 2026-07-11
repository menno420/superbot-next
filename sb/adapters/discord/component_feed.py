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
interactions (buttons and select menus — Discord wire
``InteractionType.component`` = 3) AND the whole modal-submit band (wire
``InteractionType.modal_submit`` = 5, the D-0054 wire-type-5 successor,
armed by the modal-arming slice): ``sb.confirm:`` submits keep their
feed-side typed-phrase check before the confirmed re-entry, every other
submit is a G-10 panel form dispatching through the frozen MODAL adapter
(custom_id root → the declaring PanelActionSpec → ``resolve()`` with
args = the field values over the kernel-stashed opening args).
Application-command interactions belong to the command tree's callbacks;
autocomplete (wire 4) stays a dormant successor.

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

from sb.adapters.discord import confirm_view as confirm_view_mod
from sb.adapters.discord.responders import InteractionResponder
from sb.kernel.interaction.adapters.component import CONFIRM_PREFIX, dispatch_component
from sb.kernel.interaction.adapters.modal import dispatch_modal
from sb.kernel.interaction.errors import from_exception
from sb.kernel.interaction.request import Surface
from sb.kernel.panels.engine import may_interact, session_for

logger = logging.getLogger("sb.adapters.discord.component_feed")

__all__ = [
    "COMPONENT_INTERACTION_TYPE",
    "MODAL_SUBMIT_INTERACTION_TYPE",
    "arm_component_feed",
    "handle_component_interaction",
    "handle_confirm_modal_submit",
    "handle_panel_modal_submit",
    "is_component_interaction",
    "is_confirm_modal_submit",
    "is_modal_submit",
]

#: Discord wire value for ``InteractionType.component`` (buttons + selects).
COMPONENT_INTERACTION_TYPE = 3
#: Discord wire value for ``InteractionType.modal_submit`` — the WHOLE band
#: is consumed (the modal-arming slice): ``sb.confirm:`` ids through the S9b
#: typed-phrase capture path, everything else through the G-10 panel-form
#: path (``handle_panel_modal_submit``).
MODAL_SUBMIT_INTERACTION_TYPE = 5


def is_component_interaction(interaction: object) -> bool:
    """True only for the component band (wire type 3). Application commands
    (2) belong to the command tree; autocomplete (4) stays a dormant
    successor; modal submits (5) have their own two handlers below."""
    itype = getattr(interaction, "type", None)
    return getattr(itype, "value", itype) == COMPONENT_INTERACTION_TYPE


def is_modal_submit(interaction: object) -> bool:
    """True for ANY wire-type-5 submit (confirm capture or G-10 panel
    form) — the armed modal band's gate."""
    itype = getattr(interaction, "type", None)
    return getattr(itype, "value", itype) == MODAL_SUBMIT_INTERACTION_TYPE


def is_confirm_modal_submit(interaction: object) -> bool:
    """True only for the S9b confirm capture modal's submit: wire type 5
    AND the fixed ``sb.confirm:`` custom_id — that submit needs the
    feed-side typed-phrase check before its confirmed re-entry. Every
    other type-5 submit rides ``handle_panel_modal_submit``."""
    if not is_modal_submit(interaction):
        return False
    return _custom_id(interaction).startswith(CONFIRM_PREFIX)


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
    custom_id = _custom_id(interaction)
    if custom_id.startswith(confirm_view_mod.CONFIRM_OPEN_PREFIX):
        # a typed-challenge Confirm click: answer WITH the capture modal
        # (presentation mechanics — the modal's SUBMIT is the confirmed
        # re-entry; this click never dispatches).
        rest = custom_id[len(confirm_view_mod.CONFIRM_OPEN_PREFIX):]
        target_key, _, request_id = rest.rpartition(":")
        try:
            await interaction.response.send_modal(
                confirm_view_mod.build_confirm_modal(target_key or rest,
                                                     request_id or ""))
        except Exception:  # noqa: BLE001
            logger.warning("component feed: confirm modal open failed on %r",
                           custom_id, exc_info=True)
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


async def handle_confirm_modal_submit(interaction: object) -> object | None:
    """The S9b typed-challenge capture submit: check the typed phrase, then
    re-enter through the MODAL adapter (surface=MODAL, ``confirmed=True``
    parsed from the ``sb.confirm:`` custom_id; the resolver restores the
    stashed command args). A wrong phrase declines politely — no dispatch.
    Never raises — a fault renders the K8 error envelope."""
    if not is_confirm_modal_submit(interaction):
        return None
    custom_id = _custom_id(interaction)
    rest = custom_id[len(CONFIRM_PREFIX):]
    target_key, _, _ = rest.rpartition(":")
    typed = _modal_field_value(interaction, "typed_value")
    responder = InteractionResponder(interaction, surface=Surface.MODAL)
    try:
        if not confirm_view_mod.phrase_matches(target_key or rest, typed):
            await responder.deny(
                "That didn't match — nothing was done.", ephemeral=True)
            return None
        return await dispatch_modal(interaction, responder=responder)
    except Exception as exc:  # noqa: BLE001 — the feed never breaks the event loop
        envelope = from_exception(exc, surface=Surface.MODAL, target=None)
        try:
            if not responder.is_acked():
                await responder.deny(envelope.user_message, ephemeral=True)
        except Exception:  # noqa: BLE001
            logger.warning("confirm modal feed: error render failed",
                           exc_info=True)
        logger.warning("confirm modal feed: dispatch fault on %r", custom_id,
                       exc_info=True)
        return None


async def handle_panel_modal_submit(interaction: object) -> object | None:
    """One G-10 panel-form submit (wire type 5, non-``sb.confirm:`` id):
    dispatch through the frozen MODAL adapter — the custom_id root routes
    back to the declaring PanelActionSpec (§3.4 static table) and
    ``resolve()`` runs the action's handler with args = the submitted
    fields over the kernel-stashed opening args. Returns the resolve()
    Result, or None when not consumed. Never raises — a dispatch fault
    renders the K8 error envelope (spec 02 §6)."""
    if not is_modal_submit(interaction) or is_confirm_modal_submit(interaction):
        return None
    responder = InteractionResponder(interaction, surface=Surface.MODAL)
    try:
        return await dispatch_modal(interaction, responder=responder)
    except Exception as exc:  # noqa: BLE001 — the feed never breaks the event loop
        envelope = from_exception(exc, surface=Surface.MODAL, target=None)
        try:
            if not responder.is_acked():
                await responder.deny(envelope.user_message, ephemeral=True)
        except Exception:  # noqa: BLE001
            logger.warning("panel modal feed: error render failed",
                           exc_info=True)
        logger.warning("panel modal feed: dispatch fault on %r",
                       _custom_id(interaction), exc_info=True)
        return None


def _modal_field_value(interaction: object, field_id: str) -> object:
    data = getattr(interaction, "data", None) or {}
    rows = (data.get("components") if isinstance(data, dict)
            else getattr(data, "components", None)) or ()
    for row in rows:
        inner = (row.get("components") if isinstance(row, dict)
                 else getattr(row, "components", None)) or ()
        for comp in inner:
            cid = (comp.get("custom_id") if isinstance(comp, dict)
                   else getattr(comp, "custom_id", None))
            if str(cid) == field_id:
                return (comp.get("value") if isinstance(comp, dict)
                        else getattr(comp, "value", None))
    return None


def arm_component_feed(bot: object) -> None:
    """Register the on_interaction listener (``bot.add_listener`` —
    additive, never replaces the Bot's own event). No intent gate: the
    interaction band needs no privileged intent (unlike the message feed).
    Carries the component band (wire 3) AND the whole modal-submit band
    (wire 5): confirm captures through the typed-phrase check, every other
    submit through the G-10 panel-form dispatch."""

    async def on_interaction(interaction: object) -> None:
        if is_modal_submit(interaction):
            if is_confirm_modal_submit(interaction):
                await handle_confirm_modal_submit(interaction)
            else:
                await handle_panel_modal_submit(interaction)
            return
        await handle_component_interaction(interaction)

    bot.add_listener(on_interaction, "on_interaction")
