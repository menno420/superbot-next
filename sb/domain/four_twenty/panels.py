"""The FOUR_TWENTY overview panel — the shipped ``_FourTwentyPanelView``
(disbot/cogs/four_twenty_cog.py): one overview embed (``_overview_embed`` —
title ``🍃 420``, ``_FOUR_TWENTY_COLOR`` leafy green 0x4CAF50, no footer)
over two button rows: the green 🍃 Wisdom + blurple 🔢 420 Fact pair, then
the grey ↩ Overview re-render on its own row.
``parity/goldens/four_twenty/sweep_420.json`` pins every byte.

The shipped view was a timeout-bound session view (``BaseView`` family —
public, timeout 300; the same class as the general/leaderboard panels), so
``session_lifecycle=True``: custom_ids are run-minted (engine
``_mint_ephemeral``), no ``panel_anchors`` row is recorded, and the golden
pins exactly two component rows — no nav slots.

Internal action_ids are K1-unique repo-wide (``fact`` is general's claim,
``overview`` economy's — the general_overview precedent); the wire never
sees them (session-minted ``<cid:N>``), so no ``custom_id_override``.
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "ensure_panel_refs",
    "four_twenty_overview_spec",
    "install_four_twenty_panels",
]

# the shipped overview body (_overview_embed description, verbatim — the
# golden pins every byte).
_OVERVIEW_TEXT = (
    "Take it easy. Pick an option below.\n\n"
    "**🍃 Wisdom** — a little relaxed wisdom\n"
    "**🔢 420 Fact** — number trivia for the curious\n\n"
    "_Tip: drop a `420` in chat and watch what happens._"
)


def four_twenty_overview_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="four_twenty.overview",
        subsystem="four_twenty",
        title="🍃 420",
        # the shipped BaseView was PUBLIC (no invoker lock), timeout 300.
        audience=Audience.PUBLIC,
        timeout_s=300,
        # _FOUR_TWENTY_COLOR = from_rgb(0x4C, 0xAF, 0x50), no footer.
        frame=EmbedFrameSpec(style_token="leaf_green",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_OVERVIEW_TEXT),),
        actions=(
            # row 0 — the shipped green/blurple content pair (emoji
            # in-label, the shipped decorator form).
            PanelActionSpec(
                action_id="wisdom", label="🍃 Wisdom",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("four_twenty.wisdom_view")),
            PanelActionSpec(
                action_id="four_twenty_fact", label="🔢 420 Fact",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("four_twenty.fact_view")),
            # row 1 — the shipped grey re-render Overview.
            PanelActionSpec(
                action_id="four_twenty_overview", label="↩ Overview",
                audience_tier="user",
                handler=PanelRef("four_twenty.overview"),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        # the shipped _FourTwentyPanelView carried ONLY its own buttons
        # (no nav slots; timeout session view) — the golden pins exactly
        # two component rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("wisdom", "four_twenty_fact"),
            ("four_twenty_overview",),
        )),)),
    )


@panel("four_twenty.overview")
def _overview_factory() -> PanelSpec:
    return four_twenty_overview_spec()


def install_four_twenty_panels() -> tuple[PanelSpec, ...]:
    spec = four_twenty_overview_spec()
    try:
        return (register_panel(spec),)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return (spec,)
        raise


def ensure_panel_refs() -> None:
    if not is_registered(PanelRef("four_twenty.overview")):
        panel("four_twenty.overview")(_overview_factory)
