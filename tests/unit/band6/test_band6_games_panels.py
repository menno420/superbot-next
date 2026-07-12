"""The GAMES parity-flip surfaces: the shipped 🎮 Games Hub (persistent
``games:open:<key>`` ids, the 🏆/🎲 catalog fields, the invoker-lock
footer literal, the row-3 📚 Help slot), the 🗺️ Explore world hub
(``explore:open:<key>`` + ``explore:world_card``), and the 🪪 world card
(display-name title + avatar thumbnail + the zero-XP empty-state field).

Oracle: menno420/superbot disbot/views/games/hub.py +
disbot/views/explore/world_hub.py + disbot/views/explore/world_card.py;
parity/goldens/games/sweep_games.json + sweep_slash_games.json +
sweep_world.json + sweep_worldcard.json pin the wire bytes.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

run = asyncio.run

GID, P1 = 1, 42


def _ctx(params: dict | None = None):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=P1),
        channel_id=900, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(),
        params=params or {})


# --- the hub spec: golden-pinned bytes ---------------------------------------


def test_hub_spec_shape_matches_the_golden():
    from sb.domain.games.panels import games_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = games_hub_spec()
    assert spec.panel_id == "games.hub"
    assert spec.title == "🎮 Games Hub"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "purple"        # GAME_COLOR 10181046
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True            # no panel_anchors row
    assert spec.navigation.show_help is True         # row-3 📚 Help
    assert spec.navigation.show_home is False

    by_id = {a.action_id: a for a in spec.actions}
    assert len(by_id) == 10
    # the shipped persistent ids ride custom_id_override verbatim; emoji
    # IN the label (the f"{emoji} {label}" builder — no emoji field).
    assert by_id["ga_blackjack"].custom_id_override == "games:open:blackjack"
    assert by_id["ga_blackjack"].label == "🃏 Blackjack"
    assert by_id["ga_blackjack"].emoji == ""
    assert by_id["ga_rps_tournament"].label == "✂️ Rock Paper Scissors"
    assert by_id["ga_chain"].custom_id_override == "games:open:chain"
    # Competitive primary (wire 1), Activities success (wire 3).
    for key in ("ga_blackjack", "ga_casino", "ga_deathmatch",
                "ga_rps_tournament"):
        assert by_id[key].style is ActionStyle.PRIMARY
    for key in ("ga_mining", "ga_fishing", "ga_creature", "ga_farm",
                "ga_counting", "ga_chain"):
        assert by_id[key].style is ActionStyle.SUCCESS
    assert spec.layout.pages[0].rows == (
        ("ga_blackjack", "ga_casino", "ga_deathmatch",
         "ga_rps_tournament"),
        ("ga_mining", "ga_fishing", "ga_creature", "ga_farm",
         "ga_counting"),
        ("ga_chain",),
    )


def test_world_spec_shape_matches_the_golden():
    from sb.domain.games.panels import world_hub_spec
    from sb.spec.panels import ActionStyle, Audience

    spec = world_hub_spec()
    assert spec.panel_id == "games.world"
    assert spec.title == "🗺️ Explore — the open world"
    assert spec.audience is Audience.INVOKER
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is True
    assert spec.navigation.show_home is False
    assert spec.navigation.parent is None            # golden: nav:help only

    by_id = {a.action_id: a for a in spec.actions}
    assert by_id["world_mine"].custom_id_override == "explore:open:mining"
    assert by_id["world_mine"].label == "⛏️ Mine"
    assert by_id["world_mine"].style is ActionStyle.PRIMARY
    assert by_id["world_fish"].custom_id_override == "explore:open:fishing"
    assert by_id["world_farm"].custom_id_override == "explore:open:farm"
    assert by_id["world_card"].custom_id_override == "explore:world_card"
    assert by_id["world_card"].label == "🪪 World Card"
    assert by_id["world_card"].style is ActionStyle.SECONDARY
    assert spec.layout.pages[0].rows == (
        ("world_mine", "world_fish", "world_farm"),
        ("world_card",),
    )


def test_specs_pass_the_compile_fences():
    from sb.domain.games.panels import (
        games_hub_spec,
        world_card_spec,
        world_hub_spec,
    )
    from sb.kernel.panels.compile import check_panel

    check_panel(games_hub_spec())
    check_panel(world_hub_spec())
    check_panel(world_card_spec())


# --- renders: footer literals + catalog fields + the world card ---------------


def test_hub_render_matches_the_golden_bytes():
    from sb.domain.games.panels import _render_hub, games_hub_spec

    rendered = run(_render_hub(games_hub_spec(), _ctx()))
    assert rendered.embed.description == (
        "Pick a game below to open it. "
        "Typed shortcuts (e.g. `!blackjack`, `!mine`) still work.")
    assert rendered.embed.fields == (
        ("🏆 Competitive",
         "🃏 **Blackjack** — Blackjack card game\n"
         "🎰 **Casino** — Group card games like multiplayer poker\n"
         "⚔️ **Deathmatch** — 1v1 duel battles\n"
         "✂️ **Rock Paper Scissors** — Rock Paper Scissors: quick play, "
         "PvP, bot matches, tournaments"),
        ("🎲 Activities",
         "⛏️ **Mining** — Mining minigame and resource collection\n"
         "🎣 **Fishing** — Fishing minigame — cast a line, build your "
         "collection\n"
         "🐾 **Creatures** — Catch original creatures and build your "
         "collection dex\n"
         "🐔 **Chicken Farm** — Idle egg farm — hens lay eggs over time; "
         "collect, sell, grow\n"
         "🔢 **Counting** — Collaborative counting game\n"
         "🔗 **Word Chain** — Word-chaining game"),
    )
    assert rendered.embed.footer == (
        "Only you can interact with this panel.")
    by_id = {c.custom_id: c for c in rendered.components}
    # overrides land pre-mint: the wire ids are the shipped literals.
    assert by_id["games:open:blackjack"].label == "🃏 Blackjack"
    assert by_id["games:open:counting"].label == "🔢 Counting"
    assert by_id["nav:help"].label == "📚 Help"
    assert "nav:hub:games" not in by_id              # no home slot


def test_world_render_matches_the_golden_bytes():
    from sb.domain.games.panels import _render_hub, world_hub_spec

    rendered = run(_render_hub(world_hub_spec(), _ctx()))
    assert rendered.embed.description == (
        "Walk out into the world and pick where to go. Each place is its "
        "own game — your progress in one carries its own ladder, and a "
        "shared world ties them together.")
    assert rendered.embed.fields == (
        ("Where to go",
         "⛏️ **Mine** — Dig for ores, craft gear, and grow your "
         "character.\n"
         "🎣 **Fish** — Cast a line in lakes and rivers and build your "
         "collection.\n"
         "🐔 **Farm** — Raise hens that lay eggs around the clock — an "
         "idle game."),
    )
    assert rendered.embed.footer == (
        "Only you can interact with this panel.")
    by_id = {c.custom_id: c for c in rendered.components}
    assert set(by_id) == {"explore:open:mining", "explore:open:fishing",
                          "explore:open:farm", "explore:world_card",
                          "nav:help"}


def test_world_card_render_zero_xp_matches_the_golden(fake_games_store):
    # headless (no guild directory armed) — the name degrades to the
    # mention form, never invented data; every OTHER byte is the golden's.
    from sb.domain.games.panels import _render_world_card, world_card_spec

    rendered = run(_render_world_card(world_card_spec(), _ctx()))
    assert rendered.embed.title == f"🪪 <@{P1}> — world card"
    assert rendered.embed.description == (
        "Who you are across the open world: your shared **world level** "
        "and where you stand in each game.")
    assert rendered.embed.fields == ((
        "🌍 World level — 0",
        "You have not earned any game XP here yet. Mine, craft, or fish "
        "to start your world ladder — run **`!world`** to pick a place."),)
    assert rendered.embed.footer == "Only you can see this card."
    assert rendered.components == ()                 # golden: components []


def test_world_card_render_with_game_xp(fake_games_store):
    from sb.domain.games import xp
    from sb.domain.games.panels import _render_world_card, world_card_spec

    run(xp.award_in_txn(None, user_id=P1, guild_id=GID, game="mining",
                        action="depth_record", now=1_000_000))
    rendered = run(_render_world_card(world_card_spec(), _ctx()))
    name, value = rendered.embed.fields[0]
    assert name.startswith("🌍 World level — ")
    assert "Mining" in value and "25" in value
