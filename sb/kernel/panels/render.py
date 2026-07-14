"""The pure render model (K8/S9b): ``PanelSpec + PanelContext → RenderedPanel``.

Kernel-side and discord-free — the discord adapter materializes a
``RenderedPanel`` into ``discord.Embed`` + ``discord.ui.View``
(sb/adapters/discord/panel_view.py). Everything Discord-shaped is enforced
HERE, once: embed budgets (EmbedFrameSpec + the hard platform limits),
component custom_ids from the static table mint, ``visible_when`` gating,
copy through the L-24 ``CopyResolver``, and the engine-injected nav row +
page-turn controls (outside the layout search space, §2.4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sb.kernel.interaction.locale import active_copy_resolver
from sb.kernel.interaction.predicates import EvalContext, evaluate
from sb.kernel.panels.context import PanelContext
from sb.kernel.panels.registry import (
    NAV_BACK_ID_PREFIX,
    NAV_HELP_ID,
    NAV_HUB_ID_PREFIX,
    NAV_PAGE_ID_PREFIX,
    NAV_ROW,
    resolve_home_hub,
)
from sb.spec.panels import (
    ActionStyle,
    EmbedFrameSpec,
    FieldsBlock,
    ListBlock,
    PanelSpec,
    TableBlock,
    TextBlock,
)
from sb.spec.refs import RefUnresolved, resolve as resolve_ref

logger = logging.getLogger("sb.kernel.panels.render")

__all__ = [
    "RenderedAttachment",
    "RenderedComponent",
    "RenderedEmbed",
    "RenderedPanel",
    "install_hub_resolver",
    "render_panel",
    "reset_render_ports_for_tests",
]

# EmbedFrameSpec.style_token → the shipped embed accent color (both
# presenters — the discord adapter and the parity capture twin — read this
# ONE map, so live and captured colors can never drift apart). Tokens are
# named for the shipped discord.Color constants the old bot used; ported
# bands add their tokens as their goldens pin them.
STYLE_TOKEN_COLORS: dict[str, int] = {
    "blue": 3447003,          # discord.Color.blue() — the shipped help hub
    "purple": 10181046,       # discord.Color.purple() — the shipped GAME_COLOR
                              # (views/rps/_helpers.py; goldens/rps_tournament)
    "green": 3066993,         # discord.Color.green() — the shipped
                              # SUCCESS_COLOR (utils/ui_constants.py; the
                              # blackjack table embed, goldens/blackjack)
    "red": 15158332,          # discord.Color.red() — the shipped ERROR_COLOR
                              # (cogs/hermes_cog.py missing-config cards,
                              # goldens/hermes; blackjack loss/bust terminals)
    "gold": 15844367,         # discord.Color.gold() — the shipped Daily
                              # Reward embed (cogs/economy_cog.py)
    "blurple": 5793266,       # discord.Color.blurple() — the shipped UX Lab
                              # Home card (views/ux_lab/home.py;
                              # goldens/ux_lab + goldens/uxlab)
    "light_grey": 9936031,    # discord.Color.light_grey() — the shipped BTD6
                              # low-confidence response card
                              # (utils/btd6/response_embed.py;
                              # goldens/btd6/sweep_btd6_ask)
    "greyple": 10070709,      # discord.Color.greyple() — the shipped BTD6
                              # ingestion-readiness "disabled" card
                              # (cogs/btd6/_builders.py;
                              # goldens/btd6/sweep_btd6_ops_readiness)
    "orange": 15105570,       # discord.Color.orange() — the shipped
                              # warn-state accent (the AI readiness card's
                              # warns-only state; the same constant the
                              # moderation cards pin —
                              # goldens/moderation/sweep_modmenu)
    "teal": 1752220,          # discord.Color.teal() — the shipped BTD6
                              # CT-relic detail card (cogs/btd6/_builders.py
                              # build_ct_relic_embed; unpinned found-relic
                              # path of the golden-pinned relic command) +
                              # the shipped Tide Pool panel
                              # (views/fishing/tide_pool.py _TIDE_POOL_COLOR;
                              # goldens/fishing/sweep_tidepool pins the byte)
    "dark_teal": 1146986,     # discord.Color.dark_teal() — the shipped
                              # Dock / Boathouse / Fishery structure panels
                              # (views/fishing/{dock,boathouse,fishery}.py;
                              # goldens/fishing/sweep_dock + sweep_boathouse
                              # + sweep_fishery pin the byte)
    "dark_red": 10038562,     # discord.Color.dark_red() — the shipped AI
                              # review-log cards (cogs/ai_review_cog.py
                              # _REVIEW_COLOR; goldens/ai/sweep_aireview
                              # pins the byte)
    "magenta": 15277667,      # discord.Color.magenta() — the shipped
                              # _KARMA_COLOR standing card
                              # (cogs/karma_cog.py _karma_card;
                              # goldens/karma/sweep_karma +
                              # karma_slash_card pin the accent)
    "leaf_green": 5025616,    # Color.from_rgb(0x4C, 0xAF, 0x50) — the
                              # shipped _FOUR_TWENTY_COLOR "leafy green"
                              # overview embed (cogs/four_twenty_cog.py;
                              # goldens/four_twenty/sweep_420 pins the
                              # byte)
    "dark_grey": 6323595,     # discord.Color.dark_grey() — the shipped
                              # MINING_COLOR (utils/ui_constants.py;
                              # goldens/mining/sweep_minemenu pins the
                              # byte)
    "yellow": 16705372,       # discord.Color.yellow() — the shipped
                              # WARNING_COLOR (utils/ui_constants.py; the
                              # Item Shop embed, services/economy_helpers
                              # _shop_embed — goldens/economy/sweep_shop
                              # pins the byte)
}

# hub key → the shipped hub display name (disbot/utils/subsystem_registry.py
# display_name, verbatim): the shipped standard-nav home button carried the
# HUB'S name, never a generic "Home" — the goldens pin the label bytes
# ("↩ Administration", "↩ Community", "↩ Games"). Entries land as ported
# goldens pin them (the STYLE_TOKEN_COLORS growth rule); an unmapped hub
# keeps the "Home" placeholder.
HUB_NAV_LABELS: dict[str, str] = {
    "admin": "Administration",    # goldens/uxlab/sweep_slash_uxlab
    "moderation": "Moderation",   # goldens/cleanup/sweep_cleanup
    "community": "Community",     # goldens/ticket/sweep_ticket
    "games": "Games",             # goldens/casino/sweep_casino
}

# Discord hard limits — engine-enforced (clamping is never a callsite courtesy).
TITLE_LIMIT = 256
DESCRIPTION_LIMIT = 4096
FIELD_NAME_LIMIT = 256
FIELD_VALUE_LIMIT = 1024
EMBED_TOTAL_LIMIT = 6000
MAX_EMBED_FIELDS = 25


@dataclass(frozen=True)
class RenderedComponent:
    kind: str                    # "button" | "selector"
    custom_id: str
    label: str
    row: int
    style: str = ActionStyle.SECONDARY.value
    emoji: str = ""
    disabled: bool = False
    placeholder: str = ""        # selectors
    min_values: int = 1
    max_values: int = 1
    # selector options: plain strings (label == value, the render grammar's
    # compact form) OR mappings with label/value(/description/emoji/default)
    # — the shipped rich-option shape, provider-fed (goldens pin it byte-
    # for-byte, e.g. the help category select).
    options: tuple[object, ...] = ()
    # SelectorKind.CHANNEL selectors are Discord-native pickers (wire
    # component type 8): Discord supplies the option list, so no options
    # materialize and the tuple names the allowed channel types ((0,) =
    # text channels — the shipped LogChannelSelectView shape,
    # goldens/logging/logging_enable_and_bind pins the wire bytes).
    channel_types: tuple[int, ...] | None = None
    # LINK buttons (wire style 5) carry a URL and NO custom_id — the shipped
    # discord.ui.Button(url=…, style=ButtonStyle.link) shape (the BTD6 paragon
    # calculator's 🌐 Web calculator button; goldens/btd6/sweep_paragon pins
    # the wire bytes: no custom_id key, a `url` key). Renderer_override panels
    # inject them; the grammar renderer never sets a url.
    url: str = ""
    # SelectorKind.ROLE selectors are Discord-native pickers too (wire
    # component type 6, discord.ui.RoleSelect): Discord supplies the
    # option list — "role" marks the component for both presenters (the
    # shipped ticket setup wizard's staff-role picker,
    # goldens/ticket/sweep_ticketsetup pins the wire bytes).
    native_picker: str = ""


@dataclass(frozen=True)
class RenderedEmbed:
    title: str
    description: str
    # (name, value) or (name, value, inline) — the optional third element is
    # the discord inline flag (shipped embeds mix inline fields, e.g. the
    # blackjack table's "Bet"; 2-tuples render inline=False).
    fields: tuple[tuple, ...] = ()
    footer: str = ""
    thumbnail_ref: str = ""
    alt_text: str = ""           # L-24 rider 1 — carried to the adapter's discord.File
    style_token: str = ""
    # embed author line (the shipped set_author(display_name, avatar) on
    # per-member result cards, e.g. the Daily Reward embed).
    author_name: str = ""
    author_icon: str = ""
    # embed hero image (the shipped set_image(url=...) on the avatar card —
    # goldens/utility/sweep_avatar pins the wire shape). Grammar renders
    # never set it; renderer_override panels carry it for the shipped
    # image-bearing cards.
    image_url: str = ""
    # embed timestamp (the shipped ``discord.Embed(timestamp=...)`` corner —
    # an ISO-8601 string; both presenters carry it: the parity twin
    # serializes it verbatim, the live adapter parses it to the native
    # datetime). First pinned by goldens/diagnostic/sweep_platform_findings
    # (the shipped findings card stamps utcnow); "" omits the wire key.
    timestamp: str = ""


@dataclass(frozen=True)
class RenderedAttachment:
    """One message attachment (the shipped ``discord.File`` send — e.g. the
    ``/myprofile`` hero card ``profile.png``). The presenter materializes it
    (the discord adapter builds ``discord.File``; the parity capture twin
    records the multipart shape fake_http captured: filenames only)."""

    filename: str
    data: bytes = b""


@dataclass(frozen=True)
class RenderedPanel:
    panel_id: str
    # ``embed=None`` + ``content`` = a CONTENT-only panel message (the
    # shipped plain-text send carrying a component View — logging's
    # channel-binding picker, goldens/logging/logging_enable_and_bind).
    embed: RenderedEmbed | None
    components: tuple[RenderedComponent, ...] = ()
    content: str | None = None
    # message attachments (discord.File sends) — the shipped card sends put
    # the whole payload on the multipart wire; presenters own the mapping.
    attachments: tuple[RenderedAttachment, ...] = ()
    page: int = 0
    page_count: int = 1
    invoker_lock: int | None = None    # audience=invoker ⇒ the invoker's user_id
    timeout_s: int | None = 180
    audience: str = "invoker"
    anchor_policy: str = "reply"
    # session-view refresh (the shipped in-place game-view edit): when set,
    # the presenter EDITS this message instead of sending a new one (the
    # component ack becomes a deferred UPDATE — discord type 6).
    edit_message_ref: object | None = None
    # self-reactions: emoji the BOT adds to its own message right after the
    # send (the shipped `reg_msg.add_reaction("✅")` primer on tournament
    # registration messages — goldens pin the add_reaction egress call).
    # Presenters apply these on channel sends only; interaction responses
    # have no reactable message.
    self_reactions: tuple[str, ...] = ()


# FOLLOW_PARENT resolution port: subsystem -> its CURRENT parent_hub key (the
# manifest lookup at render/click time). Installed by the composition root
# once hubs exist; None until then.
HubResolver = "callable[[str], str | None]"
_hub_resolver = None


def install_hub_resolver(resolver) -> None:
    global _hub_resolver
    _hub_resolver = resolver


def reset_render_ports_for_tests() -> None:
    global _hub_resolver
    _hub_resolver = None


def _clamp(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)] + "…"


async def _provider_rows(ref, ctx: PanelContext):
    """Resolve + call a ProviderRef; a broken provider degrades to None
    (the block renders its empty_state), never a crashed panel."""
    if ref is None:
        return None
    try:
        provider = resolve_ref(ref)
        return await provider(ctx)
    except RefUnresolved:
        logger.warning("panel provider %r unresolved", getattr(ref, "name", ref))
        return None
    except Exception:  # noqa: BLE001 — a data provider never takes the panel down
        logger.warning("panel provider %r failed", getattr(ref, "name", ref), exc_info=True)
        return None


async def _render_body(spec: PanelSpec, ctx: PanelContext, resolver, browse=None):
    """→ (description, fields, browse_page_count).

    ``browse`` is None on the default (static) render — every code path below
    is then byte-identical to the pre-engine render. When a ``BrowseState`` is
    supplied, the List/Table block it names (``browse.block``) is filtered +
    sorted + paged through the shared BrowserView engine and its page_count is
    returned so ``render_panel`` can arm the browse controls; every other
    block still renders statically."""
    loc = ctx.locale
    desc_parts: list[str] = []
    fields: list[tuple[str, str]] = []
    budget = min(spec.frame.field_budget_chars, FIELD_VALUE_LIMIT)
    max_fields = min(spec.frame.max_fields, MAX_EMBED_FIELDS)
    browse_page_count = 1

    def add_field(name: str, value: str) -> None:
        if len(fields) < max_fields:
            fields.append((_clamp(name, FIELD_NAME_LIMIT), _clamp(value or "​", budget)))

    for block_idx, block in enumerate(spec.body):
        armed = browse is not None and block_idx == browse.block
        if isinstance(block, TextBlock):
            desc_parts.append(resolver.resolve(block.text, locale=loc))
        elif isinstance(block, FieldsBlock):
            rows = await _provider_rows(block.provider, ctx)
            for name, value in (rows or ()):
                add_field(resolver.resolve(str(name), locale=loc), str(value))
        elif isinstance(block, TableBlock):
            rows = await _provider_rows(block.provider, ctx)
            t = block.table
            if armed:
                from sb.kernel.panels import browserview

                page_rows, browse_page_count, _ = browserview.browse_page(
                    rows or (), t, browse)
                rows = page_rows
            if not rows:
                desc_parts.append(resolver.resolve(t.empty_state, locale=loc))
            else:
                header = " | ".join(resolver.resolve(c.label, locale=loc) for c in t.columns)
                lines = [header]
                slice_rows = rows if armed else list(rows)[: t.page_size]
                for row in slice_rows:
                    lines.append(" | ".join(str(row.get(c.key, "")) for c in t.columns))
                desc_parts.append(_clamp("\n".join(lines), budget))
        elif isinstance(block, ListBlock):
            items = await _provider_rows(block.provider, ctx)
            ls = block.list_spec
            if armed:
                from sb.kernel.panels import browserview

                page_items, browse_page_count, _ = browserview.browse_page(
                    items or (), ls, browse)
                items = page_items
            if not items:
                desc_parts.append(resolver.resolve(ls.empty_state, locale=loc))
            else:
                rendered_items = []
                item_renderer = None
                if ls.item_render_ref is not None:
                    try:
                        item_renderer = resolve_ref(ls.item_render_ref)
                    except RefUnresolved:
                        item_renderer = None
                slice_items = items if armed else list(items)[: ls.page_size]
                for item in slice_items:
                    rendered_items.append(
                        str(item_renderer(item)) if item_renderer else f"• {item}")
                desc_parts.append(_clamp("\n".join(rendered_items), budget))
    return "\n\n".join(p for p in desc_parts if p), tuple(fields), browse_page_count


def _footer(spec: PanelSpec) -> str:
    mode = spec.frame.footer_mode.value
    if mode == "subsystem":
        return spec.subsystem
    if mode == "provenance":
        return f"{spec.subsystem} · {spec.panel_id}"
    return ""


def _clamp_embed(frame: EmbedFrameSpec, title: str, description: str,
                 fields: tuple[tuple[str, str], ...], footer: str) -> RenderedEmbed:
    title = _clamp(title, TITLE_LIMIT)
    description = _clamp(description, DESCRIPTION_LIMIT)
    # total-budget pass (6000): shed description first, then trailing fields.
    def total(f):
        return len(title) + len(description) + len(footer) + sum(
            len(n) + len(v) for n, v in f)
    fields = list(fields)
    if total(fields) > EMBED_TOTAL_LIMIT:
        overshoot = total(fields) - EMBED_TOTAL_LIMIT
        keep = max(len(description) - overshoot, 0)
        description = _clamp(description, keep) if keep else ""
    while fields and total(fields) > EMBED_TOTAL_LIMIT:
        fields.pop()
    return RenderedEmbed(
        title=title, description=description, fields=tuple(fields), footer=footer,
        thumbnail_ref=frame.thumbnail_ref, alt_text=frame.alt_text,
        style_token=frame.style_token)


async def _visible(component_spec, ctx: PanelContext) -> bool:
    pred = getattr(component_spec, "visible_when", "") or ""
    if not pred:
        return True
    return await evaluate(pred, EvalContext(
        guild_id=ctx.guild_id or 0, channel_id=ctx.channel_id, actor=ctx.actor))


async def render_panel(spec: PanelSpec, ctx: PanelContext, *, page: int = 0,
                       subsystem_hub: str | None = None,
                       browse=None, window=None) -> RenderedPanel:
    """The render entry. ``subsystem_hub`` overrides the installed hub
    resolver (tests / pre-resolved callers).

    ``browse`` (a ``browserview.BrowseState``) arms the shared BrowserView
    engine for the block it names: the block is filtered/sorted/paged and the
    interactive sort/filter/page controls are injected outside the layout
    search space (like the page-turn nav). ``browse=None`` is the default,
    static render — its output is byte-identical to the pre-engine renderer,
    so no surface's default rendering changes until it opts in.

    ``window`` (a ``selectwindow.SelectWindowState``) positions ONE declared
    ``windowed=True`` selector on a window of its option set (the
    windowed-select grammar successor); when omitted it falls back to the
    reserved ``ctx.params`` key (``selectwindow.WINDOW_PARAM``) — the
    engine's thread for renderer_override panels that re-call
    ``render_panel(spec, ctx)`` themselves — and defaults every windowed
    selector to window 0."""
    from sb.kernel.panels import selectwindow

    resolver = active_copy_resolver()
    loc = ctx.locale
    if window is None:
        params = getattr(ctx, "params", None)
        if isinstance(params, dict):
            window = params.get(selectwindow.WINDOW_PARAM)

    description, fields, browse_page_count = await _render_body(
        spec, ctx, resolver, browse)
    embed = _clamp_embed(
        spec.frame, resolver.resolve(spec.title, locale=loc), description, fields,
        resolver.resolve(_footer(spec), locale=loc))

    # components for the requested page (layout order is deterministic).
    pages = spec.layout.pages
    page_count = max(len(pages), 1)
    page = min(max(page, 0), page_count - 1)
    by_id = {a.action_id: a for a in spec.actions}
    by_id.update({s.selector_id: s for s in spec.selectors})
    components: list[RenderedComponent] = []
    # engine-injected ◀ Prev / Next ▶ window nav for windowed selectors
    # (collected while the rows render, appended after — outside the
    # searchable space, like every nav slot).
    window_nav: list[RenderedComponent] = []
    rows = pages[page].rows if pages else ()
    for row_idx, row in enumerate(rows):
        for comp_id in row:
            cspec = by_id[comp_id]
            if not await _visible(cspec, ctx):
                continue
            custom_id = getattr(cspec, "custom_id_override", "") or f"{spec.panel_id}.{comp_id}"
            if hasattr(cspec, "selector_id"):
                from sb.spec.panels import SelectorKind as _SK

                if cspec.kind is _SK.CHANNEL:
                    # Discord-native channel picker (wire type 8): the
                    # client supplies the options, so nothing materializes
                    # and the component can never be empty-disabled.
                    components.append(RenderedComponent(
                        kind="selector", custom_id=custom_id,
                        label=resolver.resolve(cspec.placeholder, locale=loc),
                        row=row_idx,
                        placeholder=resolver.resolve(cspec.placeholder,
                                                     locale=loc),
                        min_values=cspec.min_values,
                        max_values=cspec.max_values,
                        channel_types=(0,)))
                    continue
                if cspec.kind is _SK.ROLE and not cspec.options_source:
                    # Discord-native role picker (wire type 6,
                    # discord.ui.RoleSelect): same posture as CHANNEL —
                    # the client supplies the options, so the lane arms
                    # ONLY when the spec declares no options source (the
                    # shipped ticket setup staff-role picker; goldens/
                    # ticket/sweep_ticketsetup pins the wire bytes). A
                    # provider-fed ROLE selector keeps the roster-fed
                    # string-select lane below (the shipped ai policy
                    # role picker, wire type 3).
                    components.append(RenderedComponent(
                        kind="selector", custom_id=custom_id,
                        label=resolver.resolve(cspec.placeholder, locale=loc),
                        row=row_idx,
                        placeholder=resolver.resolve(cspec.placeholder,
                                                     locale=loc),
                        min_values=cspec.min_values,
                        max_values=cspec.max_values,
                        native_picker="role"))
                    continue
                if cspec.kind is _SK.MEMBER and not cspec.options_source:
                    # Discord-native member picker (wire type 5,
                    # discord.ui.UserSelect): same posture as ROLE/CHANNEL —
                    # the client supplies the roster, so no options
                    # materialize and the component can never be
                    # empty-disabled. The shipped creature-battle opponent
                    # picker (_OpponentSelect; the selected id arrives on the
                    # ordinary select `values` round-trip, so the kernel
                    # never dereferences the interaction's resolved members).
                    components.append(RenderedComponent(
                        kind="selector", custom_id=custom_id,
                        label=resolver.resolve(cspec.placeholder, locale=loc),
                        row=row_idx,
                        placeholder=resolver.resolve(cspec.placeholder,
                                                     locale=loc),
                        min_values=cspec.min_values,
                        max_values=cspec.max_values,
                        native_picker="user"))
                    continue
                if isinstance(cspec.options_source, tuple):
                    options = cspec.options_source
                else:
                    # provider-fed options (SelectorSpec.options_source is
                    # "static tuple | provider" by grammar) — materialized at
                    # render time from the invoker's context; a broken/empty
                    # provider degrades to a disabled selector showing its
                    # empty_state, never a crashed panel.
                    options = tuple(await _provider_rows(cspec.options_source, ctx) or ())
                placeholder = resolver.resolve(
                    cspec.placeholder if options else cspec.empty_state, locale=loc)
                min_vals, max_vals = cspec.min_values, cspec.max_values
                win_size = selectwindow.window_size_of(cspec)
                if getattr(cspec, "windowed", False) and len(options) > win_size:
                    # the windowed-select grammar successor: the option set
                    # pages past Discord's cap with engine-injected
                    # ◀ Prev / Next ▶ nav (the shipped SelectWindow,
                    # views/paginated_select.py) instead of front-truncating
                    # (the #1040 silent-drop class). The window position
                    # rides the placeholder; the nav pair rides the nav row.
                    widx = 0
                    if (window is not None
                            and getattr(window, "panel_id", None) == spec.panel_id
                            and getattr(window, "selector_id", None) == comp_id):
                        widx = window.window
                    options, win_count, widx = selectwindow.window_options(
                        options, win_size, widx)
                    placeholder = selectwindow.windowed_placeholder(
                        placeholder, widx, win_count)
                    # the shipped per-window clamp: Discord rejects
                    # max_values above the visible option count.
                    max_vals = max(1, min(max_vals, len(options)))
                    min_vals = max(0, min(min_vals, max_vals))
                    window_nav.extend(selectwindow.window_controls(
                        selectwindow.SelectWindowState(
                            panel_id=spec.panel_id, selector_id=comp_id,
                            window=widx),
                        win_count, resolver=resolver, locale=loc))
                else:
                    # the pre-successor truncation, byte-verbatim (windowed
                    # is opt-in — no undeclared surface changes).
                    options = options[: min(cspec.page_size, 25)]
                components.append(RenderedComponent(
                    kind="selector", custom_id=custom_id,
                    label=resolver.resolve(cspec.placeholder, locale=loc), row=row_idx,
                    placeholder=placeholder,
                    disabled=not options,
                    min_values=min_vals, max_values=max_vals,
                    # mappings (rich options) pass through verbatim; anything
                    # else keeps the compact label==value string form.
                    options=tuple(o if isinstance(o, dict) else str(o)
                                  for o in options)))
            else:
                components.append(RenderedComponent(
                    kind="button", custom_id=custom_id,
                    label=resolver.resolve(cspec.label, locale=loc), row=row_idx,
                    style=cspec.style.value, emoji=cspec.emoji))

    # engine-injected windowed-select nav (the windowed-select grammar
    # successor) — armed only when a declared ``windowed=True`` selector's
    # materialized options span more than one window; every other render
    # collects zero controls here (the non-churn guarantee).
    components.extend(window_nav)

    # engine-injected BrowserView controls (§2.3; D-0034) — the sort/filter/
    # page controls for the browse block, outside the layout search space.
    # Armed only when a BrowseState is supplied; the default render never
    # reaches here (browse is None), so no surface's static rendering changes.
    if browse is not None:
        from sb.kernel.panels import browserview

        block_spec = browserview.browse_block_spec(spec, browse.block)
        if block_spec is not None:
            components.extend(browserview.browse_controls(
                block_spec, browse, browse_page_count,
                resolver=resolver, locale=loc))

    # engine-injected page-turn controls (outside the searchable space).
    if page_count > 1:
        if page > 0:
            components.append(RenderedComponent(
                kind="button", custom_id=f"{NAV_PAGE_ID_PREFIX}{spec.panel_id}:{page - 1}",
                label="◀", row=NAV_ROW, style=ActionStyle.SECONDARY.value))
        if page < page_count - 1:
            components.append(RenderedComponent(
                kind="button", custom_id=f"{NAV_PAGE_ID_PREFIX}{spec.panel_id}:{page + 1}",
                label="▶", row=NAV_ROW, style=ActionStyle.SECONDARY.value))

    # engine-injected nav row (row 4, the shipped shape; never for self-hub help).
    nav = spec.navigation
    if nav.show_help and spec.subsystem != "help":
        components.append(RenderedComponent(
            kind="button", custom_id=NAV_HELP_ID,
            label=resolver.resolve("📚 Help", locale=loc), row=NAV_ROW,
            style=ActionStyle.SECONDARY.value))
    if nav.show_home:
        hub = resolve_home_hub(
            spec, subsystem_hub if subsystem_hub is not None
            else (_hub_resolver(spec.subsystem) if _hub_resolver else None))
        if hub:
            components.append(RenderedComponent(
                kind="button", custom_id=f"{NAV_HUB_ID_PREFIX}{hub}",
                label=resolver.resolve(
                    f"↩ {HUB_NAV_LABELS.get(hub, 'Home')}", locale=loc),
                row=NAV_ROW, style=ActionStyle.SECONDARY.value))
    if nav.parent is not None:
        components.append(RenderedComponent(
            kind="button", custom_id=f"{NAV_BACK_ID_PREFIX}{nav.parent.name}",
            label=resolver.resolve("↩ Back", locale=loc), row=NAV_ROW,
            style=ActionStyle.SECONDARY.value))
    for extra in nav.extra_routes:
        components.append(RenderedComponent(
            kind="button", custom_id=f"{NAV_BACK_ID_PREFIX}{extra.route.name}",
            label=resolver.resolve(extra.label, locale=loc), row=NAV_ROW,
            style=ActionStyle.SECONDARY.value, emoji=extra.emoji))

    invoker_lock = None
    if spec.audience.value == "invoker":
        invoker_lock = ctx.actor.user_id
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=tuple(components),
        page=page, page_count=page_count, invoker_lock=invoker_lock,
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)
