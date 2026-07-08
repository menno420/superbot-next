"""The treasury hub panel (band 3) — `!treasury`'s read-view v1: pool
balance + how-to copy; the Contribute modal/button set arrives with the
panel-action slice (successor work, the hub convention)."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import ProviderRef, is_registered, panel, provider

__all__ = ["ensure_panel_refs", "install_treasury_panels", "treasury_hub_spec"]

_HUB_PROVIDER = "treasury.hub_overview"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.treasury.store import get_treasury

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            balance = await get_treasury(guild_id)
            return (
                ("Pool balance", f"🏛️ **{balance:,}** 🪙"),
                ("Contribute", "`!treasury contribute <amount>` — donate "
                               "your own coins into the pool"),
                ("Disburse", "`!treasury grant @member <amount>` — "
                             "managers grant coins from the pool"),
            )
    return ref


def treasury_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="treasury.hub",
        subsystem="treasury",
        title="Server Treasury",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("The server-owned coin pool — the collective layer "
                      "between the economy and governance. Every movement "
                      "rides the audited seam and the economy ledger's "
                      "treasury:* money trail."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("treasury.hub")
def _hub_factory() -> PanelSpec:
    return treasury_hub_spec()


def install_treasury_panels() -> PanelSpec:
    spec = treasury_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    if not _is(PanelRef("treasury.hub")):
        _panel("treasury.hub")(_hub_factory)
