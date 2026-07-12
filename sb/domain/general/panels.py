"""The GENERAL menu panel (band 6 flip) — the shipped ``GeneralMenuView``
(disbot/cogs/general_cog.py): one overview embed (``_overview_embed`` —
title ``💬 General``, discord.Color.green(), the 7-line command legend) over
three button rows. The shipped view put the emoji INSIDE each button label
(``label="💡 Fact"`` — no separate emoji field on the wire) and carried
blurple for the content trio, grey for the question trio, green for Greet;
``parity/goldens/general/sweep_generalmenu.json`` pins the bytes.

The shipped view was a timeout-bound session view (``BaseView`` family, the
same class as the leaderboard/four_twenty panels), so ``session_lifecycle=
True``: custom_ids are run-minted (engine ``_mint_ephemeral``), no
``panel_anchors`` row is recorded, and the never-strand fence takes the
session-view exemption (the golden pins exactly three rows — no nav slots).
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.outcomes import DeferMode, ReplyVisibility
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

__all__ = [
    "CARD_PANEL_ID",
    "EIGHTBALL_MODAL",
    "TRIVIA_CARD_PANEL_ID",
    "card_spec",
    "ensure_panel_refs",
    "general_menu_spec",
    "install_general_panels",
    "trivia_card_spec",
]

CARD_PANEL_ID = "general.card"
TRIVIA_CARD_PANEL_ID = "general.trivia_card"

# the shipped 8-ball flow: a yes/no question MODAL (the golden's legend line
# "**🎱 8-Ball** — yes/no question modal"), G-10 declarative form body.
EIGHTBALL_MODAL = ModalSpec(
    modal_id="general.eightball_form",
    title="🎱 8-Ball",
    fields=(
        ModalFieldSpec(
            field_id="question", label="Your yes/no question",
            placeholder="e.g. Will it rain tomorrow?", required=True,
            max_length=200),
    ),
    on_submit=HandlerRef("general.eightball_answer"),
)

# the shipped overview legend (_overview_embed description, verbatim — the
# golden pins every byte).
_LEGEND = (
    "**💡 Fact** — random interesting fact\n"
    "**😄 Joke** — random joke\n"
    "**💬 Quote** — famous quote\n"
    "**🧠 Trivia** — trivia question with reveal\n"
    "**💪 Motivate** — motivational message\n"
    "**🎱 8-Ball** — yes/no question modal\n"
    "**👋 Greet** — random greeting"
)


def general_menu_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="general.menu",
        subsystem="general",
        title="💬 General",
        audience=Audience.INVOKER,
        # discord.Color.green(), no footer — the shipped _overview_embed.
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_LEGEND),),
        actions=(
            # row 0 — the shipped blurple content trio (emoji in-label).
            PanelActionSpec(
                action_id="fact", label="💡 Fact",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("general.fact_view")),
            PanelActionSpec(
                action_id="joke", label="😄 Joke",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("general.joke_view")),
            PanelActionSpec(
                action_id="quote", label="💬 Quote",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("general.quote_view")),
            # row 1 — the shipped grey question trio.
            PanelActionSpec(
                action_id="trivia", label="🧠 Trivia",
                audience_tier="user",
                handler=HandlerRef("general.trivia_view")),
            PanelActionSpec(
                action_id="motivate", label="💪 Motivate",
                audience_tier="user",
                handler=HandlerRef("general.motivate_view")),
            PanelActionSpec(
                action_id="eightball", label="🎱 8-Ball",
                audience_tier="user",
                defer_mode=DeferMode.MODAL, modal=EIGHTBALL_MODAL,
                handler=HandlerRef("general.eightball_answer")),
            # row 2 — green Greet + the shipped grey re-render Overview.
            PanelActionSpec(
                action_id="greet", label="👋 Greet",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("general.greet_view")),
            PanelActionSpec(
                # K1 custom_id claims are repo-global on action_id —
                # economy owns bare "overview" (the spotlight_refresh
                # precedent).
                action_id="general_overview", label="↩ Overview",
                audience_tier="user",
                handler=PanelRef("general.menu"),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        # the shipped GeneralMenuView carried ONLY its own buttons (no nav
        # slots; timeout session view) — the golden pins exactly three
        # component rows, so the never-strand fence takes the session-view
        # exemption the shipped view actually was.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("fact", "joke", "quote"),
            ("trivia", "motivate", "eightball"),
            ("greet", "general_overview"),
        )),)),
    )


def card_spec() -> PanelSpec:
    """The shipped general_cog.py prefix-command result embed (one
    ``discord.Embed(title=..., color=GENERAL_COLOR)`` per command —
    ``!fact``/``!joke``/``!quote``/``!motivate``/``!greet``/``!eightball``)
    as ONE component-less session-lifecycle card (the karma.card /
    fishing.card zero-component pattern): the shipped sends were plain
    ``send_panel(ctx, embed=embed)`` result messages, never anchored
    panels."""
    return PanelSpec(
        panel_id=CARD_PANEL_ID,
        subsystem="general",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("general.card_render"),
        justification=(
            "the shipped general prefix results are run-parameterized on "
            "every surface: the per-command title ('💡 Random Fact' / "
            "'😄 Random Joke' / '💬 Quote' / '💪 Motivation' / "
            "'👋 Greeting' / '🎱 Magic 8-Ball'), the random-pick "
            "description (greet appends the invoker mention), and the "
            "8-ball's non-inline Question/Answer field pair "
            "(general_cog.py command bodies) — outside the static grammar "
            "TextBlock vocabulary. Zero components; the renderer only "
            "composes the embed (goldens/general/sweep_fact, sweep_joke, "
            "sweep_quote, sweep_motivate, sweep_greet, sweep_eightball "
            "pin the bytes)."),
        session_lifecycle=True,
    )


def trivia_card_spec() -> PanelSpec:
    """The shipped ``!trivia`` question card (general_cog.py trivia +
    ``_TriviaRevealView``): the question-only description, the footer
    literal, and the one blurple 'Reveal Answer' button on a timeout
    session view (run-minted custom_id — goldens/general/sweep_trivia
    pins ``<cid:1>``, no panel_anchors row)."""
    return PanelSpec(
        panel_id=TRIVIA_CARD_PANEL_ID,
        subsystem="general",
        title="🧠 Trivia",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                # K1 claims action_ids BARE and repo-global (trap 19) —
                # subsystem-unique token; the wire id is run-minted anyway.
                action_id="trivia_reveal", label="Reveal Answer",
                style=ActionStyle.PRIMARY, audience_tier="user",
                # the shipped reveal replied ephemeral
                # (interaction.response.send_message(..., ephemeral=True)).
                reply_visibility=ReplyVisibility.EPHEMERAL,
                handler=HandlerRef("general.trivia_reveal")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("trivia_reveal",),)),)),
        renderer_override=HandlerRef("general.trivia_card_render"),
        justification=(
            "the shipped trivia embed is run-parameterized: the drawn "
            "question as the description and the footer literal \"Click "
            "'Reveal Answer' when ready.\" (general_cog.py trivia) — the "
            "override delegates components to the grammar render and "
            "replaces only the embed, plus clears the invoker lock (the "
            "shipped _TriviaRevealView was public=True; adjusted "
            "surfaces: embed description, embed footer, invoker lock). "
            "goldens/general/sweep_trivia pins the bytes."),
    )


async def _render_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped per-command result embed verbatim:
    title/description/fields arrive as open params (the command handler
    draws the pick; sb/domain/general/handlers.py)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    fields = tuple(tuple(f) for f in params.get("card_fields", ()) or ())
    embed = RenderedEmbed(
        title=str(params.get("card_title", "") or ""),
        description=str(params.get("card_description", "") or ""),
        fields=fields,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_trivia_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — delegate the components (the declared reveal
    button) to the grammar render, replace only the embed (the economy
    delegation pattern) and clear the invoker lock (shipped view was
    ``public=True`` — anyone may reveal)."""
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    params = getattr(ctx, "params", {}) or {}
    base = await render_panel(spec, ctx)
    embed = RenderedEmbed(
        title="🧠 Trivia",
        description=str(params.get("trivia_question", "") or ""),
        footer="Click 'Reveal Answer' when ready.",
        style_token=spec.frame.style_token)
    return dataclasses.replace(base, embed=embed, invoker_lock=None)


@panel("general.menu")
def _menu_factory() -> PanelSpec:
    return general_menu_spec()


@panel(CARD_PANEL_ID)
def _card_factory() -> PanelSpec:
    return card_spec()


@panel(TRIVIA_CARD_PANEL_ID)
def _trivia_card_factory() -> PanelSpec:
    return trivia_card_spec()


handler("general.card_render")(_render_card)
handler("general.trivia_card_render")(_render_trivia_card)


def install_general_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (general_menu_spec(), card_spec(), trivia_card_spec()):
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    for pid, factory in (("general.menu", _menu_factory),
                         (CARD_PANEL_ID, _card_factory),
                         (TRIVIA_CARD_PANEL_ID, _trivia_card_factory)):
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for hid, fn in (("general.card_render", _render_card),
                    ("general.trivia_card_render", _render_trivia_card)):
        if not is_registered(HandlerRef(hid)):
            handler(hid)(fn)
