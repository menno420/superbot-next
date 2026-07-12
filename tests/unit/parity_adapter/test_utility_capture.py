"""Utility-band capture shapes (goldens/utility).

Three wire behaviors the band-6 utility port added to the capture twin,
each mirroring what parity/harness/fake_http.py recorded for the shipped
bot:

* multipart collapse — discord.py moves the WHOLE JSON body onto the
  multipart wire when files ride along (``MultipartParameters.payload`` is
  None), so ``_params_payload`` captured only ``{"_files": [...]}``; the
  twin must lose exactly the same information (sweep_myprofile,
  sweep_slash_myprofile — note the interaction response carries no ``type``
  envelope either);
* message-surface panel edit — discord.py ``Message.edit`` through
  ``fake_http.edit_message``: channel+message args, embeds+flags+tts body,
  no ``content``, no empty ``components`` (sweep_ping's round-trip edit);
* embed hero image — ``set_image(url=...)`` → ``{"image": {"url": ...}}``
  (sweep_avatar).
"""

from __future__ import annotations

from types import SimpleNamespace

import asyncio

from sb.adapters.parity.transport import (
    ParityPresenter,
    ParityResponder,
    ParityTransport,
    rendered_panel_payload,
)
from sb.kernel.interaction.request import Surface
from sb.kernel.panels.render import (
    RenderedAttachment,
    RenderedEmbed,
    RenderedPanel,
)

run = asyncio.run


class _Ids:
    def __init__(self) -> None:
        self._next = 100

    def allocate(self) -> int:
        self._next += 1
        return self._next


def _transport() -> ParityTransport:
    return ParityTransport(ids=_Ids(), clock=SimpleNamespace(now=None))


def _card(attachments=(), image_url="") -> RenderedPanel:
    return RenderedPanel(
        panel_id="utility.test",
        embed=RenderedEmbed(title="t", description="", image_url=image_url),
        attachments=tuple(attachments))


def test_multipart_send_collapses_to_files_only():
    payload = rendered_panel_payload(
        _card(attachments=(RenderedAttachment("profile.png", b"png"),)))
    assert payload == {"_files": ["profile.png"]}


def test_multipart_interaction_response_has_no_type_envelope():
    transport = _transport()
    responder = ParityResponder(transport, surface=Surface.SLASH,
                                channel_id=7, interaction_id=99)
    responder.present_panel({"_files": ["profile.png"]}, ephemeral=True)
    (call,) = transport.calls
    assert call.method == "interaction_response"
    assert call.payload == {"_files": ["profile.png"]}   # bare — no type/data
    assert responder.is_acked()


def test_message_surface_panel_edit_records_edit_message():
    transport = _transport()
    responder = ParityResponder(transport, surface=Surface.PREFIX,
                                channel_id=7)
    responder.edit_panel(
        {"content": None, "tts": False,
         "embeds": [{"title": "🏓 Pong!"}], "components": []},
        message_ref=123)
    (call,) = transport.calls
    assert call.method == "edit_message"
    assert call.args == {"channel_id": 7, "message_id": 123}
    assert call.payload == {"tts": False, "embeds": [{"title": "🏓 Pong!"}],
                            "flags": 0}


def test_embed_image_wire_shape():
    payload = rendered_panel_payload(_card(image_url="https://cdn.example/a.png"))
    (embed,) = payload["embeds"]
    assert embed["image"] == {"url": "https://cdn.example/a.png"}


def test_placeholder_profile_card_is_a_valid_png():
    from sb.domain.utility.profile_card import CARD_FILENAME, render_profile_card

    assert CARD_FILENAME == "profile.png"       # profile_view.py _CARD_FILENAME
    png = render_profile_card(1, 2)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert png.endswith(b"IEND" + (0xAE426082).to_bytes(4, "big"))


def test_create_invite_twin_records_wire_shape_then_raises():
    """The `!invite` capture artifact (goldens/utility/sweep_invite):
    fake_http.create_invite recorded discord.py's HTTP body verbatim and
    answered a payload discord.py could not rebuild an Invite from — the
    twin records the SAME eight-key body, then raises the named artifact
    (the edit_member precedent)."""
    import pytest

    from sb.adapters.parity.transport import (
        CaptureInviteParseError,
        ParityChannelStateActions,
    )

    transport = _transport()
    actions = ParityChannelStateActions(transport)
    with pytest.raises(CaptureInviteParseError):
        run(actions.create_invite(700, max_age=0, max_uses=1,
                                  temporary=False, unique=True, reason=None))
    (call,) = transport.calls
    assert call.method == "create_invite"
    assert call.args == {"channel_id": 700, "reason": None}
    assert call.payload == {
        "flags": None, "max_age": 0, "max_uses": 1,
        "target_application_id": None, "target_type": None,
        "target_user_id": None, "temporary": False, "unique": True}


def test_format_uptime_matches_shipped_rendering():
    """utility_cog._format_uptime verbatim — days/hours only when
    non-zero, minutes always (sweep_botinfo pins the capture's '0m')."""
    from sb.domain.utility.handlers import _format_uptime

    assert _format_uptime(0) == "0m"                       # the golden byte
    assert _format_uptime(59) == "0m"
    assert _format_uptime(3900) == "1h 5m"
    assert _format_uptime(2 * 86400 + 3 * 3600 + 240) == "2d 3h 4m"


def test_error_card_renders_the_shipped_red_envelope():
    """utils/embeds.error verbatim through utility.error_card — the
    '❌ {message}' description on the red accent, nothing else
    (goldens/utility/sweep_poll pins the bytes)."""
    from sb.domain.utility.panels import _render_error_card, error_card_spec

    spec = error_card_spec()
    ctx = SimpleNamespace(params={"error_text": "You need at least two "
                                                "options for a poll."},
                          actor=SimpleNamespace(user_id=1))
    rendered = run(_render_error_card(spec, ctx))
    assert rendered.embed.title == ""
    assert rendered.embed.description == ("❌ You need at least two options "
                                          "for a poll.")
    assert rendered.embed.style_token == "red"
    assert rendered.components == ()


def test_param_card_carries_footer_and_thumbnail():
    """The shared utility param card (botinfo/membercount/userinfo) —
    footer + thumbnail ride the open params into the embed
    (sweep_botinfo pins 'Requested by AdminActor#0000' + the bot's
    default avatar; sweep_userinfo the member flavors)."""
    from sb.domain.utility.panels import _render_param_card, bot_info_spec

    ctx = SimpleNamespace(
        params={"card_title": "🤖 GalaxyBotParity",
                "card_description": "Bot information and statistics",
                "card_fields": (("Servers", "1", True),),
                "card_footer": "Requested by AdminActor#0000",
                "card_thumbnail":
                    "https://cdn.discordapp.com/embed/avatars/0.png"},
        actor=SimpleNamespace(user_id=1))
    rendered = run(_render_param_card(bot_info_spec(), ctx))
    assert rendered.embed.footer == "Requested by AdminActor#0000"
    assert rendered.embed.thumbnail_ref == (
        "https://cdn.discordapp.com/embed/avatars/0.png")
    assert rendered.embed.fields == (("Servers", "1", True),)
    assert rendered.embed.style_token == "blue"
