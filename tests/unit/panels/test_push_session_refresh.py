"""S9b engine: ``push_session_refresh`` — the interaction-free session
edit (docs/decisions.md D-0090): re-renders a LIVE session view onto its
ORIGINAL minted component ids and presents through the
``_message_editor`` port (no ResolveRequest) — the real-time twin of
``refresh_session_view``. Uninstalled editor ⇒ EDIT_UNAVAILABLE no-op
(headless posture); gone session / no channel message ⇒ EDIT_MISSING."""

from __future__ import annotations

import asyncio

from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.registry import register_panel
from sb.spec.refs import HandlerRef, PanelRef

from tests.unit.panels.conftest import make_action, make_actor, make_panel

run = asyncio.run


class FakePresenter:
    def __init__(self, message_id=555):
        self.presented: list = []
        self._message_id = message_id

    async def __call__(self, rendered, req):
        self.presented.append(rendered)
        return self._message_id


class FakeEditor:
    def __init__(self, outcome=panel_engine.EDIT_EDITED):
        self.calls: list[tuple] = []
        self.outcome = outcome

    async def __call__(self, rendered, *, channel_id, message_id):
        self.calls.append((rendered, channel_id, message_id))
        return self.outcome


def _req():
    return ResolveRequest(
        surface=Surface.SLASH,
        target=TargetRef(key="economy.shop", spec=None),
        actor=make_actor(), guild_id=42, channel_id=7, args={},
        responder=object(), origin=object())


def _open_session() -> str:
    """Open a session-lifecycle panel through the real engine and return
    its message key (the presenter's minted message id)."""
    register_panel(make_panel(
        actions=(make_action(handler=HandlerRef("noop.h")),),
        session_lifecycle=True))
    panel_engine.install_panel_presenter(FakePresenter())
    return run(panel_engine.open_panel(PanelRef("econ.shop"), _req()))


def test_uninstalled_editor_answers_unavailable() -> None:
    key = _open_session()
    outcome = run(panel_engine.push_session_refresh(
        key, params={}, actor=make_actor()))
    assert outcome == panel_engine.EDIT_UNAVAILABLE
    # the no-op left the session alive.
    assert panel_engine.session_for(key) is not None


def test_unknown_message_key_answers_missing() -> None:
    panel_engine.install_panel_message_editor(FakeEditor())
    outcome = run(panel_engine.push_session_refresh(
        "424242", params={}, actor=make_actor()))
    assert outcome == panel_engine.EDIT_MISSING


def test_channelless_session_answers_missing() -> None:
    # a confirm-surface session has no editable channel message.
    panel_engine.register_confirm_session("77", invoker_id=1, timeout_s=60)
    panel_engine.install_panel_message_editor(FakeEditor())
    outcome = run(panel_engine.push_session_refresh(
        "77", params={}, actor=make_actor()))
    assert outcome == panel_engine.EDIT_MISSING


def test_edits_onto_the_original_minted_ids() -> None:
    key = _open_session()
    session = panel_engine.session_for(key)
    assert session is not None and session.channel_id == 7
    minted = session.component_ids["do"]
    editor = FakeEditor()
    panel_engine.install_panel_message_editor(editor)

    outcome = run(panel_engine.push_session_refresh(
        key, params={"k": "v"}, actor=make_actor(), guild_id=42))

    assert outcome == panel_engine.EDIT_EDITED
    (rendered, channel_id, message_id), = editor.calls
    assert (channel_id, message_id) == (7, 555)
    # the declared component was rewritten onto the SAME minted wire id
    # — never re-minted (the shipped views kept their auto-ids); the
    # engine-injected nav slot keeps its static id (the _mint_ephemeral
    # posture).
    ids = [c.custom_id for c in rendered.components]
    assert minted in ids
    assert all(i == minted or i.startswith("nav:") for i in ids)
    # the session (and its binding) survive a non-terminal push.
    assert panel_engine.session_for(key) is not None
    assert panel_engine.ephemeral_route(minted) is not None


def test_expire_tears_the_session_down() -> None:
    key = _open_session()
    minted = panel_engine.session_for(key).component_ids["do"]
    panel_engine.install_panel_message_editor(FakeEditor())

    outcome = run(panel_engine.push_session_refresh(
        key, params={}, actor=make_actor(), expire=True))

    assert outcome == panel_engine.EDIT_EDITED
    assert panel_engine.session_for(key) is None
    assert panel_engine.ephemeral_route(minted) is None


def test_editor_outcome_passes_through() -> None:
    key = _open_session()
    panel_engine.install_panel_message_editor(
        FakeEditor(outcome=panel_engine.EDIT_FAILED))
    outcome = run(panel_engine.push_session_refresh(
        key, params={}, actor=make_actor()))
    assert outcome == panel_engine.EDIT_FAILED
