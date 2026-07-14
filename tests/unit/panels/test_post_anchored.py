"""S9b engine: the message-POSTER port + ``post_anchored_panel`` (the
on-guild-join launcher's event-time post lane — no live session, no
interaction origin; the ``edit_anchored_panel`` twin)."""

from __future__ import annotations

import asyncio

from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.context import PanelOrigin
from sb.kernel.panels.registry import register_panel
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered

from tests.unit.panels.conftest import make_action, make_actor, make_panel

run = asyncio.run


class FakePoster:
    def __init__(self, message_id: int | None = 4242):
        self.calls: list[tuple] = []
        self.message_id = message_id

    async def __call__(self, rendered, *, channel_id, mention_user_ids=()):
        self.calls.append((rendered, channel_id, mention_user_ids))
        return self.message_id


def test_uninstalled_port_answers_none() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    message_id = run(panel_engine.post_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11,
        actor=make_actor()))
    assert message_id is None


def test_post_renders_fresh_and_returns_minted_id() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    poster = FakePoster()
    panel_engine.install_panel_message_poster(poster)

    message_id = run(panel_engine.post_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11,
        actor=make_actor(), mention_user_ids=(77,)))

    assert message_id == 4242
    (rendered, channel_id, mentions), = poster.calls
    assert rendered.panel_id == "econ.shop"
    assert channel_id == 11
    assert mentions == (77,)
    # no session was minted — event-time posts bind static ids only.
    assert panel_engine.session_for("4242") is None


def test_failed_send_answers_none() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    panel_engine.install_panel_message_poster(FakePoster(message_id=None))
    message_id = run(panel_engine.post_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11,
        actor=make_actor()))
    assert message_id is None


def test_renderer_override_sees_anchor_origin() -> None:
    seen: list = []
    if not is_registered(HandlerRef("test.post_anchor_render")):
        @handler("test.post_anchor_render")
        async def _render(spec, ctx):
            from sb.kernel.panels.render import render_panel

            seen.append((ctx.origin, ctx.guild_id, dict(ctx.params)))
            return await render_panel(spec, ctx)

    register_panel(make_panel(
        panel_id="econ.post_override", actions=(make_action(
            handler=HandlerRef("noop.h")),),
        renderer_override=HandlerRef("test.post_anchor_render"),
        justification="test override"))
    poster = FakePoster()
    panel_engine.install_panel_message_poster(poster)

    message_id = run(panel_engine.post_anchored_panel(
        PanelRef("econ.post_override"), guild_id=7, channel_id=1,
        actor=make_actor(), params={"k": "v"}))

    assert message_id == 4242
    origin, guild_id, params = seen[0]
    assert origin is PanelOrigin.ANCHOR
    assert guild_id == 7
    assert params == {"k": "v"}


def test_reset_clears_the_poster() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    panel_engine.install_panel_message_poster(FakePoster())
    panel_engine.reset_panel_engine_for_tests()
    message_id = run(panel_engine.post_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11,
        actor=make_actor()))
    assert message_id is None
