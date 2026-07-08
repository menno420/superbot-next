"""The inventory hub panel (band 3) — read-view v1 over the coupled item
namespace; per-category detail views (paging/filter/sort — the shipped
_CategoryView) arrive with the panel-action slice."""

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

__all__ = ["ensure_panel_refs", "install_inventory_panels", "inventory_hub_spec"]

_HUB_PROVIDER = "inventory.hub_overview"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.economy.catalogue import (
                CATEGORY_META,
                CATEGORY_ORDER,
                ITEM_CATALOGUE,
            )

            fields = []
            for cat in CATEGORY_ORDER:
                items = [k for k, m in ITEM_CATALOGUE.items()
                         if m.get("category") == cat]
                meta = CATEGORY_META.get(cat, {"emoji": "📦"})
                fields.append((f"{meta['emoji']} {cat}",
                               ", ".join(sorted(items)) or "—"))
            return tuple(fields)
    return ref


def inventory_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="inventory.hub",
        subsystem="inventory",
        title="Inventory",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("The unified item browser — one catalogue across "
                      "economy, mining, fishing, and collectibles. "
                      "`!inventory [@user]` shows owned items grouped by "
                      "category, rarest-first."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        navigation=NavigationSpec(),
    )


@panel("inventory.hub")
def _hub_factory() -> PanelSpec:
    return inventory_hub_spec()


def install_inventory_panels() -> PanelSpec:
    spec = inventory_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    if not _is(PanelRef("inventory.hub")):
        _panel("inventory.hub")(_hub_factory)
