"""S9b engine: the message-editor port + ``edit_anchored_panel`` (the
on-ready resume sweep's boot-time edit lane — no live session, no
interaction origin)."""

from __future__ import annotations

import asyncio

from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.context import PanelOrigin
from sb.kernel.panels.registry import register_panel
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered

from tests.unit.panels.conftest import make_action, make_actor, make_panel

run = asyncio.run


class FakeEditor:
    def __init__(self, outcome=panel_engine.EDIT_EDITED):
        self.calls: list[tuple] = []
        self.outcome = outcome

    async def __call__(self, rendered, *, channel_id, message_id):
        self.calls.append((rendered, channel_id, message_id))
        return self.outcome


def test_uninstalled_port_answers_unavailable() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    outcome = run(panel_engine.edit_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11, message_id=22,
        actor=make_actor()))
    assert outcome == panel_engine.EDIT_UNAVAILABLE


def test_edit_renders_fresh_and_passes_persisted_ids() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    editor = FakeEditor()
    panel_engine.install_panel_message_editor(editor)

    outcome = run(panel_engine.edit_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11, message_id=22,
        actor=make_actor()))

    assert outcome == panel_engine.EDIT_EDITED
    (rendered, channel_id, message_id), = editor.calls
    assert rendered.panel_id == "econ.shop"
    assert (channel_id, message_id) == (11, 22)
    # no session was minted — boot edits re-bind static ids only.
    assert panel_engine.session_for("22") is None


def test_outcome_passthrough_missing() -> None:
    register_panel(make_panel(actions=(make_action(
        handler=HandlerRef("noop.h")),)))
    panel_engine.install_panel_message_editor(
        FakeEditor(outcome=panel_engine.EDIT_MISSING))
    outcome = run(panel_engine.edit_anchored_panel(
        PanelRef("econ.shop"), guild_id=9, channel_id=11, message_id=22,
        actor=make_actor()))
    assert outcome == panel_engine.EDIT_MISSING


def test_renderer_override_sees_anchor_origin() -> None:
    seen: list = []
    if not is_registered(HandlerRef("test.edit_anchor_render")):
        @handler("test.edit_anchor_render")
        async def _render(spec, ctx):
            from sb.kernel.panels.render import render_panel

            seen.append((ctx.origin, ctx.guild_id, dict(ctx.params)))
            return await render_panel(spec, ctx)

    register_panel(make_panel(
        panel_id="econ.override", actions=(make_action(
            handler=HandlerRef("noop.h")),),
        renderer_override=HandlerRef("test.edit_anchor_render"),
        justification="test override"))
    editor = FakeEditor()
    panel_engine.install_panel_message_editor(editor)

    outcome = run(panel_engine.edit_anchored_panel(
        PanelRef("econ.override"), guild_id=7, channel_id=1, message_id=2,
        actor=make_actor(), params={"k": "v"}))

    assert outcome == panel_engine.EDIT_EDITED
    origin, guild_id, params = seen[0]
    assert origin is PanelOrigin.ANCHOR
    assert guild_id == 7
    assert params == {"k": "v"}
