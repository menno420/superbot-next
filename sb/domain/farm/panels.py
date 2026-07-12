"""Farm panels (band 6 / parity flip) — the SHIPPED surfaces byte-for-byte:

* ``farm.hub`` — disbot/views/farm/menu.py ``FarmMenuView`` +
  ``build_farm_embed``: the 🐔 Chicken Farm embed (GAME_COLOR purple,
  the around-the-clock description, the three LIVE fields — Coop
  bar/worth/fill · Flock · Coop level — and the balance footer literal)
  over the three shipped buttons (Collect 🥚 success · Shop 🛒 primary ·
  Refresh 🔄 secondary) and the shipped standard nav row (📚 Help +
  ↩ Games — ``home_hub="games"`` explicit, the creature/casino
  precedent). ``parity/goldens/farm/sweep_farm.json`` pins every byte:
  run-minted ``<cid:N>`` button ids (timeout session view ⇒
  ``session_lifecycle=True``, no ``panel_anchors`` row), emoji as
  SEPARATE wire fields next to the labels (trap 15a), the literal
  ``nav:help`` / ``nav:hub:games`` slots riding through the mint, and
  the fresh-farmer read (1 starter hen · 0 eggs · level-0 coop ·
  balance 0) with NO ``chicken_farm``/``economy_balances`` row minted —
  the open is a PLAIN read (the shipped ``!balance`` no-ensure
  precedent, trap 14e; ``store.get_farm`` returns starter defaults
  row-less).

* ``farm.shop`` — disbot/views/farm/menu.py ``FarmShopView`` +
  ``build_shop_embed``: the 🛒 Farm Shop sub-panel (the coin sinks —
  Buy hen 🐔 primary · Upgrade coop 🏠 secondary · Back ◀ secondary)
  with the live 🐔 Next hen / 🏠 Coop upgrade price fields and the
  ``Balance: N 🪙`` footer. No golden clicks the Shop button (the hub's
  ``<cid:N>`` session ids are not reconstructable by imported click
  steps), so no golden pins the shop bytes — the surfaces above are the
  oracle reconstruction verbatim.

Trap-24 drift check (farm row): the oracle current-head fragments
(views/farm/menu.py build_farm_embed description/fields/footer +
FarmMenuView/FarmShopView button decorators; utils/idle_summary.py
format_duration + its own test pins; utils/ui_constants.py GAME_COLOR)
match the corpus golden byte-for-byte — NO drift (corpus sha 7f7628e1).

Under-port ledger (no golden pins these corners):
* the shipped hub buttons EDITED the panel message in place
  (``interaction.response.edit_message`` — ``_redraw``/``_redraw_shop``
  with a flash line above the embed); the port opens result cards and
  child panels as fresh sends (the creature/karma/casino open lane).
* the shipped redraw path narrated the idle gap ("while you were away…"
  via utils/idle_summary) as the flash line — a redraw-only surface
  riding the same in-place-edit lane, ported with it.

MONEY-RACE NOTE (#217 / coordinator ruling 2026-07-12): this module is
render-only — every read here is the PLAIN (unlocked) ``get_farm`` /
``get_coins`` read. The FOR UPDATE + advisory-lock shapes live in
sb/domain/farm/store.py ``get_farm(for_update=True)`` and are composed
ONLY by the K7 money legs (sb/domain/farm/ops.py); this flip does not
touch them.
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
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    WorkflowRef,
    handler,
    is_registered,
    panel,
)

__all__ = [
    "HUB_PANEL_ID",
    "SHOP_PANEL_ID",
    "ensure_panel_refs",
    "farm_hub_spec",
    "farm_shop_spec",
    "install_farm_panels",
]

HUB_PANEL_ID = "farm.hub"
SHOP_PANEL_ID = "farm.shop"

#: views/farm/menu.py build_farm_embed description, verbatim (the golden
#: pins the rendered bytes).
_HUB_DESCRIPTION = (
    "Your hens lay eggs around the clock — even while you're away. "
    "Press **Collect** to cash them in, then visit the **Shop** to grow."
)

#: views/farm/menu.py build_shop_embed description, verbatim.
_SHOP_DESCRIPTION = (
    "Spend your egg coins to grow the farm:\n\n"
    "**🐔 Buy hen** — one more hen lays eggs faster.\n"
    "**🏠 Upgrade coop** — hold more eggs so idle progress banks longer.\n\n"
    "Prices rise as your farm grows."
)


def _format_duration(seconds: int) -> str:
    """utils/idle_summary.py ``format_duration`` verbatim — the oracle's
    own test pins the vocabulary (tests/unit/utils/test_idle_summary.py:
    ``-5 → "now"``, ``45 → "45s"``, ``65 → "1m 05s"``, ``125 → "2m 05s"``,
    ``3600 → "1h 00m"``, ``3780 → "1h 03m"``); the golden pins the
    fresh-farmer fill ``"1h 40m"`` (6000s)."""
    if seconds <= 0:
        return "now"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


def farm_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=HUB_PANEL_ID,
        subsystem="farm",
        title="🐔 Chicken Farm",
        audience=Audience.INVOKER,
        # GAME_COLOR purple (10181046, utils/ui_constants.py); the three
        # live fields + the balance footer ride the override (see
        # justification).
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_HUB_DESCRIPTION),),
        actions=(
            PanelActionSpec(
                action_id="farm_collect", label="Collect", emoji="🥚",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=WorkflowRef("farm.collect")),
            PanelActionSpec(
                action_id="farm_shop", label="Shop", emoji="🛒",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef(SHOP_PANEL_ID)),
            PanelActionSpec(
                action_id="farm_refresh", label="Refresh", emoji="🔄",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID),
                result_render=ResultRender.REFRESH_PANEL),
        ),
        # the shipped standard nav row: 📚 Help + the hub-named home
        # button "↩ Games" (nav:help / nav:hub:games — both pinned by
        # the golden); home_hub explicit, the creature/casino precedent.
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("farm.render_hub"),
        justification=(
            "two shipped surfaces sit outside the grammar's vocabulary "
            "(goldens/farm/sweep_farm pins both): (1) the three FIELDS "
            "interpolate the invoker's LIVE settled farm state — the "
            "Coop egg-bar/worth/fill-countdown line, the Flock hen "
            "count/lay rate, the Coop level/capacity — with the shipped "
            "inline flags (false/true/true), read-parameterized state "
            "outside the static TextBlock/FieldsBlock vocabulary "
            "(FieldsBlock renders inline=False 2-tuples only; the "
            "creature 'Your progress' precedent); (2) the FOOTER "
            "interpolates the invoker's live coin balance ('Balance: 0 "
            "🪙  ·  🥚 Collect · 🛒 Shop', views/farm/menu.py "
            "build_farm_embed) — outside FooterMode's vocabulary (the "
            "casino/community precedent). Title, description, color and "
            "every component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("farm_collect", "farm_shop", "farm_refresh"),)),)),
    )


def farm_shop_spec() -> PanelSpec:
    return PanelSpec(
        panel_id=SHOP_PANEL_ID,
        subsystem="farm",
        title="🛒 Farm Shop",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_SHOP_DESCRIPTION),),
        actions=(
            PanelActionSpec(
                action_id="farm_buy_hen", label="Buy hen", emoji="🐔",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=WorkflowRef("farm.buy_chicken")),
            PanelActionSpec(
                action_id="farm_upgrade_coop", label="Upgrade coop",
                emoji="🏠", style=ActionStyle.SECONDARY,
                audience_tier="user",
                handler=WorkflowRef("farm.upgrade_coop")),
            PanelActionSpec(
                action_id="farm_shop_back", label="Back", emoji="◀",
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=PanelRef(HUB_PANEL_ID)),
        ),
        # FarmShopView is a HubView sibling of the menu view — the same
        # standard nav row rides along.
        navigation=NavigationSpec(show_help=True, show_home=True,
                                  home_hub="games"),
        renderer_override=HandlerRef("farm.render_shop"),
        justification=(
            "the shipped shop embed carries two LIVE price fields "
            "(views/farm/menu.py build_shop_embed: '🐔 Next hen' — "
            "price + '(own N)' or 'maxed'; '🏠 Coop upgrade' — price + "
            "'→ holds N' or 'maxed'; both inline) and the 'Balance: N "
            "🪙' footer — read-parameterized state outside the static "
            "grammar vocabulary and FooterMode's set (the farm.hub "
            "sibling justification). Title, description, color and "
            "every component stay grammar-rendered."),
        session_lifecycle=True,
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("farm_buy_hen", "farm_upgrade_coop", "farm_shop_back"),)),)),
    )


async def _read_farm(ctx) -> tuple[object, int, int]:
    """(settled FarmState, now, balance) — the PLAIN (unlocked) panel
    read set: ``get_farm`` without ``for_update`` (starter defaults for a
    row-less farmer — the golden pins 1 hen/0 eggs/level 0 with no
    ``chicken_farm`` row) + the no-ensure ``get_coins`` read (balance 0,
    no ``economy_balances`` row — the shipped ``!balance`` posture).
    ``now`` reads the SYSTEM_CLOCK seam (the ONE wall-clock seam the
    parity harness pins, D-0060); the fresh-farmer bytes are
    time-independent (``eggs_updated_at=0`` ⇒ accrual starts now)."""
    from sb.domain.economy.store import get_coins
    from sb.domain.farm import core, store
    from sb.kernel.workflow.context import SYSTEM_CLOCK

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    now = int(SYSTEM_CLOCK().timestamp())
    chickens, eggs, ts, coop = await store.get_farm(uid, gid)
    # zero timestamp = uninitialized: accrual starts NOW, never from 1970
    # (the shipped free-full-coop closure, ops._stored twin).
    settled = core.settle(core.FarmState(chickens, eggs, ts or now, coop),
                          now)
    balance = await get_coins(uid, gid)
    return settled, now, balance


async def _render_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live fields and
    balance footer (views/farm/menu.py build_farm_embed, verbatim; see
    justification)."""
    from sb.domain.farm import core
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    settled, now, balance = await _read_farm(ctx)
    cap = core.coop_capacity(settled.coop_level)
    rate = core.lay_rate_per_hour(settled.chickens)
    pending_value = core.collect_value(settled.eggs)
    if settled.eggs >= cap:
        fill = "**full!**"
    else:
        fill = ("fills in "
                f"{_format_duration(core.seconds_until_full(settled, now))}")
    embed = _dc_replace(
        rendered.embed,
        fields=(
            ("Coop",
             f"{core.egg_bar(settled.eggs, cap)}\n"
             f"Worth **{pending_value}** 🪙 · {fill}"),
            ("Flock",
             f"🐔 **{settled.chickens}** hen(s) · **{rate}** eggs/hr",
             True),
            ("Coop level",
             f"🏠 **{settled.coop_level}** · holds **{cap}** eggs",
             True),
        ),
        footer=f"Balance: {balance} 🪙  ·  🥚 Collect · 🛒 Shop")
    return _dc_replace(rendered, embed=embed)


async def _render_shop(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped live price fields
    and balance footer (views/farm/menu.py build_shop_embed, verbatim)."""
    from sb.domain.farm import core
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    settled, _now, balance = await _read_farm(ctx)
    if core.can_buy_chicken(settled.chickens):
        hen = (f"**{core.chicken_price(settled.chickens)}** 🪙 "
               f"(own {settled.chickens})")
    else:
        hen = "maxed"
    if core.can_upgrade_coop(settled.coop_level):
        coop = (f"**{core.coop_upgrade_price(settled.coop_level)}** 🪙 "
                f"→ holds {core.coop_capacity(settled.coop_level + 1)}")
    else:
        coop = "maxed"
    embed = _dc_replace(
        rendered.embed,
        fields=(("🐔 Next hen", hen, True),
                ("🏠 Coop upgrade", coop, True)),
        footer=f"Balance: {balance} 🪙")
    return _dc_replace(rendered, embed=embed)


@panel(HUB_PANEL_ID)
def _hub_factory() -> PanelSpec:
    return farm_hub_spec()


@panel(SHOP_PANEL_ID)
def _shop_factory() -> PanelSpec:
    return farm_shop_spec()


_FACTORIES = (
    (HUB_PANEL_ID, _hub_factory),
    (SHOP_PANEL_ID, _shop_factory),
)

_RENDERS = (
    ("farm.render_hub", _render_hub),
    ("farm.render_shop", _render_shop),
)


def install_farm_panels() -> tuple[PanelSpec, ...]:
    out = []
    for build in (farm_hub_spec, farm_shop_spec):
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
