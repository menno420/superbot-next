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
                              # path of the golden-pinned relic command)
    "dark_red": 10038562,     # discord.Color.dark_red() — the shipped AI
                              # review-log cards (cogs/ai_review_cog.py
                              # _REVIEW_COLOR; goldens/ai/sweep_aireview
                              # pins the byte)
    "magenta": 15277667,      # discord.Color.magenta() — the shipped
                              # _KARMA_COLOR standing card
                              # (cogs/karma_cog.py _karma_card;
                              # goldens/karma/sweep_karma +
                              # karma_slash_card pin the accent)
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
    embed: RenderedEmbed
    components: tuple[RenderedComponent, ...] = ()
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


async def _render_body(spec: PanelSpec, ctx: PanelContext, resolver):
    """→ (description, fields) from the typed content blocks."""
    loc = ctx.locale
    desc_parts: list[str] = []
    fields: list[tuple[str, str]] = []
    budget = min(spec.frame.field_budget_chars, FIELD_VALUE_LIMIT)
    max_fields = min(spec.frame.max_fields, MAX_EMBED_FIELDS)

    def add_field(name: str, value: str) -> None:
        if len(fields) < max_fields:
            fields.append((_clamp(name, FIELD_NAME_LIMIT), _clamp(value or "​", budget)))

    for block in spec.body:
        if isinstance(block, TextBlock):
            desc_parts.append(resolver.resolve(block.text, locale=loc))
        elif isinstance(block, FieldsBlock):
            rows = await _provider_rows(block.provider, ctx)
            for name, value in (rows or ()):
                add_field(resolver.resolve(str(name), locale=loc), str(value))
        elif isinstance(block, TableBlock):
            rows = await _provider_rows(block.provider, ctx)
            t = block.table
            if not rows:
                desc_parts.append(resolver.resolve(t.empty_state, locale=loc))
            else:
                header = " | ".join(resolver.resolve(c.label, locale=loc) for c in t.columns)
                lines = [header]
                for row in list(rows)[: t.page_size]:
                    lines.append(" | ".join(str(row.get(c.key, "")) for c in t.columns))
                desc_parts.append(_clamp("\n".join(lines), budget))
        elif isinstance(block, ListBlock):
            items = await _provider_rows(block.provider, ctx)
            ls = block.list_spec
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
                for item in list(items)[: ls.page_size]:
                    rendered_items.append(
                        str(item_renderer(item)) if item_renderer else f"• {item}")
                desc_parts.append(_clamp("\n".join(rendered_items), budget))
    return "\n\n".join(p for p in desc_parts if p), tuple(fields)


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
                       subsystem_hub: str | None = None) -> RenderedPanel:
    """The render entry. ``subsystem_hub`` overrides the installed hub
    resolver (tests / pre-resolved callers)."""
    resolver = active_copy_resolver()
    loc = ctx.locale

    description, fields = await _render_body(spec, ctx, resolver)
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
    rows = pages[page].rows if pages else ()
    for row_idx, row in enumerate(rows):
        for comp_id in row:
            cspec = by_id[comp_id]
            if not await _visible(cspec, ctx):
                continue
            custom_id = getattr(cspec, "custom_id_override", "") or f"{spec.panel_id}.{comp_id}"
            if hasattr(cspec, "selector_id"):
                if isinstance(cspec.options_source, tuple):
                    options = cspec.options_source
                else:
                    # provider-fed options (SelectorSpec.options_source is
                    # "static tuple | provider" by grammar) — materialized at
                    # render time from the invoker's context; a broken/empty
                    # provider degrades to a disabled selector showing its
                    # empty_state, never a crashed panel.
                    options = tuple(await _provider_rows(cspec.options_source, ctx) or ())
                options = options[: min(cspec.page_size, 25)]
                components.append(RenderedComponent(
                    kind="selector", custom_id=custom_id,
                    label=resolver.resolve(cspec.placeholder, locale=loc), row=row_idx,
                    placeholder=resolver.resolve(
                        cspec.placeholder if options else cspec.empty_state, locale=loc),
                    disabled=not options,
                    min_values=cspec.min_values, max_values=cspec.max_values,
                    # mappings (rich options) pass through verbatim; anything
                    # else keeps the compact label==value string form.
                    options=tuple(o if isinstance(o, dict) else str(o)
                                  for o in options)))
            else:
                components.append(RenderedComponent(
                    kind="button", custom_id=custom_id,
                    label=resolver.resolve(cspec.label, locale=loc), row=row_idx,
                    style=cspec.style.value, emoji=cspec.emoji))

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
