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
                  panels.collectors_card_spec, panels.record_card_spec,
                  panels.battletop_card_spec, panels.challenge_spec,
                  panels.rules_card_spec):
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
    for pid in ("creature.hub", "creature.dex_card",
                "creature.collectors_card", "creature.record_card",
                "creature.battletop_card", "creature.challenge",
                "creature.rules_card"):
        assert is_registered(PanelRef(pid)), pid
    for name in ("creature.render_hub", "creature.render_dex",
                 "creature.render_collectors", "creature.render_record",
                 "creature.render_battletop", "creature.render_challenge",
                 "creature.catch_route", "creature.dex_view",
                 "creature.dextop_view", "creature.battle_record_view",
                 "creature.battletop_view", "creature.rules_view",
                 "creature.cbattle_route", "creature.challenge_decline",
                 "creature.challenge_accept",
                 "creature.challenge_pick_pending"):
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
        "creature.hub", "creature.dex_card", "creature.collectors_card",
        "creature.record_card", "creature.battletop_card",
        "creature.challenge", "creature.rules_card"}
