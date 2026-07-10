"""The category-grouped help projection (D-0055): shipped mother-hub
grouping over the live inventory — complete coverage (nothing silently
sheds), stable order, budget-safe renders, select round-trips.

Lives in help_band (collected after the band tests — the manifest-import
ordering trap, see TestManifestPanelRegistration's docstring)."""

from __future__ import annotations

import asyncio

import pytest

from sb.domain.help import categories as cats
from sb.domain.help import service
from sb.kernel.interaction.locale import LocaleContext
from sb.kernel.panels.compile import check_panel
from sb.kernel.panels.context import PanelContext, PanelOrigin
from sb.kernel.panels.render import EMBED_TOTAL_LIMIT, MAX_EMBED_FIELDS, render_panel
from sb.spec.panels import Audience
from sb.spec.refs import PanelRef

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_projection():
    """Every test starts (and the module ends) on the REAL inventory."""
    service.build_help_panels()
    yield
    service.build_help_panels()


def _actor(*, operator: bool = False):
    from sb.kernel.interaction.request import ActorRef

    return ActorRef(user_id=7, is_guild_operator=operator, is_bot_owner=False,
                    is_dm=False, member_tier="admin" if operator else "user")


def _ctx(*, operator: bool = False):
    return PanelContext(bot=None, guild_id=42, actor=_actor(operator=operator),
                        channel_id=9,
                        origin=PanelOrigin.INTERACTION, audience=Audience.PUBLIC,
                        locale=LocaleContext())


class TestRosterCoverage:
    def test_every_inventory_subsystem_is_homed_except_help(self):
        inventory = service.command_inventory()
        rosters = cats.category_rosters(inventory.keys())
        homed = {sub for roster in rosters.values() for sub in roster}
        assert homed == set(inventory) - {"help"}    # help IS the surface

    def test_roster_order_is_shipped_first_then_alphabetical(self):
        rosters = cats.category_rosters(
            ["farm", "blackjack", "games", "zz_new_game"])
        # zz_new_game is unmapped → OTHER, never games
        assert rosters["games"] == ("games", "blackjack", "farm")
        assert rosters[cats.OTHER_CATEGORY.key] == ("zz_new_game",)

    def test_every_command_appears_across_the_chunk_providers(self):
        """The no-shed guarantee: the union of a subsystem's chunk panels
        carries EVERY declared command."""
        inventory = service.command_inventory()
        panels = {p.panel_id: p for p in service.build_help_panels()}
        for sub, commands in inventory.items():
            if sub == "help":
                continue
            seen: list[str] = []
            chunk = 0
            while True:
                pid = (f"help.sub_{sub}" if chunk == 0
                       else f"help.sub_{sub}_p{chunk + 1}")
                if pid not in panels:
                    break
                rendered = run(render_panel(panels[pid], _ctx()))
                seen.extend(name.strip("`") for name, _ in rendered.embed.fields)
                assert len(rendered.embed.fields) <= MAX_EMBED_FIELDS
                chunk += 1
            assert seen == [name for name, _ in commands], sub


class TestHomePanel:
    def test_home_lists_categories_not_subsystems(self):
        """The shipped home index (oracle-pinned, parity/goldens/help): the
        registry hubs in shipped order, staff hubs gated on operator-ness —
        6 for a member, all 8 for an operator."""
        panels = {p.panel_id: p for p in service.build_help_panels()}
        rendered = run(render_panel(panels["help.home"], _ctx()))
        names = [n for n, _ in rendered.embed.fields]
        assert any("Games" in n for n in names)
        # staff-only hubs are hidden from plain members (the goldens' 6-row view)
        assert not any("Server & Admin" in n for n in names)
        assert not any("Moderation" in n for n in names)
        assert len(names) == sum(1 for c in cats.CATEGORIES if not c.staff_only)
        operator = run(render_panel(panels["help.home"], _ctx(operator=True)))
        op_names = [n for n, _ in operator.embed.fields]
        assert any("Server & Admin" in n for n in op_names)
        assert len(op_names) == len(cats.CATEGORIES)
        # the shipped field copy: purpose + the hub command, verbatim
        assert operator.embed.fields[0][1] == "Game flows and tournaments.\n→ `!games`"
        assert operator.embed.title == "📚 Help Menu"

    def test_home_renders_inside_every_budget(self):
        panels = {p.panel_id: p for p in service.build_help_panels()}
        for pid, spec in panels.items():
            rendered = run(render_panel(spec, _ctx()))
            e = rendered.embed
            total = (len(e.title) + len(e.description) + len(e.footer)
                     + sum(len(n) + len(v) for n, v in e.fields))
            assert total <= EMBED_TOTAL_LIMIT, pid
            assert len(e.fields) <= MAX_EMBED_FIELDS, pid

    def test_home_select_options_round_trip(self):
        """Provider-fed rich options (the shipped wire shape): value is the
        category KEY; label/description/emoji the registry presentation; the
        legacy custom_id survives verbatim; a non-empty roster's key routes
        to a registered category panel."""
        panels = {p.panel_id: p for p in service.build_help_panels()}
        home = panels["help.home"]
        (selector,) = home.selectors
        assert selector.placeholder == "Pick a category…"   # shipped copy
        assert selector.custom_id_override == "help_categories:select"
        rendered = run(render_panel(home, _ctx(operator=True)))
        (component,) = rendered.components
        assert component.custom_id == "help_categories:select"
        options = component.options
        assert 0 < len(options) <= 25
        assert options[0] == {"label": "Games", "value": "games",
                              "description": "Game flows and tournaments.",
                              "emoji": "🎮"}
        for option in options:
            cat = cats.category_by_key(option["value"])
            assert cat is not None
            if service._rosters.get(cat.key):
                assert f"help.cat_{cat.key}" in panels
        member = run(render_panel(home, _ctx()))
        member_values = [o["value"] for o in member.components[0].options]
        assert "moderation" not in member_values
        assert "admin" not in member_values

    def test_category_select_options_round_trip_to_subsystem_panels(self):
        panels = {p.panel_id: p for p in service.build_help_panels()}
        inventory_keys = service.command_inventory().keys()
        for pid, spec in panels.items():
            if not pid.startswith("help.cat_"):
                continue
            (selector,) = spec.selectors
            assert 0 < len(selector.options_source) <= 25, pid
            for option in selector.options_source:
                sub = cats.subsystem_for_option(option, inventory_keys)
                assert sub is not None, (pid, option)
                assert f"help.sub_{sub}" in panels

    def test_all_panels_compile(self):
        for spec in service.build_help_panels():
            check_panel(spec)


class TestSelectHandlers:
    def test_open_category_routes_to_the_category_panel(self, monkeypatch):
        import sb.kernel.panels.engine as engine

        opened: list[str] = []

        async def fake_open(ref, req):
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        from sb.spec.refs import HandlerRef, resolve as resolve_ref

        handler = resolve_ref(HandlerRef("help.open_category"))

        class Req:
            # home select values are category KEYS (the shipped wire shape)
            args = {"values": (cats.CATEGORIES[0].key,)}

        assert run(handler(Req())) is None
        assert opened == ["help.cat_games"]

    def test_open_category_answers_stale_options_politely(self):
        from sb.spec.refs import HandlerRef, resolve as resolve_ref

        handler = resolve_ref(HandlerRef("help.open_category"))

        class Req:
            args = {"values": ("🗑 Gone",)}

        reply = run(handler(Req()))
        assert reply.user_message == "That category is no longer available."

    def test_open_subsystem_routes_to_the_subsystem_panel(self, monkeypatch):
        import sb.kernel.panels.engine as engine

        opened: list[str] = []

        async def fake_open(ref, req):
            opened.append(ref.name)

        monkeypatch.setattr(engine, "open_panel", fake_open)
        from sb.spec.refs import HandlerRef, resolve as resolve_ref

        handler = resolve_ref(HandlerRef("help.open_subsystem"))

        class Req:
            args = {"values": (cats.subsystem_option("moderation"),)}

        assert run(handler(Req())) is None
        assert opened == ["help.sub_moderation"]


class TestChunking:
    def test_large_subsystems_chain_extra_panels(self):
        inventory = service.command_inventory()
        big = [k for k, v in inventory.items() if len(v) > service.COMMANDS_PER_PAGE]
        assert big, "expected at least one >24-command subsystem (mining/btd6)"
        panels = {p.panel_id: p for p in service.build_help_panels()}
        for sub in big:
            first = panels[f"help.sub_{sub}"]
            assert first.navigation.extra_routes, sub
            assert first.navigation.extra_routes[0].route == PanelRef(
                f"help.sub_{sub}_p2")
            second = panels[f"help.sub_{sub}_p2"]
            assert second.navigation.parent is not None
