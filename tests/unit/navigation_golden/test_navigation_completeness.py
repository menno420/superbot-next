"""The A-3 navigation-completeness golden (canonical plan §5 step 11 —
the CI proof of Q-0231): drive the generated hub through every declared
node + the re-render path via the REAL panel engine; assert
framework-injected working Back/Home per state.

Two suites:
  - TestGoldenOverRegisteredPanels — the golden proper: walks WHATEVER is
    registered. Vacuously green over zero panels today; arms automatically
    as port bands register real panels (the fixture-manifest suite below
    proves the walker cannot false-green).
  - TestWalkerSemantics — the walker's own oracle-quality proofs over a
    fixture hub, including the negative cases (missing parent fallback,
    unregistered parent).

"Every feature in >=1 preset" is carried as `presets_checked=False` until
band-1 mints the preset grammar (loud arm-later, never a silent pass).
"""

from __future__ import annotations

import asyncio

from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.registry import register_hub, register_panel
from sb.spec.panels import (
    Audience,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
)
from sb.kernel.interaction.request import ActorRef
from sb.spec.refs import PanelRef
from sim.navigation_walk import walk_navigation


def make_actor(**kw) -> ActorRef:
    defaults = dict(user_id=1, is_guild_operator=False, is_bot_owner=False,
                    is_dm=False, member_tier="administrator")
    defaults.update(kw)
    return ActorRef(**defaults)


def _ctx() -> PanelContext:
    return PanelContext(
        bot=None, guild_id=42, actor=make_actor(), channel_id=7,
        origin=PanelOrigin.INTERACTION, audience=Audience.INVOKER,
    )


def _panel(panel_id, subsystem, *, actions=(), parent=None, show_home=True):
    action_specs = tuple(
        PanelActionSpec(action_id=aid, label=label, handler=handler)
        for aid, label, handler in actions
    )
    ids = tuple(a.action_id for a in action_specs)
    return PanelSpec(
        panel_id=panel_id, subsystem=subsystem, title=panel_id.title(),
        actions=action_specs,
        navigation=NavigationSpec(
            parent=PanelRef(parent) if parent else None, show_home=show_home),
        layout=LayoutSpec(pages=(PageSpec(rows=(ids,)),) if ids else ()),
    )


def _register_hub_world():
    """hub.main -> economy.panel -> economy.shop (a 2-hop generated hub)."""
    register_panel(_panel(
        "hub.main", "hub",
        actions=(("open_econ", "Economy", PanelRef("economy.panel")),),
        show_home=False,
    ))
    register_panel(_panel(
        "economy.panel", "economy",
        actions=(("open_shop", "Item Shop", PanelRef("economy.shop")),),
        parent="hub.main",
    ))
    register_panel(_panel("economy.shop", "economy", parent="economy.panel"))
    register_hub("main", "hub.main")


class TestGoldenOverRegisteredPanels:
    def test_navigation_completeness_golden(self):
        """THE golden: every registered node reachable, Back+Home injected
        and bound, re-render survives. Green over the empty registry today;
        arms as bands register panels."""
        report = asyncio.run(walk_navigation(_ctx(), subsystem_hubs={
            "economy": "main", "hub": "main"}))
        assert report.ok, report.problems

    def test_preset_leg_is_a_loud_arm_later(self):
        report = asyncio.run(walk_navigation(_ctx()))
        assert report.presets_checked is False  # band-1 grammar; never silent


class TestWalkerSemantics:
    def test_fixture_hub_walks_green(self):
        _register_hub_world()
        report = asyncio.run(walk_navigation(_ctx(), subsystem_hubs={
            "economy": "main", "hub": "main"}))
        assert report.ok, report.problems
        assert set(report.states) == {"hub.main", "economy.panel", "economy.shop"}
        assert all(s.reachable for s in report.states.values())
        child = report.states["economy.panel"]
        assert child.back_ok is True
        assert child.home_ok is True
        assert child.rerender_ok is True

    def test_direct_entry_without_parent_fallback_is_red(self):
        _register_hub_world()
        register_panel(_panel("orphan.panel", "orphan", show_home=False))
        report = asyncio.run(walk_navigation(_ctx(), subsystem_hubs={
            "economy": "main", "hub": "main"}))
        assert not report.ok
        assert any("orphan.panel" in p and "parent fallback" in p
                   for p in report.problems)

    def test_direct_entry_with_semantic_parent_is_ok(self):
        _register_hub_world()
        register_panel(_panel("deep.link", "economy", parent="economy.panel"))
        report = asyncio.run(walk_navigation(_ctx(), subsystem_hubs={
            "economy": "main", "hub": "main"}))
        assert report.ok, report.problems
        assert report.states["deep.link"].back_ok is True

    def test_unregistered_parent_is_red(self):
        register_panel(_panel("lost.child", "x", parent="never.registered"))
        report = asyncio.run(walk_navigation(_ctx()))
        assert any("never.registered" in p for p in report.problems)

    def test_home_slot_bound_in_the_static_table(self):
        _register_hub_world()
        report = asyncio.run(walk_navigation(_ctx(), subsystem_hubs={
            "economy": "main", "hub": "main"}))
        # home_ok asserts BOTH render presence and static-table binding
        assert report.states["economy.shop"].home_ok is True
