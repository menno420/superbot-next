"""S9b pure render model: budgets, blocks, locale seam, nav injection,
page-turn, visible_when gating."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.interaction.locale import LocaleContext, install_copy_resolver
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.render import (
    DESCRIPTION_LIMIT,
    EMBED_TOTAL_LIMIT,
    install_hub_resolver,
    render_panel,
)
from sb.spec.panels import (
    Audience,
    ColumnSpec,
    EmbedFrameSpec,
    FieldsBlock,
    LayoutSpec,
    ListBlock,
    ListSpec,
    NavRouteSpec,
    NavigationSpec,
    PageSpec,
    TableBlock,
    TableSpec,
    TextBlock,
)
from sb.spec.refs import PanelRef, ProviderRef, clear_ref_table, provider

from tests.unit.panels.conftest import make_action, make_actor, make_panel

run = asyncio.run


def ctx(**kw):
    defaults = dict(bot=None, guild_id=42, actor=make_actor(), channel_id=7,
                    origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER,
                    locale=LocaleContext())
    defaults.update(kw)
    return PanelContext(**defaults)


@pytest.fixture(autouse=True)
def _clean_refs():
    clear_ref_table()
    yield
    clear_ref_table()


def test_text_block_and_frame_footer():
    spec = make_panel(body=(TextBlock("Welcome to the shop."),),
                      frame=EmbedFrameSpec(alt_text="shop banner"))
    rendered = run(render_panel(spec, ctx()))
    assert "Welcome to the shop." in rendered.embed.description
    assert rendered.embed.footer == "economy"        # footer_mode=subsystem
    assert rendered.embed.alt_text == "shop banner"  # L-24 rider 1 carried


def test_fields_block_provider_and_broken_provider_degrades():
    @provider("t.fields")
    async def fields(_ctx):
        return (("Balance", "100"), ("Bank", "250"))
    spec = make_panel(body=(FieldsBlock(provider=ProviderRef("t.fields")),
                            FieldsBlock(provider=ProviderRef("t.missing"))))
    rendered = run(render_panel(spec, ctx()))
    assert ("Balance", "100") in rendered.embed.fields
    assert len(rendered.embed.fields) == 2           # missing provider degraded, no crash


def test_table_and_list_blocks_with_empty_state():
    @provider("t.rows")
    async def rows(_ctx):
        return ({"name": "Sword", "price": "10"},)
    table = TableSpec(columns=(ColumnSpec("name", "Name"), ColumnSpec("price", "Price")))
    spec = make_panel(body=(
        TableBlock(table=table, provider=ProviderRef("t.rows")),
        ListBlock(list_spec=ListSpec(empty_state="Inventory is empty."), provider=None)))
    rendered = run(render_panel(spec, ctx()))
    assert "Sword | 10" in rendered.embed.description
    assert "Inventory is empty." in rendered.embed.description


def test_budget_clamping_engine_enforced():
    spec = make_panel(body=(TextBlock("x" * 10_000),))
    rendered = run(render_panel(spec, ctx()))
    assert len(rendered.embed.description) <= DESCRIPTION_LIMIT
    e = rendered.embed
    total = len(e.title) + len(e.description) + len(e.footer) + sum(
        len(n) + len(v) for n, v in e.fields)
    assert total <= EMBED_TOTAL_LIMIT


def test_max_fields_respects_frame_budget():
    @provider("t.many")
    async def many(_ctx):
        return tuple((f"f{i}", "v") for i in range(40))
    spec = make_panel(body=(FieldsBlock(provider=ProviderRef("t.many")),),
                      frame=EmbedFrameSpec(max_fields=3))
    rendered = run(render_panel(spec, ctx()))
    assert len(rendered.embed.fields) == 3


def test_locale_seam_identity_default_and_swap_in():
    spec = make_panel(body=(TextBlock("Hello"),))
    rendered = run(render_panel(spec, ctx()))
    assert "Hello" in rendered.embed.description    # identity resolver verbatim

    class Upper:
        def resolve(self, copy, *, locale):
            return copy.upper()
    install_copy_resolver(Upper())
    rendered = run(render_panel(spec, ctx()))
    assert "HELLO" in rendered.embed.description    # swap-in, zero spec changes


def test_nav_injection_help_home_back_row4():
    install_hub_resolver(lambda subsystem: "economy")
    spec = make_panel(navigation=NavigationSpec(
        parent=PanelRef("econ.hub"),
        extra_routes=(NavRouteSpec(label="Rules", route=PanelRef("econ.rules")),)))
    rendered = run(render_panel(spec, ctx()))
    ids = {c.custom_id: c for c in rendered.components}
    assert "nav:help" in ids and ids["nav:help"].row == 4
    assert "nav:hub:economy" in ids                  # FOLLOW_PARENT resolved at render
    assert "nav:back:econ.hub" in ids
    assert "nav:back:econ.rules" in ids              # extra route


def test_help_panel_gets_no_help_button_and_no_hub_without_resolver():
    spec = make_panel(panel_id="help.home", subsystem="help")
    rendered = run(render_panel(spec, ctx()))
    ids = [c.custom_id for c in rendered.components]
    assert "nav:help" not in ids
    assert not any(i.startswith("nav:hub:") for i in ids)   # no resolver installed


def test_page_turn_controls_engine_injected():
    a, b = make_action("a", "A"), make_action("b", "B")
    spec = make_panel(actions=(a, b), layout=LayoutSpec(pages=(
        PageSpec(rows=(("a",),)), PageSpec(rows=(("b",),)))))
    page0 = run(render_panel(spec, ctx(), page=0))
    ids0 = [c.custom_id for c in page0.components]
    assert "econ.shop.a" in ids0 and "econ.shop.b" not in ids0
    assert "nav:page:econ.shop:1" in ids0 and "nav:page:econ.shop:-1" not in ids0
    page1 = run(render_panel(spec, ctx(), page=1))
    ids1 = [c.custom_id for c in page1.components]
    assert "econ.shop.b" in ids1 and "nav:page:econ.shop:0" in ids1
    assert page1.page_count == 2


def test_visible_when_gates_component_at_render():
    shown = make_action("shown", "Shown")
    hidden = make_action("hidden", "Hidden", visible_when="flag:never")
    spec = make_panel(actions=(shown, hidden),
                      layout=LayoutSpec(pages=(PageSpec(rows=(("shown", "hidden"),)),)))
    rendered = run(render_panel(spec, ctx()))
    ids = [c.custom_id for c in rendered.components]
    assert "econ.shop.shown" in ids and "econ.shop.hidden" not in ids


def test_invoker_lock_only_for_invoker_audience():
    spec = make_panel()
    rendered = run(render_panel(spec, ctx()))
    assert rendered.invoker_lock == 1
    public = make_panel(audience=Audience.PUBLIC)
    rendered = run(render_panel(public, ctx()))
    assert rendered.invoker_lock is None
