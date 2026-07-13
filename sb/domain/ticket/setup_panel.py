"""The `!ticketsetup` wizard's armed interactive lanes (band 8) — the
faithful port of ORACLE ``views/tickets/config_panel.py``
TicketConfigPanelView (menno420/superbot): role/log native picks that
re-render the panel in place, 🪄 Auto-create log channel, ✅ Enable
tickets, 📋 Post open-ticket panel here. The ``ticket.setup_pending``
terminal retires with this module (ORDER 017 night-run fix slice B).

Behavior map (oracle callbacks, copy verbatim):

* the two native selects set PENDING view state (never a DB write — the
  shipped picks only mutated the view) and re-render the Selected field;
* 🪄 Auto-create runs the audited ``ticket.create_log_channel`` op (one
  channel POST + the config upsert; disbot/services/ticket_mutation.py
  ``create_log_channel``) — success acks "✅ Created <#…> for ticket
  transcripts.", failure the shipped Manage-Channels copy;
* ✅ Enable guards the staff-role pick first ("Pick a **staff role**
  first — …"), then runs the audited ``ticket.update_config`` op
  (enabled + staff_role_id + log_channel_id) and flips the panel green
  with the shipped "Tickets are live." footer;
* 📋 Post panel guards enabled-first ("Enable tickets first, then post
  the panel."), posts the PERSISTENT launcher panel into the invoking
  channel (the `!ticketpanel` panel — one public message), and flips the
  footer to the shipped "📮 Open-ticket panel posted in #…." byte.

Ledgered deviations (D-0084): the guild-guard copy rides the shipped
"Tickets can only be configured inside a server."; the shipped
text-channel-type guard needs a channel-kind read the click path doesn't
carry (the launcher send itself fails loudly in a non-text channel — the
shipped Forbidden copy answers); the auto-created channel's BOT
self-overwrite needs a bot-identity seam the ports don't expose yet.

Handlers register at MODULE IMPORT (the BUG A rule)."""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

logger = logging.getLogger("sb.domain.ticket.setup_panel")

__all__ = ["ensure_setup_panel_refs", "setup_state"]

SETUP_PANEL_ID = "ticket.setup"

#: shipped guard bytes, verbatim (views/tickets/config_panel.py).
_NEEDS_GUILD = "Tickets can only be configured inside a server."
_PICK_ROLE_FIRST = ("Pick a **staff role** first — it's who can see and "
                    "handle tickets.")
_ENABLE_FIRST = "Enable tickets first, then post the panel."
_SEND_FORBIDDEN = "I need permission to send messages in this channel."
_CREATE_FAILED = ("I couldn't create the log channel — I may be missing "
                  "the **Manage Channels** permission.")

#: shipped footer bytes, verbatim.
FOOTER_DEFAULT = ("Tune limits / blacklist later with !ticketlimit and "
                  "!ticketblacklist.")
FOOTER_LIVE = "Tickets are live. Tap Post panel so members can open one."


# --- per-message pending state (the shipped view attributes) ------------------

_STATE: dict[str, dict] = {}
_STATE_MAX = 512


def _store_state(key: str, state: dict) -> None:
    if key:
        _STATE[key] = state
        while len(_STATE) > _STATE_MAX:
            _STATE.pop(next(iter(_STATE)))


def _message_key(req) -> str:
    message = getattr(req.origin, "message", None)
    return str(getattr(message, "id", "") or "")


def setup_state(key: str) -> dict:
    """The panel message's pending view state (empty = nothing picked
    yet — the renderer overlays it on the stored config row)."""
    return dict(_STATE.get(key) or {})


async def _refresh(req, key: str, state: dict) -> bool:
    from sb.kernel.panels.engine import refresh_session_view

    return await refresh_session_view(req, message_key=key,
                                      params=dict(state))


def _picked_id(req) -> int | None:
    values = tuple(req.args.get("values", ()) or ())
    if not values:
        return None
    raw = str(values[0])
    return int(raw) if raw.isdigit() else None


async def _channel_name(guild_id: int, channel_id: int) -> str:
    """Best-effort channel-name read for the shipped '#name' footer byte
    (the gateway-cache ``channel.name``); degrades to the raw id."""
    try:
        from sb.domain.channel import service as channel_service

        snap = await channel_service.active_directory().get_channel(
            int(guild_id), int(channel_id))
        name = str(getattr(snap, "name", "") or "")
        if name:
            return name
    except Exception:  # noqa: BLE001 — headless ⇒ the id fallback
        pass
    return str(channel_id)


# --- handlers ------------------------------------------------------------------


async def setup_select(req) -> Reply:
    """The two native picks (shipped ``_StaffRoleSelect`` /
    ``_LogChannelSelect`` callbacks): set the PENDING view state — never a
    DB write; the ✅ Enable click commits — and re-render in place."""
    picked = _picked_id(req)
    if picked is None:
        return Reply(SUCCESS, None)
    key = _message_key(req)
    state = setup_state(key)
    selector = str(req.args.get("session_action") or "")
    if selector == "setup_staff_role":
        state["staff_role_id"] = picked
    elif selector == "setup_log_channel":
        state["log_channel_id"] = picked
    _store_state(key, state)
    await _refresh(req, key, state)
    return Reply(SUCCESS, None)


async def setup_autocreate(req) -> Reply:
    """🪄 Auto-create log channel (shipped ``autocreate_log``): the
    audited create-channel op, then the in-place re-render + the shipped
    ephemeral ack."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    key = _message_key(req)
    state = setup_state(key)
    try:
        result = await engine.run(
            WorkflowRef("ticket.create_log_channel"),
            ctx_from_request(req, {
                "staff_role_id": state.get("staff_role_id")}))
    except Exception:  # noqa: BLE001 — the port refusal / live Forbidden
        logger.warning("ticket setup: log channel create failed",
                       exc_info=True)
        return Reply(BLOCKED, _CREATE_FAILED)
    if not result.ok:
        return Reply(BLOCKED, _CREATE_FAILED)
    after = (result.after or {}).get("create_log_channel") or {}
    channel_id = int(after.get("log_channel_id") or 0)
    if channel_id:
        state["log_channel_id"] = channel_id
    _store_state(key, state)
    await _refresh(req, key, state)
    # the shipped followup ack, verbatim (channel.mention → <#id>).
    return Reply(SUCCESS,
                 f"✅ Created <#{channel_id}> for ticket transcripts.")


async def setup_enable(req) -> Reply:
    """✅ Enable tickets (shipped ``enable``): staff-role-first guard,
    the audited config write, then the green 'Tickets are live.'
    re-render."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    if not req.guild_id:
        return Reply(BLOCKED, _NEEDS_GUILD)
    key = _message_key(req)
    state = setup_state(key)
    if not state.get("staff_role_id"):
        return Reply(BLOCKED, _PICK_ROLE_FIRST)
    result = await engine.run(
        WorkflowRef("ticket.update_config"),
        ctx_from_request(req, {
            "enabled": True,
            "staff_role_id": int(state["staff_role_id"]),
            "log_channel_id": state.get("log_channel_id")}))
    if not result.ok:
        return Reply(result.outcome,
                     result.user_message or "Couldn't update the ticket "
                                            "settings.")
    state["enabled"] = True
    state["footer"] = FOOTER_LIVE
    state["accent"] = "green"
    _store_state(key, state)
    await _refresh(req, key, state)
    return Reply(SUCCESS, None)


async def setup_post_panel(req) -> Reply:
    """📋 Post open-ticket panel here (shipped ``post_panel``):
    enabled-first guard, post the PERSISTENT launcher into the invoking
    channel, then the '📮 posted in #…' re-render."""
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    key = _message_key(req)
    state = setup_state(key)
    if not state.get("enabled"):
        # the pending pick may sit on an ALREADY-enabled config row (a
        # re-opened wizard) — the shipped guard read the live view state
        # seeded from the config row, so mirror that seed here.
        from sb.domain.ticket import service

        cfg = await service.get_config(int(req.guild_id or 0))
        if not (cfg and cfg.get("enabled")):
            return Reply(BLOCKED, _ENABLE_FIRST)
    try:
        await open_panel(PanelRef("ticket.launcher"), req)
    except Exception:  # noqa: BLE001 — the shipped Forbidden copy
        logger.warning("ticket setup: launcher post failed", exc_info=True)
        return Reply(BLOCKED, _SEND_FORBIDDEN)
    name = await _channel_name(int(req.guild_id or 0),
                               int(req.channel_id or 0))
    state["footer"] = f"📮 Open-ticket panel posted in #{name}."
    state["accent"] = "green"
    _store_state(key, state)
    await _refresh(req, key, state)
    return Reply(SUCCESS, None)


# --- registration — MODULE IMPORT (BUG A rule) -----------------------------------

_HANDLERS = (
    ("ticket.setup_select", setup_select),
    ("ticket.setup_autocreate", setup_autocreate),
    ("ticket.setup_enable", setup_enable),
    ("ticket.setup_post_panel", setup_post_panel),
)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register()


def ensure_setup_panel_refs() -> None:
    _register()
