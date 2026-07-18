"""Mining hub panel (band 6 / parity flip) — the SHIPPED surface
byte-for-byte: disbot/views/mining/main_panel.py ``MiningHubView`` +
its hub embed builder (the Option A six-button declutter + How-to).

``parity/goldens/mining/sweep_minemenu.json`` pins every byte: the
shipped PERSISTENT ``mining:<action>`` custom_ids (``custom_id_override``
on the ANCHORED open — the golden pins a ``panel_anchors`` row, so NO
``session_lifecycle``; static ids render straight through, the
games/community override lane), emoji IN the label (the shipped
decorator ``label="⛏️ Mine"`` form — trap 15a's in-label flavor), the
MINING_COLOR dark-grey embed (6323595, utils/ui_constants.py), the
``_ACTIONS_GUIDE`` description, the five INLINE live-overview fields
(📍 Location · 🧰 Tool · 💡 Light · 💰 Wealth · 🎒 Pack), the shared
invoker-lock footer literal, and the standard nav row (📚 Help +
↩ Games — ``home_hub="games"`` explicit, the farm/creature precedent).

Trap-24 drift check (mining row): the oracle current-head fragments
(views/mining/main_panel.py title f-string + _ACTIONS_GUIDE +
field builders `📍 Location`/`🧰 Tool`/`💡 Light`/`💰 Wealth`/`🎒 Pack`
+ pack "{used}/{cap} item types"; utils/mining/world.py
describe_position + BIOME maps; utils/ui_constants.py MINING_COLOR
dark_grey) match the corpus golden byte-for-byte — NO drift (corpus sha
7f7628e1).

Shipped click semantics (no mining golden drives a click): Harvest ran
the chop lane (REAL — routed to the ported ``mining.chop_route``);
Explore opened the open-world hub (REAL — ``games.world``); Mine opened
the grid navigator and Character/Gear/Workshop/How-to opened their
sub-hubs — all D-0043 deep-system surfaces, routed to honest pending
terminals (registered at import — never ensure-only, #111 doctrine).

Under-port ledger (no golden pins these corners):
* 🧰 Tool / 💡 Light render the shipped ``_gear_line`` EMPTY state
  ("—") unconditionally — the equipment/wear system (equipped slots +
  durability bars) is D-0043; the golden pins exactly "—".
* 💰 Wealth sums the resource/fish sell values only — the shipped
  ``items.total_value`` also valued tools/gear/treasures (the item
  catalog is D-0043); the golden pins the empty-pack **0**.
* the shipped pack/vault warning nudge lines (``capacity.pack_warning``)
  append only near the soft cap — unpinned, D-0043.
* the shipped hub buttons EDITED the panel message in place
  (``safe_edit`` redraws); the port opens result cards / child panels as
  fresh sends (the farm/creature open lane).

MONEY-RACE NOTE (#217 / coordinator ruling 2026-07-12): this module is
render-only — every read is the PLAIN (unlocked) ``get_mining_inventory``
/ ``get_depth`` read. The FOR UPDATE shapes live in
sb/domain/mining/store.py and are composed ONLY by the sell/sell_all/buy
K7 legs (sb/domain/mining/ops.py); this module touches none of them.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
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
    "CARD_PANEL_ID",
    "HUB_PANEL_ID",
    "GRID_PANEL_ID",
    "HOWTO_PANEL_ID",
    "VAULT_PANEL_ID",
    "FORGE_PANEL_ID",
    "SKILLS_PANEL_ID",
    "TITLES_PANEL_ID",
    "WORKSHOP_PANEL_ID",
    "HOME_PANEL_ID",
    "PACK_SOFT_CAP",
    "ensure_panel_refs",
    "install_mining_panels",
    "mining_card_spec",
    "mining_hub_spec",
    "mining_grid_spec",
    "mining_howto_spec",
    "mining_vault_spec",
    "mining_forge_spec",
    "mining_skills_spec",
    "mining_titles_spec",
    "mining_workshop_spec",
    "mining_home_spec",
]

HUB_PANEL_ID = "mining.hub"
GRID_PANEL_ID = "mining.grid"
HOWTO_PANEL_ID = "mining.howto"
CARD_PANEL_ID = "mining.card"
VAULT_PANEL_ID = "mining.vault"
FORGE_PANEL_ID = "mining.forge"
SKILLS_PANEL_ID = "mining.skills"
TITLES_PANEL_ID = "mining.titles"
WORKSHOP_PANEL_ID = "mining.workshop"
HOME_PANEL_ID = "mining.home"

#: the shipped shared author-locked nav-view footer literal (the
#: games/farm/community `_PANEL_FOOTER`).
_PANEL_FOOTER = "Only you can interact with this panel."

#: views/mining/main_panel.py ``_ACTIONS_GUIDE``, verbatim (the golden
#: pins the rendered description bytes).
_ACTIONS_GUIDE = (
    "**⛏️ Mine** — dig for ore, move between depths, explore for events\n"
    "**🌲 Harvest** — chop wood\n"
    "**🗺️ Explore** — the open-world explorer (fishing, roam, quests — "
    "early)\n"
    "**🧍 Character** — you: overview · inventory · stats · skills · "
    "vault · home\n"
    "**🧰 Gear** — equip your best tools, lights, and combat gear\n"
    "**🔨 Workshop** — craft & build · repair · 🔥 forge · 🛒 market "
    "(all here)\n"
    "**📖 How-to** — new here? the whole mining loop on one screen"
)

#: the shipped ``capacity.PACK_SOFT_CAP`` (the 🎒 Pack field's "/40" —
#: goldens/mining/sweep_minemenu pins the byte).
PACK_SOFT_CAP = 40

#: the shipped ``_gear_line`` empty state (no item in the slot) — the
#: only state the pre-equipment port can be in (D-0043).
_GEAR_EMPTY = "—"

_D0043_TAIL = ("the deep mining port is named successor work (D-0043); "
               "the core loop (mine/chop/explore/sell/buy) is live.")

#: The hub's two D-0043 pending terminals are RETIRED (curation rework
#: rows 59/60, PR #434): ⛏️ Mine routes to the live grid navigator panel
#: (``mining.grid`` — the ported (x, y, z) world) and 📖 How-to to the
#: static guide panel (``mining.howto``). The retired refs
#: ``mining.grid_view_pending`` / ``mining.how_to_pending`` no longer
#: register (trap 12a).

#: the shipped navigator footer literal (views/mining/grid_mine_view.py
#: ``set_footer``, verbatim).
_GRID_FOOTER = ("Each ⛏️ dig moves you one cell and mines it · "
                "only you can use this.")

#: views/mining/how_to_panel.py ``_HOW_TO``, verbatim (the one-screen
#: "how mining works" onboarding guide — completion-cert punch-list #1).
_HOW_TO = (
    "New to mining? Here's the whole loop in one screen.\n\n"
    "**1. ⛏️ Mine** — open the grid and roam the underground with the "
    "movement buttons, then **Mine here** to dig the ore under you. Deeper "
    "depths hold richer ore (and need a better 💡 light to see — grab a "
    "torch, then a lantern).\n"
    "**2. 🌲 Harvest** — chop wood, the basic crafting material. No tools "
    "needed.\n"
    "**3. 🧰 Gear** — equip your best tool, light, and combat gear. "
    "**Equip Best** does it in one click; matching set pieces give a "
    "bonus.\n"
    "**4. 🔨 Workshop** — turn raw resources into better gear and "
    "structures: **Craft** (build it), **Repair** (worn tools), "
    "**🔥 Forge** (gates the top gear tiers), **🛒 Market** (buy/sell).\n"
    "**5. 🧍 Character** — everything about you: **Inventory** · "
    "**Stats** · **🌳 Skills** (spend points to specialize) · **🏦 Vault** "
    "(stash loot safely, off your pack) · **🏠 Home**.\n\n"
    "**Watch your 🎒 pack** — it holds a limited number of *item types*; "
    "sell or vault what you don't need. **Watch durability** — tools wear "
    "down and break; repair or re-craft them at the Workshop. Level up by "
    "mining and harvesting to unlock deeper ladders and skill points."
)

#: dig-button action_id → the grid direction token it digs (the oracle
#: D-pad: N row 0 · W/E row 1 · S row 2 · Deeper/Up row 3).
_GRID_DIRECTIONS = {
    "gr_north": "north",
    "gr_west": "west",
    "gr_east": "east",
    "gr_south": "south",
    "gr_down": "down",
    "gr_up": "up",
}


def _message_key(req) -> str:
    """The clicked panel message's engine session key (the settings
    access-explorer recipe — engine keys sessions by str(message_ref))."""
    message = getattr(req.origin, "message", None)
    return str(getattr(message, "id", "") or "")


#: Per-navigator-message roaming state — lateral (x, y) + the fog-of-war
#: visited set per depth band, keyed by the panel message id (the settings
#: `_ACCESS_SESSIONS` precedent: engine ephemeral bindings freeze opening
#: args, so running UI state lives domain-side). SESSION-SCOPED BY
#: NECESSITY tonight, not by design: the durable oracle shape
#: (mining_player_state pos_x/pos_y + the mining_discovered table) is
#: parity-walled — new columns on the row-covered mining_player_state
#: change the row shape goldens/mining/mining_use_ration_restore_write
#: snapshots, and a new declared table needs a parity.yml depth-exemption
#: row (both parity.yml operations, the wp-stack lane's file). Until that
#: graduation lands, a navigator open starts at (0, 0) of your PERSISTED
#: depth with fresh fog (the pre-grid shipped baseline); loot, energy,
#: depth, wear and XP are fully durable through the audited op.
_GRID_SESSIONS: dict[str, dict] = {}
_GRID_SESSIONS_MAX = 512


def _grid_state(key: str) -> dict:
    state = _GRID_SESSIONS.setdefault(
        key, {"x": 0, "y": 0, "discovered": {}})
    while len(_GRID_SESSIONS) > _GRID_SESSIONS_MAX:
        _GRID_SESSIONS.pop(next(iter(_GRID_SESSIONS)))
    return state


def _grid_params(state: dict, depth: int, note: str, tone: str) -> dict:
    """The renderer params for one navigator re-render: the running
    session position + the CURRENT band's visited cells + the dig note."""
    discovered = state["discovered"].get(depth, set())
    return {"grid_note": note, "grid_tone": tone,
            "grid_x": state["x"], "grid_y": state["y"],
            "grid_discovered": tuple(discovered)}


async def _grid_note(req, note: str, tone: str, params: dict | None = None):
    """Re-render the navigator IN PLACE with *note* (the oracle
    ``safe_edit`` loop via ``refresh_session_view``); a refresh miss
    (restart/eviction) degrades to an honest text reply (the settings
    access-explorer posture). ``tone`` maps to the shipped colors:
    success=green, error=red, else MINING_COLOR dark grey."""
    from sb.kernel.interaction.handler_kit import Reply
    from sb.kernel.panels.engine import refresh_session_view
    from sb.spec.outcomes import SUCCESS

    key = _message_key(req)
    if key:
        try:
            if await refresh_session_view(
                    req, message_key=key,
                    params=dict(params or {"grid_note": note,
                                           "grid_tone": tone})):
                return Reply(SUCCESS, None)  # the edit IS the ack
        except Exception:  # noqa: BLE001 — degrade to the text reply
            pass
    return Reply(SUCCESS, note)


async def _grid_dig(req, direction: str):
    """One directional dig click — pure-read gates first (shipped hint
    copy; a blocked dig writes nothing and audits nothing — the
    record_descend guard posture), then the audited ``mining.dig`` op,
    then the in-place re-render with the oracle note composition."""
    import time as _time

    from sb.domain.mining import character, energy, grid, store, world
    from sb.kernel.interaction.handler_kit import ctx_from_request
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import WorkflowRef

    uid = int(getattr(req.actor, "user_id", 0) or 0)
    gid = int(getattr(req, "guild_id", 0) or 0)
    state = _grid_state(_message_key(req))

    now = int(_time.time())
    depth = await store.get_depth(uid, gid)
    e_state = energy.EnergyState(*await store.get_energy(uid, gid))
    if not energy.can_dig(e_state, now):
        wait = energy.seconds_until(e_state, now, energy.DIG_COST)
        return await _grid_note(
            req,
            "⚡ You're out of energy — rest a moment "
            f"(~{wait}s until your next dig) or eat a **ration** / "
            "**energy drink** (`!use ration`).",
            "error",
            _grid_params(state, depth,
                         "⚡ You're out of energy — rest a moment "
                         f"(~{wait}s until your next dig) or eat a "
                         "**ration** / **energy drink** (`!use ration`).",
                         "error"))
    if direction in grid.VERTICAL:
        if direction == grid.DOWN:
            equipped = await store.get_equipment(uid, gid)
            alloc = await store.get_skills(uid, gid)
            stats = character.character_stats(equipped, alloc)
            if world.descend(depth, stats) == depth:
                hint = world.descend_hint(stats)
                return await _grid_note(
                    req, hint, "error",
                    _grid_params(state, depth, hint, "error"))
        elif world.ascend(depth) == depth:
            hint = "You're already at the Surface — nowhere up to dig."
            return await _grid_note(
                req, hint, "error",
                _grid_params(state, depth, hint, "error"))

    result = await engine.run(
        WorkflowRef("mining.dig"),
        ctx_from_request(req, {"direction": direction,
                               "x": state["x"], "y": state["y"]}))
    if result.outcome != SUCCESS:
        hint = result.user_message or "You can't dig that way."
        return await _grid_note(
            req, hint, "error", _grid_params(state, depth, hint, "error"))
    after = next(iter((result.after or {}).values()), {})
    # commit the session move + fog mark (the durable writes landed in the
    # op's txn; x/y/fog are session state — see _GRID_SESSIONS).
    state["x"] = int(after.get("x", state["x"]))
    state["y"] = int(after.get("y", state["y"]))
    new_depth = int(after.get("depth", depth))
    state["discovered"].setdefault(new_depth, set()).add(
        (state["x"], state["y"]))
    parts = [f"You dig **{grid.move_phrase(direction)}** and mine "
             f"**{after.get('amount', 0)}× {after.get('found', '')}**!"]
    if after.get("cell_note"):
        parts.append(str(after["cell_note"]))
    parts.extend(str(n) for n in (after.get("wear_notes") or ()))
    if after.get("xp_note"):
        parts.append(str(after["xp_note"]))
    if after.get("pack_warning"):
        parts.append(str(after["pack_warning"]))
    note = "\n".join(parts)
    return await _grid_note(req, note, "success",
                            _grid_params(state, new_depth, note, "success"))


def _grid_button_handlers() -> None:
    """The navigator's six dig handlers — registered at IMPORT (module
    bottom), never ensure-only (#111 doctrine)."""
    from sb.spec.refs import handler as _handler

    def _dig_handler(direction: str):
        async def _route(req):
            return await _grid_dig(req, direction)
        return _route

    for action_id, direction in _GRID_DIRECTIONS.items():
        ref = HandlerRef(f"mining.{action_id}")
        if not is_registered(ref):
            _handler(ref.name)(_dig_handler(direction))


def mining_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=HUB_PANEL_ID,
        subsystem="mining",
        # the override appends the shipped "— {display name}" suffix.
        title="⛏️ Mining Hub",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py);
        # the five live fields + the footer literal ride the override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_ACTIONS_GUIDE),),
        actions=(
            # K1 claims action_ids bare and repo-global — the mi_ prefix
            # keeps the namespace clean (wire bytes are the overrides).
            PanelActionSpec(
                action_id="mi_mine", label="⛏️ Mine",
                style=ActionStyle.PRIMARY, audience_tier="user",
                # rework row 59: the live grid navigator (label/style/
                # custom_id untouched — byte-neutral vs sweep_minemenu).
                handler=PanelRef(GRID_PANEL_ID),
                custom_id_override="mining:mine"),
            PanelActionSpec(
                action_id="mi_harvest", label="🌲 Harvest",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.chop_route"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="mining:harvest"),
            PanelActionSpec(
                action_id="mi_explore_hub", label="🗺️ Explore",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("games.world"),
                custom_id_override="mining:explore_hub"),
            PanelActionSpec(
                action_id="mi_character", label="🧍 Character",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("mining.character_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="mining:character"),
            PanelActionSpec(
                action_id="mi_gear", label="🧰 Gear",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.gear_view"),
                result_render=ResultRender.RESULT_CARD,
                custom_id_override="mining:gear"),
            PanelActionSpec(
                action_id="mi_workshop", label="🔨 Workshop",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef(WORKSHOP_PANEL_ID),
                custom_id_override="mining:workshop"),
            PanelActionSpec(
                action_id="mi_how_to", label="📖 How-to",
                style=ActionStyle.SECONDARY, audience_tier="user",
                # rework row 60: the live static How-to guide (label/
                # style/custom_id untouched — byte-neutral).
                handler=PanelRef(HOWTO_PANEL_ID),
                custom_id_override="mining:how_to"),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_hub"),
        justification=(
            "three shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/mining/sweep_minemenu pins all three): (1) the "
            "TITLE interpolates the invoker's display name ('⛏️ Mining "
            "Hub — {name}', views/mining/main_panel.py title f-string — "
            "read through the guild-directory port, the world-card "
            "precedent); (2) the five FIELDS interpolate the invoker's "
            "LIVE overview — 📍 Location (depth band), 🧰 Tool / "
            "💡 Light (gear lines), 💰 Wealth (inventory net worth), "
            "🎒 Pack (type count vs soft cap) — all with the shipped "
            "inline=True flags, read-parameterized state outside the "
            "static TextBlock/FieldsBlock vocabulary (the farm 'Coop' "
            "precedent); (3) the FOOTER is the shared invoker-lock "
            "literal 'Only you can interact with this panel.' — outside "
            "FooterMode's vocabulary (the games/community/casino "
            "precedent). Description, color and every component stay "
            "grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("mi_mine", "mi_harvest", "mi_explore_hub"),
            ("mi_character", "mi_gear", "mi_workshop"),
            ("mi_how_to",),
        )),)),
    )


def mining_grid_spec() -> PanelSpec:
    """The grid Mine navigator (views/mining/grid_mine_view.py
    ``MineGridView`` + ``build_grid_embed``, curation rework rows 45/59) —
    an ephemeral (session) child of the mining hub: the oracle D-pad
    verbatim (⛏️ North row 0 · ⛏️ West/⛏️ East row 1 · ⛏️ South row 2 ·
    ⛏️ Deeper/⛏️ Up row 3 · ↩ Mining Menu + 📚 Help row 4; primary
    laterals, success verticals, the shipped 120s timeout), the live
    position/energy/map embed on a renderer override. Every dig button
    routes to its ``mining.gr_*`` handler → the audited ``mining.dig`` op
    → an IN-PLACE re-render (``refresh_session_view`` — the shipped
    ``safe_edit`` loop). No golden drives the navigator (the capture-world
    open RAISED — goldens/mining/sweep_mine pins the artifact byte on the
    prefix lane, still carried by ``mining.mine_route``)."""
    return PanelSpec(
        panel_id=GRID_PANEL_ID,
        subsystem="mining",
        title="⛏️ Mine",
        audience=Audience.INVOKER,
        # MINING_COLOR dark grey; the shipped footer literal + the live
        # description/fields ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock("Roam the underground — every ⛏️ dig moves you "
                        "one cell and mines it."),),
        session_lifecycle=True,
        timeout_s=120,
        actions=(
            PanelActionSpec(
                action_id="gr_north", label="⛏️ North",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.gr_north")),
            PanelActionSpec(
                action_id="gr_west", label="⛏️ West",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.gr_west")),
            PanelActionSpec(
                action_id="gr_east", label="⛏️ East",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.gr_east")),
            PanelActionSpec(
                action_id="gr_south", label="⛏️ South",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.gr_south")),
            PanelActionSpec(
                action_id="gr_down", label="⛏️ Deeper",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.gr_down")),
            PanelActionSpec(
                action_id="gr_up", label="⛏️ Up",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.gr_up")),
            PanelActionSpec(
                action_id="gr_menu", label="↩ Mining Menu",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped row 4: ↩ Mining Menu (the gr_menu action above) +
        # 📚 Help (the engine nav:help slot); no ↩ Games home — the oracle
        # navigator carried none.
        navigation=NavigationSpec(show_help=True, show_home=False),
        renderer_override=HandlerRef("mining.render_grid"),
        justification=(
            "the shipped navigator embed is fully live-state-parameterized "
            "(views/mining/grid_mine_view.py build_grid_embed): the "
            "note+describe_cell DESCRIPTION, the 📍 Depth / 🧭 Position / "
            "⚡ Energy / 🌐 World seed inline FIELDS, the fog-of-war 🗺️ Map "
            "code block + legend, the dig-note COLOR swap (MINING/SUCCESS/"
            "ERROR — the shipped _rerender color parameter, rendered as the "
            "green/red style tokens), and the shipped footer literal — all "
            "read-parameterized state outside the static TextBlock/"
            "FieldsBlock vocabulary (the mining hub/home live-overview "
            "precedent). Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("gr_north",),
            ("gr_west", "gr_east"),
            ("gr_south",),
            ("gr_down", "gr_up"),
            ("gr_menu",),
        )),)),
    )


def mining_howto_spec() -> PanelSpec:
    """The 📖 How-to guide (views/mining/how_to_panel.py
    ``MiningHowToView`` + ``build_how_to_embed``, curation rework row 60)
    — a STATIC one-screen onboarding card (the ``_HOW_TO`` copy verbatim)
    with the shipped ↩ Mining Hub back button; an ephemeral (session)
    child of the hub (the mining.home lifecycle). Only the shipped
    invoker-lock footer literal rides the renderer override."""
    return PanelSpec(
        panel_id=HOWTO_PANEL_ID,
        subsystem="mining",
        title="📖 How mining works",
        audience=Audience.INVOKER,
        # MINING_COLOR dark grey; the footer literal rides the override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_HOW_TO),),
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="hw_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the oracle How-to carried ONLY its back button (HubView added no
        # nav slots to this child) — no help, no home.
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("mining.render_howto"),
        justification=(
            "one shipped surface sits outside the grammar's vocabulary: the "
            "FOOTER is the shared invoker-lock literal 'Only you can "
            "interact with this panel.' (build_how_to_embed set_footer) — "
            "outside FooterMode's vocabulary (the mining-hub/games/"
            "community precedent). Title, description, color and the back "
            "button stay grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("hw_hub",),
        )),)),
    )


def mining_card_spec() -> PanelSpec:
    """The generic one-embed reply card (the shipped ``ctx.send(embed=…)``)
    — the ai.card/karma.card pattern for the mining read views
    (``!market`` / ``!minestats``)."""
    return PanelSpec(
        panel_id=CARD_PANEL_ID,
        subsystem="mining",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("mining.render_card"),
        justification=(
            "the shipped `!market` / `!minestats` replies are fully "
            "live-state-parameterized embeds built in the handler "
            "(mining_cog.py market_cmd's shop/sellables listing + dynamic "
            "balance footer; the stats command's location/level/net-worth "
            "fields — goldens/mining/sweep_market + sweep_minestats pin "
            "the bytes). Zero components; the renderer presents the "
            "handler-built RenderedEmbed verbatim (the ai.card/karma.card "
            "precedent)."),
    )


async def _render_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — present the handler-built embed verbatim (the
    ai.card ``_render_card`` shape). When the handler set an ``_attachment``
    filename (the shipped ``!gear`` / ``!character`` paper-doll sends), the
    card carries a single ``RenderedAttachment`` — the parity transport
    collapses the whole payload to ``{"_files": [filename]}`` (the
    multipart-serializer information loss, goldens/mining/sweep_gear +
    sweep_character; the PNG bytes are never compared)."""
    from sb.kernel.panels.render import (
        RenderedAttachment,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    embed = params.get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    filename = params.get("_attachment")
    attachments = ((RenderedAttachment(filename=str(filename)),)
                   if filename else ())
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, attachments=attachments,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# The 🏦 Vault panel's 📥 Deposit / 📤 Withdraw modal forms (G-10 ModalSpec —
# the treasury Contribute precedent, sb/domain/treasury/panels.py). The shipped
# _VaultMoveModal (views/mining/vault_panel.py) carried one item field + one
# amount field (default "1"); the submit re-enters the frozen MODAL adapter and
# runs the SAME audited move op the LIVE `!stash` / `!unstash` command lane
# carries (mining.stash / mining.unstash — record_stash / record_unstash), so
# the deposit/withdraw write stays byte-pinned by mining_stash_write /
# mining_unstash_write. The vault-move ops take the item VERBATIM (lowercased)
# — sb mining carries no vault-item fuzzy resolver, the accepted sb divergence
# from the oracle's resolve_item_name (the same posture the `!stash`/`!unstash`
# routes already ship). No golden drives a vault-panel click and the parity
# harness cannot drive a modal submit, so this terminal is unpinned (covered by
# unit tests); the MODAL-defer button renders identical session <cid:N> wire
# bytes (sweep_vault stays byte-clean).
VAULT_DEPOSIT_MODAL = ModalSpec(
    modal_id="mining.vault_deposit_form",
    title="Deposit into Vault",              # shipped verb ("Deposit into" + " Vault")
    fields=(
        ModalFieldSpec(
            field_id="item", label="Item name",
            placeholder="e.g. diamond, iron, lucky charm",
            required=True, max_length=100),
        ModalFieldSpec(
            field_id="qty", label="Amount", placeholder="how many",
            required=False, default="1", max_length=9),
    ),
    on_submit=HandlerRef("mining.vault_deposit_route"),
)

VAULT_WITHDRAW_MODAL = ModalSpec(
    modal_id="mining.vault_withdraw_form",
    title="Withdraw from Vault",             # shipped verb ("Withdraw from" + " Vault")
    fields=(
        ModalFieldSpec(
            field_id="item", label="Item name",
            placeholder="e.g. diamond, iron, lucky charm",
            required=True, max_length=100),
        ModalFieldSpec(
            field_id="qty", label="Amount", placeholder="how many",
            required=False, default="1", max_length=9),
    ),
    on_submit=HandlerRef("mining.vault_withdraw_route"),
)


def mining_forge_spec() -> PanelSpec:
    """The shipped 🔥 Forge panel (views/mining/forge_panel.py ``MiningForgeView``
    + ``build_forge_embed``) — an ephemeral (session) child of the mining hub:
    the two buttons mint session `<cid:N>` ids, and the live built-level /
    unlocked-tiers / next-cost embed rides a renderer override
    (goldens/mining/sweep_forge.json pins every byte: the MINING_COLOR dark-grey
    frame, the Level / Unlocks / Next fields, the build-prompt footer, the
    🔥 Build + ↩ Workshop row and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=FORGE_PANEL_ID,
        subsystem="mining",
        title="🔥 Forge",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + build-prompt footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="fo_build", label="🔥 Build",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.forge_build_route")),
            PanelActionSpec(
                action_id="fo_workshop", label="↩ Workshop",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(WORKSHOP_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_forge"),
        justification=(
            "the shipped `!forge` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/forge_panel.py "
            "build_forge_embed: the Level `{level_name} ({level}/{max})` line, "
            "the Unlocks tiers list, the Next-cost field "
            "`{materials} + {coins} 🪙`, and the built/maxed footer — "
            "goldens/mining/sweep_forge.json pins the not-built bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / vault live-overview precedent). Every "
            "component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("fo_build", "fo_workshop"),
        )),)),
    )


async def _render_forge(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live forge embed
    (built-level line, unlocked-tiers list, next-build cost / maxed state, and
    the build-prompt footer; see justification). Reads get_structures → the
    forge's built level (a fresh player reads level 0 off the store's no-row
    default → the not-built card goldens/mining/sweep_forge.json pins)."""
    from sb.domain.mining import store, structures, workshop
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    built = await store.get_structures(uid, gid)
    level = built.get(structures.FORGE, 0)
    fields: list[tuple[str, str, bool]] = [
        ("Level",
         f"**{structures.forge_level_name(level)}** "
         f"({level}/{structures.MAX_FORGE_LEVEL})", False)]
    unlocked = structures.tiers_unlocked_at(level)
    unlocked_text = ", ".join(t.title() for t in unlocked) if unlocked else "—"
    fields.append((
        "Unlocks (beyond free tiers)",
        f"{unlocked_text}\nBronze · Iron · Silver gear, tools, and structures "
        "craft without a forge.", False))
    cost = structures.forge_build_cost(level)
    if cost is None:
        fields.append((
            "Maxed",
            "Your forge is at its highest level — it unlocks every gear tier.",
            False))
        footer = "↩ Mining Hub"
    else:
        nxt = structures.forge_level_name(level + 1)
        nxt_tiers = structures.tiers_unlocked_at(level + 1)
        gain = [t for t in nxt_tiers if t not in unlocked]
        gain_text = f" → unlocks **{gain[-1]}-tier** gear" if gain else ""
        fields.append((
            f"Next: {nxt}{gain_text}",
            f"{workshop.describe_materials(cost.materials)} + "
            f"**{cost.coins}** 🪙", False))
        footer = "🔥 Build  •  ↩ Mining Hub"
    embed = _dc_replace(rendered.embed, title="🔥 Forge",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


def _skills_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminal for the skill-tree panel's per-branch spend button — the
    point spend rides the deferred panel port (D-0043); the LIVE command lane
    `!skill <branch>` is the named successor for the audited allocate. The ♻
    Respec button is LIVE as of WP-7 (``mining.skill_respec_route`` ->
    mining.respec -> record_respec, the ported skill_service.respec), so its
    pending registration is retired (the forge/home 🔥 Build precedent).
    Registered at IMPORT (module bottom), never ensure-only (#111 doctrine)."""
    from sb.domain.operator_spine import pending_handler

    return {
        "spend": pending_handler(
            "mining.skill_spend_pending",
            "🌳 Spending a skill point from the panel rides the deep-system "
            "panel port (D-0043) — spend now with `!skill <branch>` (mining, "
            "combat, fortune, crafting)."),
    }


def mining_skills_spec() -> PanelSpec:
    """The shipped 🌳 Skill Tree panel (views/mining/skills_panel.py
    ``MiningSkillsView`` + ``build_skills_embed``) — an ephemeral (session)
    child of the mining hub: the four branch buttons + ♻ Respec / 🏆 Titles /
    ↩ Mining Hub mint session `<cid:N>` ids, and the live points / per-branch
    allocation embed rides a renderer override (goldens/mining/sweep_skills.json
    pins every byte: the MINING_COLOR dark-grey frame, the Points field, the four
    branch fields, the respec-cost footer, the 2×(4,3) button rows and the
    standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=SKILLS_PANEL_ID,
        subsystem="mining",
        title="🌳 Skill Tree",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + respec-cost footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="sk_mining", label="⛏️ Mining",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_combat", label="⚔️ Combat",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_fortune", label="🍀 Fortune",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_crafting", label="🛠️ Crafting",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.skill_spend_pending")),
            PanelActionSpec(
                action_id="sk_respec", label="♻ Respec",
                style=ActionStyle.DANGER, audience_tier="user",
                handler=HandlerRef("mining.skill_respec_route")),
            PanelActionSpec(
                action_id="sk_titles", label="🏆 Titles",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=PanelRef(TITLES_PANEL_ID)),
            PanelActionSpec(
                action_id="sk_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_skills"),
        justification=(
            "the shipped `!skills` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/skills_panel.py "
            "build_skills_embed: the Points `{avail} available · {spent} spent` "
            "line + the `Game level {level}` cap note, the four branch "
            "`{blurb}  ({points}/{cap})` fields with their describe_stats "
            "previews, and the `♻ Respec refunds all for {cost} 🪙` footer — "
            "goldens/mining/sweep_skills.json pins the fresh-player bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / vault / forge live-overview "
            "precedent). Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("sk_mining", "sk_combat", "sk_fortune", "sk_crafting"),
            ("sk_respec", "sk_titles", "sk_hub"),
        )),)),
    )


async def _render_skills(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live skill-tree embed
    (points line, per-branch allocation + describe_stats preview, respec-cost
    footer; see justification). Reads the shared game level + get_skills → a
    fresh player reads level 0 / no allocation → the 0-available card
    goldens/mining/sweep_skills.json pins."""
    from sb.domain.games.xp import shared_level
    from sb.domain.mining import equipment as _eq
    from sb.domain.mining import skills, store
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    level, _ = await shared_level(uid, gid)
    alloc = await store.get_skills(uid, gid)
    spent = skills.total_spent(alloc)
    avail = max(0, min(level, skills.SOFT_TOTAL_CAP) - spent)
    fields: list[tuple[str, str, bool]] = [
        ("Points",
         f"**{avail}** available · {spent} spent\n"
         f"Game level **{level}** (points cap at **{skills.SOFT_TOTAL_CAP}** "
         "— you can't max every branch, so specialize).", False)]
    for branch in skills.BRANCHES:
        points = alloc.get(branch, 0)
        bonus = _eq.describe_stats(skills.branch_stats(branch, points))
        bonus_text = ", ".join(f"+{v} {label}" for label, v in bonus) or "—"
        fields.append(
            (f"{skills.BRANCH_LABELS[branch]}  "
             f"({points}/{skills.PER_BRANCH_CAP})", bonus_text, False))
    footer = ("Tap a branch to spend a point  •  "
              f"♻ Respec refunds all for {skills.respec_cost(level)} 🪙")
    embed = _dc_replace(rendered.embed, title="🌳 Skill Tree",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


#: the oracle's clear-choice sentinel (views/mining/titles_panel.py
#: ``_NONE_VALUE`` verbatim) — the select's "(none)" option value.
_TITLE_NONE_VALUE = "__none__"

#: the earned-title select options provider id (registered at import in
#: _register_refs).
_TITLES_SELECT_OPTIONS = "mining.titles_select_options"


def _ensure_titles_select_provider() -> ProviderRef:
    """The 🏆 Titles panel select's rich options — the shipped
    ``views/mining/titles_panel.py`` ``_TitleSelect`` rows verbatim: the
    leading ``(none)`` clear option (description "Display no title",
    default when nothing is equipped), then the player's EARNED titles in
    catalogue order (label / value / emoji, default on the equipped one).
    Earned titles are DERIVED from skills / max-depth / level; a player
    with NO earned titles returns () and the renderer override drops the
    component entirely (the shipped view only adds ``_TitleSelect`` when
    ``earned`` is non-empty — goldens/mining/sweep_titles.json pins the
    fresh-player selectless bytes). Max 1 + 9 = 10 options (9-title
    catalogue), under Discord's 25 cap — plain select, no windowing."""
    ref = ProviderRef(_TITLES_SELECT_OPTIONS)
    if not is_registered(ref):
        @provider(_TITLES_SELECT_OPTIONS)
        async def titles_select_options(ctx: object):
            from sb.domain.games.xp import shared_level
            from sb.domain.mining import store, titles

            uid = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                      or 0)
            gid = int(getattr(ctx, "guild_id", 0) or 0)
            alloc = await store.get_skills(uid, gid)
            max_depth = await store.get_max_depth(uid, gid)
            level, _ = await shared_level(uid, gid)
            tctx = titles.TitleContext(skills=alloc, max_depth=max_depth,
                                       level=level)
            earned = titles.earned_titles(tctx)
            if not earned:
                return ()
            equipped = titles.get_title(
                await store.get_equipped_title(uid, gid))
            equipped_id = (equipped.id if equipped is not None
                           and titles.is_earned(equipped.id, tctx)
                           else None)
            options: list[dict] = [{
                "label": "(none)", "value": _TITLE_NONE_VALUE,
                "description": "Display no title",
                "default": equipped_id is None,
            }]
            for t in earned:
                options.append({"label": t.label, "value": t.id,
                                "emoji": t.emoji,
                                "default": t.id == equipped_id})
            return tuple(options)
    return ref


def mining_titles_spec() -> PanelSpec:
    """The shipped 🏆 Titles panel (views/mining/titles_panel.py
    ``MiningTitlesView`` + ``build_titles_embed``) — an ephemeral (session)
    child of the skill-tree panel: the earned-title display select +
    ↩ Mining Hub button mint session `<cid:N>` ids, and the live
    equipped/earned/locked embed rides a renderer override
    (goldens/mining/sweep_titles.json pins every byte: the MINING_COLOR
    dark-grey frame, the Equipped + 🔒 Locked (9) fields, the earn-guidance footer,
    the single ↩ Mining Hub button and the standard nav row 📚 Help + ↩ Games).

    A fresh player has NO earned titles, so the earned-title display Select (the
    equip WRITE lane) is ABSENT from the view — the shipped ``create`` only adds
    ``_TitleSelect`` when ``earned`` is non-empty; the renderer override drops
    the empty-provider component to keep that shape (the fresh-player golden
    stays byte-identical). A pick routes through ``mining.titles_pick`` into
    the audited ``mining.equip_title`` / ``mining.unequip_title`` ops
    (title-equip write slice — the D-0043 pending retired). Below the 4-action
    auto-exempt sim floor (1 action), so no legacy-seed overlay is needed."""
    return PanelSpec(
        panel_id=TITLES_PANEL_ID,
        subsystem="mining",
        title="🏆 Titles",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live equipped/earned/locked fields ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        selectors=(
            # the shipped _TitleSelect (row 0): pick an earned title to
            # display, or clear it — placeholder verbatim.
            SelectorSpec(
                selector_id="ti_select", kind=SelectorKind.ENTITY,
                on_select=HandlerRef("mining.titles_pick"),
                options_source=_ensure_titles_select_provider(),
                placeholder="Choose a title to display…",
                empty_state="Choose a title to display…",
                audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="ti_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_titles"),
        justification=(
            "the shipped `!titles` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/titles_panel.py "
            "build_titles_embed: the Equipped title line, the optional "
            "`Earned ({n})` list, and the `🔒 Locked ({n})` list of "
            "`{emoji} {label} — {requirement}` lines derived from the player's "
            "skills / max-depth / level — goldens/mining/sweep_titles.json pins "
            "the fresh-player Equipped `— none —` + 🔒 Locked (9) bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / skills-panel live-overview precedent). "
            "Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ti_select",),
            ("ti_hub",),
        )),)),
    )


async def _titles_pick(req):
    """`mining.titles_pick` — the shipped ``_TitleSelect.callback``: the
    ``(none)`` sentinel clears via the audited ``mining.unequip_title`` op,
    any other value equips via ``mining.equip_title`` (validation + copy
    live in the leg, title_service verbatim), then the panel re-renders IN
    PLACE with the oracle note composition — ``("✅ " if ok else "❌ ") +
    message`` as the embed description, SUCCESS green / ERROR red frame
    (the `build_titles_embed(note=…)` + `embed.color` bytes). A refresh
    miss (restart/eviction) degrades to an honest text reply (the grid
    `_grid_note` posture)."""
    from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
    from sb.kernel.panels.engine import refresh_session_view
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import WorkflowRef

    values = tuple(req.args.get("values", ()) or ())
    choice = str(values[0]) if values else ""
    if choice == _TITLE_NONE_VALUE:
        result = await engine.run(WorkflowRef("mining.unequip_title"),
                                  ctx_from_request(req, {}))
    else:
        result = await engine.run(WorkflowRef("mining.equip_title"),
                                  ctx_from_request(req,
                                                   {"title_id": choice}))
    if result.outcome == SUCCESS:
        after = next(iter((result.after or {}).values()), {})
        note = "✅ " + str(after.get("message", ""))
        tone = "success"
    else:
        note = "❌ " + str(result.user_message or "")
        tone = "error"
    key = _message_key(req)
    if key:
        try:
            if await refresh_session_view(
                    req, message_key=key,
                    params={"titles_note": note, "titles_tone": tone}):
                return Reply(SUCCESS, None)  # the edit IS the ack
        except Exception:  # noqa: BLE001 — degrade to the text reply
            pass
    return Reply(SUCCESS, note)


async def _render_titles(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live titles embed
    (equipped title, optional earned list, locked list with earn requirements;
    see justification). Earned titles are DERIVED from the player's skills /
    max-depth / level (sb/domain/mining/titles.py) — a fresh player earns none →
    Equipped `— none —` + all 9 locked, the bytes goldens/mining/sweep_titles.json
    pins — and the earned-title select is DROPPED entirely (the shipped
    ``create`` adds ``_TitleSelect`` only when ``earned`` is non-empty; the
    drop happens BEFORE session-id minting, so the fresh-player `<cid:N>`
    numbering is unchanged). The equipped title is gated on still being earned
    (a post-respec choice silently un-displays). An equip re-render carries
    its note + color in the params (``titles_note``/``titles_tone`` — the
    refresh_session_view lane, the grid ``grid_note`` recipe; the shipped
    ``build_titles_embed(note=…)`` description + SUCCESS/ERROR color)."""
    from sb.domain.games.xp import shared_level
    from sb.domain.mining import store, titles
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    note = str(ctx.params.get("titles_note", "") or "")
    tone = str(ctx.params.get("titles_tone", "") or "")
    alloc = await store.get_skills(uid, gid)
    max_depth = await store.get_max_depth(uid, gid)
    level, _ = await shared_level(uid, gid)
    tctx = titles.TitleContext(skills=alloc, max_depth=max_depth, level=level)
    earned = titles.earned_titles(tctx)
    equipped = titles.get_title(await store.get_equipped_title(uid, gid))
    if equipped is not None and not titles.is_earned(equipped.id, tctx):
        equipped = None
    fields: list[tuple[str, str, bool]] = [
        ("Equipped",
         titles.display(equipped) if equipped else "— none —", False)]
    if earned:
        fields.append((
            f"Earned ({len(earned)})",
            "\n".join(titles.display(t) for t in earned), False))
    locked = tuple(t for t in titles.ALL_TITLES
                   if not titles.is_earned(t.id, tctx))
    if locked:
        fields.append((
            f"🔒 Locked ({len(locked)})",
            "\n".join(f"{t.emoji} {t.label} — {t.requirement}" for t in locked),
            False))
    footer = ("Earn titles by mastering skill branches, descending, and "
              "levelling up.")
    embed = _dc_replace(
        rendered.embed, title="🏆 Titles",
        description=note or rendered.embed.description,
        fields=tuple(fields), footer=footer,
        # the shipped note colors: SUCCESS green / ERROR red on an equip
        # result edit, MINING dark grey on the open (build_titles_embed).
        style_token={"success": "green",
                     "error": "red"}.get(tone, "dark_grey"))
    components = rendered.components
    if not earned:
        # no earned titles ⇒ no select AT ALL (the shipped view shape;
        # goldens/mining/sweep_titles.json pins the selectless bytes).
        components = tuple(c for c in components
                           if getattr(c, "kind", "") != "selector")
    return _dc_replace(rendered, embed=embed, components=components)


#: the craft-select options provider id (registered at import in _register_refs).
_WORKSHOP_CRAFT_OPTIONS = "mining.workshop_craft_options"


def _ensure_workshop_craft_provider() -> ProviderRef:
    """The Workshop craft select's rich options — the shipped
    ``views/mining/workshop_panel.py`` ``_CraftSelect`` rows verbatim: the
    equippable recipes annotated craftable-now, sorted (craftable-first, then
    name), the top 25 rendered as ``{Name} — {materials}`` (a ``✅`` emoji only
    when the player can craft it now). A fresh player owns nothing → all 39
    gear recipes are not-craftable → the first 25 alphabetically, no emoji
    (goldens/mining/sweep_workshop pins the 25 option bytes)."""
    ref = ProviderRef(_WORKSHOP_CRAFT_OPTIONS)
    if not is_registered(ref):
        @provider(_WORKSHOP_CRAFT_OPTIONS)
        async def workshop_craft_options(ctx: object):
            from sb.domain.mining import store, workshop
            from sb.domain.mining.recipes import load_recipes

            uid = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
            gid = int(getattr(ctx, "guild_id", 0) or 0)
            inventory = await store.get_mining_inventory(uid, gid)
            options = []
            for g in sorted(workshop.craftable_gear(load_recipes(), inventory),
                            key=lambda g: (not g.craftable, g.name)):
                opt = {
                    "label": (f"{g.name.title()} — "
                              f"{workshop.describe_materials(g.materials)}")[:100],
                    "value": g.name,
                }
                if g.craftable:
                    opt["emoji"] = "✅"
                options.append(opt)
            return tuple(options)
    return ref


def _workshop_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminal for the Workshop panel's deferred lane — the craft
    select's material→product write rides the deferred structures/panel port
    (D-0043); the LIVE lanes (`!repair`, `!quickcraft`, the 🔁 Quick-craft
    button) already carry the audited moves, and ↩ Workshop navigates to the
    live mining hub (its `workshop_hub_pending` terminal retired by the
    2026-07-13 curation rework). Registered at IMPORT (module bottom), never
    ensure-only (#111 doctrine). No golden drives a workshop click, so the
    terminal copy is unpinned."""
    from sb.domain.operator_spine import pending_handler

    return {
        "craft": pending_handler(
            "mining.workshop_craft_pending",
            "🛠️ Crafting gear from the dropdown rides the deep-system panel "
            "port (D-0043) — " + _D0043_TAIL),
    }


def mining_workshop_spec() -> PanelSpec:
    """The shipped 🔧 Workshop panel (views/mining/workshop_panel.py
    ``MiningWorkshopView`` + ``build_workshop_embed``) — an ephemeral (session)
    child of the mining hub: a provider-fed gear-craft select + 🔁 Quick-craft
    last broken + ↩ Workshop mint session `<cid:N>` ids, and the live
    equipped-gear / craftable-gear / balance embed rides a renderer override
    (goldens/mining/sweep_workshop.json pins every byte: the MINING_COLOR
    dark-grey frame, the 🧰 Equipped gear + 🛠️ Craft gear fields, the balance
    footer, the 25-option craft select, the disabled 🔁 Quick-craft + ↩ Workshop
    row, and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=WORKSHOP_PANEL_ID,
        subsystem="mining",
        title="🔧 Workshop",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + balance footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        selectors=(
            SelectorSpec(
                selector_id="ws_craft", kind=SelectorKind.ENTITY,
                on_select=HandlerRef("mining.workshop_craft_pending"),
                options_source=_ensure_workshop_craft_provider(),
                placeholder="Craft gear from resources…",
                empty_state="Craft gear from resources…",
                audience_tier="user"),
        ),
        actions=(
            PanelActionSpec(
                action_id="ws_quickcraft",
                label="🔁 Quick-craft last broken",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.quickcraft_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="ws_back", label="↩ Workshop",
                style=ActionStyle.SECONDARY, audience_tier="user",
                # back to the live mining hub (the sk_hub / vault / forge
                # back-button pattern; curation rework 2026-07-13 — the
                # pending sub-hub terminal retired, byte-neutral: session
                # panels mint <cid:N> ids, the golden pins label+style only).
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_workshop"),
        justification=(
            "the shipped `!workshop` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/workshop_panel.py "
            "build_workshop_embed: the 🧰 Equipped gear condition/repair lines, "
            "the 🛠️ Craft gear list + the `All {n} gear recipes` pointer, and "
            "the dynamic `Balance: {n} 🪙` footer — goldens/mining/"
            "sweep_workshop.json pins the fresh-player bytes), read-parameterized "
            "state outside the static TextBlock/FieldsBlock vocabulary (the "
            "mining hub / vault / forge live-overview precedent). The craft "
            "select's options ride the declared provider; the renderer patches "
            "only the embed and the 🔁 Quick-craft disabled flag (disabled with "
            "no last-broken item). Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ws_craft",),
            ("ws_quickcraft", "ws_back"),
        )),)),
    )


async def _render_workshop(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live workshop embed
    (equipped-gear condition/repair lines, craftable-gear list, balance footer;
    see justification) and the disabled-when-no-last-broken 🔁 Quick-craft
    button. A fresh player owns nothing / has nothing equipped / never broke a
    tool → `Nothing equipped yet.` + `▫️ Nothing craftable …` + `All 39 gear
    recipes` + `Balance: 0 🪙` and a DISABLED Quick-craft — the bytes
    goldens/mining/sweep_workshop.json pins."""
    from sb.domain.economy.store import get_coins
    from sb.domain.mining import equipment as _eq
    from sb.domain.mining import store, workshop
    from sb.domain.mining.recipes import load_recipes
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    inventory = await store.get_mining_inventory(uid, gid)
    equipped = await store.get_equipment(uid, gid)
    wear = await store.get_gear_wear(uid, gid)
    last_broken = await store.get_last_broken(uid, gid)
    balance = await get_coins(uid, gid)

    gear_lines: list[str] = []
    for slot in _eq.SLOTS:
        item = equipped.get(slot)
        if not item:
            continue
        maximum = _eq.max_durability(item)
        if maximum is None:
            gear_lines.append(f"**{item.title()}** — does not wear")
            continue
        remaining = wear.get(item, maximum)
        line = f"**{item.title()}** {workshop.durability_bar(remaining, maximum)}"
        cost = workshop.repair_cost(item, remaining)
        if cost is not None:
            line += f" — repair {cost} 🪙"
        gear_lines.append(line)
    fields: list[tuple[str, str, bool]] = [
        ("🧰 Equipped gear",
         "\n".join(gear_lines) if gear_lines else "Nothing equipped yet.",
         False)]
    if last_broken:
        fields.append((
            "💥 Last broken",
            f"**{last_broken.title()}** — hit 🔁 Quick-craft to replace it.",
            False))
    craftables = workshop.craftable_gear(load_recipes(), inventory)
    if craftables:
        ready = [g for g in craftables if g.craftable]
        lines = [f"✅ **{g.name.title()}** — "
                 f"{workshop.describe_materials(g.materials)}" for g in ready[:12]]
        if not ready:
            lines = ["▫️ Nothing craftable from your current resources."]
        lines.append(
            f"📖 All **{len(craftables)}** gear recipes: the Recipe browser "
            "(`!recipes`).")
        fields.append(("🛠️ Craft gear", "\n".join(lines), False))
    embed = _dc_replace(
        rendered.embed, title="🔧 Workshop", fields=tuple(fields),
        footer=(f"Balance: {balance} 🪙  •  !repair <item> · !craft <item> · "
                "!quickcraft"))
    components = tuple(
        _dc_replace(c, disabled=True)
        if (not last_broken
            and getattr(c, "custom_id", "").endswith(".ws_quickcraft"))
        else c
        for c in rendered.components)
    return _dc_replace(rendered, embed=embed, components=components)


def mining_home_spec() -> PanelSpec:
    """The shipped 🏠 Home panel (views/mining/home_panel.py ``MiningHomeView``
    + ``build_home_embed``) — an ephemeral (session) child of the mining hub:
    the 🏠 Build + ↩ Mining Hub buttons mint session `<cid:N>` ids, and the live
    built-level / backdrop-blurb / next-cost embed rides a renderer override
    (goldens/mining/sweep_home.json pins every byte: the MINING_COLOR dark-grey
    frame, the Level / What it does / Next fields, the build-prompt footer, the
    🏠 Build + ↩ Mining Hub row and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=HOME_PANEL_ID,
        subsystem="mining",
        title="🏠 Home",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + build-prompt footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="ho_build", label="🏠 Build",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.home_build_route")),
            PanelActionSpec(
                action_id="ho_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_home"),
        justification=(
            "the shipped `!home` reply is a fully live-state-parameterized embed "
            "built in the view (views/mining/home_panel.py build_home_embed: the "
            "Level `{level_name} ({level}/{max})` line, the cosmetic-backdrop "
            "blurb, and the Next-cost `{materials} + {coins} 🪙` field / maxed "
            "state — goldens/mining/sweep_home.json pins the not-built bytes), "
            "read-parameterized state outside the static TextBlock/FieldsBlock "
            "vocabulary (the mining hub / vault / forge live-overview precedent). "
            "Every component stays grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ho_build", "ho_hub"),
        )),)),
    )


async def _render_home(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live home embed
    (built-level line, cosmetic-backdrop blurb, next-build cost / maxed state,
    and the build-prompt footer; see justification). Reads get_structures → the
    Home's built level (a fresh player reads level 0 off the store's no-row
    default → the not-built card goldens/mining/sweep_home.json pins)."""
    from sb.domain.mining import store, structures, workshop
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    built = await store.get_structures(uid, gid)
    level = built.get(structures.HOME, 0)
    fields: list[tuple[str, str, bool]] = [
        ("Level",
         f"**{structures.level_name(structures.HOME, level)}** "
         f"({level}/{structures.MAX_HOME_LEVEL})", False),
        ("What it does",
         "A built Home gives your **Character card** a personalized backdrop "
         "— each level a richer one. Purely cosmetic.", False)]
    cost = structures.build_cost(structures.HOME, level)
    if cost is None:
        fields.append((
            "Maxed",
            "Your Home is at its grandest — the Grand Hall backdrop is yours.",
            False))
        footer = "↩ Mining Hub"
    else:
        nxt = structures.level_name(structures.HOME, level + 1)
        fields.append((
            f"Next: {nxt}",
            f"{workshop.describe_materials(cost.materials)} + "
            f"**{cost.coins}** 🪙", False))
        footer = "🏠 Build  •  ↩ Mining Hub"
    embed = _dc_replace(rendered.embed, title="🏠 Home",
                        fields=tuple(fields), footer=footer)
    return _dc_replace(rendered, embed=embed)


def mining_vault_spec() -> PanelSpec:
    """The shipped 🏦 Mining Vault panel (views/mining/vault_panel.py
    ``MiningVaultView`` + ``build_vault_embed``) — an ephemeral (session)
    child of the mining hub: the five move buttons mint session `<cid:N>`
    ids (never the anchored `mining:<x>` overrides the hub carries), and the
    live capacity/stored-value/empty-state embed rides a renderer override
    (goldens/mining/sweep_vault pins every byte: the MINING_COLOR dark-grey
    frame, the 📦 Capacity + empty-state fields, the stored-value footer, the
    2×2+1 button rows and the standard nav row 📚 Help + ↩ Games)."""
    return PanelSpec(
        panel_id=VAULT_PANEL_ID,
        subsystem="mining",
        title="🏦 Mining Vault",
        audience=Audience.INVOKER,
        # MINING_COLOR = discord.Color.dark_grey() (utils/ui_constants.py); the
        # live fields + stored-value footer ride the renderer override.
        frame=EmbedFrameSpec(style_token="dark_grey",
                             footer_mode=FooterMode.NONE),
        # ephemeral child → session-minted <cid:N> ids (no custom_id_override,
        # so no panel_anchors row — the shipped HubView child send).
        session_lifecycle=True,
        actions=(
            PanelActionSpec(
                action_id="va_deposit", label="📥 Deposit",
                style=ActionStyle.PRIMARY, audience_tier="user",
                defer_mode=DeferMode.MODAL, modal=VAULT_DEPOSIT_MODAL,
                handler=HandlerRef("mining.vault_deposit_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="va_withdraw", label="📤 Withdraw",
                style=ActionStyle.SECONDARY, audience_tier="user",
                defer_mode=DeferMode.MODAL, modal=VAULT_WITHDRAW_MODAL,
                handler=HandlerRef("mining.vault_withdraw_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="va_stash_all", label="📦 Stash All Ore",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("mining.stash_all_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="va_upgrade", label="⬆️ Upgrade",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("mining.vaultupgrade_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="va_hub", label="↩ Mining Hub",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # the shipped standard nav row: 📚 Help + "↩ Games"
        # (nav:help / nav:hub:games — both pinned by the golden).
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("mining.render_vault"),
        justification=(
            "the shipped `!vault` reply is a fully live-state-parameterized "
            "embed built in the view (views/mining/vault_panel.py "
            "build_vault_embed: the 📦 Capacity `{used}/{cap} item types "
            "(tier {level})` line, the empty-state / grouped-stored fields, "
            "and the dynamic `Stored value: {n}` footer — "
            "goldens/mining/sweep_vault pins the bytes), read-parameterized "
            "state outside the static TextBlock/FieldsBlock vocabulary (the "
            "mining hub's own live-overview precedent). Every component stays "
            "grammar-rendered."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("va_deposit", "va_withdraw"),
            ("va_stash_all", "va_upgrade"),
            ("va_hub",),
        )),)),
    )


async def _render_vault(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live vault embed
    (capacity line, empty-state / stored listing, stored-value footer; see
    justification). Stored value uses the resource/fish sell valuation (the
    same D-0043 item-catalog boundary the hub's 💰 Wealth field draws — the
    shipped ``items.total_value`` also valued tools/gear/treasure); the golden
    pins the empty-vault **0**. The grouped-by-kind listing rides the deferred
    item taxonomy, so a non-empty vault renders one flat 📦 Stored field."""
    from sb.domain.mining import capacity, market, store
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    vault = await store.get_vault(uid, gid)
    level = await store.get_vault_level(uid, gid)
    status = capacity.vault_status(vault, level)
    fields: list[tuple[str, str, bool]] = [
        ("📦 Capacity",
         f"{status.used}/{status.cap} item types (tier {level})", False)]
    nudge = capacity.vault_warning(status)
    if nudge:
        fields.append(("​", nudge, False))
    if not vault:
        fields.append((
            "Your vault is empty",
            "A vault is a **safe stash** for your loot, kept separate from "
            "your mining pack.\nUse **📥 Deposit** (or `!stash <item> [n]`) "
            "to tuck something away.", False))
    else:
        fields.append((
            "📦 Stored",
            "\n".join(f"**{name.title()}** ×{qty}"
                      for name, qty in sorted(vault.items())), False))
    stored_value = sum(qty * (market.sell_price(item) or 0)
                       for item, qty in vault.items())
    embed = _dc_replace(
        rendered.embed, title="🏦 Mining Vault", fields=tuple(fields),
        footer=(f"Stored value: {stored_value}  •  📥 Deposit · "
                "📤 Withdraw · 📦 Stash All Ore · ⬆️ Upgrade"))
    return _dc_replace(rendered, embed=embed)


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped display-name
    title, live overview fields and footer literal (see justification)."""
    from sb.domain.mining import market, store
    from sb.domain.mining.world import describe_position
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    inventory = await store.get_mining_inventory(uid, gid)
    depth = await store.get_depth(uid, gid)
    name = await _display_name(uid, gid)
    # shipped net worth: items.total_value — resource/fish values here;
    # tool/gear/treasure values ride the D-0043 item catalog (ledgered
    # above); the golden pins the empty-pack 0.
    worth = sum(qty * (market.sell_price(item) or 0)
                for item, qty in inventory.items())
    embed = _dc_replace(
        rendered.embed,
        title=f"⛏️ Mining Hub — {name}" if name else "⛏️ Mining Hub",
        fields=(
            ("📍 Location", describe_position(depth), True),
            ("🧰 Tool", _GEAR_EMPTY, True),
            ("💡 Light", _GEAR_EMPTY, True),
            ("💰 Wealth", f"Net worth: **{worth}**", True),
            ("🎒 Pack", f"{len(inventory)}/{PACK_SOFT_CAP} item types",
             True),
        ),
        footer=_PANEL_FOOTER)
    return _dc_replace(rendered, embed=embed)


async def _render_grid(spec: PanelSpec, ctx) -> object:
    """renderer_override — the navigator embed (build_grid_embed verbatim
    over the ported reads): position · current cell · fog-of-war map ·
    energy bar; a dig re-render carries its note + color in the params
    (``grid_note``/``grid_tone`` — the refresh_session_view lane)."""
    import time as _time

    from sb.domain.mining import character, energy, grid, store, world
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    note = str(ctx.params.get("grid_note", "") or "")
    tone = str(ctx.params.get("grid_tone", "") or "")

    depth = await store.get_depth(uid, gid)
    # Lateral position + fog ride the navigator session (the dig handlers
    # pass them through the refresh params; a fresh open starts at the
    # origin of the persisted depth band with fresh fog — see the
    # _GRID_SESSIONS parity-wall note).
    x = int(ctx.params.get("grid_x", 0) or 0)
    y = int(ctx.params.get("grid_y", 0) or 0)
    discovered = {(int(px), int(py))
                  for px, py in (ctx.params.get("grid_discovered") or ())}
    seed = await store.get_world_seed(gid)
    # A brighter equipped light widens the fog-of-war window (the shipped
    # BUG-0026 wiring): the same radius feeds the render window; a
    # light_radius of 0-1 keeps the default 2.
    equipped = await store.get_equipment(uid, gid)
    alloc = await store.get_skills(uid, gid)
    radius = grid.reveal_radius(
        character.character_stats(equipped, alloc).light_radius)
    cell = grid.cell_at(seed, x, y, depth)
    body = grid.render_local_map(seed, x, y, depth, discovered,
                                 radius=radius)
    description = grid.describe_cell(cell)
    if note:
        description = f"{note}\n\n{description}"

    e_cur, e_ts = await store.get_energy(uid, gid)
    e_now = energy.settle(energy.EnergyState(e_cur, e_ts),
                          int(_time.time())).current
    embed = _dc_replace(
        rendered.embed,
        title="⛏️ Mine",
        description=description,
        fields=(
            ("📍 Depth", world.describe_position(depth), True),
            ("🧭 Position", f"({x}, {y})", True),
            ("⚡ Energy", energy.bar(e_now), True),
            ("🌐 World seed", str(seed), True),
            ("🗺️ Map", f"```\n{body}\n```\n{grid.MAP_LEGEND}", False),
        ),
        footer=_GRID_FOOTER,
        # the shipped _rerender color parameter: SUCCESS green on a dig,
        # ERROR red on a blocked one, MINING dark grey on the open.
        style_token={"success": "green",
                     "error": "red"}.get(tone, "dark_grey"))
    return _dc_replace(rendered, embed=embed)


async def _render_howto(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped invoker-lock
    footer literal (build_how_to_embed set_footer; see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed,
                                         footer=_PANEL_FOOTER))


async def _display_name(user_id: int, guild_id: int) -> str:
    """Invoker display name through the guild-directory read port (the
    games world-card recipe); degrades to "" — the shipped no-name title
    branch, never invented data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
    except Exception:  # noqa: BLE001 — no directory ⇒ bare title
        return ""
    return member.tag.rsplit("#", 1)[0]


@panel(HUB_PANEL_ID)
def _hub_factory() -> PanelSpec:
    return mining_hub_spec()


@panel(GRID_PANEL_ID)
def _grid_factory() -> PanelSpec:
    return mining_grid_spec()


@panel(HOWTO_PANEL_ID)
def _howto_factory() -> PanelSpec:
    return mining_howto_spec()


@panel(CARD_PANEL_ID)
def _card_factory() -> PanelSpec:
    return mining_card_spec()


@panel(VAULT_PANEL_ID)
def _vault_factory() -> PanelSpec:
    return mining_vault_spec()


@panel(FORGE_PANEL_ID)
def _forge_factory() -> PanelSpec:
    return mining_forge_spec()


@panel(SKILLS_PANEL_ID)
def _skills_factory() -> PanelSpec:
    return mining_skills_spec()


@panel(TITLES_PANEL_ID)
def _titles_factory() -> PanelSpec:
    return mining_titles_spec()


@panel(WORKSHOP_PANEL_ID)
def _workshop_factory() -> PanelSpec:
    return mining_workshop_spec()


@panel(HOME_PANEL_ID)
def _home_factory() -> PanelSpec:
    return mining_home_spec()


def _register_refs() -> None:
    from sb.spec.refs import handler

    _grid_button_handlers()
    _skills_button_handlers()
    _workshop_button_handlers()
    _ensure_workshop_craft_provider()
    _ensure_titles_select_provider()
    if not is_registered(HandlerRef("mining.titles_pick")):
        handler("mining.titles_pick")(_titles_pick)
    if not is_registered(HandlerRef("mining.render_hub")):
        handler("mining.render_hub")(_render_hub)
    if not is_registered(HandlerRef("mining.render_grid")):
        handler("mining.render_grid")(_render_grid)
    if not is_registered(HandlerRef("mining.render_howto")):
        handler("mining.render_howto")(_render_howto)
    if not is_registered(HandlerRef("mining.render_card")):
        handler("mining.render_card")(_render_card)
    if not is_registered(HandlerRef("mining.render_vault")):
        handler("mining.render_vault")(_render_vault)
    if not is_registered(HandlerRef("mining.render_forge")):
        handler("mining.render_forge")(_render_forge)
    if not is_registered(HandlerRef("mining.render_skills")):
        handler("mining.render_skills")(_render_skills)
    if not is_registered(HandlerRef("mining.render_titles")):
        handler("mining.render_titles")(_render_titles)
    if not is_registered(HandlerRef("mining.render_workshop")):
        handler("mining.render_workshop")(_render_workshop)
    if not is_registered(HandlerRef("mining.render_home")):
        handler("mining.render_home")(_render_home)
    if not is_registered(PanelRef(HUB_PANEL_ID)):
        panel(HUB_PANEL_ID)(_hub_factory)
    if not is_registered(PanelRef(GRID_PANEL_ID)):
        panel(GRID_PANEL_ID)(_grid_factory)
    if not is_registered(PanelRef(HOWTO_PANEL_ID)):
        panel(HOWTO_PANEL_ID)(_howto_factory)
    if not is_registered(PanelRef(CARD_PANEL_ID)):
        panel(CARD_PANEL_ID)(_card_factory)
    if not is_registered(PanelRef(VAULT_PANEL_ID)):
        panel(VAULT_PANEL_ID)(_vault_factory)
    if not is_registered(PanelRef(FORGE_PANEL_ID)):
        panel(FORGE_PANEL_ID)(_forge_factory)
    if not is_registered(PanelRef(SKILLS_PANEL_ID)):
        panel(SKILLS_PANEL_ID)(_skills_factory)
    if not is_registered(PanelRef(TITLES_PANEL_ID)):
        panel(TITLES_PANEL_ID)(_titles_factory)
    if not is_registered(PanelRef(WORKSHOP_PANEL_ID)):
        panel(WORKSHOP_PANEL_ID)(_workshop_factory)
    if not is_registered(PanelRef(HOME_PANEL_ID)):
        panel(HOME_PANEL_ID)(_home_factory)


def install_mining_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (mining_hub_spec(), mining_grid_spec(), mining_howto_spec(),
                 mining_card_spec(), mining_vault_spec(),
                 mining_forge_spec(), mining_skills_spec(),
                 mining_titles_spec(), mining_workshop_spec(),
                 mining_home_spec()):
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


_register_refs()
