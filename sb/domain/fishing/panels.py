"""Fishing panels (band 6 / parity flip) — the SHIPPED surfaces byte-for-byte:

* ``fishing.cast`` — disbot/views/fishing/cast_view.py ``prepare_cast``'s
  waiting-for-a-bite panel: the GAME_COLOR purple embed ("You cast a line
  from the shoreline… 🏖️" + the Reel coaching italic), the
  weather-of-the-day field (shown only when the condition moves a knob —
  clear renders silent, shipped conditional), the venue+energy footer
  (``🏖️ Shore · ⚡ 58/60 [▰▰▰▰▰▰▰▰▰▰]``) and the single grey
  ``🎣 Waiting for a bite…`` button. ``goldens/fishing/sweep_fish.json``
  pins every byte: the run-minted ``<cid:1>`` button id (timeout session
  view ⇒ ``session_lifecycle=True``, no ``panel_anchors`` row), the
  emoji-in-label form (trap 15a's other flavor), style 2, and the spent
  fresh-bar ``fishing_energy`` row (60→58, CAST_COST=2) the cast-open
  handler writes BEFORE the panel renders.

* ``fishing.log`` — disbot/views/fishing/menu.py's fishdex embed
  (``build_fishdex_embed`` lane): the ``🎣 {display_name}'s Fishing Log``
  blue embed — the discovered/total/level description line, one field per
  venue (``🏖️ Shore — up to size #N`` / ``⛵ Deepwater (boat-only) — up
  to size #N``) listing every species as caught (**bold** ×count · 🏅
  trophy) / not-yet-caught / ``🔒 ??? — *locked*``, and the literal
  cast/sail/rod footer. ``goldens/fishing/sweep_fishlog.json`` pins the
  fresh-angler read (0/32 · 0 catches · level 1/7) with ZERO components
  (``components: []`` — the karma error-card zero-component session-panel
  wire shape) and no db_delta row (a pure read).

Trap-24 drift check (fishing row): the oracle current-head fragments
(views/fishing/cast_view.py description/field/footer + the reel button
decorator; views/fishing/menu.py log title/description/venue
fields/footer + _venue_log_lines; utils/fishing/weather.py CONDITIONS +
effect_text; utils/fishing/energy.py bar/settle constants) match the
corpus goldens byte-for-byte — NO drift (corpus sha 7f7628e1).

Under-port ledger (no golden pins these corners):
* the shipped cast view ran the live minigame in-place — bite-delay
  timers flipping the button to the reel window, fake-out shakes, early
  reel escapes, a reeled catch EDITING the panel into the result embed
  (``interaction.response.edit_message``). The port's Reel button
  commits the cast-time roll through the audited ``fishing.cast`` K7 op
  (dex upsert + pearl/coral/fish materials + game-XP in one leg txn)
  and opens the result as a fresh result card (the farm in-place-edit
  under-port precedent); the TIMING layer stays parked on the D-0043
  minigame rung (real-time asyncio the headless panel engine doesn't
  model) even though its pure math is now ported
  (sb/domain/fishing/minigame.py) — see the ops.py DEVIATION header.
* the shipped ``active_casts`` one-line-in-the-water guard now lives as
  the service.py pending-cast registry (the guard copy is answered;
  the 45 s window is modelled without a timer); the timed view
  lifecycle itself — same successor rung.
* the cast LEG is WIRED (the cast-leg depth wiring): venue (slice 1),
  rod (slice 2), bait (slice 3) and the structures (slice 4) state all
  drive the roll through the shipped ``begin_cast`` compound —
  deepwater species pool + coral drop, the compounded rarity_pull
  (rod × bait × weather × gear × tide pool), the per-cast bait charge
  spend, the boathouse regen interval and the fishery double-catch
  chance. Every knob reads exactly neutral on a fresh player (no row ⇒
  shore / tier 0 / bait-less / not built ⇒ ×1.0/+0.0), so every
  golden-pinned fresh-player byte is unchanged. The bite-SPEED half of
  the compound (rod/bait/weather/gear/dock) is computed + surfaced but
  outcome-inert until the timing rung above lands. The shipped
  Build-click in-place panel edit (safe_edit with the ✅/❌ note +
  SUCCESS/ERROR recolor) opens as a fresh result card instead — the
  farm in-place-edit under-port precedent.

MONEY-RACE NOTE (#217 / coordinator ruling 2026-07-12): this module and
the cast-open handler touch NO money primitive — fishing_energy is game
pacing, never coins; reads/writes here are the shipped unlocked
get→settle→set pair on a non-money table. The FOR UPDATE + advisory-lock
shapes (sb/domain/games/wager.py, sb/domain/games/store.py, farm/mining
#217 legs) are not in this diff; fishing's own K7 leg
(ops.py record_cast) is untouched.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
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
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

__all__ = [
    "BAIT_PANEL_ID",
    "BOATHOUSE_PANEL_ID",
    "CARD_PANEL_ID",
    "CAST_PANEL_ID",
    "DOCK_PANEL_ID",
    "FISHERY_PANEL_ID",
    "HUB_PANEL_ID",
    "LOG_PANEL_ID",
    "ROD_PANEL_ID",
    "ROD_RECIPES_PANEL_ID",
    "STRUCTURES_PANEL_ID",
    "TIDE_POOL_PANEL_ID",
    "bait_shop_spec",
    "boathouse_spec",
    "cast_spec",
    "dock_spec",
    "ensure_panel_refs",
    "fishery_spec",
    "fishing_card_spec",
    "fishing_hub_spec",
    "install_fishing_panels",
    "log_spec",
    "rod_recipes_spec",
    "rod_shop_spec",
    "structures_hub_spec",
    "tide_pool_spec",
]

CAST_PANEL_ID = "fishing.cast_panel"
LOG_PANEL_ID = "fishing.log"
HUB_PANEL_ID = "fishing.hub"
CARD_PANEL_ID = "fishing.card"
ROD_PANEL_ID = "fishing.rod_panel"
ROD_RECIPES_PANEL_ID = "fishing.rod_recipes_panel"
BAIT_PANEL_ID = "fishing.bait_panel"
STRUCTURES_PANEL_ID = "fishing.structures_panel"
TIDE_POOL_PANEL_ID = "fishing.tide_pool_panel"
DOCK_PANEL_ID = "fishing.dock_panel"
BOATHOUSE_PANEL_ID = "fishing.boathouse_panel"
FISHERY_PANEL_ID = "fishing.fishery_panel"


#: views/fishing/cast_view.py, verbatim (the golden pins the rendered
#: bytes) — the SHORE form of the ``where`` line. The grammar TextBlock
#: carries this static shore copy; ``_render_cast`` recomposes the
#: description from the cast's live venue profile, which on shore
#: reproduces this literal byte-for-byte.
_CAST_DESCRIPTION = (
    "You cast a line from the shoreline… 🏖️\n"
    "*Watch the water — hit **Reel** the moment it bites, but not before!*"
)

#: views/fishing/menu.py set_footer literal, verbatim.
_LOG_FOOTER = "🎣 Cast to fish · ⛵ Set sail for the deep · 🎒 Rod to upgrade"


def _hub_description() -> str:
    """views/fishing/menu.py ``build_fishing_menu_embed`` description,
    verbatim — the shore/deep species counts interpolate the catalog
    (21/11 at the shipped table; goldens/fishing/sweep_fishing pins the
    rendered bytes)."""
    from sb.domain.fishing import catalog

    shore_n = len(catalog.species_for_venue(catalog.SHORE_VENUE))
    deep_n = len(catalog.species_for_venue(catalog.DEEPWATER))
    return (
        f"Cast a line to catch from **{shore_n}** shoreline fish — or set "
        f"sail for the **{deep_n}** rare boat-only fish of the deep. Wait "
        "for the bite, reel it in, and fight the big ones; then level up "
        "and buy better rods.\n\n"
        "**🎣 Cast** — wait → bite → reel\n"
        "**⛵ Set sail** — shore ↔ deepwater\n"
        "**🎒 Rod** — view & upgrade your rod\n"
        "**🪱 Bait** — load a lure for rarer catches\n"
        "**🏗 Structures** — build coral structures\n"
        "**📖 Fishdex** — your collection"
    )


def fishing_hub_spec() -> PanelSpec:
    """The shipped fishing hub (disbot/views/fishing/menu.py
    ``FishingMenuView`` + ``build_fishing_menu_embed``): the 🎣 Fishing
    GAME_COLOR embed over the shipped SEVEN buttons (Cast 🎣 success ·
    Set sail / Dock ⛵ primary · Rod 🎒 · Bait 🪱 · Structures 🏗 on row
    one; Fishdex 📖 · How to fish 📖 on row two) and the shipped standard
    nav row (📚 Help + ↩ Games — ``home_hub="games"`` explicit, the
    farm/creature/casino precedent).
    ``goldens/fishing/sweep_fishing.json`` pins every byte: run-minted
    ``<cid:N>`` button ids (timeout session view ⇒
    ``session_lifecycle=True``, NO ``panel_anchors`` row — the previous
    anchored 3-button hub was an invented deviation, no D-record backs
    it), emoji as SEPARATE wire fields (trap 15a), the literal
    ``nav:help`` / ``nav:hub:games`` slots riding through the mint, and
    the three live fields (venue / forecast / energy) on the embed."""
    return PanelSpec(
        panel_id=HUB_PANEL_ID,
        subsystem="fishing",
        title="🎣 Fishing",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046, utils/ui_constants.py); the three
        # live fields ride the override (see justification).
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_hub_description()),),
        actions=(
            PanelActionSpec(
                action_id="fishing_cast", label="Cast", emoji="🎣",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("fishing.cast_open"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="fishing_sail", label="Set sail / Dock",
                emoji="⛵", style=ActionStyle.PRIMARY,
                audience_tier="user",
                handler=HandlerRef("fishing.sail_route")),
            PanelActionSpec(
                action_id="fishing_rod", label="Rod", emoji="🎒",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(ROD_PANEL_ID)),
            PanelActionSpec(
                action_id="fishing_bait", label="Bait", emoji="🪱",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(BAIT_PANEL_ID)),
            PanelActionSpec(
                action_id="fishing_structures", label="Structures",
                emoji="🏗", style=ActionStyle.SECONDARY,
                audience_tier="user",
                handler=PanelRef(STRUCTURES_PANEL_ID)),
            PanelActionSpec(
                action_id="fishing_log", label="Fishdex", emoji="📖",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(LOG_PANEL_ID)),
            PanelActionSpec(
                action_id="fishing_rules", label="How to fish",
                emoji="📖", style=ActionStyle.SECONDARY,
                audience_tier="user",
                handler=HandlerRef("fishing.howtofish_pending")),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden);
        # home_hub explicit, the farm/creature/casino precedent.
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("fishing.render_hub"),
        justification=(
            "three shipped embed FIELDS sit outside the grammar's static "
            "vocabulary (views/fishing/menu.py build_fishing_menu_embed; "
            "goldens/fishing/sweep_fishing pins the bytes): (1) 'Fishing "
            "from' interpolates the invoker's venue profile (emoji + bold "
            "name + blurb); (2) 'Today's forecast: {emoji} {name}' renders "
            "the day-keyed shared weather condition with its blurb + "
            "effect line; (3) 'Energy' renders the invoker's LIVE settled "
            "energy gauge (fish_energy.bar). Title, description, color "
            "and every component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("fishing_cast", "fishing_sail", "fishing_rod",
             "fishing_bait", "fishing_structures"),
            ("fishing_log", "fishing_rules"),)),)),
    )


def fishing_card_spec() -> PanelSpec:
    """The generic one-embed reply card (the shipped ``ctx.send(embed=…)``)
    — the mining.card/ai.card/karma.card pattern for the fishing read
    views (``!fishtop`` / ``!trophies``)."""
    return PanelSpec(
        panel_id=CARD_PANEL_ID,
        subsystem="fishing",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("fishing.render_card"),
        justification=(
            "the shipped `!fishtop` / `!trophies` replies are "
            "live-state-parameterized embeds built in the handler "
            "(fishing_cog.py fishtop/trophies — the _FISHING_COLOR blue "
            "leaderboard/hall-of-fame embeds; goldens/fishing/"
            "sweep_fishtop + sweep_trophies pin the empty-world bytes). "
            "Zero components; the renderer presents the handler-built "
            "RenderedEmbed verbatim (the mining.card/ai.card/karma.card "
            "precedent)."),
    )


def cast_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=CAST_PANEL_ID,
        subsystem="fishing",
        title="",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046, utils/ui_constants.py) — the farm
        # hub token; description/weather-field/footer ride the override.
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_CAST_DESCRIPTION),),
        actions=(
            PanelActionSpec(
                action_id="fishing_reel", label="🎣 Waiting for a bite…",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("fishing.fish_route"),
                result_render=ResultRender.RESULT_CARD),
        ),
        # the shipped CastView is a bare timer view — no help/home nav row
        # (the golden pins the single-button component row).
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("fishing.render_cast"),
        justification=(
            "two shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/fishing/sweep_fish pins both): (1) the FOOTER "
            "interpolates the venue profile and the invoker's LIVE "
            "settled energy gauge ('🏖️ Shore · ⚡ 58/60 [▰▰▰▰▰▰▰▰▰▰]', "
            "views/fishing/cast_view.py footer = profile + energy.bar) — "
            "outside FooterMode's vocabulary (the farm balance-footer "
            "precedent); (2) the WEATHER FIELD is the day's shared "
            "condition rendered only when it moves a cast knob "
            "(cast_view's clear-is-silent conditional; name '{emoji} "
            "{name}', value '*{blurb}* ({effect_text})') — day-keyed "
            "state outside the static TextBlock/FieldsBlock vocabulary. "
            "Description, color and the component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(("fishing_reel",),)),)),
    )


def log_spec() -> PanelSpec:
    """The shipped fishdex — a component-less per-read result card (the
    shipped send was a plain ``ctx.send(embed=...)``, never an anchored
    panel; the karma card/casino precedent)."""
    return PanelSpec(
        panel_id=LOG_PANEL_ID,
        subsystem="fishing",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("fishing.render_log"),
        justification=(
            "the shipped fishdex embed is read-parameterized end to end "
            "(views/fishing/menu.py; goldens/fishing/sweep_fishlog pins "
            "the bytes): the TITLE carries the invoker's display name "
            "('🎣 AdminActor's Fishing Log'), the description "
            "interpolates discovered/total/level, and the per-venue "
            "fields render the live dex (caught ×count · trophy / not "
            "yet caught / locked) against the level-banded species "
            "catalog — all outside the static grammar vocabulary. Zero "
            "components; the renderer only composes the embed."),
        session_lifecycle=True,
    )


def _knob_summary(rod) -> str:
    """A friendly one-liner of what a rod's knobs buy (vs. the bare
    starter) — views/fishing/rod_shop.py ``_knob_summary`` verbatim
    (goldens/fishing/sweep_rod pins the starter + Bronze bytes)."""
    if rod.tier == 0:
        return "the trusty starter — catches everything, just no bonuses"
    bits = [
        f"+{rod.window_bonus:.1f}s reaction time",
        f"bites {round((1 - rod.bite_speed) * 100)}% faster",
        "better catches in your band",
        f"{round(rod.escape_resist * 100)}% less escape in fights",
        f"{round(rod.premature_grace * 100)}% chance to forgive an early reel",
    ]
    return " · ".join(bits)


def rod_shop_spec() -> PanelSpec:
    """The shipped rod shop (views/fishing/rod_shop.py ``RodShopView`` +
    ``build_rod_embed``): the 🎣 Your Fishing Rod ECONOMY_COLOR gold
    embed (current rod + the ladder + the next upgrade with live
    balance) over the shipped FOUR buttons (⬆️ Upgrade rod success ·
    🎣 Craft from fish primary · 📋 Recipes secondary on row one;
    ↩ Fishing menu secondary on row two — emoji-in-label, trap 15a's
    other flavor). No help/home nav row (the shipped author-restricted
    BaseView). ``goldens/fishing/sweep_rod.json`` pins every byte of the
    fresh tier-0 open: run-minted ``<cid:N>`` button ids (timeout
    session view ⇒ ``session_lifecycle=True``, no ``panel_anchors``
    row), all four buttons enabled, and the Bare-Rod/Bronze-next
    embed."""
    return PanelSpec(
        panel_id=ROD_PANEL_ID,
        subsystem="fishing",
        title="🎣 Your Fishing Rod",
        audience=Audience.INVOKER,
        # ECONOMY_COLOR gold (15844367, utils/ui_constants.py); the live
        # description + fields ride the override (see justification).
        frame=EmbedFrameSpec(style_token="gold",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="rs_upgrade", label="⬆️ Upgrade rod",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("fishing.rod_upgrade_route")),
            PanelActionSpec(
                action_id="rs_craft", label="🎣 Craft from fish",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("fishing.craftrod_route")),
            PanelActionSpec(
                action_id="rs_recipes", label="📋 Recipes",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(ROD_RECIPES_PANEL_ID)),
            PanelActionSpec(
                action_id="rs_menu", label="↩ Fishing menu",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("fishing.render_rod_shop"),
        justification=(
            "the shipped `!rod` reply is a fully live-state-parameterized "
            "embed built in the view (views/fishing/rod_shop.py "
            "build_rod_embed: the current-rod description + knob summary, "
            "the ✅/▶/🔒 ladder field, and the next-upgrade field with the "
            "live `Your balance: {n} 🪙` line + the craft-recipe pointer — "
            "goldens/fishing/sweep_rod.json pins the fresh tier-0 bytes), "
            "read-parameterized state outside the static TextBlock/"
            "FieldsBlock vocabulary (the mining workshop/home precedent). "
            "The renderer patches only the embed and the at-max disabled "
            "flags on ⬆️ Upgrade rod / 🎣 Craft from fish (the shipped "
            "RodShopView gating); every component stays grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("rs_upgrade", "rs_craft", "rs_recipes"),
            ("rs_menu",),)),)),
    )


def rod_recipes_spec() -> PanelSpec:
    """The shipped rod recipe browser (views/fishing/rod_recipe_browser.py
    ``RodRecipeBrowserView`` + ``build_rod_recipe_embed``): the
    📋 Rod Recipes ECONOMY_COLOR gold embed (every fish→rod recipe with
    the player's live eligible-fish progress) over the shipped TWO
    buttons (🎣 Craft next primary on row one; ↩ Rod shop secondary on
    row two). No help/home nav row. ``goldens/fishing/
    sweep_rodrecipes.json`` pins every byte of the fresh tier-0 open."""
    return PanelSpec(
        panel_id=ROD_RECIPES_PANEL_ID,
        subsystem="fishing",
        title="📋 Rod Recipes",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold",
                             footer_mode=FooterMode.NONE),
        # the shipped static description (build_rod_recipe_embed, verbatim
        # — the golden pins the bytes); the ladder field rides the override.
        body=(TextBlock(
            "Craft your way up the ladder from caught fish — smallest "
            "catches spend first, so your trophies are always safe. Coins "
            "remain the fast alternative (`!rod`)."),),
        actions=(
            PanelActionSpec(
                action_id="rr_craft", label="🎣 Craft next",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("fishing.craftrod_route")),
            PanelActionSpec(
                action_id="rr_back", label="↩ Rod shop",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(ROD_PANEL_ID)),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("fishing.render_rod_recipes"),
        justification=(
            "the shipped `!rodrecipes` ladder field is live-state-"
            "parameterized end to end (views/fishing/rod_recipe_browser.py "
            "_recipe_line: every craftable tier renders the player's "
            "current eligible-fish count against the requirement — "
            "`0/10 eligible fish (size ≤ 6)` — with the ✅ owned / ▶ next / "
            "🔒 locked marks and the ready-to-craft tail; goldens/fishing/"
            "sweep_rodrecipes.json pins the fresh tier-0 bytes), outside "
            "the static TextBlock/FieldsBlock vocabulary (the rod-shop / "
            "mining-workshop precedent). The renderer patches only the "
            "embed field and the at-max disabled flag on 🎣 Craft next; "
            "every component stays grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("rr_craft",),
            ("rr_back",),)),)),
    )


def _bait_buy_options() -> tuple[dict, ...]:
    """views/fishing/bait_shop.py ``_BaitSelect`` options verbatim — one
    per shelf entry (goldens/fishing/sweep_bait pins every option
    byte)."""
    from sb.domain.fishing import bait as bait_mod

    return tuple(
        {"label": f"{bait.name} — {bait.price} coins", "value": bait.key,
         "emoji": bait.emoji,
         "description": f"×{bait.charges} casts · "
                        f"{bait_mod.bait_effect_text(bait)}"}
        for bait in bait_mod.BAIT_CATALOG)


def _bait_craft_options() -> tuple[dict, ...]:
    """views/fishing/bait_shop.py ``_BaitCraftSelect`` options verbatim —
    one per fish-craftable bait."""
    from sb.domain.fishing import bait as bait_mod

    options = []
    for key in bait_mod.CRAFTABLE_KEYS:
        bait = bait_mod.bait_by_key(key)
        recipe = bait_mod.craft_recipe(key)
        if bait is None or recipe is None:
            continue
        options.append(
            {"label": f"{bait.name} — {bait_mod.recipe_text(recipe)}",
             "value": bait.key, "emoji": bait.emoji,
             "description": f"×{bait.charges} casts · "
                            f"{bait_mod.bait_effect_text(bait)}"})
    return tuple(options)


def _bait_pearl_options() -> tuple[dict, ...]:
    """views/fishing/bait_shop.py ``_PearlCraftSelect`` options verbatim
    — one per pearl-craftable bait (the 🦪 option emoji is the shipped
    literal, not the bait's own)."""
    from sb.domain.fishing import bait as bait_mod

    options = []
    for key in bait_mod.PEARL_CRAFTABLE_KEYS:
        bait = bait_mod.bait_by_key(key)
        pearl_cost = bait_mod.pearl_recipe(key)
        if bait is None or pearl_cost is None:
            continue
        options.append(
            {"label": f"{bait.name} — "
                      f"{bait_mod.pearl_recipe_text(pearl_cost)}",
             "value": bait.key, "emoji": "🦪",
             "description": f"×{bait.charges} casts · "
                            f"{bait_mod.bait_effect_text(bait)}"})
    return tuple(options)


def bait_shop_spec() -> PanelSpec:
    """The shipped bait shop (views/fishing/bait_shop.py ``BaitShopView``
    + ``build_bait_embed``): the 🪱 Bait Shop ECONOMY_COLOR gold embed
    (loaded bait / the shelf / craft-from-fish / craft-from-pearls with
    the live pearl count / your balance) over the shipped THREE selects
    (buy a pack · craft from caught fish · craft from pearls) + the
    ↩ Fishing menu button on its own row. No help/home nav row (the
    shipped author-restricted BaseView). ``goldens/fishing/
    sweep_bait.json`` (and the byte-identical no-arg ``!craftbait`` open,
    sweep_craftbait) pins every byte of the fresh bait-less open:
    run-minted ``<cid:N>`` ids (timeout session view ⇒
    ``session_lifecycle=True``, no ``panel_anchors`` row), every select
    option label/emoji/description, and the No-bait-loaded embed."""
    return PanelSpec(
        panel_id=BAIT_PANEL_ID,
        subsystem="fishing",
        title="🪱 Bait Shop",
        audience=Audience.INVOKER,
        # ECONOMY_COLOR gold (15844367, utils/ui_constants.py); the live
        # description + fields ride the override (see justification).
        frame=EmbedFrameSpec(style_token="gold",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="bs_buy", kind=SelectorKind.ENUM,
                on_select=HandlerRef("fishing.bait_buy_route"),
                options_source=_bait_buy_options(),
                placeholder="Buy a pack of bait…", audience_tier="user"),
            SelectorSpec(
                selector_id="bs_craft", kind=SelectorKind.ENUM,
                on_select=HandlerRef("fishing.craftbait_route"),
                options_source=_bait_craft_options(),
                placeholder="Craft a pack from caught fish…",
                audience_tier="user"),
            SelectorSpec(
                selector_id="bs_pearl", kind=SelectorKind.ENUM,
                on_select=HandlerRef("fishing.craftpearl_route"),
                options_source=_bait_pearl_options(),
                placeholder="Craft a pack from pearls…",
                audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="bs_menu", label="↩ Fishing menu",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("fishing.render_bait_shop"),
        justification=(
            "the shipped `!bait` reply is a fully live-state-parameterized "
            "embed built in the view (views/fishing/bait_shop.py "
            "build_bait_embed: the loaded-bait/charges description, the "
            "shelf + craft-from-fish fields, the craft-from-pearls field "
            "whose NAME interpolates the live pearl count, and the live "
            "`Your balance` field — goldens/fishing/sweep_bait.json pins "
            "the fresh bait-less bytes), read-parameterized state outside "
            "the static TextBlock/FieldsBlock vocabulary (the rod-shop / "
            "mining-workshop precedent). The renderer patches only the "
            "embed; every component (the three static-option selects + the "
            "menu button) stays grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("bs_buy",),
            ("bs_craft",),
            ("bs_pearl",),
            ("bs_menu",),)),)),
    )


async def _render_bait_shop(spec: PanelSpec, ctx) -> object:
    """renderer_override — bait_shop.py's ``build_bait_embed`` verbatim
    (see justification): grammar render + the live loaded-bait
    description, the shelf / craft-from-fish / craft-from-pearls (live
    pearl count) / balance fields. A fresh player reads no loadout /
    0 pearls / balance 0 → the bytes goldens/fishing/sweep_bait.json
    (and sweep_craftbait) pin."""
    from sb.domain.economy.store import get_coins
    from sb.domain.fishing import bait as bait_mod
    from sb.domain.fishing import store
    from sb.domain.fishing.ops import PEARL_ITEM
    from sb.domain.mining.store import get_mining_inventory
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    cur_key, charges = await store.get_active_bait(uid, gid)
    active = bait_mod.bait_by_key(cur_key)
    if active is None or charges <= 0:
        active, charges = None, 0
    balance = await get_coins(uid, gid)
    inventory = await get_mining_inventory(uid, gid)
    pearls = inventory.get(PEARL_ITEM, 0)

    if active is not None and charges > 0:
        description = (
            f"Loaded: **{active.name}** {active.emoji} — "
            f"**{charges}** casts left "
            f"({bait_mod.bait_effect_text(active)}).\n"
            "*Each cast spends one charge and applies these on top of "
            "your rod.*")
    else:
        description = (
            "No bait loaded — you're fishing bare (which catches "
            "fine!).\n"
            "*Load a pack for rarer, bigger fish or quicker bites.*")

    shelf = [
        f"{bait.emoji} **{bait.name}** — {bait.price} 🪙 "
        f"(×{bait.charges} casts, {bait_mod.bait_effect_text(bait)})"
        for bait in bait_mod.BAIT_CATALOG]
    fields: list[tuple[str, str]] = [("The shelf", "\n".join(shelf))]

    craftable = []
    for key in bait_mod.CRAFTABLE_KEYS:
        bait = bait_mod.bait_by_key(key)
        recipe = bait_mod.craft_recipe(key)
        if bait is None or recipe is None:
            continue
        craftable.append(
            f"{bait.emoji} **{bait.name}** — {bait_mod.recipe_text(recipe)}")
    if craftable:
        fields.append((
            "Craft from fish",
            "\n".join(craftable)
            + "\n*Turn small catches into bait — no coins needed.*"))

    pearl_craftable = []
    for key in bait_mod.PEARL_CRAFTABLE_KEYS:
        bait = bait_mod.bait_by_key(key)
        pearl_cost = bait_mod.pearl_recipe(key)
        if bait is None or pearl_cost is None:
            continue
        pearl_craftable.append(
            f"{bait.emoji} **{bait.name}** — "
            f"{bait_mod.pearl_recipe_text(pearl_cost)}")
    if pearl_craftable:
        fields.append((
            f"Craft from pearls (you have {pearls} 🦪)",
            "\n".join(pearl_craftable)
            + "\n*Pearls drop rarely when you reel in a fish — bigger "
            "fish, better odds.*"))

    fields.append(("Your balance", f"**{balance}** 🪙"))
    embed = _dc_replace(rendered.embed, description=description,
                        fields=tuple(fields))
    return _dc_replace(rendered, embed=embed)


async def _member_display_name(user_id: int, guild_id: int) -> str:
    """The invoker's display name through the guild-directory read port
    (the karma/economy author-line precedent) — degrades to the bare
    mention, never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ mention fallback
        return f"<@{user_id}>"
    return member.tag.rsplit("#", 1)[0]


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped three live fields
    (views/fishing/menu.py build_fishing_menu_embed, verbatim; see
    justification). The energy field is the honest settled read — the hub
    open never spends."""
    from sb.domain.fishing import energy as energy_mod
    from sb.domain.fishing import store
    from sb.domain.fishing import venue as venue_mod
    from sb.domain.fishing import weather as weather_mod
    from sb.kernel.panels.render import render_panel
    from sb.kernel.workflow.context import SYSTEM_CLOCK

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    now = int(SYSTEM_CLOCK().timestamp())
    cur, ts = await store.get_fishing_energy(uid, gid)
    current = energy_mod.settle(energy_mod.EnergyState(cur, ts), now).current
    # the LIVE stored venue (slice 1 — no row reads as shore, so a fresh
    # player renders the golden-pinned shore bytes verbatim)
    profile = venue_mod.profile_for(
        await store.get_fishing_venue(uid, gid))
    w = weather_mod.current_weather()
    embed = _dc_replace(
        rendered.embed,
        fields=(
            ("Fishing from",
             f"{profile.emoji} **{profile.name}** — {profile.blurb}"),
            (f"Today's forecast: {w.emoji} {w.name}",
             f"*{w.blurb}* ({weather_mod.effect_text(w)})"),
            ("Energy", energy_mod.bar(int(current))),
        ))
    return _dc_replace(rendered, embed=embed)


async def _render_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — present the handler-built embed verbatim (the
    mining.card ``_render_card`` shape, no attachment seam)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    embed = (getattr(ctx, "params", {}) or {}).get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_cast(spec: PanelSpec, ctx) -> object:
    """renderer_override — cast_view.py's embed dressing (see
    justification): grammar render + the venue-keyed description (the
    ``where`` line, prepare_cast L100-111), the weather field, and the
    venue/energy footer with the shipped bait/gear/tide-pool/dock notes
    (prepare_cast L120-137) driven off the cast-open args. The energy
    was already settled+spent by the cast-open handler (the write
    precedes the render — the golden's 58/60 gauge is the POST-spend
    read). A fresh shore player composes byte-identically to the static
    ``_CAST_DESCRIPTION`` + bare footer the golden pins."""
    from sb.domain.fishing import bait as bait_mod
    from sb.domain.fishing import energy as energy_mod
    from sb.domain.fishing import store
    from sb.domain.fishing import venue as venue_mod
    from sb.domain.fishing import weather as weather_mod
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    params = getattr(ctx, "params", {}) or {}
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    current = params.get("cast_energy")
    if current is None:
        # direct panel open (no cast-open hop) — honest settled read,
        # no spend.
        from sb.kernel.workflow.context import SYSTEM_CLOCK

        now = int(SYSTEM_CLOCK().timestamp())
        cur, ts = await store.get_fishing_energy(uid, gid)
        current = energy_mod.settle(energy_mod.EnergyState(cur, ts),
                                    now).current
    w = weather_mod.current_weather()
    fields: tuple = ()
    if w.bite_speed_mult != 1.0 or w.rarity_mult != 1.0:
        # Only show the forecast when it actually changes the cast
        # (clear = silent) — cast_view.py verbatim.
        fields = ((f"{w.emoji} {w.name}",
                   f"*{w.blurb}* ({weather_mod.effect_text(w)})"),)
    # the cast's venue: the cast-open hop passes the profile it ROLLED
    # at; a direct panel open reads the LIVE stored venue (both default
    # shore — a fresh no-row player renders the golden-pinned bytes).
    venue_arg = params.get("cast_venue")
    profile = venue_mod.profile_for(
        str(venue_arg) if venue_arg is not None
        else await store.get_fishing_venue(uid, gid))
    # the shipped where-line (prepare_cast L100-111) — on shore this
    # composes to _CAST_DESCRIPTION byte-for-byte.
    where = (
        "from the boat, out over the deep water"
        if profile.key == venue_mod.DEEPWATER
        else "from the shoreline"
    )
    description = (
        f"You cast a line {where}… {profile.emoji}\n"
        "*Watch the water — hit **Reel** the moment it bites, but not "
        "before!*"
    )
    footer = (f"{profile.emoji} {profile.name} · "
              + energy_mod.bar(int(current)))
    # the shipped cast-note tail (prepare_cast L121-137, verbatim) —
    # each note renders only when the cast-open hop said the knob was
    # on, so a fresh player's footer is byte-identical.
    bait = bait_mod.bait_by_key(str(params.get("cast_bait_key") or ""))
    if bait is not None:
        footer += (
            f" · {bait.emoji} {bait.name} "
            f"({int(params.get('cast_bait_charges_left', 0) or 0)} left)"
        )
    if params.get("cast_gear_bonus"):
        footer += " · 🎣 fishing gear"
    if params.get("cast_tide_pool"):
        footer += " · 🪸 tide pool"
    if params.get("cast_dock"):
        footer += " · ⚓ dock"
    embed = _dc_replace(rendered.embed, description=description,
                        fields=fields, footer=footer)
    return _dc_replace(rendered, embed=embed)


async def _render_log(spec: PanelSpec, ctx) -> object:
    """renderer_override — menu.py's fishdex embed verbatim (see
    justification)."""
    from sb.domain.fishing import catalog, store
    from sb.domain.games import xp as game_xp
    from sb.domain.games.store import game_xp_rows
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    rows = await store.get_catch_log(uid, gid)
    log = {str(r["species"]): int(r["count"]) for r in rows}
    records = {str(r["species"]): float(r["best_weight"]) for r in rows}
    known = set(catalog.fish_names())
    xp_rows = {str(r["game"]): int(r["xp"])
               for r in await game_xp_rows(uid, gid)}
    level = catalog.fishing_level_from_xp(
        xp_rows.get(game_xp.GAME_FISHING, 0))
    caught = sum(1 for name in log if name in known)
    total = sum(c for name, c in log.items() if name in known)
    name = await _member_display_name(uid, gid)
    fields: list[tuple] = []
    for venue, label in (
        (catalog.SHORE_VENUE, "🏖️ Shore"),
        (catalog.DEEPWATER, "⛵ Deepwater (boat-only)"),
    ):
        cap = catalog.max_size_rank_for_level(level, venue)
        lines = _venue_log_lines(log, venue, cap, records)
        if lines:
            fields.append((f"{label} — up to size #{cap}",
                           "\n".join(lines)))
    embed = RenderedEmbed(
        title=f"🎣 {name}'s Fishing Log",
        description=(
            f"**{caught}/{len(known)}** species discovered · "
            f"**{total}** total catches · "
            f"Fishing level **{level}/{catalog.MAX_LEVEL}**"),
        fields=tuple(fields),
        footer=_LOG_FOOTER,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


def _venue_log_lines(log: dict[str, int], venue: str, cap: int,
                     records: dict[str, float]) -> list[str]:
    """views/fishing/menu.py ``_venue_log_lines`` verbatim — one line per
    species in the venue: caught (bold, ×count, 🏅 trophy) /
    unlocked-but-uncaught / locked."""
    from sb.domain.fishing import catalog

    lines: list[str] = []
    for species in catalog.species_for_venue(venue):
        count = log.get(species.name, 0)
        unlocked = species.size_rank <= cap
        if count:
            best = records.get(species.name, 0.0)
            trophy = f" · 🏅 {best:g}kg" if best > 0 else ""
            lines.append(
                f"{species.emoji} **{species.name.title()}** "
                f"(#{species.size_rank}) ×{count}{trophy}")
        elif unlocked:
            lines.append(
                f"{species.emoji} {species.name.title()} "
                f"(#{species.size_rank}) — *not yet caught*")
        else:
            lines.append(f"🔒 ??? (#{species.size_rank}) — *locked*")
    return lines


async def _render_rod_shop(spec: PanelSpec, ctx) -> object:
    """renderer_override — rod_shop.py's ``build_rod_embed`` verbatim
    (see justification): grammar render + the live current-rod
    description, the ladder field and the next-upgrade field (live coin
    balance + craft-recipe pointer), plus the shipped at-max button
    gating. A fresh player reads tier 0 / balance 0 → the bytes
    goldens/fishing/sweep_rod.json pins."""
    from sb.domain.economy.store import get_coins
    from sb.domain.fishing import rods as rods_mod
    from sb.domain.fishing import store
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    tier = await store.get_rod_tier(uid, gid)
    current = rods_mod.rod_for_tier(tier)
    nxt = rods_mod.next_rod(tier)
    balance = await get_coins(uid, gid)

    ladder_lines = []
    for rod in rods_mod.ROD_LADDER:
        if rod.tier < current.tier:
            mark = "✅"
        elif rod.tier == current.tier:
            mark = "**▶**"
        else:
            mark = "🔒"
        price = "—" if rod.price == 0 else f"{rod.price} 🪙"
        ladder_lines.append(f"{mark} {rod.emoji} **{rod.name}** ({price})")
    fields: list[tuple[str, str]] = [
        ("The ladder", "\n".join(ladder_lines))]
    if nxt is None:
        fields.append(("Next upgrade",
                       "You wield the finest rod there is. 💎"))
    else:
        recipe = rods_mod.rod_recipe(nxt.tier)
        craft_line = (
            f"\n🎣 _or craft from {rods_mod.rod_recipe_text(recipe)}_"
            " (📋 Recipes shows your live progress)"
            if recipe is not None
            else ""
        )
        fields.append((
            f"Next: {nxt.emoji} {nxt.name} — {nxt.price} 🪙",
            f"_{_knob_summary(nxt)}_\nYour balance: **{balance}** 🪙"
            f"{craft_line}"))
    embed = _dc_replace(
        rendered.embed,
        description=(f"You're wielding the **{current.name}** "
                     f"{current.emoji}\n*{_knob_summary(current)}*"),
        fields=tuple(fields))
    at_max = nxt is None
    components = tuple(
        _dc_replace(c, disabled=True)
        if (at_max and (getattr(c, "custom_id", "").endswith(".rs_upgrade")
                        or getattr(c, "custom_id", "").endswith(".rs_craft")))
        else c
        for c in rendered.components)
    return _dc_replace(rendered, embed=embed, components=components)


async def _render_rod_recipes(spec: PanelSpec, ctx) -> object:
    """renderer_override — rod_recipe_browser.py's
    ``build_rod_recipe_embed`` verbatim (see justification): grammar
    render + the live-progress ladder field, plus the shipped at-max
    gating on 🎣 Craft next. A fresh player reads tier 0 / an empty pack
    → the bytes goldens/fishing/sweep_rodrecipes.json pins."""
    from sb.domain.fishing import crafting, rods as rods_mod
    from sb.domain.fishing import store
    from sb.domain.mining.store import get_mining_inventory
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    tier = await store.get_rod_tier(uid, gid)
    inventory = await get_mining_inventory(uid, gid)
    nxt = rods_mod.next_rod(tier)
    lines = []
    for rod in rods_mod.ROD_LADDER:
        recipe = rods_mod.rod_recipe(rod.tier)
        if recipe is None:  # the starter tier has no recipe
            continue
        lines.append(_recipe_line(
            rod, recipe,
            crafting.eligible_fish_total(inventory, recipe),
            owned=rod.tier <= tier,
            is_next=nxt is not None and rod.tier == nxt.tier))
    embed = _dc_replace(rendered.embed,
                        fields=(("The ladder", "\n".join(lines)),))
    at_max = nxt is None
    components = tuple(
        _dc_replace(c, disabled=True)
        if (at_max and getattr(c, "custom_id", "").endswith(".rr_craft"))
        else c
        for c in rendered.components)
    return _dc_replace(rendered, embed=embed, components=components)


def _recipe_line(rod, recipe, eligible: int, *, owned: bool,
                 is_next: bool) -> str:
    """views/fishing/rod_recipe_browser.py ``_recipe_line`` verbatim —
    one ladder line: owned (✅), the live-progress next tier (▶), or
    locked (🔒)."""
    if owned:
        return f"✅ {rod.emoji} **{rod.name}** — already wielded"
    target = recipe.fish_count
    progress = f"{min(eligible, target)}/{target} eligible fish"
    cutoff = f"size ≤ {recipe.max_size_rank}"
    mark = "**▶**" if is_next else "🔒"
    ready = " — ready to craft!" if is_next and eligible >= target else ""
    return f"{mark} {rod.emoji} **{rod.name}** — {progress} ({cutoff}){ready}"


# --- the coral structures (slice 4, FINAL): the shipped structures sub-hub
# (views/fishing/structures_hub.py) + the four per-structure build panels
# (views/fishing/{tide_pool,dock,boathouse,fishery}.py), verbatim. The four
# panel goldens (sweep_tidepool / sweep_dock / sweep_boathouse /
# sweep_fishery) pin every byte of the fresh not-built opens: the
# emoji-in-label Build buttons (style 3) + ↩ Structures, the standard nav
# row (📚 Help + ↩ Games — the shipped HubView, unlike the author-locked
# rod/bait BaseViews), and the teal / dark-teal embeds with the live
# Level / Current bonus / Next fields + the Build footer. No golden pins
# the sub-hub itself (the shipped capture only ever reached it by button).


def _tide_pool_bonus_text(level: int) -> str:
    """views/fishing/tide_pool.py ``_bonus_text`` verbatim."""
    from sb.domain.mining import structures

    pct = round((structures.tide_pool_pull_mult(level) - 1.0) * 100)
    return f"+{pct}% pull toward rarer fish" if pct else "no bonus yet"


def _dock_bonus_text(level: int) -> str:
    """views/fishing/dock.py ``_bonus_text`` verbatim."""
    from sb.domain.mining import structures

    pct = round((1.0 - structures.dock_bite_speed_mult(level)) * 100)
    return f"{pct}% faster bites" if pct else "no bonus yet"


def _boathouse_bonus_text(level: int) -> str:
    """views/fishing/boathouse.py ``_bonus_text`` verbatim."""
    from sb.domain.mining import structures

    pct = round((1.0 - structures.boathouse_regen_mult(level)) * 100)
    return f"{pct}% faster energy regen" if pct else "no bonus yet"


def _fishery_bonus_text(level: int) -> str:
    """views/fishing/fishery.py ``_bonus_text`` verbatim."""
    from sb.domain.mining import structures

    pct = round(structures.fishery_bonus_chance(level) * 100)
    return f"+{pct}% double-catch chance" if pct else "no bonus yet"


#: One row per structure panel: (panel-id, structure key, title,
#: style token, Build emoji, action prefix, static description, maxed
#: line, bonus-text fn) — the four shipped view modules, verbatim copy.
def _structure_panel_rows() -> tuple[tuple, ...]:
    from sb.domain.mining import structures

    return (
        (TIDE_POOL_PANEL_ID, structures.TIDE_POOL, "🪸 Tide Pool", "teal",
         "🪸", "tp",
         "Stock a reef pool with **coral** to nudge your casts toward "
         "rarer fish. Coral drops on a **deepwater** reel (`!sail`) — "
         "the same coral you can carve into curios, now with a second, "
         "*useful* home.",
         "Your Tide Pool is at its highest level — casts pull their "
         "best.",
         _tide_pool_bonus_text),
        (DOCK_PANEL_ID, structures.DOCK, "⚓ Dock", "dark_teal", "⚓",
         "dk",
         "Build a dock with **coral** and **wood** so the fish bite "
         "sooner — the cheap, early counterpart to the Tide Pool. Coral "
         "drops on a **deepwater** reel (`!sail`); wood you already "
         "mine. Faster bites vs. the Tide Pool's rarer fish — spend "
         "your coral where you like.",
         "Your Dock is at its highest level — the bite is as quick as "
         "it gets.",
         _dock_bonus_text),
        (BOATHOUSE_PANEL_ID, structures.BOATHOUSE, "🛖 Boathouse",
         "dark_teal", "🛖", "bh",
         "Build a boathouse with **coral** and **wood** so your fishing "
         "energy refills faster — less waiting when the line needs to "
         "rest. Coral drops on a **deepwater** reel (`!sail`); wood you "
         "already mine. More fishing (Boathouse) vs. rarer fish (Tide "
         "Pool) vs. faster bites (Dock) — spend your coral where you "
         "like.",
         "Your Boathouse is at its highest level — energy refills as "
         "fast as it gets.",
         _boathouse_bonus_text),
        (FISHERY_PANEL_ID, structures.FISHERY, "🐟 Fishery", "dark_teal",
         "🐟", "fy",
         "Build a fishery with **coral** and **wood** to keep the "
         "waters well-stocked — a landed reel is more likely to hook a "
         "**second** fish (extra craft fodder). Coral drops on a "
         "**deepwater** reel (`!sail`); wood you already mine. More "
         "fish per catch (Fishery) vs. rarer fish (Tide Pool) vs. "
         "faster bites (Dock) vs. faster energy (Boathouse) — spend "
         "your coral where you like.",
         "Your Fishery is at its highest level — double catches as "
         "often as it gets.",
         _fishery_bonus_text),
    )


_STRUCTURE_BUILD_ROUTES = {
    "tp": "fishing.tidepool_build_route",
    "dk": "fishing.dock_build_route",
    "bh": "fishing.boathouse_build_route",
    "fy": "fishing.fishery_build_route",
}


def _structure_spec(panel_id: str, title: str, style_token: str,
                    emoji: str, prefix: str, description: str) -> PanelSpec:
    """One shipped structure panel (views/fishing/*.py: the build embed
    over the {emoji} Build success button + ↩ Structures, on the shipped
    HubView nav frame). The matching golden pins every byte of the fresh
    not-built open: run-minted ``<cid:N>`` button ids (timeout session
    view ⇒ ``session_lifecycle=True``, no ``panel_anchors`` row), the
    emoji-in-label Build form (trap 15a's other flavor), style 3, the
    nav:help / nav:hub:games slots, and the not-built embed."""
    return PanelSpec(
        panel_id=panel_id,
        subsystem="fishing",
        title=title,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token=style_token,
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(description),),
        actions=(
            PanelActionSpec(
                action_id=f"{prefix}_build", label=f"{emoji} Build",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef(_STRUCTURE_BUILD_ROUTES[prefix]),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id=f"{prefix}_back", label="↩ Structures",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(STRUCTURES_PANEL_ID)),
        ),
        # the shipped structure panels are HubView children — they carry
        # the standard nav row (📚 Help + ↩ Games; the goldens pin both
        # slots), unlike the author-locked rod/bait BaseViews.
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef(f"fishing.render_{prefix}_structure"),
        justification=(
            "the shipped structure panel embed is live-state-"
            "parameterized (views/fishing/ build_*_embed: the Level "
            "field reads the player's built mining_structures level, "
            "Current bonus renders the level's mult, and the Next field "
            "interpolates the ladder cost — the matching "
            "goldens/fishing sweep pins the fresh not-built bytes), and "
            "the FOOTER switches between the Build hint and the maxed "
            "form — read-parameterized state outside the static "
            "TextBlock/FieldsBlock + FooterMode vocabulary (the "
            "rod-shop / mining-forge precedent). The renderer patches "
            "only the embed fields + footer; every component stays "
            "grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            (f"{prefix}_build", f"{prefix}_back"),)),)),
    )


def tide_pool_spec() -> PanelSpec:
    rows = _structure_panel_rows()[0]
    return _structure_spec(rows[0], rows[2], rows[3], rows[4], rows[5],
                           rows[6])


def dock_spec() -> PanelSpec:
    rows = _structure_panel_rows()[1]
    return _structure_spec(rows[0], rows[2], rows[3], rows[4], rows[5],
                           rows[6])


def boathouse_spec() -> PanelSpec:
    rows = _structure_panel_rows()[2]
    return _structure_spec(rows[0], rows[2], rows[3], rows[4], rows[5],
                           rows[6])


def fishery_spec() -> PanelSpec:
    rows = _structure_panel_rows()[3]
    return _structure_spec(rows[0], rows[2], rows[3], rows[4], rows[5],
                           rows[6])


def structures_hub_spec() -> PanelSpec:
    """The shipped fishing structures sub-hub (views/fishing/
    structures_hub.py ``StructuresView`` + ``build_structures_embed``):
    the 🏗 Fishing structures GAME_COLOR embed (every coral structure's
    status at a glance) over the shipped FIVE buttons (Tide Pool 🪸 ·
    Dock ⚓ · Boathouse 🛖 · Fishery 🐟 secondary on row one; ↩ Fishing
    menu on row two — emoji as SEPARATE wire fields, trap 15a) and the
    standard nav row. The fishing hub's 🏗 Structures button routes
    here; each per-structure panel's ↩ Structures button routes back.
    No golden pins this open (the shipped capture never clicked through)
    — copy oracle-source-verbatim."""
    return PanelSpec(
        panel_id=STRUCTURES_PANEL_ID,
        subsystem="fishing",
        title="🏗 Fishing structures",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046) — structures_hub.py passes
        # color=GAME_COLOR (its _STRUCTURES_COLOR constant is unused).
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
            "Spend the **coral** you reel in out on the **deepwater** "
            "(`!sail`) on structures that make every cast better. Pick "
            "one to build or upgrade."),),
        actions=(
            PanelActionSpec(
                action_id="st_tidepool", label="Tide Pool", emoji="🪸",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(TIDE_POOL_PANEL_ID)),
            PanelActionSpec(
                action_id="st_dock", label="Dock", emoji="⚓",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(DOCK_PANEL_ID)),
            PanelActionSpec(
                action_id="st_boathouse", label="Boathouse", emoji="🛖",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(BOATHOUSE_PANEL_ID)),
            PanelActionSpec(
                action_id="st_fishery", label="Fishery", emoji="🐟",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(FISHERY_PANEL_ID)),
            PanelActionSpec(
                action_id="st_menu", label="↩ Fishing menu",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("fishing.render_structures_hub"),
        justification=(
            "the shipped sub-hub embed renders every coral structure's "
            "LIVE status at a glance (views/fishing/structures_hub.py "
            "build_structures_embed: one field per structure whose value "
            "interpolates the player's built level, its max and the "
            "level's bonus — `**Reef Pool** (1/3) — +4% pull toward "
            "rarer fish`), read-parameterized state outside the static "
            "TextBlock/FieldsBlock vocabulary, plus the shipped literal "
            "footer outside FooterMode's vocabulary. The renderer "
            "patches only the embed fields + footer; every component "
            "stays grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("st_tidepool", "st_dock", "st_boathouse", "st_fishery"),
            ("st_menu",),)),)),
    )


async def _render_structure(spec: PanelSpec, ctx, structure_key: str,
                            emoji: str, maxed_line: str,
                            bonus_text) -> object:
    """renderer_override body shared by the four structure panels —
    views/fishing/*.py ``build_*_embed`` verbatim (note="" — the open
    path; the Build click replies a result card instead of editing in
    place, the farm in-place-edit under-port precedent): grammar render
    + the live Level / Current bonus / Next-or-Maxed fields + the
    Build/Structures footer. A fresh player reads no row → level 0 →
    the bytes the matching golden pins."""
    from sb.domain.mining import structures, workshop
    from sb.domain.mining.store import get_structures
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    built = await get_structures(uid, gid)
    level = built.get(structure_key, 0)
    fields: list[tuple[str, str]] = [
        ("Level",
         f"**{structures.level_name(structure_key, level)}** "
         f"({level}/{structures.max_level(structure_key)})"),
        ("Current bonus", bonus_text(level)),
    ]
    cost = structures.build_cost(structure_key, level)
    if cost is None:
        fields.append(("Maxed", maxed_line))
        footer = "↩ Structures"
    else:
        nxt = structures.level_name(structure_key, level + 1)
        fields.append((
            f"Next: {nxt} → {bonus_text(level + 1)}",
            f"{workshop.describe_materials(cost.materials)} + "
            f"**{cost.coins}** 🪙"))
        footer = f"{emoji} Build  •  ↩ Structures"
    embed = _dc_replace(rendered.embed, fields=tuple(fields),
                        footer=footer)
    return _dc_replace(rendered, embed=embed)


async def _render_tide_pool(spec: PanelSpec, ctx) -> object:
    from sb.domain.mining import structures

    return await _render_structure(
        spec, ctx, structures.TIDE_POOL, "🪸",
        "Your Tide Pool is at its highest level — casts pull their "
        "best.", _tide_pool_bonus_text)


async def _render_dock(spec: PanelSpec, ctx) -> object:
    from sb.domain.mining import structures

    return await _render_structure(
        spec, ctx, structures.DOCK, "⚓",
        "Your Dock is at its highest level — the bite is as quick as "
        "it gets.", _dock_bonus_text)


async def _render_boathouse(spec: PanelSpec, ctx) -> object:
    from sb.domain.mining import structures

    return await _render_structure(
        spec, ctx, structures.BOATHOUSE, "🛖",
        "Your Boathouse is at its highest level — energy refills as "
        "fast as it gets.", _boathouse_bonus_text)


async def _render_fishery(spec: PanelSpec, ctx) -> object:
    from sb.domain.mining import structures

    return await _render_structure(
        spec, ctx, structures.FISHERY, "🐟",
        "Your Fishery is at its highest level — double catches as "
        "often as it gets.", _fishery_bonus_text)


def _structure_status_line(structure_key: str, level: int,
                           bonus_text) -> str:
    """views/fishing/structures_hub.py ``_*_line`` verbatim — one status
    line per structure: bold built name, (level/max), the bonus (or
    "not built yet" at level 0)."""
    from sb.domain.mining import structures

    bonus = bonus_text(level)
    if bonus == "no bonus yet":
        bonus = "not built yet"
    name = structures.level_name(structure_key, level)
    return (f"**{name}** ({level}/{structures.max_level(structure_key)})"
            f" — {bonus}")


async def _render_structures_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — structures_hub.py's ``build_structures_embed``
    verbatim (see justification): grammar render + the four live status
    fields + the shipped literal footer."""
    from sb.domain.mining import structures
    from sb.domain.mining.store import get_structures
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    built = await get_structures(uid, gid)
    fields = (
        ("🪸 Tide Pool",
         _structure_status_line(structures.TIDE_POOL,
                                built.get(structures.TIDE_POOL, 0),
                                _tide_pool_bonus_text)),
        ("⚓ Dock",
         _structure_status_line(structures.DOCK,
                                built.get(structures.DOCK, 0),
                                _dock_bonus_text)),
        ("🛖 Boathouse",
         _structure_status_line(structures.BOATHOUSE,
                                built.get(structures.BOATHOUSE, 0),
                                _boathouse_bonus_text)),
        ("🐟 Fishery",
         _structure_status_line(structures.FISHERY,
                                built.get(structures.FISHERY, 0),
                                _fishery_bonus_text)),
    )
    embed = _dc_replace(
        rendered.embed, fields=fields,
        footer=("🪸 Tide Pool  •  ⚓ Dock  •  🛖 Boathouse  •  "
                "🐟 Fishery  •  ↩ Fishing menu"))
    return _dc_replace(rendered, embed=embed)


@panel(CAST_PANEL_ID)
def _cast_factory() -> PanelSpec:
    return cast_spec()


@panel(LOG_PANEL_ID)
def _log_factory() -> PanelSpec:
    return log_spec()


@panel(HUB_PANEL_ID)
def _hub_factory() -> PanelSpec:
    return fishing_hub_spec()


@panel(CARD_PANEL_ID)
def _card_factory() -> PanelSpec:
    return fishing_card_spec()


@panel(ROD_PANEL_ID)
def _rod_factory() -> PanelSpec:
    return rod_shop_spec()


@panel(ROD_RECIPES_PANEL_ID)
def _rod_recipes_factory() -> PanelSpec:
    return rod_recipes_spec()


@panel(BAIT_PANEL_ID)
def _bait_factory() -> PanelSpec:
    return bait_shop_spec()


@panel(STRUCTURES_PANEL_ID)
def _structures_hub_factory() -> PanelSpec:
    return structures_hub_spec()


@panel(TIDE_POOL_PANEL_ID)
def _tide_pool_factory() -> PanelSpec:
    return tide_pool_spec()


@panel(DOCK_PANEL_ID)
def _dock_factory() -> PanelSpec:
    return dock_spec()


@panel(BOATHOUSE_PANEL_ID)
def _boathouse_factory() -> PanelSpec:
    return boathouse_spec()


@panel(FISHERY_PANEL_ID)
def _fishery_factory() -> PanelSpec:
    return fishery_spec()


_FACTORIES = (
    (CAST_PANEL_ID, _cast_factory),
    (LOG_PANEL_ID, _log_factory),
    (HUB_PANEL_ID, _hub_factory),
    (CARD_PANEL_ID, _card_factory),
    (ROD_PANEL_ID, _rod_factory),
    (ROD_RECIPES_PANEL_ID, _rod_recipes_factory),
    (BAIT_PANEL_ID, _bait_factory),
    (STRUCTURES_PANEL_ID, _structures_hub_factory),
    (TIDE_POOL_PANEL_ID, _tide_pool_factory),
    (DOCK_PANEL_ID, _dock_factory),
    (BOATHOUSE_PANEL_ID, _boathouse_factory),
    (FISHERY_PANEL_ID, _fishery_factory),
)

_RENDERS = (
    ("fishing.render_cast", _render_cast),
    ("fishing.render_log", _render_log),
    ("fishing.render_hub", _render_hub),
    ("fishing.render_card", _render_card),
    ("fishing.render_rod_shop", _render_rod_shop),
    ("fishing.render_rod_recipes", _render_rod_recipes),
    ("fishing.render_bait_shop", _render_bait_shop),
    ("fishing.render_structures_hub", _render_structures_hub),
    ("fishing.render_tp_structure", _render_tide_pool),
    ("fishing.render_dk_structure", _render_dock),
    ("fishing.render_bh_structure", _render_boathouse),
    ("fishing.render_fy_structure", _render_fishery),
)


def install_fishing_panels() -> tuple[PanelSpec, ...]:
    out = []
    for build in (cast_spec, log_spec, fishing_hub_spec, fishing_card_spec,
                  rod_shop_spec, rod_recipes_spec, bait_shop_spec,
                  structures_hub_spec, tide_pool_spec, dock_spec,
                  boathouse_spec, fishery_spec):
        spec = build()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def _register_renders() -> None:
    for name, fn in _RENDERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _register_renders()
    for panel_id, factory in _FACTORIES:
        if not is_registered(_P(panel_id)):
            _panel(panel_id)(factory)


_register_renders()
