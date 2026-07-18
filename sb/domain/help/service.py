"""Help projection service (band 1; category rework D-0055).

Help stays a PROJECTION (D-0026, C-7 one-description-surface): every entry
derives from the live manifest command inventory. The rework replaces the
single-embed hub (which silently shed past Discord's 6000-char budget — 16
of 39 subsystems rendered) with the shipped three-level shape:

    help.home            — category index ("Pick a category…" select; one
                           compact field per category — never sheds)
    help.cat_<hub>       — one panel per category: member features + a
                           "Pick a feature…" select
    help.sub_<key>[_pN]  — one panel per subsystem: every command with its
                           summary, chunked across chained panels past the
                           24-field bound (nothing ever silently sheds)

Categories are the shipped mother hubs (sb/domain/help/categories.py —
harvested verbatim @7f7628e1); ROSTERS are computed from the live inventory
so an unmapped subsystem lands in OTHER, never nowhere.
"""

from __future__ import annotations

import importlib
import pkgutil

from sb.domain.help import categories as cats
from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import SUCCESS
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    NavRouteSpec,
    PageSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, is_registered, provider

__all__ = [
    "build_help_panel",
    "build_help_panels",
    "command_inventory",
    "install_help",
]

#: max command fields per subsystem panel (Discord caps fields at 25; the
#: shipped help reserved one slot — cogs/help_cog.py _FIELD_CAP = 24).
COMMANDS_PER_PAGE = 24

# module-side projection state: providers are registered SINGLETONS (ref
# re-registration is an error by design), so they read these dicts and
# rebuilds refresh the data, never the refs.
_inventory: dict[str, tuple[tuple[str, str], ...]] = {}
_rosters: dict[str, tuple[str, ...]] = {}
_built: dict[str, PanelSpec] = {}     # panel_id -> latest built spec (ref factories)


def command_inventory() -> dict[str, tuple[tuple[str, str], ...]]:
    """subsystem -> ((command name, summary), ...) — generated from EVERY
    sb.manifest declaration (the single source; help can never drift)."""
    import sb.manifest as manifest_pkg

    inventory: dict[str, list[tuple[str, str]]] = {}
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda i: i.name):
        module = importlib.import_module(f"sb.manifest.{info.name}")
        for manifest in ([getattr(module, "MANIFEST", None)]
                         + list(getattr(module, "MANIFESTS", ()) or ())):
            if manifest is None:
                continue
            key = str(getattr(manifest, "key", info.name))
            for cmd in getattr(manifest, "commands", ()) or ():
                # the QUALIFIED name (group path + name) — a grouped
                # subcommand's bare name ("add", "list") is ambiguous in
                # the hub listing (owner-feedback triage, 2026-07-09).
                name = str(getattr(cmd, "qualified_name", "") or ""
                           ) or str(getattr(cmd, "name", "") or "")
                if name:
                    inventory.setdefault(key, []).append(
                        (name, str(getattr(cmd, "summary", "") or "")))
    # deterministic, sensible order at BOTH levels: subsystems
    # alphabetically, commands alphabetically within each subsystem.
    return {k: tuple(sorted(v)) for k, v in sorted(inventory.items())}


# --- providers (registered once; read the module-side state) -------------------

def _ensure_provider(name: str, fn) -> ProviderRef:
    ref = ProviderRef(name)
    if not is_registered(ref):
        provider(name)(fn)
    return ref


def _visible_categories(ctx) -> tuple[cats.HelpCategory, ...]:
    """The shipped home index: exactly the eight registry hubs, in shipped
    order, with the staff-only hubs (moderation, admin) gated on the
    invoker's operator-ness — parity/goldens/help pins the 6-category member
    view against the 8-category operator view. Empty rosters do NOT hide a
    hub (the shipped index was static registry data, not inventory-driven)."""
    actor = getattr(ctx, "actor", None)
    is_staff = bool(getattr(actor, "is_guild_operator", False)
                    or getattr(actor, "is_bot_owner", False))
    return tuple(cat for cat in cats.CATEGORIES
                 if is_staff or not cat.staff_only)


async def _guild_overlay(ctx):
    """The guild's Help presentation overlay (the D-0026 lane, armed by
    the editor slice) — the EMPTY overlay for DMs/faults, so every
    default render stays byte-identical (goldens/help pin the bytes)."""
    from sb.domain.help.overlay import get_guild_help_overlay

    return await get_guild_help_overlay(
        int(getattr(ctx, "guild_id", 0) or 0) or None)


def _ensure_home_provider() -> ProviderRef:
    async def help_home_categories(ctx):
        # the shipped home field copy, verbatim: purpose + the hub command
        # (± the guild overlay's display-only hide/rename/re-describe —
        # empty overlay renders byte-identical defaults).
        overlay = await _guild_overlay(ctx)
        rows = []
        for cat in _visible_categories(ctx):
            if overlay.hidden("hub", cat.key):
                continue
            row = overlay.get("hub", cat.key)
            name = overlay.display_name_for("hub", cat.key,
                                            cat.display_name)
            purpose = (row.description if row is not None
                       and row.description is not None else cat.purpose)
            rows.append((f"{cat.emoji} {name}",
                         f"{purpose}\n→ `{cat.hub_command}`"))
        return tuple(rows)

    return _ensure_provider("sb.panels.help_home_categories",
                            help_home_categories)


def _ensure_home_options_provider() -> ProviderRef:
    async def help_home_options(ctx):
        # the shipped rich select options (label/value/description/emoji),
        # same visibility gate + overlay as the fields; VALUES stay the
        # stable category keys, so renames never break routing.
        overlay = await _guild_overlay(ctx)
        options = []
        for cat in _visible_categories(ctx):
            if overlay.hidden("hub", cat.key):
                continue
            row = overlay.get("hub", cat.key)
            options.append({
                "label": overlay.display_name_for("hub", cat.key,
                                                  cat.display_name),
                "value": cat.key,
                "description": (row.description if row is not None
                                and row.description is not None
                                else cat.purpose),
                "emoji": cat.emoji})
        return tuple(options)

    return _ensure_provider("sb.panels.help_home_options", help_home_options)


def _ensure_category_provider(cat_key: str) -> ProviderRef:
    async def help_category(ctx, _key=cat_key):
        overlay = await _guild_overlay(ctx)
        rows = []
        for sub in _rosters.get(_key, ()):
            if overlay.hidden("subsystem", sub):
                continue
            display, emoji = cats.subsystem_display(sub)
            display = overlay.display_name_for("subsystem", sub, display)
            names = " ".join(f"`{n}`" for n, _ in _inventory.get(sub, ()))
            rows.append((f"{emoji} {display}",
                         names or "No commands declared yet."))
        if not rows:
            rows.append(("Nothing here yet",
                         "No feature is homed under this category."))
        return tuple(rows)

    return _ensure_provider(f"sb.panels.help_cat_{cat_key}", help_category)


def _ensure_category_options_provider(cat_key: str) -> ProviderRef:
    """The feature select's options, provider-fed so the guild overlay's
    display-only hide/rename applies per render (label==value display
    strings — the D-0054 call-2 grammar; empty overlay ⇒ the identical
    static strings the panels previously declared)."""
    async def help_category_options(ctx, _key=cat_key):
        overlay = await _guild_overlay(ctx)
        options = []
        for sub in _rosters.get(_key, ()):
            if overlay.hidden("subsystem", sub):
                continue
            options.append(_overlay_subsystem_option(overlay, sub))
        return tuple(options)

    return _ensure_provider(f"sb.panels.help_cat_opts_{cat_key}",
                            help_category_options)


def _overlay_subsystem_option(overlay, sub: str) -> str:
    """``subsystem_option`` ± the overlay rename (same emoji, the custom
    display name)."""
    display, emoji = cats.subsystem_display(sub)
    return f"{emoji} {overlay.display_name_for('subsystem', sub, display)}"


def _ensure_commands_provider(sub_key: str, chunk: int) -> ProviderRef:
    async def help_commands(ctx, _key=sub_key, _chunk=chunk):
        commands = _inventory.get(_key, ())
        start = _chunk * COMMANDS_PER_PAGE
        rows = [(f"`{name}`", summary or "No description.")
                for name, summary in commands[start:start + COMMANDS_PER_PAGE]]
        if not rows:
            rows.append(("No commands declared yet",
                         "This feature declares no commands in its manifest."))
        return tuple(rows)

    return _ensure_provider(f"sb.panels.help_cmds_{sub_key}_{chunk}",
                            help_commands)


# --- select handlers (thin routes; the panel engine owns presentation) ---------

from dataclasses import dataclass


@dataclass(frozen=True)
class _Reply:
    """Duck-read by resolve() (outcome + user_message) — the stale-option
    terminal (the shipped copy: "That category is no longer available.")."""

    outcome: str
    user_message: str


def _ensure_handlers() -> None:
    from sb.spec.refs import handler

    if is_registered(HandlerRef("help.open_category")):
        return

    @handler("help.open_category")
    async def open_category(req):
        from sb.kernel.panels.engine import open_panel

        values = tuple(req.args.get("values", ()) or ())
        # home select values are category KEYS (the shipped wire shape —
        # goldens pin value="games" against label="Games").
        cat = cats.category_by_key(str(values[0])) if values else None
        if cat is None or cat.key not in _rosters:
            return _Reply(SUCCESS, "That category is no longer available.")
        await open_panel(PanelRef(f"help.cat_{cat.key}"), req)
        return None

    @handler("help.open_subsystem")
    async def open_subsystem(req):
        from sb.kernel.panels.engine import open_panel

        values = tuple(req.args.get("values", ()) or ())
        sub = (cats.subsystem_for_option(str(values[0]), _inventory.keys())
               if values else None)
        if sub is None and values:
            # an overlay-RENAMED option carries the custom display name —
            # resolve it against the guild's overlay (values stay display
            # strings per the D-0054 call-2 grammar).
            overlay = await _guild_overlay(req)
            option = str(values[0])
            sub = next((key for key in _inventory
                        if _overlay_subsystem_option(overlay, key) == option),
                       None)
        if sub is None:
            return _Reply(SUCCESS, "That feature is no longer available.")
        await open_panel(PanelRef(f"help.sub_{sub}"), req)
        return None

    @handler("help.render_home")
    async def render_home(spec, ctx):
        """Grammar render + the guild's saved Home-message frame (Q-0059
        live-home). A guild with NO home row renders the byte-identical
        default — the override returns the grammar render UNCHANGED (the
        mandatory no-op guard: parity/goldens/help/*.json replay verbatim).
        When a home row exists its title / body / accent override the
        default frame through the same ``home_embed_frame`` the builder's
        preview composes (preview-is-exact; mention suppression included)."""
        import dataclasses

        from sb.domain.help.overlay import (
            HOME_DEFAULT_COLOR,
            get_guild_help_overlay,
            home_color_token,
            home_embed_frame,
        )
        from sb.kernel.panels.render import render_panel

        rendered = await render_panel(spec, ctx)
        gid = int(getattr(ctx, "guild_id", 0) or 0)
        overlay = await get_guild_help_overlay(gid or None)
        if overlay.home is None:
            # no deviation stored — the default Home frame renders byte-
            # identical; leave the grammar render untouched.
            return rendered
        title, body, _color = home_embed_frame(
            overlay.home, default_color=HOME_DEFAULT_COLOR)
        # RenderedEmbed carries a style_token, not a raw color int — the
        # per-guild accent rides the named token (v1 stores only named
        # colors; an unknown int degrades to the default blue accent).
        return dataclasses.replace(
            rendered,
            embed=dataclasses.replace(
                rendered.embed,
                title=title,
                description=body,
                style_token=home_color_token(overlay.home.color)))


# --- the panel family -----------------------------------------------------------

def _chunk_panel_id(sub_key: str, chunk: int) -> str:
    return f"help.sub_{sub_key}" if chunk == 0 else f"help.sub_{sub_key}_p{chunk + 1}"


def _subsystem_panels(sub_key: str, cat_key: str) -> tuple[PanelSpec, ...]:
    display, emoji = cats.subsystem_display(sub_key)
    commands = _inventory.get(sub_key, ())
    chunks = max(1, -(-len(commands) // COMMANDS_PER_PAGE))
    panels = []
    for chunk in range(chunks):
        ref = _ensure_commands_provider(sub_key, chunk)
        page_note = f" · page {chunk + 1}/{chunks}" if chunks > 1 else ""
        extra = ()
        if chunk + 1 < chunks:
            extra = (NavRouteSpec(
                label=f"More ({chunk + 2}/{chunks}) ▶",
                route=PanelRef(_chunk_panel_id(sub_key, chunk + 1))),)
        elif chunks > 1:
            extra = (NavRouteSpec(
                label="◀ First page",
                route=PanelRef(_chunk_panel_id(sub_key, 0))),)
        panels.append(PanelSpec(
            panel_id=_chunk_panel_id(sub_key, chunk),
            subsystem="help",
            title=f"{emoji} {display} — commands{page_note}",
            audience=Audience.PUBLIC,
            frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
            body=(
                TextBlock(f"{len(commands)} command(s), generated from the "
                          f"`{sub_key}` manifest."),
                FieldsBlock(provider=ref),
            ),
            navigation=NavigationSpec(
                parent=PanelRef(f"help.cat_{cat_key}"),
                show_help=False, extra_routes=extra),
        ))
    return tuple(panels)


def _category_panel(cat: cats.HelpCategory) -> PanelSpec:
    ref = _ensure_category_provider(cat.key)
    # provider-fed (was a boot-static tuple): the guild overlay's
    # display-only hide/rename applies per render; an empty overlay
    # produces the identical display strings (byte-parity by
    # construction — goldens/help pin the default bytes).
    options_ref = _ensure_category_options_provider(cat.key)
    return PanelSpec(
        panel_id=f"help.cat_{cat.key}",
        subsystem="help",
        title=f"{cat.emoji} {cat.display_name}",
        audience=Audience.PUBLIC,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        body=(
            TextBlock(cat.purpose),
            FieldsBlock(provider=ref),
        ),
        selectors=(
            SelectorSpec(
                selector_id="feature_select", kind=SelectorKind.SUBSYSTEM,
                on_select=HandlerRef("help.open_subsystem"),
                options_source=options_ref,
                placeholder="Pick a feature for its full command list…",
                empty_state="No features in this category yet.",
                audience_tier="user"),
        ),
        navigation=NavigationSpec(parent=PanelRef("help.home"),
                                  show_help=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(("feature_select",),)),)),
    )


def _home_panel() -> PanelSpec:
    ref = _ensure_home_provider()
    options_ref = _ensure_home_options_provider()
    return PanelSpec(
        panel_id="help.home",
        subsystem="help",
        # the shipped home shape, byte-pinned by parity/goldens/help: title,
        # copy, blue accent, the verbatim legacy select id, rich options
        # (provider-fed — visibility is per-invoker), invoker audience
        # (slash opens ephemeral, the shipped behavior).
        title="📚 Help Menu",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(
            TextBlock("Pick a category from the dropdown below."),
            FieldsBlock(provider=ref),
        ),
        selectors=(
            SelectorSpec(
                selector_id="category_select", kind=SelectorKind.ENTITY,
                on_select=HandlerRef("help.open_category"),
                options_source=options_ref,
                placeholder="Pick a category…",   # the shipped copy, verbatim
                empty_state="No categories available.",
                audience_tier="user",
                custom_id_override="help_categories:select"),  # legacy pin
        ),
        # the help hub IS home — no help slot on itself (render also guards
        # subsystem=="help"), home stays for the root hub when one exists.
        navigation=NavigationSpec(show_help=False),
        renderer_override=HandlerRef("help.render_home"),
        justification=(
            "the Q-0059 live Help-Home frame (title / body / accent) is a "
            "per-guild deviation the static grammar cannot carry: when the "
            "guild stored a custom Home message the override re-frames the "
            "embed through home_embed_frame (the same composer the builder "
            "preview uses — preview-is-exact); a guild with no home row "
            "returns the grammar render UNCHANGED, so the byte-identical "
            "default Home replays verbatim. The override adjusts only the "
            "embed title / description / accent; the category fields, the "
            "select and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(("category_select",),)),)),
    )


def build_help_panels() -> tuple[PanelSpec, ...]:
    """(Re)build the WHOLE help family from the live inventory: home +
    per-category + per-subsystem chunk panels, in registration order
    (children first so parents' back-routes always resolve)."""
    _inventory.clear()
    _inventory.update(command_inventory())
    _rosters.clear()
    _rosters.update(cats.category_rosters(_inventory.keys()))
    _ensure_handlers()

    panels: list[PanelSpec] = []
    for cat in (*cats.CATEGORIES, cats.OTHER_CATEGORY):
        roster = _rosters.get(cat.key)
        if not roster:
            continue
        for sub in roster:
            panels.extend(_subsystem_panels(sub, cat.key))
        panels.append(_category_panel(cat))
    panels.append(_home_panel())

    # PanelRef factories (P2 resolves navigation parents / extra routes):
    # registered once per id, reading the latest built spec.
    from sb.spec.refs import panel as panel_ref_decorator

    for spec in panels:
        _built[spec.panel_id] = spec
        if spec.panel_id != "help.home" and not is_registered(
                PanelRef(spec.panel_id)):
            panel_ref_decorator(spec.panel_id)(
                lambda _pid=spec.panel_id: _built[_pid])
    return tuple(panels)


def build_help_panel() -> PanelSpec:
    """(Re)build the help HOME hub from the live inventory (the historical
    single-panel entry — kept as the `help.home` factory seam)."""
    build_help_panels()
    return _home_panel()


def install_help() -> PanelSpec:
    """Boot wiring: rebuild from the full inventory + register the family
    (idempotent for identical specs)."""
    home = None
    for spec in build_help_panels():
        try:
            registered = register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and "duplicate" not in str(exc):
                raise
            registered = spec
        if spec.panel_id == "help.home":
            home = registered
    return home


# import-time ref registration (P2 resolves PanelRef("help.home"))
from sb.spec.refs import panel as _panel  # noqa: E402


@_panel("help.home")
def _help_home_factory() -> PanelSpec:
    return build_help_panel()
