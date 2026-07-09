"""The community-family panels (band 4):

* ``community.hub`` — the shipped router-only Community hub (views/
  community/hub.py): pure navigation to XP / Karma / Leaderboard /
  Spotlight. Counting/Chain cross-links join at band 6 (their panels
  don't exist yet — a PanelRef must resolve, never dangle).
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
"""

from __future__ import annotations

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
            from sb.domain.community.rank_providers import provider_names

            return tuple(provider_names())
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


def community_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="community.hub",
        subsystem="community",
        title="🌱 Community Hub",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Pick a community feature below.\n"
                      "**Progression** — 🏆 XP · ✨ Karma\n"
                      "**Standings** — 📊 Leaderboards · 🌟 Spotlight\n"
                      "*Community games (Counting, Word Chain) join with "
                      "the games band.*"),
        ),
        actions=(
            PanelActionSpec(
                action_id="xp", label="XP", emoji="🏆",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("xp.hub")),
            PanelActionSpec(
                action_id="karma", label="Karma", emoji="✨",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("karma.card_view")),
            PanelActionSpec(
                action_id="leaderboard", label="Leaderboards", emoji="📊",
                audience_tier="user",
                handler=PanelRef("leaderboard.board")),
            PanelActionSpec(
                action_id="spotlight", label="Spotlight", emoji="🌟",
                audience_tier="user",
                handler=PanelRef("community_spotlight.hub")),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("xp", "karma"),
            ("leaderboard", "spotlight"),
        )),)),
    )


def leaderboard_board_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="leaderboard.board",
        subsystem="leaderboard",
        title="📊 Leaderboards",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
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
        navigation=NavigationSpec(parent=PanelRef("community.hub")),
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


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_category_options()
    _ensure_game_options()
    _ensure_spotlight_overview()
    for pid, factory in (("community.hub", _community_hub_factory),
                         ("leaderboard.board", _board_factory),
                         ("community_spotlight.hub", _spotlight_factory),
                         ("community_spotlight.games", _games_factory)):
        if not _is(_P(pid)):
            _panel(pid)(factory)
