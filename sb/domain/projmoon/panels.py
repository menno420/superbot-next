"""Project Moon panels (band 7) — the SHIPPED LimbusBrowseView
(views/projmoon/browse.py @7f7628e1) plus the oracle-card presentation
panel.

* ``projmoon.hub`` — the shipped browse panel byte-for-byte
  (goldens/project_moon/sweep_pm + goldens/projectmoon/sweep_slash_pm):
  the overview embed + one button per entity kind, bracketed by the 🌑
  Overview reset (primary) and the 📖 Origins cross-reference — eight
  buttons on session-minted custom_ids (the shipped discord.py auto
  ids — the goldens pin the ``<cid:1>``…``<cid:8>`` roster), rows 5+3
  (discord.py's sequential add_item packing), NO nav row. The shipped
  view was never anchored (timeout-bound BaseView session) and public
  (no invoker lock on clicks); ephemeral on the slash surface (the
  shipped ``/pm`` sent it ``ephemeral=True``).
* ``projmoon.card`` — the generic one-embed reply card every
  ``!pm <sub>`` command presents through (the shipped
  ``ctx.send(embed=…)``).

Click routes are golden-UNPINNED (no projmoon golden drives a click):
the shipped buttons EDITED the message in place; here each button
presents its kind/overview/origins card through the result lane.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

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
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = ["ensure_panel_refs", "install_projmoon_panels",
           "projmoon_card_spec", "projmoon_hub_spec"]


def _kind_action(action_id: str, label: str, ref: str,
                 emoji: str = "", style: ActionStyle = ActionStyle.SECONDARY,
                 ) -> PanelActionSpec:
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji, style=style,
        audience_tier="user", handler=HandlerRef(ref),
        result_render=ResultRender.RESULT_CARD)


def projmoon_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="projmoon.hub",
        subsystem="projmoon",
        title="🌑 Project Moon — Limbus knowledge",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="purple", footer_mode=FooterMode.NONE),
        actions=(
            # row 0 — the shipped add_item order: Overview, then one
            # button per entity kind in dataset display order…
            _kind_action("pm_overview", "Overview", "projmoon.overview_view",
                         emoji="🌑", style=ActionStyle.PRIMARY),
            _kind_action("pm_sinners", "Sinners", "projmoon.sinner_view"),
            _kind_action("pm_sins", "Sins", "projmoon.sin_view"),
            _kind_action("pm_damage", "Damage types", "projmoon.damage_view"),
            _kind_action("pm_mechanics", "Mechanics", "projmoon.mechanic_view"),
            # row 1 — …continuing the roster, closed by Origins.
            _kind_action("pm_ego", "E.G.O grades", "projmoon.ego_view"),
            _kind_action("pm_statuses", "Statuses", "projmoon.status_view"),
            _kind_action("pm_origins", "Origins", "projmoon.origins_view",
                         emoji="📖"),
        ),
        # the shipped BaseView carried NO nav slot on this panel — the
        # goldens pin exactly eight buttons in two rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("projmoon.render_hub"),
        justification=(
            "the shipped overview embed is live-data-parameterized (per-"
            "kind counts + first-six name rosters over the committed "
            "fixtures) with the verify-at-ingest provenance footer — "
            "outside FooterMode's vocabulary and the static TextBlock "
            "grammar. The override delegates the component rows to the "
            "grammar renderer and replaces ONLY the embed "
            "(goldens/project_moon/sweep_pm pins every byte)."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("pm_overview", "pm_sinners", "pm_sins", "pm_damage",
             "pm_mechanics"),
            ("pm_ego", "pm_statuses", "pm_origins"),)),)),
    )


def projmoon_card_spec() -> PanelSpec:
    """The generic oracle-card reply (one embed, zero components)."""
    return PanelSpec(
        panel_id="projmoon.card",
        subsystem="projmoon",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("projmoon.render_card"),
        justification=(
            "the shipped `!pm <sub>` replies are fully live-data-"
            "parameterized embeds built by sb/domain/projmoon/"
            "oracle_cards.py (the provenance footer + the greyple "
            "footer-less miss cards sit outside the grammar vocabulary — "
            "goldens/project_moon pins the bytes). Zero components; the "
            "renderer presents the handler-built RenderedEmbed verbatim."),
    )


# --- renderer overrides ------------------------------------------------------


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar-rendered components + the shipped overview embed bytes."""
    from sb.domain.projmoon import oracle_cards
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=oracle_cards.overview_card())


async def _render_card(spec: PanelSpec, ctx) -> object:
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    embed = (ctx.params or {}).get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# --- registration — MODULE IMPORT (BUG A rule) --------------------------------


_SPECS = {
    "projmoon.hub": projmoon_hub_spec,
    "projmoon.card": projmoon_card_spec,
}

_RENDERERS = {
    "projmoon.render_hub": _render_hub,
    "projmoon.render_card": _render_card,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register_refs()


def install_projmoon_panels() -> tuple[PanelSpec, ...]:
    out = []
    for factory in _SPECS.values():
        spec = factory()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    _register_refs()
