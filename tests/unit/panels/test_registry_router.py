"""S9b registry mint + the §3.4 router precedence (static → g<N>: → expiry)."""

from __future__ import annotations

import pytest

from sb.kernel.panels.compile import PanelCompileError
from sb.kernel.panels.registry import (
    ComponentBinding,
    NavBinding,
    clear_panels_for_tests,
    get_panel,
    register_hub,
    register_panel,
    static_route,
)
from sb.kernel.panels.router import (
    DynamicRoute,
    ExpiredRoute,
    parse_g1,
    register_scheme_parser,
    route,
)
from sb.spec.panels import LayoutSpec, NavigationSpec, PageSpec
from sb.spec.refs import PanelRef

from tests.unit.panels.conftest import make_action, make_panel


def test_registration_mints_canonical_and_legacy_ids():
    spec = make_panel(actions=(make_action("buy", "Buy"),
                               make_action("sell", "Sell", custom_id_override="legacy_sell")),
                      layout=LayoutSpec(pages=(PageSpec(rows=(("buy", "sell"),)),)))
    register_panel(spec)
    b = static_route("econ.shop.buy")
    assert isinstance(b, ComponentBinding) and b.component_id == "buy"
    legacy = static_route("legacy_sell")
    assert isinstance(legacy, ComponentBinding) and legacy.component_id == "sell"
    assert get_panel("econ.shop") is spec


def test_reregistration_identical_ok_differing_fails():
    spec = make_panel(actions=(make_action(),))
    register_panel(spec)
    register_panel(spec)   # no-op
    with pytest.raises(PanelCompileError):
        register_panel(make_panel(actions=(make_action(),), title="Other"))


def test_nav_ids_minted_help_back_hub_page():
    parent = make_panel(panel_id="econ.hub", actions=(make_action("open", "Open"),))
    register_panel(parent)
    child = make_panel(
        panel_id="econ.shop",
        actions=(make_action("a", "A"), make_action("b", "B")),
        navigation=NavigationSpec(parent=PanelRef("econ.hub")),
        layout=LayoutSpec(pages=(PageSpec(rows=(("a",),)), PageSpec(rows=(("b",),)))))
    register_panel(child)
    register_hub("economy", "econ.hub")

    assert static_route("nav:help") == NavBinding(kind="help", target="help")
    assert static_route("nav:back:econ.hub") == NavBinding(kind="back", target="econ.hub")
    assert static_route("nav:hub:economy") == NavBinding(kind="hub", target="economy")
    assert static_route("nav:page:econ.shop:1") == NavBinding(
        kind="page", target="econ.shop:1")


def test_custom_id_collision_is_registration_error():
    register_panel(make_panel(panel_id="a.p", actions=(
        make_action("x", "X", custom_id_override="shared"),)))
    with pytest.raises(PanelCompileError):
        register_panel(make_panel(panel_id="b.p", actions=(
            make_action("y", "Y", custom_id_override="shared"),)))


def test_router_precedence_static_beats_scheme_parse():
    # a legacy override CANNOT look like a scheme id (compile fence), so the
    # precedence contract is: static first, then scheme parse, then expiry.
    register_panel(make_panel(actions=(make_action("buy", "Buy"),)))
    assert isinstance(route("econ.shop.buy"), ComponentBinding)
    parsed = route("g1:blackjack:sess42:hit")
    assert parsed == DynamicRoute(scheme="g1", key="blackjack",
                                  session_id="sess42", action="hit")
    dead = route("nonsense_id")
    assert isinstance(dead, ExpiredRoute) and dead.disable_components


def test_malformed_or_unknown_scheme_yields_polite_expiry():
    assert parse_g1("g1:only:two") is None
    assert isinstance(route("g1:only:two"), ExpiredRoute)
    assert isinstance(route("g9:some:future:id"), ExpiredRoute)   # no parser yet


def test_register_scheme_parser_g2_window():
    def parse_g2(cid):
        parts = cid.split(":")
        return DynamicRoute("g2", parts[1], parts[2], parts[3]) if len(parts) == 4 else None
    register_scheme_parser("g2", parse_g2)
    assert route("g2:k:s:a").scheme == "g2"
    assert route("g1:k:s:a").scheme == "g1"    # deprecation window: g1 keeps parsing
    with pytest.raises(ValueError):
        register_scheme_parser("g2", parse_g2)
    with pytest.raises(ValueError):
        register_scheme_parser("nope", parse_g2)


def test_clear_resets_everything():
    register_panel(make_panel(actions=(make_action(),)))
    clear_panels_for_tests()
    assert static_route("econ.shop.do") is None
    with pytest.raises(LookupError):
        get_panel("econ.shop")
