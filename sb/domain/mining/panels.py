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
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "CARD_PANEL_ID",
    "HUB_PANEL_ID",
    "PACK_SOFT_CAP",
    "ensure_panel_refs",
    "install_mining_panels",
    "mining_card_spec",
    "mining_hub_spec",
]

HUB_PANEL_ID = "mining.hub"
CARD_PANEL_ID = "mining.card"

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


def _pending_button_handlers() -> dict[str, HandlerRef]:
    """Pending terminals for the hub's D-0043 sub-surfaces — registered
    at IMPORT (module bottom), never ensure-only (#111 doctrine)."""
    from sb.domain.operator_spine import pending_handler

    return {
        "grid": pending_handler(
            "mining.grid_view_pending",
            "⛏️ The grid Mine navigator needs the mining world-grid "
            "system — " + _D0043_TAIL),
        "how_to": pending_handler(
            "mining.how_to_pending",
            "📖 The mining How-to guide rides the deep-system hub port — "
            + _D0043_TAIL),
    }


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
                handler=HandlerRef("mining.grid_view_pending"),
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
                handler=HandlerRef("mining.workshop_pending"),
                custom_id_override="mining:workshop"),
            PanelActionSpec(
                action_id="mi_how_to", label="📖 How-to",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=HandlerRef("mining.how_to_pending"),
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


@panel(CARD_PANEL_ID)
def _card_factory() -> PanelSpec:
    return mining_card_spec()


def _register_refs() -> None:
    from sb.spec.refs import handler

    _pending_button_handlers()
    if not is_registered(HandlerRef("mining.render_hub")):
        handler("mining.render_hub")(_render_hub)
    if not is_registered(HandlerRef("mining.render_card")):
        handler("mining.render_card")(_render_card)
    if not is_registered(PanelRef(HUB_PANEL_ID)):
        panel(HUB_PANEL_ID)(_hub_factory)
    if not is_registered(PanelRef(CARD_PANEL_ID)):
        panel(CARD_PANEL_ID)(_card_factory)


def install_mining_panels() -> tuple[PanelSpec, ...]:
    out = []
    for spec in (mining_hub_spec(), mining_card_spec()):
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
