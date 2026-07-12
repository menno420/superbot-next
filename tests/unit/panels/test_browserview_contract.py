"""Contract tests for the shared BrowserView engine (K8/S9b — D-0034):

  * the engine honors the ListSpec DECLARATIONS — a ListSpec whose
    sort_options are X/Y/Z yields exactly those sort choices, and its
    filter_options become the filter choices (plus the leading "All");
  * a control-click custom_id re-resolves to the expected page/sort/filter,
    re-rendering the panel with the new browse state;
  * the engine reuses the EXISTING component routing seam — browse clicks
    ride the same ``dispatch_component`` → §3.4 router → panel-engine path
    every other panel component uses (mirrors test_engine_dispatch's
    page-turn/nav contract), never a second listener.
"""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.interaction.adapters.component import dispatch_component
from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.panels import browserview as bv
from sb.kernel.panels import engine as panel_engine
from sb.kernel.panels.browserview import ALL_FILTER, BrowseState
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.registry import register_panel
from sb.kernel.panels.render import RenderedPanel, render_panel
from sb.spec.panels import (
    Audience,
    LayoutSpec,
    ListBlock,
    ListSpec,
    NavigationSpec,
    PageSpec,
    PanelSpec,
)
from sb.spec.refs import HandlerRef, ProviderRef, clear_ref_table, handler, provider

from tests.unit.panels.conftest import make_actor

run = asyncio.run

ROWS = (
    {"name": "Axe", "type": "Tools", "quantity": 3},
    {"name": "Copper", "type": "Mining", "quantity": 40},
    {"name": "Diamond", "type": "Mining", "quantity": 1},
    {"name": "Bread", "type": "Food", "quantity": 12},
    {"name": "Rod", "type": "Tools", "quantity": 2},
)

PANEL_ID = "inv.cat_all"


@pytest.fixture(autouse=True)
def _clean_refs():
    clear_ref_table()
    yield
    clear_ref_table()


def _install_refs():
    @provider("browse.rows")
    async def rows(ctx):
        return ROWS

    @handler("browse.render_line")
    def render_line(row):
        return f"{row['name']} x{row['quantity']}"


def _spec(page_size=2):
    return PanelSpec(
        panel_id=PANEL_ID, subsystem="inventory", title="All Items",
        audience=Audience.INVOKER,
        body=(ListBlock(
            list_spec=ListSpec(
                item_render_ref=HandlerRef("browse.render_line"),
                page_size=page_size,
                sort_options=("name", "quantity"),
                filter_options=("Tools", "Mining", "Food"),
                default_sort="name"),
            provider=ProviderRef("browse.rows")),),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)))


def _ctx():
    return PanelContext(
        bot=None, guild_id=42, actor=make_actor(), channel_id=7,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER,
        locale=LocaleContext())


# --- contract 1: the engine honors ListSpec declarations ------------------------

def test_render_arms_exactly_the_declared_sort_and_filter_choices():
    _install_refs()
    spec = _spec()
    state = BrowseState(PANEL_ID, 0, sort="name", filter=ALL_FILTER, page=0)
    rendered = run(render_panel(spec, _ctx(), browse=state))
    selectors = [c for c in rendered.components if c.kind == "selector"]
    assert len(selectors) == 2
    sort_sel, filter_sel = selectors
    # exactly the declared sort_options — no more, no fewer.
    assert [o["value"] for o in sort_sel.options] == ["name", "quantity"]
    # the declared filter_options, with the engine's leading "All".
    assert [o["value"] for o in filter_sel.options] == \
        [ALL_FILTER, "Tools", "Mining", "Food"]


def test_render_first_page_reflects_default_sort_and_paging():
    _install_refs()
    spec = _spec(page_size=2)
    state = BrowseState(PANEL_ID, 0, sort="", filter=ALL_FILTER, page=0)
    rendered = run(render_panel(spec, _ctx(), browse=state))
    # default_sort="name" → first two are Axe, Bread; page_size 2.
    assert "Axe x3" in rendered.embed.description
    assert "Bread x12" in rendered.embed.description
    assert "Rod x2" not in rendered.embed.description       # page 2


def test_render_no_browse_is_unchanged_static_view():
    # the default (browse=None) render never emits browse controls — the
    # non-churn guarantee (no surface's default rendering changes).
    _install_refs()
    rendered = run(render_panel(_spec(), _ctx()))
    assert not any(c.custom_id.startswith("nav:browse:")
                   for c in rendered.components)


# --- shared dispatch harness (mirrors test_engine_dispatch) ---------------------

class FakeResponder:
    from sb.kernel.interaction.request import Surface as _S
    surface = _S.COMPONENT

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

    async def render(self, result):
        pass


class FakePresenter:
    def __init__(self):
        self.presented: list[RenderedPanel] = []
        self._next_id = 500

    async def __call__(self, rendered, req):
        self.presented.append(rendered)
        self._next_id += 1
        return self._next_id


class FakeInteraction:
    def __init__(self, custom_id, values=None):
        self.data = {"custom_id": custom_id}
        if values is not None:
            self.data["values"] = list(values)
        self.guild = None
        self.user = None
        self.channel_id = 7
        self.id = 1


def _armed():
    """Register the panel + refs + presenter; return the presenter."""
    _install_refs()
    register_panel(_spec())
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)
    return presenter


# --- contract 2 + 3: a click re-resolves through the EXISTING seam ---------------

def test_next_button_click_re_resolves_to_the_next_page():
    presenter = _armed()
    responder = FakeResponder()
    # a "next" click from page 0 → page 1 (default sort, no filter).
    cid = "nav:browse:next:inv.cat_all:0:-1:-1:0"
    run(dispatch_component(FakeInteraction(cid), responder=responder))
    assert not responder.denials                     # not the expiry terminal
    presented = presenter.presented[-1]
    # page 2 of name-sorted rows (Axe, Bread | Copper, Diamond | Rod) → Copper, Diamond
    assert "Copper x40" in presented.embed.description
    assert "Diamond x1" in presented.embed.description
    assert "Axe x3" not in presented.embed.description


def test_sort_select_click_re_resolves_with_the_chosen_key():
    presenter = _armed()
    # a sort select carries its new key in the interaction's ``values``.
    cid = "nav:browse:sort:inv.cat_all:0:-1:-1:0"
    run(dispatch_component(FakeInteraction(cid, values=("quantity",)),
                           responder=FakeResponder()))
    presented = presenter.presented[-1]
    # quantity-ascending → first page is Diamond(1), Rod(2)
    desc = presented.embed.description
    assert "Diamond x1" in desc and "Rod x2" in desc
    assert "Copper x40" not in desc                   # trails to a later page


def test_filter_select_click_re_resolves_and_resets_page():
    presenter = _armed()
    # currently on page 1; a filter select resets to page 0 of the filtered set.
    cid = "nav:browse:filter:inv.cat_all:0:-1:-1:1"
    run(dispatch_component(FakeInteraction(cid, values=("Mining",)),
                           responder=FakeResponder()))
    presented = presenter.presented[-1]
    desc = presented.embed.description
    # Mining = Copper, Diamond only; nothing else present.
    assert "Copper x40" in desc and "Diamond x1" in desc
    assert "Axe x3" not in desc and "Bread x12" not in desc


def test_rendered_control_ids_round_trip_through_dispatch():
    # end-to-end: render arms the controls, and the "next" control's own
    # custom_id, fed back through the SAME dispatch seam, advances the page —
    # the loop closes with no hand-built id.
    _install_refs()
    spec = _spec()
    register_panel(spec)
    presenter = FakePresenter()
    panel_engine.install_panel_presenter(presenter)
    state = BrowseState(PANEL_ID, 0, sort="name", filter=ALL_FILTER, page=0)
    rendered = run(render_panel(spec, _ctx(), browse=state))
    next_btn = next(c for c in rendered.components if c.label == "▶")
    run(dispatch_component(FakeInteraction(next_btn.custom_id),
                           responder=FakeResponder()))
    assert "Copper x40" in presenter.presented[-1].embed.description


def test_browse_click_uses_the_same_router_as_other_components():
    # the browse family routes through the §3.4 router into a NavBinding —
    # the SAME table/precedence page-turn and hub/back nav use (no parallel
    # scheme). A stale/malformed browse id still lands on polite expiry.
    from sb.kernel.panels.registry import NavBinding
    from sb.kernel.panels.router import route as route_custom_id

    routed = route_custom_id("nav:browse:next:inv.cat_all:0:-1:-1:0")
    assert isinstance(routed, NavBinding) and routed.kind == "browse"

    presenter = _armed()
    responder = FakeResponder()
    # a browse id whose block index doesn't exist decodes to None → expiry,
    # never a crash or a mis-render.
    run(dispatch_component(FakeInteraction("nav:browse:next:inv.cat_all:9:-1:-1:0"),
                           responder=responder))
    assert responder.denials and "expired" in responder.denials[0].lower()
    assert not presenter.presented                    # nothing re-rendered
