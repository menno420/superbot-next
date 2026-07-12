"""Band 6 — the GENERAL menu panel (the shipped GeneralMenuView as a
session-lifecycle panel): the golden-pinned spec bytes, the compile fences,
the manifest surface, and the thin content handlers.

Oracle: menno420/superbot disbot/cogs/general_cog.py (GeneralMenuView +
_overview_embed); parity/goldens/general/sweep_generalmenu.json pins the
wire bytes.
"""

from __future__ import annotations

import asyncio

run = asyncio.run


# --- the spec: golden-pinned bytes ---------------------------------------------------


def test_menu_spec_shape_matches_the_golden():
    from sb.spec.panels import ActionStyle, Audience, FooterMode
    from sb.domain.general.panels import general_menu_spec

    spec = general_menu_spec()
    assert spec.panel_id == "general.menu"
    assert spec.subsystem == "general"
    assert spec.title == "💬 General"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "green"
    assert spec.frame.footer_mode is FooterMode.NONE
    # the shipped session view: run-minted ids, no anchor row, no nav slots.
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False

    by_id = {a.action_id: a for a in spec.actions}
    # emoji lives INSIDE the label (the shipped buttons carried no separate
    # emoji field — the golden pins buttons without an "emoji" key).
    assert [a.emoji for a in spec.actions] == [""] * 8
    assert by_id["fact"].label == "💡 Fact"
    assert by_id["joke"].label == "😄 Joke"
    assert by_id["quote"].label == "💬 Quote"
    assert by_id["trivia"].label == "🧠 Trivia"
    assert by_id["motivate"].label == "💪 Motivate"
    assert by_id["eightball"].label == "🎱 8-Ball"
    assert by_id["greet"].label == "👋 Greet"
    assert by_id["general_overview"].label == "↩ Overview"
    for aid in ("fact", "joke", "quote"):
        assert by_id[aid].style is ActionStyle.PRIMARY       # wire style 1
    for aid in ("trivia", "motivate", "eightball", "general_overview"):
        assert by_id[aid].style is ActionStyle.SECONDARY     # wire style 2
    assert by_id["greet"].style is ActionStyle.SUCCESS       # wire style 3

    assert spec.layout.pages[0].rows == (
        ("fact", "joke", "quote"),
        ("trivia", "motivate", "eightball"),
        ("greet", "general_overview"),
    )

    # the 8-ball is the shipped yes/no-question modal (G-10 form body).
    assert by_id["eightball"].modal is not None
    assert by_id["eightball"].modal.fields[0].field_id == "question"


def test_green_style_token_is_the_shipped_color():
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    assert STYLE_TOKEN_COLORS["green"] == 3066993  # discord.Color.green()


def test_menu_spec_passes_the_compile_fences():
    from sb.kernel.panels.compile import check_panel
    from sb.domain.general.panels import general_menu_spec

    check_panel(general_menu_spec())  # raises PanelCompileError on drift


# --- the refs: panel + handlers registered -------------------------------------------


def test_panel_and_handler_refs_registered():
    from sb.domain.general import handlers, panels
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    panels.ensure_panel_refs()
    handlers.ensure_handler_refs()
    assert is_registered(PanelRef("general.menu"))
    for name in ("general.menu_view", "general.fact_view",
                 "general.joke_view", "general.quote_view",
                 "general.trivia_view", "general.motivate_view",
                 "general.greet_view", "general.eightball_answer"):
        assert is_registered(HandlerRef(name)), name


def test_manifest_declares_the_menu_and_prefix_entry_points():
    from sb.manifest.general import MANIFEST
    from sb.spec.refs import HandlerRef

    assert MANIFEST.key == "general"
    by_name = {c.name: c for c in MANIFEST.commands}
    assert set(by_name) == {"generalmenu", "fact", "joke", "quote",
                            "trivia", "motivate", "eightball", "greet"}
    assert by_name["generalmenu"].aliases == ("gmenu",)
    assert by_name["generalmenu"].route == HandlerRef("general.menu_view")
    # the shipped decorators: only eightball carried an alias.
    assert by_name["eightball"].aliases == ("8ball",)
    for name in ("fact", "joke", "quote", "trivia", "motivate", "greet"):
        assert by_name[name].aliases == ()
        assert by_name[name].route == HandlerRef(f"general.{name}_cmd")
    panel_ids = [p.panel_id for p in MANIFEST.panels]
    assert panel_ids == ["general.menu", "general.card",
                         "general.trivia_card"]
    # R2 stays vacuous for general: no declared events/stores/settings.
    assert MANIFEST.stores == () and MANIFEST.events == ()
    assert MANIFEST.settings == ()


def test_prefix_command_draw_trajectories_match_the_goldens():
    """The seed-42 pick + XP bytes the re-homed goldens pin: ONE
    module-global choice draw per command, then the chat-award
    randint(15, 25) — see the manifest docstring's XP-byte note."""
    import random as _random

    from sb.domain.general import content as c

    cases = (
        (c.FACTS, "The first computer bug was an actual bug — a moth "
                  "found in a Harvard Mark II in 1947.", 16),
        (c.JOKES, "I'm on a seafood diet — I see food and I eat it.", 16),
        (c.QUOTES, '"The greatest glory in living lies not in never '
                   'falling, but in rising every time we fall." '
                   "— Nelson Mandela", 16),
        (c.TRIVIA, "In what year did World War II end? || 1945.", 16),
        (c.GREETINGS, "Hello!", 15),
        (c.MOTIVATIONS, "Believe in yourself and all that you are!", 15),
        (c.EIGHTBALL, "No.", 15),
    )
    for pool, want_pick, want_xp in cases:
        _random.seed(42)
        assert _random.choice(pool) == want_pick
        assert _random.randint(15, 25) == want_xp


# --- the handlers: thin content reads ------------------------------------------------


def _req(args=None):
    from types import SimpleNamespace

    return SimpleNamespace(args=dict(args or {}), guild_id=1)


def test_content_handlers_reply_from_the_pools():
    from sb.domain.general import handlers  # noqa: F401 — registers refs
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    fact = run(resolve(HandlerRef("general.fact_view"))(_req()))
    assert fact.outcome == SUCCESS
    from sb.domain.general.content import FACTS

    assert fact.user_message.removeprefix("💡 ") in FACTS

    trivia = run(resolve(HandlerRef("general.trivia_view"))(_req()))
    assert trivia.outcome == SUCCESS
    assert "||" in trivia.user_message        # spoiler-wrapped reveal
    assert "**Answer:**" in trivia.user_message


def test_empty_pool_falls_back_to_the_shipped_string():
    from sb.domain.general.content import pick

    # the shipped general_cog.py empty-pool rule, verbatim shape.
    assert pick((), "motivational messages") == (
        "No motivational messages available.")


def test_eightball_submit_echoes_the_question():
    from sb.domain.general import handlers  # noqa: F401 — registers refs
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    reply = run(resolve(HandlerRef("general.eightball_answer"))(
        _req({"question": "Will it rain tomorrow?"})))
    assert reply.outcome == SUCCESS
    assert reply.user_message.startswith("🎱 *Will it rain tomorrow?*")
