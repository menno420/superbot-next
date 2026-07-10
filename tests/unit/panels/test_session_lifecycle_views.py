"""Session-lifecycle game views (the shipped discord.py view semantics made
declarative): engine-minted 32-hex custom ids bound in memory to the DECLARED
component spec + the opening request's args; invoker-locked clicks; polite
expiry after timeout/restart; never anchored (band 6 — the rps quick-play
picker is the first consumer; goldens/rps_tournament pins the wire shape)."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import replace as dc_replace

from sb.kernel.interaction.adapters.component import dispatch_component
from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.registry import register_panel
from sb.spec.panels import NavigationSpec
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered

from tests.unit.panels.conftest import make_action, make_actor, make_panel

run = asyncio.run

_HEX32 = re.compile(r"^[0-9a-f]{32}$")


class FakePresenter:
    def __init__(self):
        self.presented = []
        self._next_id = 500

    async def __call__(self, rendered, req):
        self.presented.append(rendered)
        self._next_id += 1
        return self._next_id


class FakeResponder:
    surface = Surface.COMPONENT

    def __init__(self):
        self.denials: list[str] = []
        self.acks: list[bool] = []
        self.rendered: list[object] = []

    def is_acked(self):
        return bool(self.acks)

    def committed_visibility(self):
        return None

    async def ack(self, *, ephemeral):
        self.acks.append(ephemeral)

    async def deny(self, message, *, ephemeral):
        self.denials.append(message)

    async def open_modal(self, modal_ref):
        pass

    async def open_confirm(self, prompt):
        pass

    async def render(self, result):
        self.rendered.append(result)


def _session_panel(handler_name="test.session_click"):
    if not is_registered(HandlerRef(handler_name)):
        @handler(handler_name)
        async def _click(req):
            _click.calls.append(req)

            class _R:
                outcome = "success"
                user_message = "clicked"

            return _R()

        _click.calls = []
    action = make_action(action_id="go", label="Go",
                        handler=HandlerRef(handler_name),
                        audience_tier="user")
    return make_panel(
        panel_id="game.session", subsystem="games", actions=(action,),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True)


def _open(spec, presenter, args=None, *, invoker=make_actor()):
    register_panel(spec)
    panel_engine.install_panel_presenter(presenter)
    req = ResolveRequest(
        surface=Surface.PREFIX, target=TargetRef(key="games.x", spec=object()),
        actor=invoker, guild_id=42, channel_id=7, args=dict(args or {}),
        responder=FakeResponder(), origin=object())
    run(panel_engine.open_panel(PanelRef(spec.panel_id), req))
    return presenter.presented[-1]


def _interaction(custom_id, user_id=1):
    from types import SimpleNamespace

    return SimpleNamespace(
        id=999, user=SimpleNamespace(id=user_id, name="u"),
        guild=SimpleNamespace(id=42, owner_id=0),
        channel_id=7, message=SimpleNamespace(id=1),
        data={"custom_id": custom_id, "component_type": 2})


def test_session_view_mints_32hex_ids_and_binds_args():
    rendered = _open(_session_panel(), FakePresenter(),
                     args={"argv": ("25",)})
    (button,) = rendered.components
    assert _HEX32.match(button.custom_id), button.custom_id
    binding = panel_engine.ephemeral_route(button.custom_id)
    assert binding is not None
    assert binding.panel_id == "game.session"
    assert binding.component_id == "go"
    assert binding.args["argv"] == ("25",)
    assert binding.args["session_action"] == "go"
    assert binding.invoker_id == 1          # audience=invoker default


def test_session_view_is_never_anchored_but_grammar_panels_are():
    anchored = []

    async def anchor_store(**kw):
        anchored.append(kw)

    panel_engine.install_panel_anchor_store(anchor_store)
    _open(_session_panel(), FakePresenter())
    assert anchored == []                   # session view: no anchor row
    plain = make_panel(panel_id="econ.plain", subsystem="economy",
                       actions=(make_action(handler=HandlerRef("test.session_click")),))
    _open(plain, FakePresenter())
    assert len(anchored) == 1               # channel-sent grammar panel anchors


def test_session_click_reenters_resolve_with_bound_args():
    rendered = _open(_session_panel("test.session_click2"), FakePresenter(),
                     args={"argv": ("10",)})
    (button,) = rendered.components
    responder = FakeResponder()
    run(dispatch_component(_interaction(button.custom_id, user_id=1),
                           responder=responder))
    assert responder.denials == []
    from sb.spec.refs import resolve as resolve_ref

    clicked = resolve_ref(HandlerRef("test.session_click2"))
    (req,) = clicked.calls
    assert req.args["argv"] == ("10",)
    assert req.args["session_action"] == "go"
    assert req.target.key == "game.session.go"


def test_session_click_is_invoker_locked():
    rendered = _open(_session_panel("test.session_click3"), FakePresenter())
    (button,) = rendered.components
    responder = FakeResponder()
    run(dispatch_component(_interaction(button.custom_id, user_id=777),
                           responder=responder))
    # the shipped views' interaction_check copy (views/rps/solo_play.py)
    assert responder.denials == ["This game isn't yours."]


def test_expired_session_click_gets_polite_expiry():
    rendered = _open(_session_panel("test.session_click4"), FakePresenter())
    (button,) = rendered.components
    binding = panel_engine._ephemeral[button.custom_id]
    panel_engine._ephemeral[button.custom_id] = dc_replace(
        binding, opened_at=time.monotonic() - 10_000)
    responder = FakeResponder()
    run(dispatch_component(_interaction(button.custom_id, user_id=1),
                           responder=responder))
    assert responder.denials == [
        "This session has expired — start a new one."]
    assert panel_engine.ephemeral_route(button.custom_id) is None


def test_unknown_32hex_id_gets_polite_expiry():
    responder = FakeResponder()
    run(dispatch_component(_interaction("ab" * 16, user_id=1),
                           responder=responder))
    assert responder.denials == [
        "This session has expired — start a new one."]


def test_session_view_override_ids_stay_verbatim():
    """A custom_id_override component keeps its VERBATIM id inside a session
    view (the shipped timeout views mixed auto-ids with explicit persistent
    child-forwarding ids — utility_cog's `utility:open:<child>` buttons;
    goldens/utility/sweep_utilitymenu pins the mix). It stays routable
    through the ONE static table, never the ephemeral bindings."""
    from sb.kernel.panels.registry import static_route
    from sb.spec.panels import LayoutSpec, PageSpec

    minted = make_action(action_id="go",
                         handler=HandlerRef("test.session_click"))
    pinned = make_action(action_id="open_child", label="💬 Child",
                         handler=HandlerRef("test.session_click"),
                         custom_id_override="utility_test:open:child")
    spec = make_panel(
        panel_id="game.mixed", subsystem="games",
        actions=(minted, pinned),
        layout=LayoutSpec(pages=(PageSpec(rows=(("go",), ("open_child",))),)),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True)
    rendered = _open(spec, FakePresenter())
    by_id = {c.custom_id: c for c in rendered.components}
    assert "utility_test:open:child" in by_id          # verbatim on the wire
    (minted_id,) = [cid for cid in by_id if cid != "utility_test:open:child"]
    assert _HEX32.match(minted_id), minted_id          # sibling still minted
    assert panel_engine.ephemeral_route("utility_test:open:child") is None
    binding = static_route("utility_test:open:child")
    assert binding is not None and binding.component_id == "open_child"


def test_open_panel_returns_session_message_key():
    """open_panel returns the stored session's key so an opening handler can
    drive a follow-up refresh (the shipped send-then-edit !ping flow)."""
    presenter = FakePresenter()
    spec = _session_panel()
    register_panel(spec)
    panel_engine.install_panel_presenter(presenter)
    req = ResolveRequest(
        surface=Surface.PREFIX, target=TargetRef(key="games.x", spec=object()),
        actor=make_actor(), guild_id=42, channel_id=7, args={},
        responder=FakeResponder(), origin=object())
    key = run(panel_engine.open_panel(PanelRef(spec.panel_id), req))
    assert key == "501"                        # FakePresenter's minted id
    assert panel_engine.session_for(key) is not None
