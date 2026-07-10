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
from sb.spec.outcomes import DeferMode
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "EIGHTBALL_MODAL",
    "ensure_panel_refs",
    "general_menu_spec",
    "install_general_panels",
]

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


@panel("general.menu")
def _menu_factory() -> PanelSpec:
    return general_menu_spec()


def install_general_panels() -> tuple[PanelSpec, ...]:
    spec = general_menu_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    if not is_registered(PanelRef("general.menu")):
        panel("general.menu")(_menu_factory)
