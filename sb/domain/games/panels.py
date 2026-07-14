"""GAMES panels (band 6 / parity flip) — the SHIPPED surfaces byte-for-byte:

* ``games.hub`` — disbot/views/games/hub.py (Games Hub v2): the 🎮 Games
  Hub embed (GAME_COLOR purple, the 🏆 Competitive / 🎲 Activities catalog
  fields, the shared invoker-lock footer) over the registry-discovered
  child roster grouped by ``hub_group`` — Competitive on row 0 (primary
  style), Activities on rows 1-2 (success style) — plus the grammar's own
  ``nav:help`` slot as the shipped row-3 📚 Help button.
  ``parity/goldens/games/sweep_games.json`` + ``sweep_slash_games.json``
  pin every byte: the shipped PERSISTENT ``games:open:<key>`` ids ride
  ``custom_id_override`` through the session mint (the community
  ``community:open:<key>`` / btd6 precedent — ``session_lifecycle=True``,
  no ``panel_anchors`` row in either golden), emoji IN the label (the
  shipped ``f"{emoji} {label}"`` builder — trap 15a's in-label form).
* ``games.world`` — disbot/views/explore/world_hub.py: the 🗺️ Explore
  open-world hub (the "Where to go" catalog field; Mine/Fish/Farm primary
  buttons on ``explore:open:<key>`` ids + the secondary 🪪 World Card on
  ``explore:world_card``). ``parity/goldens/games/sweep_world.json``
  (re-homed from _unmapped) pins every byte.
* ``games.world_card`` — disbot/views/explore/world_card.py
  ``build_world_card_embed``: the read-only cross-game identity card
  (display-name title + avatar thumbnail through the guild-directory read
  port — the inventory ``_member_display`` recipe; the zero-XP
  "🌍 World level — 0" empty-state field; the "Only you can see this
  card." footer; ZERO components).
  ``parity/goldens/games/sweep_worldcard.json`` (re-homed) pins the
  zero-XP bytes; the XP-bearing branch is golden-UNPINNED (no capture
  ever earned game XP) and renders the port's honest game_xp reads.

Trap-24 drift check (games row): the oracle current-head fragments
(views/games/hub.py title/description + the hub_group grouping docstring
+ ``custom_id stays f"games:open:{subsystem}"``; views/explore/
world_hub.py title/description/"Where to go" builder + the
``f"{entry.emoji} {entry.label}"`` in-label form, primary style,
``explore:open:{entry.key}`` ids, the "🪪 World Card" secondary button;
views/explore/world_card.py title/description/thumbnail/zero-XP field/
footer) match the corpus goldens byte-for-byte — NO drift (corpus sha
7f7628e1).

Shipped click semantics (no games golden drives a click): every hub
button forwarded to the child cog's panel — the port routes each to its
REAL ported surface (blackjack.hub / casino.hub / deathmatch.hub /
rps_tournament.hub / mining.hub / fishing.hub / creature.hub / farm.hub /
counting.hub / chain.hub), the world buttons to mining/fishing/farm and
the world card panel.

Per-guild enablement (D-0082 slice 3, docs/design/game-sections.md §6):
both hubs render the ENABLED set — the ``games.hub_fields`` provider
filters through the slice-1 ``enabled_games(guild_id)`` read seam (a
section whose games are all disabled DROPS), the ``games.world_fields``
provider filters its per-game "Where to go" lines the same way, and
every game button carries a ``visible_when`` enablement predicate
(``games.enabled_<key>``) so a disabled game's button drops at render
AND its stale click (an already-rendered message) is denied by
resolve.py's dispatch-time ``visible_when`` re-evaluation (02 §3.0 —
"This control is no longer available."). Fail-open posture throughout
(the governance ``subsystem_enabled`` posture): an unreadable enablement
(no DB / seam failure) or an unpopulated sections registry renders
TODAY'S full static roster byte-for-byte, so the ported games goldens
(fully-default guilds — no overrides) replay unchanged. Update contract
= NEXT-INTERACTION consistency: every open/nav/refresh re-resolves at
click time (engine §6.1); the anchor refresh sweep is a named successor
(design §6.3), not this slice.
"""

from __future__ import annotations

import logging

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
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    PredicateRef,
    ProviderRef,
    is_registered,
    panel,
    predicate,
    provider,
)

logger = logging.getLogger("sb.domain.games.panels")

__all__ = [
    "ensure_panel_refs",
    "games_hub_spec",
    "install_games_panels",
    "world_card_spec",
    "world_hub_spec",
]

_HUB_FIELDS = "games.hub_fields"
_WORLD_FIELDS = "games.world_fields"

#: the shipped footer literal (the shared author-locked nav view) —
#: outside FooterMode's vocabulary, hence the renderer_override (the
#: community/casino/admin precedent).
_PANEL_FOOTER = "Only you can interact with this panel."
#: the shipped world-card footer (views/explore/world_card.py).
_CARD_FOOTER = "Only you can see this card."

# views/games/hub.py, verbatim (the goldens pin every byte).
_HUB_DESCRIPTION = (
    "Pick a game below to open it. "
    "Typed shortcuts (e.g. `!blackjack`, `!mine`) still work."
)

# The hub roster grouped per the casino-section spec taxonomy
# (docs/specs/casino-section-spec.md §2 — 🎰 casino / 🕹️ arcade / 🌍 world;
# the ORIGINAL shipped capture-world pin was the oracle's 2-group
# competitive/activities split, replaced through design §7's single
# replacement slot). Per-game bytes (key, emoji, display, description,
# route) are unchanged; the drift-guard test pins agreement with
# sb/manifest/games.py GAME_SECTIONS both directions.
# (key, emoji, display, description, ported route)
GAMES_CASINO: tuple[tuple[str, str, str, str, object], ...] = (
    ("blackjack", "🃏", "Blackjack", "Blackjack card game",
     PanelRef("blackjack.hub")),
    ("casino", "🎰", "Casino", "Group card games like multiplayer poker",
     PanelRef("casino.hub")),
)
GAMES_ARCADE: tuple[tuple[str, str, str, str, object], ...] = (
    ("deathmatch", "⚔️", "Deathmatch", "1v1 duel battles",
     PanelRef("deathmatch.hub")),
    ("rps_tournament", "✂️", "Rock Paper Scissors",
     "Rock Paper Scissors: quick play, PvP, bot matches, tournaments",
     PanelRef("rps_tournament.hub")),
    ("counting", "🔢", "Counting", "Collaborative counting game",
     PanelRef("counting.hub")),
    ("chain", "🔗", "Word Chain", "Word-chaining game",
     PanelRef("chain.hub")),
)
GAMES_WORLD: tuple[tuple[str, str, str, str, object], ...] = (
    ("mining", "⛏️", "Mining", "Mining minigame and resource collection",
     PanelRef("mining.hub")),
    ("fishing", "🎣", "Fishing",
     "Fishing minigame — cast a line, build your collection",
     PanelRef("fishing.hub")),
    ("creature", "🐾", "Creatures",
     "Catch original creatures and build your collection dex",
     PanelRef("creature.hub")),
    ("farm", "🐔", "Chicken Farm",
     "Idle egg farm — hens lay eggs over time; collect, sell, grow",
     PanelRef("farm.hub")),
)
#: the three rosters in hub render order (one tuple per section).
_GAME_ROSTERS = (GAMES_CASINO, GAMES_ARCADE, GAMES_WORLD)

#: the shipped per-button style split — the pre-swap wire bytes
#: (card games + duels primary, channel/world games success); pinned so
#: the section regroup moves NO component byte (spec §5.4 restyle skipped).
_PRIMARY_STYLE_KEYS = frozenset(
    {"blackjack", "casino", "deathmatch", "rps_tournament"})

#: the hub buttons in the SHIPPED declaration order (the manifest
#: snapshot pinned this order pre-regroup; the wire rows are pinned by
#: the hub LayoutSpec) — the section regroup moves catalog FIELDS only.
_BY_KEY = {entry[0]: entry
           for roster in _GAME_ROSTERS for entry in roster}
_HUB_BUTTON_ROSTER = tuple(_BY_KEY[k] for k in (
    "blackjack", "casino", "deathmatch", "rps_tournament", "mining",
    "fishing", "creature", "farm", "counting", "chain"))


def _catalog_lines(entries) -> str:
    # the shipped f"{emoji} **{display}** — {desc}" line builder.
    return "\n".join(f"{emoji} **{display}** — {desc}"
                     for _k, emoji, display, desc, _r in entries)


#: game key → the shipped hub blurb (the roster is the ONE place the
#: descriptions live — GameEntry deliberately carries no blurb, slice 1).
_GAME_DESCRIPTIONS: dict[str, str] = {
    key: desc
    for roster in _GAME_ROSTERS
    for key, _emoji, _display, desc, _ref in roster
}

#: the fully-default render, byte-for-byte (the goldens' bytes) — also the
#: fail-open degradation when enablement cannot be read (D-0082 §6: a
#: broken read renders today's hub, never a blank one).
_STATIC_HUB_FIELDS = (
    ("🎰 Casino", _catalog_lines(GAMES_CASINO)),
    ("🕹️ Arcade", _catalog_lines(GAMES_ARCADE)),
    ("🌍 World", _catalog_lines(GAMES_WORLD)),
)


async def _game_enabled_fail_open(guild_id: int, key: str) -> bool:
    """Per-game enablement through governance ``subsystem_enabled`` (the
    slice-1 seam shape: lazy domain→governance import, PL-001). FAIL-OPEN
    on a read failure — enforcement lives at dispatch (resolve.py's
    visibility gate + the component ``visible_when`` re-evaluation); a
    render-time read outage must not hide the hub (and the ported goldens
    replay the default all-enabled bytes)."""
    try:
        from sb.domain.governance import service as governance

        return await governance.subsystem_enabled(guild_id, key)
    except Exception:  # noqa: BLE001 — render-side read, fail-open by design
        logger.debug("game enablement read failed for %r — fail-open",
                     key, exc_info=True)
        return True


def _entry_line(entry) -> str:
    """One catalog line from a GameSectionView entry — the shipped
    ``f"{emoji} **{display}** — {desc}"`` builder over the roster blurb
    (byte-identical to ``_catalog_lines`` for the default inventory; a
    future SBW entry without a roster blurb renders without the dash)."""
    desc = _GAME_DESCRIPTIONS.get(entry.key, "")
    if desc:
        return f"{entry.emoji} **{entry.label}** — {desc}"
    return f"{entry.emoji} **{entry.label}**"


def _ensure_hub_fields() -> ProviderRef:
    ref = ProviderRef(_HUB_FIELDS)
    if not is_registered(ref):
        @provider(_HUB_FIELDS)
        async def hub_fields(ctx: object):
            """D-0082 §6: the catalog fields are the ENABLED set — one
            field per ``enabled_games`` section view (a fully-disabled
            section drops; all games disabled ⇒ no catalog fields). An
            unpopulated sections registry (boot never declared the
            inventory) or a failed read renders the full static roster —
            fail-open, byte-identical to the goldens."""
            from sb.spec.sections import all_sections

            if not all_sections():
                return _STATIC_HUB_FIELDS
            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            try:
                from sb.domain.games.sections import enabled_games

                views = await enabled_games(guild_id)
            except Exception:  # noqa: BLE001 — fail-open (see _game_enabled_fail_open)
                logger.warning("enabled_games read failed — rendering the "
                               "full static roster (fail-open)", exc_info=True)
                return _STATIC_HUB_FIELDS
            return tuple(
                (f"{view.emoji} {view.title}",
                 "\n".join(_entry_line(e) for e in view.games))
                for view in views)
    return ref


def _predicate_name(key: str) -> str:
    return f"games.enabled_{key}"


def _ensure_enabled_predicate(key: str) -> str:
    """Register (idempotently) the per-game enablement predicate and
    return its REGISTERED PredicateRef string form for ``visible_when``.
    The ONE predicate serves both gates: render-time component drop
    (render.py ``_visible``) and resolve.py's dispatch-time stale-click
    re-evaluation (02 §3.0)."""
    name = _predicate_name(key)
    if not is_registered(PredicateRef(name)):
        @predicate(name)
        async def game_enabled(ctx: object, _key: str = key) -> bool:
            return await _game_enabled_fail_open(
                int(getattr(ctx, "guild_id", 0) or 0), _key)
    return name


# views/explore/world_hub.py, verbatim (sweep_world pins every byte).
_WORLD_DESCRIPTION = (
    "Walk out into the world and pick where to go. Each place is its own "
    "game — your progress in one carries its own ladder, and a shared "
    "world ties them together."
)
# (game key, the shipped line) — keyed so the enablement filter (D-0082
# §6, same treatment as the hub) can drop a disabled game's line.
_WORLD_PLACE_LINES: tuple[tuple[str, str], ...] = (
    ("mining",
     "⛏️ **Mine** — Dig for ores, craft gear, and grow your character."),
    ("fishing",
     "🎣 **Fish** — Cast a line in lakes and rivers and build your "
     "collection."),
    ("farm",
     "🐔 **Farm** — Raise hens that lay eggs around the clock — an idle "
     "game."),
)
_WORLD_PLACES = "\n".join(line for _key, line in _WORLD_PLACE_LINES)


def _ensure_world_fields() -> ProviderRef:
    ref = ProviderRef(_WORLD_FIELDS)
    if not is_registered(ref):
        @provider(_WORLD_FIELDS)
        async def world_fields(ctx: object):
            """D-0082 §6 (same treatment as the hub): a disabled game's
            line drops from "Where to go"; all three disabled ⇒ the field
            drops. Fail-open per game — the default all-enabled render is
            byte-identical to ``_WORLD_PLACES`` (the golden's bytes)."""
            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            lines = [line for key, line in _WORLD_PLACE_LINES
                     if await _game_enabled_fail_open(guild_id, key)]
            if not lines:
                return ()
            return (("Where to go", "\n".join(lines)),)
    return ref


def _hub_action(key: str, emoji: str, display: str, route: object, *,
                style: ActionStyle) -> PanelActionSpec:
    return PanelActionSpec(
        # K1 claims action_ids bare and repo-global — the ga_ prefix keeps
        # the namespace clean (the wire byte is the override below).
        action_id=f"ga_{key}",
        label=f"{emoji} {display}",          # emoji IN the label (wire shape)
        style=style, audience_tier="user",
        handler=route,
        custom_id_override=f"games:open:{key}",  # the shipped persistent id
        # D-0082 §6: render-time drop when the game is disabled per guild
        # + resolve.py's dispatch-time stale-click deny (the SAME predicate).
        visible_when=_ensure_enabled_predicate(key),
    )


def games_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="games.hub",
        subsystem="games",
        title="🎮 Games Hub",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046); footer via the override.
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(
            TextBlock(_HUB_DESCRIPTION),
            FieldsBlock(provider=_ensure_hub_fields()),
        ),
        actions=tuple(
            # per-button styles + declaration order keep the SHIPPED wire
            # bytes (the oracle's card-games/duels primary vs
            # channel-and-world success split); the spec's per-section
            # style re-derivation is a deliberately skipped cosmetic
            # option (casino-section-spec.md §5.4).
            _hub_action(k, e, d, r,
                        style=(ActionStyle.PRIMARY
                               if k in _PRIMARY_STYLE_KEYS
                               else ActionStyle.SUCCESS))
            for k, e, d, _desc, r in _HUB_BUTTON_ROSTER),
        # the shipped hub carried the row-3 📚 Help button — the grammar's
        # own nav:help slot (custom_id verbatim; both goldens pin it); no
        # home/back slots.
        navigation=NavigationSpec(show_help=True, show_home=False),
        renderer_override=HandlerRef("games.render_hub"),
        justification=(
            "the shipped hub footer is the literal 'Only you can "
            "interact with this panel.' (the shared author-locked nav "
            "view) — outside FooterMode's none/subsystem/provenance "
            "vocabulary (goldens/games/sweep_games + sweep_slash_games "
            "pin the byte; the community/casino precedent). The override "
            "adjusts ONLY the embed footer; body, title, color and every "
            "component stay grammar-rendered."),
        # the shipped view carried EXPLICIT persistent ids — the
        # custom_id_override pins ride the session mint verbatim (the
        # community/btd6 precedent); no panel_anchors row in either golden.
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ga_blackjack", "ga_casino", "ga_deathmatch",
             "ga_rps_tournament"),
            ("ga_mining", "ga_fishing", "ga_creature", "ga_farm",
             "ga_counting"),
            ("ga_chain",),
        )),)),
    )


def world_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="games.world",
        subsystem="games",
        title="🗺️ Explore — the open world",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(
            TextBlock(_WORLD_DESCRIPTION),
            FieldsBlock(provider=_ensure_world_fields()),
        ),
        actions=(
            PanelActionSpec(
                action_id="world_mine", label="⛏️ Mine",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("mining.hub"),
                custom_id_override="explore:open:mining",
                visible_when=_ensure_enabled_predicate("mining")),
            PanelActionSpec(
                action_id="world_fish", label="🎣 Fish",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("fishing.hub"),
                custom_id_override="explore:open:fishing",
                visible_when=_ensure_enabled_predicate("fishing")),
            PanelActionSpec(
                action_id="world_farm", label="🐔 Farm",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("farm.hub"),
                custom_id_override="explore:open:farm",
                visible_when=_ensure_enabled_predicate("farm")),
            # the world card is NOT a game — never enablement-gated.
            PanelActionSpec(
                action_id="world_card", label="🪪 World Card",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef("games.world_card"),
                custom_id_override="explore:world_card"),
        ),
        navigation=NavigationSpec(show_help=True, show_home=False),
        renderer_override=HandlerRef("games.render_world"),
        justification=(
            "the shipped Explore hub footer is the literal 'Only you can "
            "interact with this panel.' — outside FooterMode's vocabulary "
            "(goldens/games/sweep_world pins the byte; the community/"
            "casino precedent). The override adjusts ONLY the embed "
            "footer; body, title, color and every component stay "
            "grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("world_mine", "world_fish", "world_farm"),
            ("world_card",),
        )),)),
    )


def world_card_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="games.world_card",
        subsystem="games",
        title="🪪 world card",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("games.render_world_card"),
        justification=(
            "the shipped world card (views/explore/world_card.py "
            "build_world_card_embed) is member-parameterized beyond the "
            "grammar's vocabulary on three named embed surfaces "
            "(goldens/games/sweep_worldcard pins the bytes): the TITLE "
            "interpolates the invoker's display name ('🪪 {name} — world "
            "card'), the THUMBNAIL is the invoker's display avatar "
            "(set_thumbnail(user.display_avatar.url) — read through the "
            "guild-directory port, the inventory _member_display "
            "precedent), and the FIELD is state-dependent (the zero-XP "
            "'🌍 World level — 0' empty state vs the live per-game "
            "standing lines) with the 'Only you can see this card.' "
            "footer. Zero components (the golden pins components: [])."),
        session_lifecycle=True,
    )


async def _member_display(user_id: int, guild_id: int) -> tuple[str, str]:
    """(display name, avatar url) through the guild-directory read port
    (the inventory ``_member_display`` recipe). Degrades to ("", "") when
    no directory is armed — never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ no name/thumbnail
        return "", ""
    return member.tag.rsplit("#", 1)[0], member.display_avatar_url


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed,
                                                   footer=_PANEL_FOOTER))


async def _render_world_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — views/explore/world_card.py
    ``build_world_card_embed``: display-name title + avatar thumbnail +
    the world-level field + the card footer (goldens/games/
    sweep_worldcard pins the zero-XP bytes; the XP-bearing branch is
    golden-unpinned and renders the port's game_xp reads)."""
    from sb.domain.games import store, xp as game_xp
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    name, icon = await _member_display(uid, gid)
    if not name:
        name = f"<@{uid}>"
    level, total = await game_xp.shared_level(uid, gid)
    if total <= 0:
        fields = ((
            "🌍 World level — 0",
            "You have not earned any game XP here yet. Mine, craft, or "
            "fish to start your world ladder — run **`!world`** to pick "
            "a place."),)
    else:
        rows = await store.game_xp_rows(uid, gid)
        lines = [f"{game_xp.game_display(str(r['game']))[0]} "
                 f"**{game_xp.game_display(str(r['game']))[1]}** — "
                 f"{int(r['xp']):,} XP" for r in rows]
        fields = ((f"🌍 World level — {level}",
                   "\n".join(lines) or f"{total:,} game XP total"),)
    embed = RenderedEmbed(
        title=f"🪪 {name} — world card",
        description=("Who you are across the open world: your shared "
                     "**world level** and where you stand in each game."),
        fields=fields,
        footer=_CARD_FOOTER,
        thumbnail_ref=icon,
        style_token=spec.frame.style_token)
    return _dc_replace(rendered, embed=embed)


# --- registration ----------------------------------------------------------

_SPECS = {
    "games.hub": games_hub_spec,
    "games.world": world_hub_spec,
    "games.world_card": world_card_spec,
}

_RENDERERS = {
    "games.render_hub": _render_hub,
    "games.render_world": _render_hub,       # same footer adjustment
    "games.render_world_card": _render_world_card,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    _ensure_hub_fields()
    _ensure_world_fields()
    for roster in _GAME_ROSTERS:
        for key, _emoji, _display, _desc, _ref in roster:
            _ensure_enabled_predicate(key)
    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register_refs()


def install_games_panels() -> tuple[PanelSpec, ...]:
    out = []
    for factory in _SPECS.values():
        spec = factory()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    _register_refs()
