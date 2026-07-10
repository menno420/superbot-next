"""The hermes bridge-unconfigured panel — the shipped missing-config reply
(disbot/cogs/hermes_cog.py: red "Hermes bridge not configured" embed,
no footer, no components), declared as a static PanelSpec."""

from __future__ import annotations

from sb.domain.hermes.service import MISSING_CONFIG_HELP
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import PanelRef, is_registered, panel

__all__ = [
    "BRIDGE_UNCONFIGURED_PANEL_ID",
    "bridge_unconfigured_spec",
    "ensure_hermes_refs",
]

BRIDGE_UNCONFIGURED_PANEL_ID = "hermes.bridge_unconfigured"


def bridge_unconfigured_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=BRIDGE_UNCONFIGURED_PANEL_ID,
        subsystem="hermes",
        title="Hermes bridge not configured",
        audience=Audience.INVOKER,
        # the shipped embed carried no footer and no components — a plain
        # discord.Color.red() error card (goldens/hermes pin the bytes).
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock(MISSING_CONFIG_HELP),),
        # show_home + FOLLOW_PARENT: the home slot stays declared (the §2.4
        # never-strand floor) and resolves against the subsystem's hub —
        # hermes registers none, so the shipped bare error card renders
        # with zero components (the goldens' shape).
        navigation=NavigationSpec(show_help=False, show_home=True),
    )


@panel(BRIDGE_UNCONFIGURED_PANEL_ID)
def _bridge_unconfigured_factory() -> PanelSpec:
    return bridge_unconfigured_spec()


def ensure_hermes_refs() -> None:
    """Idempotent re-arm (the ENSURE_REFS pattern, D-0025)."""
    if not is_registered(PanelRef(BRIDGE_UNCONFIGURED_PANEL_ID)):
        panel(BRIDGE_UNCONFIGURED_PANEL_ID)(_bridge_unconfigured_factory)
