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


def _ctx_target(ctx: object) -> int:
    """The viewed member — the shipped ``UnifiedInventoryView.target``
    threading: ``!inventory @user`` opens the hub with ``inv_target`` in the
    request args, and the session-click adapter replays the OPEN's args on
    every category click (``EphemeralComponent.args``), so detail panels
    render the TARGET's items, not the clicker's (the shipped
    ``self._hub.target`` semantic). Falls back to the actor."""
    params = getattr(ctx, "params", {}) or {}
    target = int(params.get("inv_target", 0) or 0)
    return target or int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                         or 0)

# The shipped category population is STATIC catalogue metadata (+ the
# "Other" catch-all) — so the hub's per-category buttons are declarable.
# The shipped `_add_category_buttons` showed one button per NON-EMPTY
# category (clear_items + the ordered non-empty fold) — the hub's
# renderer_override drops empty-category buttons per render (the D-0068
# component-drop lane); parity/goldens/inventory/sweep_inventory.json pins
# the zero-component empty-inventory wire shape.
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
            user_id = _ctx_target(ctx)
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
            user_id = _ctx_target(ctx)
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
        # the shipped accent — ECONOMY_COLOR (discord.Color.gold()); the
        # shipped footer is a literal outside FooterMode's vocabulary
        # (renderer_override below, the treasury/cleanup-hub precedent).
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        body=(
            TextBlock("The unified item browser — one catalogue across "
                      "economy, mining, fishing, and collectibles, grouped "
                      "by category, rarest-first. Select a category below "
                      "to view details."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=tuple(actions),
        # the shipped UnifiedInventoryView carried ONLY its own category
        # buttons (a timeout BaseView — no nav row); the golden pins the
        # zero-component empty state.
        navigation=NavigationSpec(show_help=False, show_home=False),
        # the shipped view was ctx-bound and timeout-based (view-local
        # button callbacks, no persistent custom_ids) — run-minted ids,
        # never a panel_anchors row (the golden's db_delta carries none).
        session_lifecycle=True,
        renderer_override=HandlerRef("inventory.render_hub"),
        justification=(
            "the shipped hub embed (disbot/cogs/inventory_cog.py "
            "UnifiedInventoryView.build_hub_embed) is state-dependent on "
            "every surface — outside the grammar's static vocabulary. The "
            "override delegates the COMPONENTS to render_panel and adjusts: "
            "the target-parameterized TITLE (\"🎒 {display_name}'s "
            "Inventory\"), the state-dependent DESCRIPTION (the category "
            "preview lines, or the empty-state literal 'No items yet — go "
            "mining with `!mine` or visit `!shop`!'), the FOOTER literal "
            "('Select a category below to view details.'), the target-"
            "avatar THUMBNAIL (set_thumbnail(target.display_avatar.url)), "
            "the FIELDS dropped (the shipped embed had none — the declared "
            "FieldsBlock preview renders as the shipped DESCRIPTION), and "
            "the COMPONENT DROP of empty-category buttons (the shipped "
            "_add_category_buttons added one button per NON-EMPTY category "
            "— parity/goldens/inventory/sweep_inventory.json pins the "
            "empty-inventory zero-component shape)."),
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


async def _member_display(user_id: int, guild_id: int) -> tuple[str, str]:
    """(display name, avatar url) through the guild-directory read port —
    for PanelRef-routed opens (the economy hub's 🎒 Inventory button) that
    carry no origin message. Degrades to ("", "") when no directory is
    armed — never invented data (the economy-hub precedent)."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ no name/thumbnail
        return "", ""
    return member.tag.rsplit("#", 1)[0], member.display_avatar_url


@handler("inventory.render_hub")
async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped hub embed verbatim (see the spec's
    justification): target-name title, gold accent, avatar thumbnail, the
    state-dependent description, the footer literal, no fields; components
    delegate to render_panel then DROP the empty-category buttons (the
    shipped one-button-per-non-empty-category fold)."""
    import dataclasses

    from sb.domain.inventory import service
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    params = getattr(ctx, "params", {}) or {}
    invoker = int(getattr(ctx.actor, "user_id", 0) or 0)
    target = int(params.get("inv_target", 0) or 0) or invoker
    name = str(params.get("inv_name", "") or "")
    icon = str(params.get("inv_icon", "") or "")
    if not name:        # PanelRef-routed open (no command params)
        name, icon = await _member_display(target, int(ctx.guild_id or 0))
        if not name:
            name = f"<@{target}>"
    grouped = await service.build_combined_inventory(
        target, int(ctx.guild_id or 0))
    if not grouped:
        description = ("No items yet — go mining with `!mine` or visit "
                       "`!shop`!")
    else:
        description = "\n".join(service.render_hub_lines(grouped))
    embed = RenderedEmbed(
        title=f"🎒 {name}'s Inventory",
        description=description,
        footer="Select a category below to view details.",
        style_token=spec.frame.style_token,
        thumbnail_ref=icon)
    # canonical-id matching (overrides run before _mint_ephemeral).
    keep = {f"{spec.panel_id}.open_{category_slug(c)}"
            for c in _CATEGORIES if c in grouped}
    components = tuple(c for c in base.components if c.custom_id in keep)
    return dataclasses.replace(base, embed=embed, components=components)


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

    from sb.spec.refs import HandlerRef as _H, handler as _handler

    _ensure_hub_provider()
    _ensure_line_renderer()
    if not _is(_H("inventory.render_hub")):
        _handler("inventory.render_hub")(_render_hub)
    for cat in _CATEGORIES:
        _ensure_detail_provider(cat)
        pid = _detail_panel_id(cat)
        if not _is(_P(pid)):
            _panel(pid)(_detail_factory(cat))
    if not _is(_P("inventory.hub")):
        _panel("inventory.hub")(_hub_factory)
