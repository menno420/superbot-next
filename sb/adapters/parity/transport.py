"""The capture boundary for the NEW bot — sb/'s egress seams → OutboundCall.

Twin of parity/harness/fake_http.py, recording in the SAME wire vocabulary
(the goldens' language) but listening on sb/'s own ports instead of
discord.py's HTTPClient:

* :class:`ParityResponder`   — the `SurfaceResponder` implementation
  (slash/component/modal interactions AND the prefix message surface);
* :class:`ParityPresenter`   — the panel engine's presenter port
  (RenderedPanel → discord-wire embed/component payloads);
* :class:`ParityChannelEmitter` — the RC-21 send-egress port.

Unknown/unmodeled effects are recorded as GAPS (the capture-integrity
honesty rule: a golden must never silently drop an outbound effect).
"""

from __future__ import annotations

from typing import Any

from parity.harness.fake_http import OutboundCall
from sb.kernel.interaction.egress import EmitResult, OutboundContent, TrustLevel, neutralize_untrusted
from sb.kernel.interaction.request import ConfirmPrompt, Surface
from sb.spec.outcomes import ReplyVisibility

__all__ = [
    "ParityAvatarFetcher",
    "ParityChannelEmitter",
    "ParityHistoryReader",
    "ParityModerationActions",
    "ParityPresenter",
    "ParityResponder",
    "ParityTransport",
]

_EPHEMERAL_FLAG = 64


def _followup_payload(data: dict[str, Any]) -> dict[str, Any]:
    """discord.py's ``Webhook.send`` wire shape: unlike the interaction
    type-4 response (which always carries ``content``/``components``), a
    followup omits ``content`` when None and ``components`` when no view
    was passed — the goldens' shape for every ``followup_send`` the old
    bot made (goldens/hermes, goldens/karma: embeds+flags+tts only)."""
    return {k: v for k, v in data.items()
            if not (k == "content" and v is None)
            and not (k == "components" and not v)}


def _followup_args() -> dict[str, Any]:
    """``interaction.followup`` is the application's webhook — fake_http
    captured its id as the BOT user (every corpus followup_send carries
    ``webhook_id: <@bot>``), never the interaction id."""
    from parity.harness.world import World

    return {"webhook_id": World.BOT_USER_ID}

#: RenderedComponent.style token → discord button style int.
_BUTTON_STYLES = {"primary": 1, "secondary": 2, "success": 3, "danger": 4, "link": 5}


class ParityTransport:
    """One case-run's outbound-call ledger (the `harness.http` twin)."""

    def __init__(self, *, ids: Any, clock: Any) -> None:
        self.calls: list[OutboundCall] = []
        self.gaps: list[str] = []
        self._ids = ids
        self._clock = clock

    # ------------------------------------------------------------- recording

    def record(self, method: str, args: dict[str, Any],
               payload: dict[str, Any] | None = None) -> None:
        self.calls.append(OutboundCall(method=method, args=args, payload=payload))

    def record_send(self, channel_id: int, payload: dict[str, Any]) -> int:
        """A channel send mints a message id (click-targeting contract)."""
        message_id = self._ids.allocate()
        self.calls.append(OutboundCall(
            method="send_message", args={"channel_id": int(channel_id)},
            payload=payload, response_id=message_id))
        return message_id

    def gap(self, name: str) -> None:
        self.gaps.append(name)


# --- wire mapping (RenderedPanel → discord payload shapes) --------------------

def _embed_payload(embed: Any) -> dict[str, Any]:
    # discord.py's Embed.to_dict() always carries "flags": 0 — the goldens'
    # wire shape for every embed the old bot sent.
    out: dict[str, Any] = {"type": "rich", "flags": 0}
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    color = STYLE_TOKEN_COLORS.get(getattr(embed, "style_token", "") or "")
    if color is not None:
        out["color"] = color
    if getattr(embed, "author_name", ""):
        author: dict[str, Any] = {"name": embed.author_name}
        if getattr(embed, "author_icon", ""):
            author["icon_url"] = embed.author_icon
        out["author"] = author
    if getattr(embed, "title", ""):
        out["title"] = embed.title
    if getattr(embed, "description", ""):
        out["description"] = embed.description
    fields = [{"name": f[0], "value": f[1],
               "inline": bool(f[2]) if len(f) > 2 else False}
              for f in getattr(embed, "fields", ()) or ()]
    if fields:
        out["fields"] = fields
    if getattr(embed, "footer", ""):
        out["footer"] = {"text": embed.footer}
    if getattr(embed, "image_url", ""):
        # discord.py Embed.set_image — the shipped avatar card's wire shape
        # (goldens/utility/sweep_avatar).
        out["image"] = {"url": embed.image_url}
    if getattr(embed, "thumbnail_ref", ""):
        # discord.py Embed.set_thumbnail — the live presenter reads the same
        # field (sb/adapters/discord/panel_view.py); the shipped wallet card
        # pins the shape (goldens/economy/sweep_balance).
        out["thumbnail"] = {"url": embed.thumbnail_ref}
    return out


def _option_payload(option: Any) -> dict[str, Any]:
    """One select option, discord.py SelectOption.to_dict()-shaped: rich
    mappings carry label/value/description/emoji; plain strings keep the
    compact label==value form."""
    if isinstance(option, dict):
        out: dict[str, Any] = {
            "label": str(option.get("label", "")),
            "value": str(option.get("value", option.get("label", ""))),
            "default": bool(option.get("default", False)),
        }
        if option.get("description"):
            out["description"] = str(option["description"])
        if option.get("emoji"):
            out["emoji"] = {"id": None, "name": str(option["emoji"])}
        return out
    return {"label": str(option), "value": str(option), "default": False}


def _component_payload(component: Any) -> dict[str, Any]:
    if component.kind == "selector":
        out: dict[str, Any] = {
            "type": 3,
            "custom_id": component.custom_id,
            "min_values": component.min_values,
            "max_values": component.max_values,
            "disabled": bool(component.disabled),
            # discord.py's Select.to_component_dict() always emits
            # "required" (true at min_values >= 1) — the goldens carry it
            # on every select the old bot sent.
            "required": component.min_values >= 1,
            "options": [_option_payload(o) for o in component.options],
        }
        if component.placeholder:
            out["placeholder"] = component.placeholder
        return out
    out = {
        "type": 2,
        "style": _BUTTON_STYLES.get(str(component.style), 2),
        "custom_id": component.custom_id,
        "label": component.label,
        "disabled": bool(component.disabled),
    }
    if component.emoji:
        out["emoji"] = {"id": None, "name": component.emoji}
    return out


def rendered_panel_payload(rendered: Any) -> dict[str, Any]:
    """The message payload a RenderedPanel sends (embeds + component rows).

    Attachment-bearing panels collapse to the ``{"_files": [...]}`` shape:
    discord.py moves the whole JSON body onto the multipart wire when files
    ride along (``MultipartParameters.payload`` is None), so fake_http's
    ``_params_payload`` captured ONLY the filenames — the goldens' shape for
    every shipped file send (utility/sweep_myprofile, xp/xp_chat_award).
    The capture twin must lose exactly the same information."""
    attachments = getattr(rendered, "attachments", ()) or ()
    if attachments:
        return {"_files": [a.filename for a in attachments]}
    rows: dict[int, list[dict[str, Any]]] = {}
    for component in getattr(rendered, "components", ()) or ():
        rows.setdefault(int(component.row), []).append(_component_payload(component))
    return {
        "content": None,
        "tts": False,
        "embeds": [_embed_payload(rendered.embed)],
        "components": [{"type": 1, "components": rows[r]} for r in sorted(rows)],
    }


# --- the SurfaceResponder implementation --------------------------------------

_INTERACTION_SURFACES = frozenset({
    Surface.SLASH, Surface.COMPONENT, Surface.MODAL,
    Surface.NL_INTENT, Surface.NL_ORCHESTRATION,
})


class ParityResponder:
    """Records what the discord responders would send, wire-shaped.

    One instance per driven input. For interaction surfaces the first reply
    is an ``interaction_response`` (type 4 message / type 5 defer) and every
    later one a ``followup_send`` — mirroring discord.py's seam split that
    the goldens captured. The prefix/message surface replies with channel
    ``send_message`` records (which mint click-targetable message ids).
    """

    def __init__(self, transport: ParityTransport, *, surface: Surface,
                 channel_id: int | None, interaction_id: int | None = None) -> None:
        self._transport = transport
        self.surface = surface
        self._channel_id = channel_id
        self._interaction_id = interaction_id
        self._acked = False
        self._committed: ReplyVisibility | None = None

    # -- contract ----------------------------------------------------------

    def is_acked(self) -> bool:
        return self._acked

    def committed_visibility(self) -> ReplyVisibility | None:
        return self._committed

    async def ack(self, *, ephemeral: bool) -> None:
        if self.surface not in _INTERACTION_SURFACES:
            return                          # message surfaces: ack is a no-op
        if self._acked:
            return
        self._acked = True
        self._committed = (ReplyVisibility.EPHEMERAL if ephemeral
                           else ReplyVisibility.PUBLIC)
        data: dict[str, Any] = {"flags": _EPHEMERAL_FLAG} if ephemeral else {}
        self._transport.record(
            "interaction_response",
            {"interaction_id": self._interaction_id},
            {"type": 5, "data": data})

    async def deny(self, message: str, *, ephemeral: bool) -> None:
        self._reply(message, ephemeral=ephemeral)

    async def open_modal(self, modal_ref: object) -> None:
        if self.surface in _INTERACTION_SURFACES:
            self._transport.record(
                "interaction_response",
                {"interaction_id": self._interaction_id},
                {"type": 9, "data": {"custom_id": getattr(modal_ref, "modal_id", None)
                                     or getattr(modal_ref, "custom_id", None)}})
            self._acked = True
        else:
            self._reply("This action needs the slash-command version.",
                        ephemeral=False)

    async def open_confirm(self, prompt: ConfirmPrompt) -> None:
        # the sb.adapters.discord responders' copy, verbatim
        if self.surface in _INTERACTION_SURFACES:
            custom_id = f"sb.confirm:{prompt.target_key}:{prompt.request_id}"
            self._reply(f"{prompt.prompt_text} (confirm id: `{custom_id}`)",
                        ephemeral=True)
        else:
            self._reply(prompt.prompt_text, ephemeral=False)

    async def render(self, result: object) -> None:
        message = getattr(result, "user_message", None)
        visibility = getattr(result, "reply_visibility", ReplyVisibility.EPHEMERAL)
        if message is None or visibility is ReplyVisibility.SILENT:
            return
        self._reply(str(message), ephemeral=visibility is ReplyVisibility.EPHEMERAL)

    async def fetch_original_response(self) -> None:
        """The shipped ``await interaction.original_response()`` fetch —
        fake_http captured the HTTP GET verbatim as a bare
        ``get_original_response`` call (goldens/uxlab/sweep_slash_uxlab
        pins it as the response's follow-up call). Only meaningful after
        an interaction response exists; message surfaces have a real
        channel message and never fetch."""
        if self.surface in _INTERACTION_SURFACES and self._acked:
            self._transport.record("get_original_response", {})

    # -- panel presentation (called by ParityPresenter) ---------------------

    def edit_panel(self, payload: dict[str, Any], message_ref: object) -> None:
        """Session-view refresh — the shipped component-click edit loop as
        discord.py's HTTP layer captured it (parity/harness/fake_http.py):
        a DEFERRED UPDATE ack (interaction response type 6, bare payload)
        followed by the webhook message edit (``edit_followup`` keyed on
        the application id). Edit payloads carry no ``content`` key."""
        from parity.harness.world import World

        if self.surface not in _INTERACTION_SURFACES:
            # message-surface edit — discord.py Message.edit through the
            # HTTP layer (fake_http.edit_message): channel+message args, the
            # edit body without the send-only keys. The shipped !ping
            # round-trip edit pins the shape (goldens/utility/sweep_ping:
            # embeds + flags + tts, no content, no empty components).
            if message_ref is None:
                self._transport.gap("ParityResponder.edit_panel: no message ref")
                return
            body = {k: v for k, v in payload.items()
                    if k != "content" and not (k == "components" and not v)}
            body.setdefault("flags", 0)
            self._transport.record(
                "edit_message",
                {"channel_id": self._channel_id,
                 "message_id": int(str(message_ref))},
                body)
            return
        if not self._acked:
            self._acked = True
            self._committed = ReplyVisibility.PUBLIC
            self._transport.record(
                "interaction_response",
                {"interaction_id": self._interaction_id},
                {"type": 6})
        body = {k: v for k, v in payload.items() if k != "content"}
        self._transport.record(
            "edit_followup",
            {"webhook_id": World.BOT_USER_ID,
             "message_id": int(str(message_ref))},
            body)

    def present_panel(self, payload: dict[str, Any], *,
                      ephemeral: bool = False) -> int | None:
        """Send a rendered panel on this responder's surface; returns the
        minted message id for channel sends (None on interaction paths —
        the old capture never minted ids for interaction responses).
        ``ephemeral`` applies only on interaction surfaces (the live
        presenter's ``audience == "invoker"`` rule, mirrored)."""
        if self.surface in _INTERACTION_SURFACES:
            if "_files" in payload:
                # multipart response: discord.py moved the whole {type, data}
                # envelope onto the multipart wire, so fake_http captured the
                # bare filename list (goldens/utility/sweep_slash_myprofile).
                self._acked = True
                if self._committed is None:
                    self._committed = (ReplyVisibility.EPHEMERAL if ephemeral
                                       else ReplyVisibility.PUBLIC)
                self._transport.record(
                    "interaction_response",
                    {"interaction_id": self._interaction_id},
                    dict(payload))
                return None
            data = dict(payload)
            if ephemeral:
                data["flags"] = _EPHEMERAL_FLAG
            if not self._acked:
                self._acked = True
                self._transport.record(
                    "interaction_response",
                    {"interaction_id": self._interaction_id},
                    {"type": 4, "data": data})
                return None
            self._transport.record(
                "followup_send", _followup_args(), _followup_payload(data))
            return None
        if self._channel_id is None:
            self._transport.gap("ParityResponder.present_panel: no channel")
            return None
        return self._transport.record_send(self._channel_id, payload)

    # -- internals -----------------------------------------------------------

    def _reply(self, message: str, *, ephemeral: bool) -> None:
        if self.surface in _INTERACTION_SURFACES:
            data: dict[str, Any] = {"content": message}
            if ephemeral:
                data["flags"] = _EPHEMERAL_FLAG
            if not self._acked:
                self._acked = True
                self._transport.record(
                    "interaction_response",
                    {"interaction_id": self._interaction_id},
                    {"type": 4, "data": data})
            else:
                self._transport.record(
                    "followup_send", _followup_args(), _followup_payload(data))
            return
        if self._channel_id is None:
            self._transport.gap("ParityResponder._reply: no channel")
            return
        # discord.py's HTTP send always carries components ([] when no
        # view) — the goldens' wire shape for every plain-content send.
        self._transport.record_send(
            self._channel_id,
            {"components": [], "content": message, "tts": False})


class ParityPresenter:
    """The panel engine's presenter port — presents through the driving
    request's own responder so the surface split (interaction vs channel)
    matches what discord.py would have done."""

    def __init__(self, transport: ParityTransport) -> None:
        self._transport = transport

    async def __call__(self, rendered: Any, req: Any) -> object:
        payload = rendered_panel_payload(rendered)
        # the live DiscordPanelPresenter's rule, mirrored: invoker-audience
        # panels are ephemeral on interaction surfaces.
        ephemeral = getattr(rendered, "audience", "") == "invoker"
        responder = getattr(req, "responder", None)
        edit_ref = getattr(rendered, "edit_message_ref", None)
        channel_id = getattr(req, "channel_id", None)
        if isinstance(responder, ParityResponder):
            if edit_ref is not None:
                responder.edit_panel(payload, edit_ref)
                return edit_ref
            if (getattr(rendered, "anchor_policy", "") == "channel_anchor"
                    and channel_id is not None):
                # CHANNEL_ANCHOR panels are fresh channel messages even when
                # a click drives them (the live twin sends to the origin's
                # channel) — the send mints a click-targetable message id,
                # never a webhook followup.
                message_id = self._transport.record_send(int(channel_id),
                                                         payload)
                self._record_self_reactions(rendered, channel_id, message_id)
                return message_id
            message_id = responder.present_panel(payload, ephemeral=ephemeral)
            self._record_self_reactions(rendered, channel_id, message_id)
            return message_id
        if channel_id is None:
            self._transport.gap("ParityPresenter: no responder and no channel")
            return None
        message_id = self._transport.record_send(int(channel_id), payload)
        self._record_self_reactions(rendered, channel_id, message_id)
        return message_id

    def _record_self_reactions(self, rendered: Any, channel_id: Any,
                               message_id: Any) -> None:
        """The bot's own post-send reactions (`message.add_reaction`), in
        the goldens' wire verb — channel sends only (an interaction
        response has no reactable message; the shape mirrors fake_http's
        add_reaction capture)."""
        emoji_list = tuple(getattr(rendered, "self_reactions", ()) or ())
        if not emoji_list:
            return
        if message_id is None or channel_id is None:
            self._transport.gap("ParityPresenter: self_reactions on a "
                                "message-less surface")
            return
        for emoji in emoji_list:
            self._transport.record(
                "add_reaction",
                {"channel_id": int(channel_id), "emoji": str(emoji),
                 "message_id": int(message_id)})


class ParityChannelEmitter:
    """RC-21 send-egress capture (service-initiated sends). Applies the
    same UNTRUSTED neutralization the discord emitter owns, so captured
    content is what would actually hit the wire."""

    def __init__(self, transport: ParityTransport) -> None:
        self._transport = transport

    async def send(self, channel_id: int, content: OutboundContent, *,
                   guild_id: int) -> EmitResult:
        body = content.body
        if content.trust is TrustLevel.UNTRUSTED:
            body = neutralize_untrusted(body)
        message_id = self._transport.record_send(
            int(channel_id),
            {"components": [], "content": body, "tts": False})
        return EmitResult(sent=True, message_id=message_id)


class ParityHistoryReader:
    """The cleanup history-reader capture twin — the shipped
    ``ctx.channel.history(limit=...)`` read that discord.py's HTTP layer
    performed as ``logs_from`` (parity/harness/fake_http.py records
    ``{"channel_id", "limit"}``; goldens/cleanup/sweep_cleanuphistory.json
    pins the call). The capture world holds no channel messages, exactly
    like the old harness (its ``logs_from`` returned the world's empty
    backlog), so the read yields the goldens' 0-scanned shape."""

    def __init__(self, transport: ParityTransport) -> None:
        self._transport = transport

    async def __call__(self, channel_id: int, *, limit: int) -> tuple:
        self._transport.record(
            "logs_from", {"channel_id": int(channel_id), "limit": int(limit)})
        return ()


#: fake_http.get_from_cdn's deterministic 1×1 PNG, verbatim — what the old
#: harness fed the shipped card pipeline's avatar read.
_CDN_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd4000000004945"
    "4e44ae426082",
)


class ParityAvatarFetcher:
    """The rank-card avatar-read capture twin — the shipped
    ``services/xp_helpers.fetch_avatar_png`` CDN asset fetch that
    discord.py's HTTP layer performed as ``get_from_cdn``
    (parity/harness/fake_http.py records the ALIAS literal
    ``{"url": "<cdn>"}`` and answers a deterministic 1×1 PNG;
    goldens/xp/xp_chat_award.json + sweep_xpmenu.json pin the call).
    The twin loses exactly the same information — the alias literal,
    never the concrete URL."""

    def __init__(self, transport: ParityTransport) -> None:
        self._transport = transport

    async def __call__(self, user_id: int, guild_id: int) -> bytes | None:
        del user_id, guild_id
        self._transport.record("get_from_cdn", {"url": "<cdn>"})
        return _CDN_PNG


class ParityModerationActions:
    """The GuildModerationActions capture twin — the moderation EFFECT
    legs' Discord state mutations, recorded in the goldens' wire verbs
    (fake_http captured discord.py's HTTP layer: member timeout is an
    ``edit_member`` PATCH with ``communication_disabled_until``; kick/
    ban/unban are their own routes). Without this the replay composition
    root leaves the not-installed port raising, so every moderation op
    degrades to PARTIAL with an operator finding — a harness gap, not
    bot behavior."""

    def __init__(self, transport: ParityTransport, clock: Any) -> None:
        self._transport = transport
        self._clock = clock

    def _until(self, minutes: int) -> str:
        from datetime import timedelta

        return (self._clock.now + timedelta(minutes=minutes)).isoformat()

    async def timeout_member(self, guild_id: int, user_id: int, *,
                             minutes: int, reason: str) -> None:
        self._transport.record(
            "edit_member",
            {"guild_id": int(guild_id), "user_id": int(user_id),
             "reason": reason},
            {"communication_disabled_until": self._until(int(minutes))})

    async def kick_member(self, guild_id: int, user_id: int, *,
                          reason: str) -> None:
        self._transport.record(
            "kick", {"guild_id": int(guild_id), "user_id": int(user_id),
                     "reason": reason})

    async def ban_member(self, guild_id: int, user_id: int, *, reason: str,
                         delete_message_days: int) -> None:
        args: dict[str, Any] = {"guild_id": int(guild_id),
                                "user_id": int(user_id), "reason": reason}
        if int(delete_message_days) > 0:
            # discord.py sends seconds; shipped only passed the kwarg when
            # a purge window was configured (moderation_service.ban).
            args["delete_message_seconds"] = int(delete_message_days) * 86400
        self._transport.record("ban", args)

    async def unban_member(self, guild_id: int, user_id: int, *,
                           reason: str) -> None:
        self._transport.record(
            "unban", {"guild_id": int(guild_id), "user_id": int(user_id),
                      "reason": reason})

    async def dm_member(self, user_id: int, text: str) -> None:
        # no golden exercises the courtesy DM (dm_on_action defaults off);
        # record the honesty gap rather than inventing a wire shape.
        self._transport.gap(f"dm_member:{user_id}")
