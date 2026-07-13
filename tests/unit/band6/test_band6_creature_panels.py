"""The CREATURE parity-flip surfaces: the shipped 🐾 hub (footer literal
+ live "Your progress" field via the renderer_override, the standard
nav row with the "↩ Games" hub label), the four component-less embed
cards (dex / collectors / record / battletop — empty-state bytes
golden-pinned), the CONTENT-only Accept/Decline challenge (opponent
lock + the declined terminal) and the !cbattle guards.

Oracle: menno420/superbot disbot/views/creature/{menu,embeds}.py +
disbot/views/creature_battle/challenge.py + cogs/creature_cog.py +
cogs/creature_battle_cog.py; parity/goldens/creature/ pins the wire
bytes (sweep_creatures, sweep_dex, sweep_dextop [re-homed],
sweep_cbrecord, sweep_cbattletop, sweep_cbattle).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

UID, GID = 42, 1


@pytest.fixture()
def empty_world(monkeypatch):
    """The capture world's zero-row epoch: empty collection/battle
    stores, zero game xp, no guild directory (the shipped ``User {id}``
    resolver fallback)."""
    from sb.domain.creature import store as cs
    from sb.domain.games import store as gs

    async def get_collection(user_id, guild_id, conn=None):
        return {}

    async def top_catchers(guild_id, limit=10, conn=None):
        return []

    async def get_battle_record(user_id, guild_id, conn=None):
        return (0, 0)

    async def top_battlers(guild_id, limit=10, conn=None):
        return []

    async def game_xp_rows(user_id, guild_id, conn=None):
        return []

    monkeypatch.setattr(cs, "get_collection", get_collection)
    monkeypatch.setattr(cs, "top_catchers", top_catchers)
    monkeypatch.setattr(cs, "get_battle_record", get_battle_record)
    monkeypatch.setattr(cs, "top_battlers", top_battlers)
    monkeypatch.setattr(gs, "game_xp_rows", game_xp_rows)


def _ctx(params: dict | None = None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=UID),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=dict(params or {}))


# --- the hub spec: golden-pinned bytes -----------------------------------------------


def test_hub_spec_shape_matches_the_golden():
    from sb.domain.creature.panels import creature_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = creature_hub_spec()
    assert spec.panel_id == "creature.hub"
    assert spec.title == "🐾 Creatures"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "green"         # CREATURE_COLOR 3066993
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True            # <cid:N>, no anchor row
    assert spec.navigation.show_help is True
    assert spec.navigation.show_home is True
    assert spec.navigation.home_hub == "games"
    by_id = {a.action_id: a for a in spec.actions}
    # the shipped decorators, in golden order (styles = wire 3/2/1/2/2).
    assert by_id["creature_catch"].label == "Catch"
    assert by_id["creature_catch"].emoji == "🐾"
    assert by_id["creature_catch"].style is ActionStyle.SUCCESS
    assert by_id["creature_dex"].label == "Dex"
    assert by_id["creature_dex"].emoji == "📖"
    assert by_id["creature_dex"].style is ActionStyle.SECONDARY
    # the shipped hub Dex button opened the INTERACTIVE element-filter view
    # (CreatureDexView), so it routes to the declarative browse panel — NOT
    # the static `!dex` card. Repointing never touches the rendered bytes
    # (label/emoji/style above are the golden-pinned wire fields).
    from sb.spec.refs import PanelRef
    assert by_id["creature_dex"].handler == PanelRef("creature.dex")
    assert by_id["creature_challenge"].label == "Challenge"
    assert by_id["creature_challenge"].emoji == "⚔️"
    assert by_id["creature_challenge"].style is ActionStyle.PRIMARY
    assert by_id["creature_ladder"].label == "Ladder"
    assert by_id["creature_ladder"].emoji == "🏆"
    assert by_id["creature_ladder"].style is ActionStyle.SECONDARY
    assert by_id["creature_howto"].label == "How to play"
    assert by_id["creature_howto"].emoji == "📖"
    assert by_id["creature_howto"].style is ActionStyle.SECONDARY
    assert spec.layout.pages[0].rows == (
        ("creature_catch", "creature_dex", "creature_challenge",
         "creature_ladder", "creature_howto"),)


def test_specs_pass_the_compile_fences():
    from sb.domain.creature import panels
    from sb.kernel.panels.compile import check_panel

    for build in (panels.creature_hub_spec, panels.dex_card_spec,
                  panels.dex_browse_spec, panels.collectors_card_spec,
                  panels.record_card_spec, panels.battletop_card_spec,
                  panels.challenge_spec, panels.rules_card_spec):
        check_panel(build())


def test_hub_render_matches_the_golden_bytes(empty_world):
    from sb.domain.creature.panels import _render_hub, creature_hub_spec

    rendered = run(_render_hub(creature_hub_spec(), _ctx()))
    # views/creature/embeds.py build_menu_embed, verbatim.
    assert rendered.embed.description == (
        "Catch from **36** original creatures across 6 elements. Rarer "
        "creatures show up less often and are harder to catch — fill "
        "out your dex, then battle other trainers in a level-normalized "
        "PvP where type matchups decide it.\n\n"
        "**🐾 Catch** — head into the wild\n"
        "**📖 Dex** — browse your collection by element\n"
        "**⚔️ Challenge** — battle another trainer\n"
        "**🏆 Ladder** — the server's top trainers\n"
        "**📖 How to play** — the rules")
    # the live progress field (0/36 at level 1 in the empty world) —
    # inline False on the wire (the golden pins "inline": false).
    assert rendered.embed.fields == (
        ("Your progress", "**0/36** creatures · level **1**"),)
    assert rendered.embed.footer == "Only you can use this panel."
    by_id = {c.custom_id: c for c in rendered.components}
    # the shipped standard nav row, labeled with the HUB'S display name.
    assert by_id["nav:help"].label == "📚 Help"
    assert by_id["nav:hub:games"].label == "↩ Games"
    # five action buttons + two nav slots, one action row (the golden's
    # component rows).
    assert len(rendered.components) == 7


# --- the four cards: empty-state bytes -------------------------------------------------


def test_dex_render_matches_the_golden_empty_state(empty_world):
    from sb.domain.creature.panels import _render_dex, dex_card_spec

    rendered = run(_render_dex(dex_card_spec(), _ctx()))
    assert rendered.embed.title == "🐾 User 42's Creature Dex"
    assert rendered.embed.description == (
        "**0/36** creatures discovered · **0** total catches · "
        "Creature level **1**")
    # six per-element INLINE fields in catalog order (rarity tier then
    # name inside each element — the golden pins Ember first, Cindling
    # leading).
    assert [f[0] for f in rendered.embed.fields] == [
        "Ember", "Stone", "Gust", "Tide", "Spark", "Bramble"]
    assert all(f[2] is True for f in rendered.embed.fields)
    assert rendered.embed.fields[0][1].startswith(
        "🔥 Cindling — *not yet caught*\n🔥 Emberpaw — *not yet caught*")
    assert rendered.embed.footer == (
        "🐾 Catch to hunt · 🏆 Ladder for the leaderboard")
    assert rendered.components == ()


def test_collectors_render_matches_the_golden_empty_state(empty_world):
    from sb.domain.creature.panels import (
        _render_collectors,
        collectors_card_spec,
    )

    rendered = run(_render_collectors(collectors_card_spec(), _ctx()))
    assert rendered.embed.title == "🐾 Top Collectors"
    assert rendered.embed.description == (
        "No one has been catching yet — be the first with `!catch`!")
    assert rendered.components == ()


def test_record_render_matches_the_golden_empty_state(empty_world):
    from sb.domain.creature.panels import _render_record, record_card_spec

    rendered = run(_render_record(record_card_spec(), _ctx()))
    assert rendered.embed.title == "⚔️ User 42's Battle Record"
    # the zero-battle em-dash winrate (the golden pins '—').
    assert rendered.embed.description == (
        "**0** wins · **0** losses · win rate **—**")
    assert rendered.embed.footer == (
        "⚔️ Challenge a trainer to fight · 🏆 Ladder for the rankings")


def test_battletop_render_matches_the_golden_empty_state(empty_world):
    from sb.domain.creature.panels import (
        _render_battletop,
        battletop_card_spec,
    )

    rendered = run(_render_battletop(battletop_card_spec(), _ctx()))
    assert rendered.embed.title == "⚔️ Top Trainers"
    assert rendered.embed.description == (
        "No battles won yet — challenge someone with `!cbattle @member`!")


def test_battletop_render_ranks_with_medals_and_winrate(monkeypatch,
                                                        empty_world):
    from sb.domain.creature import store as cs
    from sb.domain.creature.panels import (
        _render_battletop,
        battletop_card_spec,
    )

    async def top_battlers(guild_id, limit=10, conn=None):
        return [{"user_id": 7, "wins": 3, "losses": 1},
                {"user_id": 8, "wins": 1, "losses": 1}]

    monkeypatch.setattr(cs, "top_battlers", top_battlers)
    rendered = run(_render_battletop(battletop_card_spec(), _ctx()))
    assert rendered.embed.description == (
        "🥇 User 7 — **3**W · 1L (75%)\n🥈 User 8 — **1**W · 1L (50%)")


def test_collectors_render_ranks_by_total_caught(monkeypatch, empty_world):
    from sb.domain.creature import store as cs
    from sb.domain.creature.panels import (
        _render_collectors,
        collectors_card_spec,
    )

    async def top_catchers(guild_id, limit=10, conn=None):
        # species-major order from the store; the shipped board ranks
        # by total caught.
        return [{"user_id": 7, "species": 4, "total": 5},
                {"user_id": 8, "species": 2, "total": 9}]

    monkeypatch.setattr(cs, "top_catchers", top_catchers)
    rendered = run(_render_collectors(collectors_card_spec(), _ctx()))
    assert rendered.embed.description == (
        "🥇 User 8 — **9** caught (2/36 creatures)\n"
        "🥈 User 7 — **5** caught (4/36 creatures)")


# --- the interactive dex: the shipped element-filter view, armed on the engine -----------
#
# Oracle: disbot/views/creature/menu.py CreatureDexView (one _ElementFilterSelect
# + a Back button — NO sort, NO pagination) over build_dex_embed's per-creature
# lines. The hub Dex button opened it; the `!dex` COMMAND sent the static grouped
# card (goldens/creature/sweep_dex — an embed with no view). The browse conversion
# arms the element FILTER through the shared BrowserView engine (D-0034); the flat
# list + one-page indicator is the generic engine's chrome (owner hand-pass).


def _dex_rows_for(collection: dict):
    """Resolve the registered dex-rows provider against a ctx whose store
    returns *collection* (the engine's browse-block items source)."""
    from sb.domain.creature import panels
    from sb.domain.creature import store as cs
    from sb.spec.refs import ProviderRef, resolve

    panels.ensure_panel_refs()
    orig = cs.get_collection

    async def get_collection(user_id, guild_id, conn=None):
        return dict(collection)

    cs.get_collection = get_collection
    try:
        provider = resolve(ProviderRef("creature.dex_rows"))
        return run(provider(_ctx()))
    finally:
        cs.get_collection = orig


def test_dex_line_is_the_shipped_per_creature_line_verbatim():
    from sb.domain.creature.catalog import Creature
    from sb.domain.creature.panels import dex_line

    c = Creature(name="Cindling", element="Ember", rarity="Common",
                 archetype="balanced", emoji="🔥")
    # disbot/views/creature/embeds.py build_dex_embed, verbatim.
    assert dex_line(c, 3) == "🔥 **Cindling** ×3"
    assert dex_line(c, None) == "🔥 Cindling — *not yet caught*"
    assert dex_line(c, 0) == "🔥 Cindling — *not yet caught*"


def test_dex_row_carries_the_declared_filter_key_and_line():
    from sb.domain.creature.catalog import Creature
    from sb.domain.creature.panels import dex_row

    c = Creature(name="Infernox", element="Ember", rarity="Epic",
                 archetype="tank", emoji="🔥")
    caught = dex_row(c, 2)
    # exactly the keys the dex ListSpec names: the element FILTER value +
    # the display line. NO sort key (the shipped dex declares no sort).
    assert caught == {"element": "Ember", "_line": "🔥 **Infernox** ×2"}
    uncaught = dex_row(c, None)
    assert uncaught["element"] == "Ember"
    assert uncaught["_line"] == "🔥 Infernox — *not yet caught*"


def test_dex_browse_spec_declares_the_oracle_algebra():
    from sb.domain.creature import catalog
    from sb.domain.creature.panels import dex_browse_spec
    from sb.spec.panels import Audience, FooterMode, ListBlock
    from sb.spec.refs import PanelRef

    spec = dex_browse_spec()
    assert spec.panel_id == "creature.dex"
    assert spec.title == "🐾 Creature Dex"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "green"          # CREATURE_COLOR
    assert spec.frame.footer_mode is FooterMode.SUBSYSTEM
    assert spec.session_lifecycle is True             # a timeout view, never anchored
    assert spec.renderer_override is None              # grammar-render → the auto-arm hook
    # the shipped Back button (CreatureDexView had one → the menu).
    assert spec.navigation.parent == PanelRef("creature.hub")
    block = spec.body[0]
    assert isinstance(block, ListBlock)
    ls = block.list_spec
    # the element FILTER, derived EXACTLY as the oracle ELEMENTS
    # (dict.fromkeys over the catalog) — the golden's dex field order.
    assert ls.filter_options == tuple(
        dict.fromkeys(c.element for c in catalog.CREATURES))
    assert ls.filter_options == (
        "Ember", "Stone", "Gust", "Tide", "Spark", "Bramble")
    # NO sort (the shipped view had no sort control) — never invented.
    assert ls.sort_options == ()
    assert ls.default_sort == ""


def test_dex_browse_auto_arms_the_element_filter():
    from sb.domain.creature.panels import dex_browse_spec
    from sb.kernel.panels import browserview as bv

    spec = dex_browse_spec()
    state = bv.default_browse_state(spec)
    # declaring a filter_options set arms the surface on open (no filter,
    # page 0, the browse ListBlock at body index 0).
    assert state is not None
    assert state.panel_id == "creature.dex"
    assert state.block == 0
    assert state.filter == bv.ALL_FILTER
    assert state.sort == ""
    assert state.page == 0


def test_dex_rows_provider_emits_element_grouped_catalog(empty_world):
    from sb.domain.creature import catalog

    rows = _dex_rows_for({})
    # one row per catalog creature.
    assert len(rows) == len(catalog.CREATURES) == 36
    # GROUPED by element in the oracle's field order, six per element.
    elements = [r["element"] for r in rows]
    assert elements[:6] == ["Ember"] * 6
    assert elements[6:12] == ["Stone"] * 6
    order = list(dict.fromkeys(elements))
    assert order == ["Ember", "Stone", "Gust", "Tide", "Spark", "Bramble"]
    # every creature not-yet-caught in the empty world.
    assert all("not yet caught" in r["_line"] for r in rows)


def test_dex_rows_provider_reflects_the_caught_count(empty_world):
    rows = _dex_rows_for({"Cindling": 4})
    by_line = {r["_line"] for r in rows}
    assert "🔥 **Cindling** ×4" in by_line
    # the rest stay not-yet-caught.
    assert sum(1 for r in rows if "not yet caught" in r["_line"]) == 35


def test_dex_browse_filter_keeps_only_that_element(empty_world):
    from sb.kernel.panels import browserview as bv

    rows = _dex_rows_for({})
    for element in ("Ember", "Stone", "Gust", "Tide", "Spark", "Bramble"):
        kept = bv.filter_items(rows, element)
        assert len(kept) == 6, element
        assert all(r["element"] == element for r in kept)
    # the All pseudo-value is passthrough — every creature.
    assert len(bv.filter_items(rows, bv.ALL_FILTER)) == 36


def test_dex_browse_paginates_every_creature_without_truncation(empty_world):
    from sb.domain.creature.panels import dex_browse_spec
    from sb.kernel.panels import browserview as bv

    spec = dex_browse_spec()
    ls = spec.body[0].list_spec
    rows = _dex_rows_for({})
    # the all-view pages (18/page) so the 36-line list never overflows the
    # engine's 1024-char description budget — every creature stays visible.
    seen: list[str] = []
    page = 0
    while True:
        slice_rows, page_count, clamped = bv.browse_page(
            rows, ls, bv.BrowseState("creature.dex", 0, "", bv.ALL_FILTER, page))
        seen.extend(r["_line"] for r in slice_rows)
        rendered = "\n".join(r["_line"] for r in slice_rows)
        assert len(rendered) <= 1024            # within the engine's list budget
        if page >= page_count - 1:
            break
        page += 1
    assert page_count == 2                       # 36 / 18
    assert len(seen) == 36 and len(set(seen)) == 36
    # a single-element filter is one page (six creatures ≤ the page size).
    _, ember_pages, _ = bv.browse_page(
        rows, ls, bv.BrowseState("creature.dex", 0, "", "Ember", 0))
    assert ember_pages == 1


# --- the challenge: content-only send + opponent lock + declined terminal ---------------


def test_challenge_spec_shape_matches_the_golden():
    from sb.domain.creature.panels import challenge_spec
    from sb.spec.panels import ActionStyle, Audience

    spec = challenge_spec()
    assert spec.audience is Audience.PUBLIC
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False
    by_id = {a.action_id: a for a in spec.actions}
    assert by_id["cbattle_accept"].label == "Accept"
    assert by_id["cbattle_accept"].emoji == "⚔️"
    assert by_id["cbattle_accept"].style is ActionStyle.SUCCESS    # wire 3
    assert by_id["cbattle_decline"].label == "Decline"
    assert by_id["cbattle_decline"].emoji == "❌"
    assert by_id["cbattle_decline"].style is ActionStyle.DANGER    # wire 4


def test_challenge_render_matches_the_golden_bytes(empty_world):
    from sb.domain.creature.panels import _render_challenge, challenge_spec

    rendered = run(_render_challenge(
        challenge_spec(),
        _ctx({"cb_challenger_id": UID, "cb_opponent_id": 77})))
    assert rendered.embed is None
    assert rendered.content == (
        "<@77> — <@42> challenges you to a creature battle! Teams are "
        "level-normalized; your collection and type matchups decide it.")
    # the shipped BaseView author=opponent lock.
    assert rendered.invoker_lock == 77
    assert len(rendered.components) == 2


def test_challenge_declined_terminal_disables_the_buttons(empty_world):
    from sb.domain.creature.panels import _render_challenge, challenge_spec

    rendered = run(_render_challenge(
        challenge_spec(),
        _ctx({"cb_challenger_id": UID, "cb_opponent_id": 77,
              "stage": "declined"})))
    assert rendered.embed is None
    assert rendered.content == "❌ User 77 declined the challenge."
    assert all(c.disabled for c in rendered.components)


def test_cbattle_route_guards(empty_world):
    from sb.domain.creature import service
    from sb.kernel.interaction.errors import ValidatorError
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("creature.cbattle_route"))

    def _req(argv):
        return SimpleNamespace(
            actor=SimpleNamespace(user_id=UID), guild_id=GID,
            channel_id=2, args={"argv": argv}, origin=None,
            request_id="r1", surface=None)

    # cogs/creature_battle_cog.py, verbatim: the self guard.
    reply = run(route(_req((f"<@{UID}>",))))
    assert reply.outcome is BLOCKED
    assert reply.user_message == ("🪞 You can't battle yourself — "
                                  "challenge someone else!")
    # a missing opponent is a polite user_error denial.
    with pytest.raises(ValidatorError):
        run(route(_req(())))


# --- the refs + manifest ---------------------------------------------------------------


def test_refs_registered_and_manifest_routes():
    from sb.domain.creature import panels, service
    from sb.manifest.creature import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    panels.ensure_panel_refs()
    service.ensure_handler_refs()
    for pid in ("creature.hub", "creature.dex_card", "creature.dex",
                "creature.collectors_card", "creature.record_card",
                "creature.battletop_card", "creature.challenge",
                "creature.challenge_select", "creature.rules_card"):
        assert is_registered(PanelRef(pid)), pid
    # the interactive dex's provider + per-row line renderer.
    from sb.spec.refs import ProviderRef
    assert is_registered(ProviderRef("creature.dex_rows"))
    assert is_registered(HandlerRef("creature.render_dex_line"))
    for name in ("creature.render_hub", "creature.render_dex",
                 "creature.render_collectors", "creature.render_record",
                 "creature.render_battletop", "creature.render_challenge",
                 "creature.catch_route", "creature.dex_view",
                 "creature.dextop_view", "creature.battle_record_view",
                 "creature.battletop_view", "creature.rules_view",
                 "creature.cbattle_route", "creature.challenge_decline",
                 "creature.challenge_accept",
                 "creature.challenge_pick",
                 "creature.challenge_rematch"):
        assert is_registered(HandlerRef(name)), name

    by_name = {c.name: c for c in MANIFEST.commands}
    # !catch stays DECLARED though sweep-skipped (capture-determinism
    # artifact, the treasury-grant precedent — see the manifest
    # docstring); the golden-pinned hub button routes the same lane.
    assert by_name["catch"].route == HandlerRef("creature.catch_route")
    assert by_name["catch"].aliases == ("hunt",)
    assert by_name["creatures"].route == PanelRef("creature.hub")
    assert by_name["cbattle"].route == HandlerRef("creature.cbattle_route")
    assert {p.panel_id for p in MANIFEST.panels} == {
        "creature.hub", "creature.dex_card", "creature.dex",
        "creature.collectors_card", "creature.record_card",
        "creature.battletop_card", "creature.challenge",
        "creature.challenge_select", "creature.rules_card"}
