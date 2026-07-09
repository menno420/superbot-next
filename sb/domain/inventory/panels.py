"""The inventory panels (band 3, panel-action slice) — the shipped
`UnifiedInventoryView` hub (one button per category → a category detail
panel) over the coupled item namespace, all through the declarative grammar.

Detail panels render the shipped default view: the invoker's items in that
category, rarity-grouped rarest-first (the unit-pinned pure cores in
sb/domain/inventory/service.py). The shipped INTERACTIVE re-sort / type
filter / page cycle are DECLARED as ListSpec sort/filter options — the
grammar's §2.3 "one shared BrowserView engine" interprets them when it
lands (named successor work, K8 kernel; D-0034): declared data today,
honest static default view until the engine arms."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    ListBlock,
    ListSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    handler,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "category_detail_specs",
    "category_slug",
    "ensure_panel_refs",
    "install_inventory_panels",
    "inventory_hub_spec",
]

_HUB_PROVIDER = "inventory.hub_overview"
_LINE_RENDERER = "inventory.render_line"

# The shipped category population is STATIC catalogue metadata (+ the
# "Other" catch-all) — so the hub's per-category buttons are declarable.
# Deviation from shipped (D-0034): every category button always shows
# (no per-render count badge / non-empty filtering); an empty category's
# detail panel renders its empty_state.
_CATEGORIES: tuple[str, ...] = (
    "Mining Materials", "Crafted Items", "Tools", "Fishing",
    "Collectibles", "Economy Items", "Other",
)


def category_slug(category: str) -> str:
    return category.lower().replace(" ", "_")


def _detail_panel_id(category: str) -> str:
    return f"inventory.cat_{category_slug(category)}"


def _detail_provider_name(category: str) -> str:
    return f"inventory.items_{category_slug(category)}"


def _category_types(category: str) -> tuple[str, ...]:
    from sb.domain.economy.catalogue import ITEM_CATALOGUE

    return tuple(sorted({m.get("type", "Item")
                         for m in ITEM_CATALOGUE.values()
                         if m.get("category") == category}))


def _ensure_line_renderer() -> HandlerRef:
    ref = HandlerRef(_LINE_RENDERER)
    if not is_registered(ref):
        @handler(_LINE_RENDERER)
        def render_line(item: object) -> str:
            # the detail providers emit pre-rendered lines (headers + the
            # shipped item lines) — identity keeps the engine's bullet off.
            return str(item)
    return ref


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.inventory import service

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            grouped = await service.build_combined_inventory(user_id, guild_id)
            if not grouped:
                return (("🎒 Inventory",
                         "No items yet — go mining with `!mine` or visit "
                         "`!shop`!"),)
            lines = service.render_hub_lines(grouped)
            return (("🎒 Inventory", "\n".join(lines)),)
    return ref


def _ensure_detail_provider(category: str) -> ProviderRef:
    name = _detail_provider_name(category)
    ref = ProviderRef(name)
    if not is_registered(ref):
        @provider(name)
        async def category_items(ctx: object, _category: str = category):
            from sb.domain.inventory import service

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            grouped = await service.build_combined_inventory(user_id, guild_id)
            items = grouped.get(_category, [])
            if not items:
                return ()
            lines: list[str] = []
            for tier, tier_lines in service.group_by_rarity(
                    service.sort_items(items, "rarity")):
                lines.append(f"__{tier} ({len(tier_lines)})__")
                lines.extend(tier_lines)
            return tuple(lines)
    return ref


def inventory_hub_spec() -> PanelSpec:
    from sb.domain.economy.catalogue import CATEGORY_META

    actions = []
    for cat in _CATEGORIES:
        meta = CATEGORY_META.get(cat, {"emoji": "📦"})
        actions.append(PanelActionSpec(
            action_id=f"open_{category_slug(cat)}", label=cat,
            emoji=str(meta.get("emoji", "📦")),
            style=ActionStyle.PRIMARY, audience_tier="user",
            handler=PanelRef(_detail_panel_id(cat))))
    return PanelSpec(
        panel_id="inventory.hub",
        subsystem="inventory",
        title="🎒 Inventory",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("The unified item browser — one catalogue across "
                      "economy, mining, fishing, and collectibles, grouped "
                      "by category, rarest-first. Select a category below "
                      "to view details."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=tuple(actions),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            tuple(f"open_{category_slug(c)}" for c in _CATEGORIES[:5]),
            tuple(f"open_{category_slug(c)}" for c in _CATEGORIES[5:]),
        )),)),
    )


def category_detail_specs() -> tuple[PanelSpec, ...]:
    from sb.domain.economy.catalogue import CATEGORY_META

    specs = []
    for cat in _CATEGORIES:
        meta = CATEGORY_META.get(cat, {"emoji": "📦"})
        specs.append(PanelSpec(
            panel_id=_detail_panel_id(cat),
            subsystem="inventory",
            title=f"{meta.get('emoji', '📦')} {cat}",
            audience=Audience.INVOKER,
            frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
            body=(
                ListBlock(
                    list_spec=ListSpec(
                        item_render_ref=_ensure_line_renderer(),
                        page_size=12,      # 8 shipped items + rarity headers
                        empty_state="Nothing here.",
                        sort_options=("rarity", "quantity", "name"),
                        filter_options=_category_types(cat),
                        default_sort="rarity"),
                    provider=_ensure_detail_provider(cat)),
            ),
            navigation=NavigationSpec(parent=PanelRef("inventory.hub")),
        ))
    return tuple(specs)


@panel("inventory.hub")
def _hub_factory() -> PanelSpec:
    return inventory_hub_spec()


def _detail_factory(category: str):
    def _factory() -> PanelSpec:
        for spec in category_detail_specs():
            if spec.panel_id == _detail_panel_id(category):
                return spec
        raise LookupError(category)
    return _factory


# module-import registration (the manifest references these PanelRefs from
# the hub's open-category actions — P2 resolves against the refs table).
for _cat in _CATEGORIES:
    if not is_registered(PanelRef(_detail_panel_id(_cat))):
        panel(_detail_panel_id(_cat))(_detail_factory(_cat))
del _cat


def install_inventory_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (inventory_hub_spec(), *category_detail_specs()):
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, is_registered as _is, panel as _panel

    _ensure_hub_provider()
    _ensure_line_renderer()
    for cat in _CATEGORIES:
        _ensure_detail_provider(cat)
        pid = _detail_panel_id(cat)
        if not _is(_P(pid)):
            _panel(pid)(_detail_factory(cat))
    if not _is(_P("inventory.hub")):
        _panel("inventory.hub")(_hub_factory)
