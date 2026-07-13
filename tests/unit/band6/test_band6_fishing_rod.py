"""Fishing depth slice 2 — the rod ladder: the ported rods module
(shipped ``utils/fishing/rods.py`` verbatim), the shared fish-spend
planner (``services/fishing_workflow.py`` verbatim), the ``!craftrod``
guard bytes (goldens/fishing/sweep_craftrod pins them), the rod-shop /
recipe-browser panel specs (goldens/fishing/sweep_rod + sweep_rodrecipes
pin the component trees), the new ``fishing_rod`` store spec + erasure
ref, and the manifest/hub route flips."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

run = asyncio.run

GID, P1 = 1, 42


@dataclass(frozen=True)
class _FakeReq:
    """The ResolveRequest subset these handlers touch — a dataclass so
    the handler lane's ``dataclasses.replace(req, args=…)`` works."""

    actor: object = field(
        default_factory=lambda: SimpleNamespace(user_id=P1,
                                                actor_type="user"))
    guild_id: int = GID
    channel_id: int = 2
    args: dict = field(default_factory=dict)
    origin: object = None
    request_id: str = "r1"
    surface: object = None


def _req(uid: int = P1, gid: int = GID, argv: tuple = ()):
    return _FakeReq(actor=SimpleNamespace(user_id=uid, actor_type="user"),
                    guild_id=gid, args={"argv": argv})


# --- the pure rods module (shipped verbatim) ---------------------------------------


def test_rod_ladder_verbatim_numbers():
    from sb.domain.fishing import rods

    assert rods.MAX_TIER == 4
    assert rods.STARTER is rods.ROD_LADDER[0]
    names = [(r.name, r.emoji, r.price) for r in rods.ROD_LADDER]
    assert names == [
        ("Bare Rod", "🎣", 0),
        ("Bronze Rod", "🥉", 250),
        ("Silver Rod", "🥈", 750),
        ("Gold Rod", "🥇", 2000),
        ("Diamond Rod", "💎", 5000),
    ]
    # the five sim-tuned knobs, tier by tier (utils/fishing/rods.py
    # ROD_LADDER verbatim)
    knobs = [(r.window_bonus, r.bite_speed, r.rarity_pull,
              r.escape_resist, r.premature_grace) for r in rods.ROD_LADDER]
    assert knobs == [
        (0.0, 1.00, 1.00, 0.00, 0.00),
        (0.4, 0.95, 1.10, 0.10, 0.15),
        (0.8, 0.88, 1.25, 0.22, 0.30),
        (1.2, 0.80, 1.45, 0.35, 0.45),
        (1.7, 0.70, 1.70, 0.50, 0.60),
    ]


def test_rod_helpers_and_recipes_verbatim():
    from sb.domain.fishing import rods

    assert rods.rod_for_tier(-3) is rods.STARTER
    assert rods.rod_for_tier(99).name == "Diamond Rod"
    assert rods.next_rod(0).tier == 1
    assert rods.next_rod(4) is None
    # ROD_RECIPES verbatim: 1:10≤6 · 2:16≤12 · 3:26≤18 · 4:40≤21
    shelf = {t: (r.fish_count, r.max_size_rank)
             for t, r in rods.ROD_RECIPES.items()}
    assert shelf == {1: (10, 6), 2: (16, 12), 3: (26, 18), 4: (40, 21)}
    assert rods.rod_recipe(0) is None
    assert rods.rod_recipe_text(rods.ROD_RECIPES[1]) == "10 fish (size ≤ 6)"


# --- the shared fish-spend planner (fishing_workflow verbatim) ---------------------


def test_plan_fish_spend_smallest_first_ties_by_name():
    from sb.domain.fishing import catalog, crafting, rods

    recipe = rods.ROD_RECIPES[1]        # 10 fish, size ≤ 6
    # pick real catalog species around the cutoff
    small = [s for s in catalog.SPECIES if s.size_rank <= 6]
    big = [s for s in catalog.SPECIES if s.size_rank > 6]
    assert small and big
    a = min(small, key=lambda s: (s.size_rank, s.name))
    z = max(small, key=lambda s: (s.size_rank, s.name))
    inventory = {a.name: 4, z.name: 20, big[0].name: 50, "not-a-fish": 9}
    assert crafting.eligible_fish_total(inventory, recipe) == 24
    spend = crafting.plan_fish_spend(inventory, recipe)
    # smallest rank drains first; the trophy-band fish are never touched
    assert spend == {a.name: 4, z.name: 6}
    assert big[0].name not in spend
    # short pack → None (the guard the golden pins)
    assert crafting.plan_fish_spend({a.name: 9}, recipe) is None


# --- !craftrod — the fresh-player guard (sweep_craftrod bytes) ---------------------


class FakeRodStore:
    """In-memory fishing_rod over the sole-writer store module."""

    def __init__(self):
        self.rows: dict[tuple, int] = {}

    def install(self, monkeypatch):
        from sb.domain.fishing import store as fs

        async def get_rod_tier(user_id, guild_id, conn=None):
            return self.rows.get((user_id, guild_id), 0)

        async def set_rod_tier(user_id, guild_id, tier, conn=None):
            self.rows[(user_id, guild_id)] = tier

        monkeypatch.setattr(fs, "get_rod_tier", get_rod_tier)
        monkeypatch.setattr(fs, "set_rod_tier", set_rod_tier)
        return self


def _install_inventory(monkeypatch, items: dict[str, int]):
    from sb.domain.mining import store as ms

    async def get_mining_inventory(user_id, guild_id, conn=None, *,
                                   for_update=False):
        return dict(items)

    monkeypatch.setattr(ms, "get_mining_inventory", get_mining_inventory)


def test_craftrod_fresh_player_guard_is_the_golden_byte(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.craftrod_route"))
    FakeRodStore().install(monkeypatch)
    _install_inventory(monkeypatch, {})

    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    # goldens/fishing/sweep_craftrod, byte-for-byte
    assert reply.user_message == (
        "You need **10** fish of size ≤ **6** to craft the **Bronze Rod** "
        "🥉 — catch more fish with `!fish` (or buy it with `!rod`).")


def test_craftrod_and_upgrade_at_max_answer_the_finest_rod(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    store = FakeRodStore().install(monkeypatch)
    store.rows[(P1, GID)] = 4
    _install_inventory(monkeypatch, {})
    expected = ("You already wield the **Diamond Rod** 💎 — the finest "
                "rod there is!")
    for ref in ("fishing.craftrod_route", "fishing.rod_upgrade_route"):
        reply = run(resolve(HandlerRef(ref))(_req()))
        assert reply.outcome is BLOCKED
        assert reply.user_message == expected


def test_rod_upgrade_insufficient_funds_is_a_pure_read(monkeypatch):
    from sb.domain.economy import store as es
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    FakeRodStore().install(monkeypatch)

    async def get_coins(user_id, guild_id, conn=None):
        return 0

    monkeypatch.setattr(es, "get_coins", get_coins)
    reply = run(resolve(HandlerRef("fishing.rod_upgrade_route"))(_req()))
    assert reply.outcome is BLOCKED
    # services/fishing_workflow.py buy_rod refusal, oracle-source-verbatim
    assert reply.user_message == (
        "The **Bronze Rod** 🥉 costs **250** 🪙 — you only have "
        "**0** 🪙.")


# --- the panel specs (sweep_rod / sweep_rodrecipes component trees) ----------------


def test_rod_shop_spec_pins_the_golden_component_tree():
    from sb.domain.fishing.panels import HUB_PANEL_ID, rod_shop_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import HandlerRef, PanelRef

    spec = rod_shop_spec()
    assert spec.title == "🎣 Your Fishing Rod"
    assert spec.frame.style_token == "gold"      # ECONOMY_COLOR 15844367
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False
    by_id = {a.action_id: a for a in spec.actions}
    # goldens/fishing/sweep_rod: labels + styles, emoji-in-label form
    assert by_id["rs_upgrade"].label == "⬆️ Upgrade rod"
    assert by_id["rs_upgrade"].style is ActionStyle.SUCCESS      # style 3
    assert by_id["rs_upgrade"].handler == HandlerRef(
        "fishing.rod_upgrade_route")
    assert by_id["rs_craft"].label == "🎣 Craft from fish"
    assert by_id["rs_craft"].style is ActionStyle.PRIMARY        # style 1
    assert by_id["rs_craft"].handler == HandlerRef(
        "fishing.craftrod_route")
    assert by_id["rs_recipes"].label == "📋 Recipes"
    assert by_id["rs_recipes"].style is ActionStyle.SECONDARY    # style 2
    assert by_id["rs_menu"].label == "↩ Fishing menu"
    assert by_id["rs_menu"].style is ActionStyle.SECONDARY
    assert by_id["rs_menu"].handler == PanelRef(HUB_PANEL_ID)
    # the golden's two component rows
    assert spec.layout.pages[0].rows == (
        ("rs_upgrade", "rs_craft", "rs_recipes"), ("rs_menu",))


def test_rod_recipes_spec_pins_the_golden_component_tree():
    from sb.domain.fishing.panels import ROD_PANEL_ID, rod_recipes_spec
    from sb.spec.panels import ActionStyle, TextBlock
    from sb.spec.refs import HandlerRef, PanelRef

    spec = rod_recipes_spec()
    assert spec.title == "📋 Rod Recipes"
    assert spec.frame.style_token == "gold"
    # goldens/fishing/sweep_rodrecipes: the static description bytes
    body = spec.body[0]
    assert isinstance(body, TextBlock)
    assert body.text == (
        "Craft your way up the ladder from caught fish — smallest "
        "catches spend first, so your trophies are always safe. Coins "
        "remain the fast alternative (`!rod`).")
    by_id = {a.action_id: a for a in spec.actions}
    assert by_id["rr_craft"].label == "🎣 Craft next"
    assert by_id["rr_craft"].style is ActionStyle.PRIMARY
    assert by_id["rr_craft"].handler == HandlerRef(
        "fishing.craftrod_route")
    assert by_id["rr_back"].label == "↩ Rod shop"
    assert by_id["rr_back"].style is ActionStyle.SECONDARY
    assert by_id["rr_back"].handler == PanelRef(ROD_PANEL_ID)
    assert spec.layout.pages[0].rows == (("rr_craft",), ("rr_back",))


# --- the store spec + refs ---------------------------------------------------------


def test_rod_store_spec_and_erasure_ref():
    from sb.domain.fishing import ops, store
    from sb.spec.refs import WorkflowRef, is_registered
    from sb.spec.versioning import DataClass

    spec = store.FISHING_ROD_STORE
    assert spec.table == "fishing_rod"
    assert spec.data_class is DataClass.MEMBER_ID
    assert spec.erasure_ref == WorkflowRef("fishing.erase_subject_rod")
    ops.ensure_ops_refs()
    assert is_registered(WorkflowRef("fishing.erase_subject_rod"))
    # the two audited rod write ops registered
    assert is_registered(WorkflowRef("fishing.buy_rod"))
    assert is_registered(WorkflowRef("fishing.craft_rod"))
    assert ops.ROD_PURCHASE_REASON == "fishing:rod_purchase"


# --- manifest + hub routes ----------------------------------------------------------


def test_manifest_and_hub_route_the_live_lanes():
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import ROD_PANEL_ID, fishing_hub_spec
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["rod"].route == HandlerRef("fishing.rod_shop")
    assert by_name["rod"].aliases == ("rodshop", "buyrod")
    assert by_name["craftrod"].route == HandlerRef("fishing.craftrod_route")
    assert by_name["craftrod"].aliases == ("rodcraft",)
    assert by_name["rodrecipes"].route == HandlerRef(
        "fishing.rodrecipes_view")
    assert by_name["rodrecipes"].aliases == ("rodrecipe", "rrecipes")
    # the new store is a declared fishing surface (guard-only sweeps —
    # exempt in parity.yml, never covered by an imported golden)
    assert "fishing_rod" in {s.table for s in MANIFEST.stores}
    # the two new panels are declared manifest surfaces
    panel_ids = {p.panel_id for p in MANIFEST.panels}
    assert {"fishing.rod_panel", "fishing.rod_recipes_panel"} <= panel_ids
    # the hub 🎒 Rod button repointed to the live rod shop panel
    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_rod"].handler == PanelRef(ROD_PANEL_ID)
    # rod/rodrecipes/craftrod left PENDING; their *_pending refs no
    # longer register (trap 12a)
    service.ensure_handler_refs()
    for name in ("rod", "rodrecipes", "craftrod"):
        assert name not in service.PENDING
        assert not is_registered(HandlerRef(f"fishing.{name}_pending"))
