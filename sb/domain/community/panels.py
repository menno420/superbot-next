"""The community-family panels (band 4 + the parity flip):

* ``community.hub`` — the SHIPPED 🌱 Community Hub (views/community/
  hub.py ``build_community_hub_panel``, parity flip): the registry-
  discovered child roster as the capture-world PIN (the utility
  UTILITY_CHILDREN precedent — the shipped view ran
  ``discover_community_children()`` per render over
  utils/subsystem_registry SUBSYSTEMS.parent_hub == "community" +
  hub_registry cross_link_children; the declarative spec pins the
  roster the goldens captured), the GENERAL_COLOR green embed with the
  two-section bullet legend ("• {emoji} **{display}** — {desc}"), the
  "Only you can interact with this panel." footer (renderer_override —
  outside FooterMode's vocabulary), the shipped PERSISTENT
  ``community:open:<key>`` child-forwarding ids riding
  ``custom_id_override`` through the session mint (the utility
  ``utility:open:<key>`` precedent), and the grammar's own ``nav:help``
  slot as the shipped row-4 📚 Help button.
  ``parity/goldens/community/sweep_community.json`` +
  ``sweep_slash_community.json`` pin every byte (prefix send + the
  ephemeral type-4 flags-64 slash twin; session view ⇒ no
  ``panel_anchors`` row in either).
* ``leaderboard.board`` — the shipped category-selector view over the
  provider registry (options are PROVIDER-FED, so band-6 game categories
  appear without edits — the shipped "register a provider, not a view"
  invariant, now grammar).
* ``community_spotlight.hub`` — the shipped SpotlightView (XP Leaders /
  Richest / Games / Refresh) + the games sub-panel whose selector is
  provider-fed from the GAME provider subset (empty until band 6 — the
  disabled-selector empty_state is the honest waiting surface).

Shipped spotlight/leaderboard buttons carried no persistent custom_ids
(view-local decorators); back-nav is engine ``nav:*`` (band-1 convention;
the shipped ``community:back`` closure id is replaced BY DESIGN —
kick-confirm class deviation, ledgered).

Trap-24 drift check (community row): the oracle current-head fragments
(views/community/hub.py "Pick a community feature below." + the
"• {emoji} **{display}** — {desc}" line builder + the "Community games
& standings" heading; utils/subsystem_registry.py child entries, e.g.
the ticket row's display_name/description/emoji verbatim) match the
corpus goldens — NO drift (corpus sha 7f7628e1).

Shipped click semantics (no golden drives any click): the shared
HubChildButton forwarded into each child cog's ``build_help_menu_view``
— the port routes every child to its REAL ported surface (ticket.hub /
xp.hub / karma.card_view / community_spotlight.hub / welcome.status /
counters.status / role.hub / counting.hub / chain.hub /
leaderboard.board).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "community_hub_spec",
    "ensure_panel_refs",
    "install_community_panels",
    "leaderboard_board_spec",
    "spotlight_games_spec",
    "spotlight_hub_spec",
]

_CATEGORY_OPTIONS = "leaderboard.category_options"
_GAME_OPTIONS = "community_spotlight.game_options"
_SPOTLIGHT_OVERVIEW = "community_spotlight.overview"

# The band-6 game categories (the shipped GamesView subset); used to
# filter the games selector until those providers register.
_GAME_CATEGORIES = ("mining", "rps", "deathmatch", "counting", "farm",
                    "fishing", "creatures")


def _ensure_category_options() -> ProviderRef:
    ref = ProviderRef(_CATEGORY_OPTIONS)
    if not is_registered(ref):
        @provider(_CATEGORY_OPTIONS)
        async def category_options(ctx: object):
            # the shipped rich select options (_select_options in
            # cogs/leaderboard_cog.py: label/emoji from the provider's own
            # select_label/select_emoji, value = the canonical name), in
            # provider_names() registration order.
            from sb.domain.community.rank_providers import (
                get_provider,
                provider_names,
            )

            options = []
            for name in provider_names():
                p = get_provider(name)
                if p is None:
                    continue
                option = {"label": p.select_label, "value": p.name}
                if p.select_emoji:
                    option["emoji"] = p.select_emoji
                options.append(option)
            return tuple(options)
    return ref


def _ensure_game_options() -> ProviderRef:
    ref = ProviderRef(_GAME_OPTIONS)
    if not is_registered(ref):
        @provider(_GAME_OPTIONS)
        async def game_options(ctx: object):
            from sb.domain.community.rank_providers import provider_names

            return tuple(n for n in provider_names()
                         if n in _GAME_CATEGORIES)
    return ref


def _ensure_spotlight_overview() -> ProviderRef:
    ref = ProviderRef(_SPOTLIGHT_OVERVIEW)
    if not is_registered(ref):
        @provider(_SPOTLIGHT_OVERVIEW)
        async def spotlight_overview(ctx: object):
            from sb.domain.community.spotlight import overview_fields

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            return await overview_fields(guild_id)
    return ref


# --- the shipped community child rosters (utils/subsystem_registry.py +
# hub_registry cross_link_children, verbatim as the goldens captured them
# in the sweep guild — the capture-world PIN; re-derivation from the
# manifest inventory is the follow-up when discovery ports).
# (key, display_name, emoji, description, ported route)
COMMUNITY_PRIMARY: tuple[tuple[str, str, str, str, object], ...] = (
    ("ticket", "Support Tickets", "🎫",
     "Private support tickets — open by command, panel, or the AI",
     PanelRef("ticket.hub")),
    ("xp", "XP & Levels", "⭐",
     "Experience points, levels, and leaderboards",
     PanelRef("xp.hub")),
    ("karma", "Karma", "✨",
     "Peer reputation — thank helpful members with !thanks",
     HandlerRef("karma.card_view")),
    ("community_spotlight", "Community Spotlight", "🌟",
     "Live server activity dashboard — leaders, level-ups, game stats",
     PanelRef("community_spotlight.hub")),
    ("welcome", "Welcome", "👋",
     "Member greetings, farewells, and an optional entry role",
     PanelRef("welcome.status")),
    ("counters", "Server Counters", "📊",
     "Live member-count channels (total · humans · bots)",
     PanelRef("counters.status")),
    ("role", "Roles", "🎭",
     "Time-based and XP-based automatic role assignment",
     PanelRef("role.hub")),
)

COMMUNITY_CROSS_LINKS: tuple[tuple[str, str, str, str, object], ...] = (
    ("counting", "Counting", "🔢", "Collaborative counting game",
     PanelRef("counting.hub")),
    ("chain", "Word Chain", "🔗", "Word-chaining game",
     PanelRef("chain.hub")),
    ("leaderboard", "Leaderboard", "🏆",
     "Server leaderboards for XP, coins, and games",
     PanelRef("leaderboard.board")),
)

#: the shipped footer literal (views/community/hub.py ``set_footer`` —
#: the shared invoker-lock footer) — outside FooterMode's vocabulary,
#: hence the renderer_override below (the utility/admin precedent).
_HUB_FOOTER = "Only you can interact with this panel."


def _hub_description() -> str:
    """views/community/hub.py ``build_community_hub_embed`` verbatim —
    the goldens pin every byte of the discovered snapshot."""
    parts = ["Pick a community feature below.", "\n**Progression**"]
    parts += [f"• {emoji} **{display}** — {desc}"
              for _k, display, emoji, desc, _r in COMMUNITY_PRIMARY]
    parts.append("\n**Community games & standings**")
    parts += [f"• {emoji} **{display}** — {desc}"
              for _k, display, emoji, desc, _r in COMMUNITY_CROSS_LINKS]
    return "\n".join(parts)


def _child_action(key: str, display: str, emoji: str, route: object, *,
                  style: ActionStyle) -> PanelActionSpec:
    return PanelActionSpec(
        # K1 claims action_ids bare and repo-global — utility owns
        # "open_<key>", ticket owns "open_ticket"; the co_ prefix keeps
        # the namespace clean (the wire byte is the override below).
        action_id=f"co_{key}",
        label=f"{emoji} {display}",              # emoji IN the label (wire shape)
        style=style, audience_tier="user",
        handler=route,
        custom_id_override=f"community:open:{key}",  # the shipped persistent id
    )


def community_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="community.hub",
        subsystem="community",
        title="🌱 Community Hub",
        audience=Audience.INVOKER,
        # GENERAL_COLOR green (3066993), footer via the override.
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_hub_description()),),
        actions=(
            tuple(_child_action(k, d, e, r, style=ActionStyle.PRIMARY)
                  for k, d, e, _desc, r in COMMUNITY_PRIMARY)
            + tuple(_child_action(k, d, e, r, style=ActionStyle.SECONDARY)
                    for k, d, e, _desc, r in COMMUNITY_CROSS_LINKS)
        ),
        # the shipped hub carried the row-4 📚 Help button — the
        # grammar's own nav:help slot (custom_id verbatim; both goldens
        # pin it); no home/back slots.
        navigation=NavigationSpec(show_help=True, show_home=False),
        renderer_override=HandlerRef("community.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Only you can "
            "interact with this panel.' (views/community/hub.py "
            "set_footer — the shared invoker-lock footer) — outside "
            "FooterMode's none/subsystem/provenance vocabulary "
            "(goldens/community/sweep_community + sweep_slash_community "
            "pin the byte; the utility/admin precedent). The override "
            "adjusts ONLY the embed footer; body, title, color and "
            "every component stay grammar-rendered."),
        # the shipped view was a timeout session view whose child-
        # forwarding buttons carried EXPLICIT persistent ids — the
        # custom_id_override pins ride the session mint verbatim (the
        # utility precedent); no panel_anchors row in either golden.
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("co_ticket", "co_xp", "co_karma", "co_community_spotlight",
             "co_welcome"),
            ("co_counters", "co_role"),
            ("co_counting", "co_chain", "co_leaderboard"),
        )),)),
    )


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed,
                                                   footer=_HUB_FOOTER))


def leaderboard_board_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="leaderboard.board",
        subsystem="leaderboard",
        title="📊 Leaderboards",
        audience=Audience.INVOKER,
        # the shipped overview embed (cogs/leaderboard_cog.py
        # `_build_overview_embed`): UTILITY_COLOR blue, no footer —
        # parity/goldens/leaderboard/sweep_leaderboard.json pins the bytes.
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        body=(
            TextBlock("Select a category below to view the leaderboard."),
        ),
        selectors=(
            SelectorSpec(
                selector_id="category_select", kind=SelectorKind.ENTITY,
                on_select=HandlerRef("leaderboard.category_view"),
                options_source=_ensure_category_options(),
                placeholder="Choose a leaderboard category…",
                empty_state="No leaderboard categories registered.",
                audience_tier="user"),
        ),
        # the shipped LeaderboardView carried ONLY the selector (no nav
        # buttons; timeout=120 session view) — the golden pins exactly one
        # component row, so the never-strand fence takes the session-view
        # exemption the shipped view actually was.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("category_select",),)),)),
    )


def spotlight_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="community_spotlight.hub",
        subsystem="community_spotlight",
        title="🌟 Community Spotlight",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Live server activity — leaders, level-ups, and "
                      "game stats."),
            FieldsBlock(provider=_ensure_spotlight_overview()),
        ),
        actions=(
            PanelActionSpec(
                action_id="xp_leaders", label="XP Leaders", emoji="🏆",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("spotlight.xp_leaders")),
            PanelActionSpec(
                action_id="richest", label="Richest", emoji="💰",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("spotlight.richest")),
            PanelActionSpec(
                action_id="games", label="Games", emoji="🎮",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=PanelRef("community_spotlight.games")),
            PanelActionSpec(
                # K1 custom_id claims are repo-global on action_id (the
                # compiler's namespace key) — treasury owns bare "refresh".
                action_id="spotlight_refresh", label="Refresh", emoji="🔄",
                audience_tier="user",
                handler=PanelRef("community_spotlight.hub"),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("xp_leaders", "richest", "games", "spotlight_refresh"),
        )),)),
    )


def spotlight_games_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="community_spotlight.games",
        subsystem="community_spotlight",
        title="🎮 Game Leaderboards",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Select a game below to view its leaderboard."),
        ),
        selectors=(
            SelectorSpec(
                selector_id="game_select", kind=SelectorKind.ENTITY,
                on_select=HandlerRef("leaderboard.category_view"),
                options_source=_ensure_game_options(),
                placeholder="Choose a game leaderboard…",
                empty_state="🎮 Game leaderboards arrive with the games "
                            "band (mining, RPS, deathmatch, counting…).",
                audience_tier="user"),
        ),
        navigation=NavigationSpec(parent=PanelRef("community_spotlight.hub")),
        layout=LayoutSpec(pages=(PageSpec(rows=(("game_select",),)),)),
    )


@panel("community.hub")
def _community_hub_factory() -> PanelSpec:
    return community_hub_spec()


@panel("leaderboard.board")
def _board_factory() -> PanelSpec:
    return leaderboard_board_spec()


@panel("community_spotlight.hub")
def _spotlight_factory() -> PanelSpec:
    return spotlight_hub_spec()


@panel("community_spotlight.games")
def _games_factory() -> PanelSpec:
    return spotlight_games_spec()


def install_community_panels() -> tuple[PanelSpec, ...]:
    specs = (community_hub_spec(), leaderboard_board_spec(),
             spotlight_hub_spec(), spotlight_games_spec())
    out = []
    for spec in specs:
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def _register_hub_render() -> None:
    from sb.spec.refs import handler

    if not is_registered(HandlerRef("community.render_hub")):
        handler("community.render_hub")(_render_hub)


_register_hub_render()


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_category_options()
    _ensure_game_options()
    _ensure_spotlight_overview()
    _register_hub_render()
    for pid, factory in (("community.hub", _community_hub_factory),
                         ("leaderboard.board", _board_factory),
                         ("community_spotlight.hub", _spotlight_factory),
                         ("community_spotlight.games", _games_factory)):
        if not _is(_P(pid)):
            _panel(pid)(factory)
