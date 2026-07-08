"""S9b engine: OPEN_PANEL through resolve(), the presenter port, sessions +
invoker lock, nav dispatch through the component adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field as dc_field

from sb.kernel.interaction.adapters.component import (
    dispatch_component,
    install_dynamic_dispatcher,
)
from sb.kernel.interaction.request import ResolveRequest, Surface, TargetRef
from sb.kernel.interaction.resolve import install_panel_engine, resolve
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.registry import register_hub, register_panel
from sb.kernel.panels.render import RenderedPanel
from sb.spec.outcomes import ReplyVisibility
from sb.spec.panels import Audience
from sb.spec.refs import PanelRef

from tests.unit.panels.conftest import make_action, make_actor, make_panel

run = asyncio.run


class FakeResponder:
    surface = Surface.SLASH

    def __init__(self):
        self.denials: list = []
        self.acks: list = []

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
        pass


class FakePresenter:
    def __init__(self):
        self.presented: list[RenderedPanel] = []
        self._next_id = 100

    async def __call__(self, rendered, req):
        self.presented.append(rendered)
        self._next_id += 1
        return self._next_id


@dataclass
class OpenPanelSpec:
    """A duck-typed command spec whose route is a PanelRef."""

    route: object
    authority_ref: str = ""
    enabled_when: str = ""
    reply_visibility: object = ReplyVisibility.EPHEMERAL
    defer_mode: object = None
    cooldown: object = None
    confirm: object = None
    owner_subsystem: str = "economy"


def make_req(spec, responder=None, origin=None):
    return ResolveRequest(
        surface=Surface.SLASH, target=TargetRef(key="economy.shop", spec=spec),
        actor=make_actor(), guild_id=42, channel_id=7, args={},
        responder=responder or FakeResponder(), origin=origin or object())


def test_open_panel_through_resolve_presents_and_stores_session():
    register_panel(make_panel(actions=(make_action(),)))
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)
    install_panel_engine(panel_engine.open_panel)

    result = run(resolve(make_req(OpenPanelSpec(route=PanelRef("econ.shop")))))
    assert result.outcome == "success"
    assert presenter.presented and presenter.presented[0].panel_id == "econ.shop"
    session = panel_engine.session_for("101")
    assert session is not None and session.invoker_id == 1


def test_presenter_not_installed_classifies_as_error_not_crash():
    register_panel(make_panel(actions=(make_action(),)))
    install_panel_engine(panel_engine.open_panel)
    result = run(resolve(make_req(OpenPanelSpec(route=PanelRef("econ.shop")))))
    assert result.outcome != "success"      # enveloped, never raised


def test_invoker_lock_semantics():
    assert panel_engine.may_interact(None, 999)          # no session ⇒ open
    session = panel_engine.PanelSession(panel_id="p", invoker_id=1, audience="invoker")
    assert panel_engine.may_interact(session, 1)
    assert not panel_engine.may_interact(session, 2)
    public = panel_engine.PanelSession(panel_id="p", invoker_id=None, audience="public")
    assert panel_engine.may_interact(public, 2)


class FakeInteraction:
    def __init__(self, custom_id):
        self.data = {"custom_id": custom_id}
        self.guild = None
        self.user = None
        self.channel_id = 7
        self.id = 1


def test_component_adapter_routes_panel_binding_through_resolve():
    register_panel(make_panel(actions=(make_action("buy", "Buy"),)))
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)
    responder = FakeResponder()
    # the action has no handler => resolve() envelopes it as an error, but the
    # dispatch itself found the ComponentBinding (no "no longer available").
    result = run(dispatch_component(FakeInteraction("econ.shop.buy"),
                                    responder=responder))
    assert result is not None
    assert not any("no longer available" in d for d in responder.denials)


def test_component_adapter_nav_hub_and_back_rebuild_fresh():
    hub = make_panel(panel_id="econ.hub", actions=(make_action("open", "Open"),))
    register_panel(hub)
    register_hub("economy", "econ.hub")
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)

    run(dispatch_component(FakeInteraction("nav:hub:economy"),
                           responder=FakeResponder()))
    assert presenter.presented[-1].panel_id == "econ.hub"
    run(dispatch_component(FakeInteraction("nav:back:econ.hub"),
                           responder=FakeResponder()))
    assert presenter.presented[-1].panel_id == "econ.hub"


def test_component_adapter_page_turn():
    from sb.spec.panels import LayoutSpec, PageSpec
    spec = make_panel(actions=(make_action("a", "A"), make_action("b", "B")),
                      layout=LayoutSpec(pages=(PageSpec(rows=(("a",),)),
                                               PageSpec(rows=(("b",),)))))
    register_panel(spec)
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)
    run(dispatch_component(FakeInteraction("nav:page:econ.shop:1"),
                           responder=FakeResponder()))
    assert presenter.presented[-1].page == 1


def test_component_adapter_dynamic_and_expiry():
    seen = []

    async def dyn(routed, interaction):
        seen.append(routed)
        return "handled"
    install_dynamic_dispatcher(dyn)
    result = run(dispatch_component(FakeInteraction("g1:blackjack:s1:hit"),
                                    responder=FakeResponder()))
    assert result == "handled" and seen[0].session_id == "s1"

    responder = FakeResponder()
    run(dispatch_component(FakeInteraction("totally_dead_id"), responder=responder))
    assert responder.denials and "expired" in responder.denials[0]


def test_session_expiry_clock():
    s = panel_engine.PanelSession(panel_id="p", invoker_id=1, audience="invoker",
                                  timeout_s=None)
    assert not s.expired                     # persistent: never expires
    s2 = panel_engine.PanelSession(panel_id="p", invoker_id=1, audience="invoker",
                                   timeout_s=0)
    s2.opened_at -= 1
    assert s2.expired
