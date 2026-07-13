"""Fishing depth slice 3 — the bait shelf: the ported bait module
(shipped ``utils/fishing/bait.py`` verbatim), the charm-craft shelf
(shipped ``utils/fishing/gear.py`` verbatim, names byte-matching the
mining gear catalog), the ``!craftpearl`` / ``!craftcharm`` /
``!craftbait`` guard bytes (goldens/fishing/sweep_craftpearl +
sweep_craftcharm pin them), the bait-shop panel spec
(goldens/fishing/sweep_bait + sweep_craftbait pin the component tree),
the new ``fishing_bait`` store spec + erasure ref, and the manifest/hub
route flips."""

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


def _req(uid: int = P1, gid: int = GID, argv: tuple = (),
         values: tuple = ()):
    return _FakeReq(actor=SimpleNamespace(user_id=uid, actor_type="user"),
                    guild_id=gid, args={"argv": argv, "values": values})


# --- the pure bait module (shipped verbatim) ---------------------------------------


def test_bait_catalog_verbatim_numbers():
    from sb.domain.fishing import bait

    shelf = [(b.key, b.name, b.emoji, b.price, b.charges,
              b.rarity_pull, b.bite_speed) for b in bait.BAIT_CATALOG]
    assert shelf == [
        ("worm", "Worm Bait", "🪱", 150, 10, 1.25, 1.0),
        ("grub", "Glow Grub", "🐛", 400, 10, 1.50, 1.0),
        ("lure", "Shimmer Lure", "✨", 1000, 10, 2.00, 1.0),
        ("minnow", "Live Minnow", "🐟", 200, 10, 1.00, 0.80),
        ("spinner", "Flash Spinner", "🌀", 600, 10, 1.00, 0.60),
        ("feast", "Royal Feast", "👑", 1800, 10, 1.75, 0.70),
    ]
    assert bait.BAIT_KEYS == ("worm", "grub", "lure", "minnow", "spinner",
                              "feast")
    assert bait.bait_by_key("worm").name == "Worm Bait"
    assert bait.bait_by_key("") is None
    assert bait.bait_by_key("kraken") is None


def test_effect_text_shows_only_turned_knobs():
    from sb.domain.fishing import bait

    by_key = {b.key: b for b in bait.BAIT_CATALOG}
    # goldens/fishing/sweep_bait pins these exact strings in the select
    # descriptions + shelf field
    assert bait.bait_effect_text(by_key["worm"]) == "×1.25 rarity"
    assert bait.bait_effect_text(by_key["grub"]) == "×1.5 rarity"
    assert bait.bait_effect_text(by_key["lure"]) == "×2 rarity"
    assert bait.bait_effect_text(by_key["minnow"]) == "−20% wait"
    assert bait.bait_effect_text(by_key["spinner"]) == "−40% wait"
    assert bait.bait_effect_text(by_key["feast"]) == "×1.75 rarity · −30% wait"


def test_craft_recipes_verbatim():
    from sb.domain.fishing import bait

    shelf = {k: (r.fish_count, r.max_size_rank)
             for k, r in bait.CRAFT_RECIPES.items()}
    assert shelf == {"worm": (3, 3), "minnow": (3, 3), "grub": (5, 6),
                     "spinner": (5, 6), "lure": (6, 9)}
    # shelf order, the premium combo deliberately absent
    assert bait.CRAFTABLE_KEYS == ("worm", "grub", "lure", "minnow",
                                   "spinner")
    assert "feast" not in bait.CRAFT_RECIPES
    assert bait.recipe_text(bait.CRAFT_RECIPES["worm"]) == (
        "3 fish (size ≤ 3)")
    # key and display-name resolution, case-insensitive
    assert bait.craftable_key_for("worm") == "worm"
    assert bait.craftable_key_for("Worm Bait") == "worm"
    assert bait.craftable_key_for("GLOW GRUB") == "grub"
    assert bait.craftable_key_for("feast") is None      # coin-only
    assert bait.craftable_key_for("") is None


def test_pearl_recipes_verbatim():
    from sb.domain.fishing import bait

    assert bait.PEARL_BAIT_RECIPES == {"feast": 4}   # Royal Feast = 4 pearls
    assert bait.PEARL_CRAFTABLE_KEYS == ("feast",)
    assert bait.pearl_recipe("feast") == 4
    assert bait.pearl_recipe("worm") is None
    assert bait.pearl_recipe_text(4) == "4 🦪 pearls"
    assert bait.pearl_craftable_key_for("feast") == "feast"
    assert bait.pearl_craftable_key_for("Royal Feast") == "feast"
    assert bait.pearl_craftable_key_for("worm") is None
    assert bait.pearl_craftable_key_for("") is None


def test_charm_recipes_verbatim_and_gear_catalog_names():
    from sb.domain.fishing import gear
    from sb.domain.mining import equipment

    shelf = {k: (r.fish_count, r.max_size_rank)
             for k, r in gear.CHARM_RECIPES.items()}
    assert shelf == {"fishing charm": (8, 8), "anglers charm": (12, 14),
                     "master angler charm": (18, 21)}
    # every craftable charm name byte-matches the mining gear catalog, so
    # a crafted charm equips exactly like a bought one (CHARM slot)
    for name in gear.CRAFTABLE_CHARM_NAMES:
        assert name in equipment.gear_names()
        assert equipment.slot_for(name) == equipment.CHARM
    assert gear.charm_recipe_text(gear.CHARM_RECIPES["fishing charm"]) == (
        "8 fish (size ≤ 8)")
    assert gear.craftable_charm_for("fishing charm") == "fishing charm"
    assert gear.craftable_charm_for("  Anglers Charm ") == "anglers charm"
    assert gear.craftable_charm_for("lucky charm") is None
    assert gear.craftable_charm_for("") is None


# --- the fresh-player guard bytes (sweep_craftpearl / sweep_craftcharm) ------------


def _install_inventory(monkeypatch, items: dict[str, int]):
    from sb.domain.mining import store as ms

    async def get_mining_inventory(user_id, guild_id, conn=None, *,
                                   for_update=False):
        return dict(items)

    monkeypatch.setattr(ms, "get_mining_inventory", get_mining_inventory)


def test_craftpearl_fresh_player_guard_is_the_golden_byte(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    _install_inventory(monkeypatch, {})
    reply = run(resolve(HandlerRef("fishing.craftpearl_route"))(_req()))
    assert reply.outcome is BLOCKED
    # goldens/fishing/sweep_craftpearl, byte-for-byte (the no-arg call
    # auto-selects the single pearl recipe)
    assert reply.user_message == (
        "You need **4** 🦪 pearls to craft **Royal Feast** 👑 — you have "
        "**0**. Pearls drop rarely when you reel in a fish (bigger fish, "
        "better odds).")


def test_craftpearl_unknown_bait_lists_pearl_craftable(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    reply = run(resolve(HandlerRef("fishing.craftpearl_route"))(
        _req(argv=("worm",))))
    assert reply.outcome is BLOCKED
    # fishing_cog.py craftpearl, oracle-source-verbatim
    assert reply.user_message == (
        "You can't craft **worm** from pearls. Pearl-craftable: "
        "Royal Feast.")


def test_craftcharm_no_arg_listing_is_the_golden_byte():
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    reply = run(resolve(HandlerRef("fishing.craftcharm_route"))(_req()))
    assert reply.outcome is SUCCESS
    # goldens/fishing/sweep_craftcharm, byte-for-byte
    assert reply.user_message == (
        "Craft a fishing charm from caught fish (or buy one with "
        "`!gear`):\n"
        "🎣 **Fishing Charm** — 8 fish (size ≤ 8)\n"
        "🎣 **Anglers Charm** — 12 fish (size ≤ 14)\n"
        "🎣 **Master Angler Charm** — 18 fish (size ≤ 21)")


def test_craftcharm_fresh_player_guard_is_a_pure_read(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    _install_inventory(monkeypatch, {})
    reply = run(resolve(HandlerRef("fishing.craftcharm_route"))(
        _req(argv=("fishing", "charm"))))
    assert reply.outcome is BLOCKED
    # services/fishing_workflow.py craft_charm, oracle-source-verbatim
    assert reply.user_message == (
        "You need **8** fish of size ≤ **8** to craft a "
        "**fishing charm** — catch more fish with `!fish`.")


def test_craftbait_guards_are_pure_reads(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.craftbait_route"))
    # unknown / non-craftable bait (fishing_cog.py craftbait verbatim —
    # the premium combo does not resolve)
    reply = run(route(_req(argv=("feast",))))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "You can't craft **feast** from fish. Craftable: Worm Bait, "
        "Glow Grub, Shimmer Lure, Live Minnow, Flash Spinner.")
    # not enough fish (services/fishing_workflow.py craft_bait verbatim)
    _install_inventory(monkeypatch, {})
    reply = run(route(_req(argv=("worm",))))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "You need **3** fish of size ≤ **3** to craft **Worm Bait** 🪱 — "
        "catch more small fish with `!fish`.")


def test_bait_buy_insufficient_funds_is_a_pure_read(monkeypatch):
    from sb.domain.economy import store as es
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()

    async def get_coins(user_id, guild_id, conn=None):
        return 0

    monkeypatch.setattr(es, "get_coins", get_coins)
    route = resolve(HandlerRef("fishing.bait_buy_route"))
    reply = run(route(_req(values=("worm",))))
    assert reply.outcome is BLOCKED
    # services/fishing_workflow.py buy_bait refusal, oracle-source-verbatim
    assert reply.user_message == (
        "A pack of **Worm Bait** 🪱 costs **150** 🪙 — you only have "
        "**0** 🪙.")
    reply = run(route(_req(values=("kraken",))))
    assert reply.outcome is BLOCKED
    assert reply.user_message == "That bait doesn't exist on the shelf."


# --- the panel spec (sweep_bait / sweep_craftbait component tree) ------------------


def test_bait_shop_spec_pins_the_golden_component_tree():
    from sb.domain.fishing.panels import HUB_PANEL_ID, bait_shop_spec
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import HandlerRef, PanelRef

    spec = bait_shop_spec()
    assert spec.title == "🪱 Bait Shop"
    assert spec.frame.style_token == "gold"      # ECONOMY_COLOR 15844367
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False
    assert spec.navigation.show_home is False
    by_id = {s.selector_id: s for s in spec.selectors}
    # goldens/fishing/sweep_bait: placeholders + every option byte
    buy = by_id["bs_buy"]
    assert buy.placeholder == "Buy a pack of bait…"
    assert buy.on_select == HandlerRef("fishing.bait_buy_route")
    assert [o["label"] for o in buy.options_source] == [
        "Worm Bait — 150 coins", "Glow Grub — 400 coins",
        "Shimmer Lure — 1000 coins", "Live Minnow — 200 coins",
        "Flash Spinner — 600 coins", "Royal Feast — 1800 coins"]
    assert buy.options_source[0] == {
        "label": "Worm Bait — 150 coins", "value": "worm",
        "emoji": "🪱", "description": "×10 casts · ×1.25 rarity"}
    craft = by_id["bs_craft"]
    assert craft.placeholder == "Craft a pack from caught fish…"
    assert craft.on_select == HandlerRef("fishing.craftbait_route")
    assert [o["label"] for o in craft.options_source] == [
        "Worm Bait — 3 fish (size ≤ 3)", "Glow Grub — 5 fish (size ≤ 6)",
        "Shimmer Lure — 6 fish (size ≤ 9)",
        "Live Minnow — 3 fish (size ≤ 3)",
        "Flash Spinner — 5 fish (size ≤ 6)"]
    pearl = by_id["bs_pearl"]
    assert pearl.placeholder == "Craft a pack from pearls…"
    assert pearl.on_select == HandlerRef("fishing.craftpearl_route")
    assert pearl.options_source == ({
        "label": "Royal Feast — 4 🦪 pearls", "value": "feast",
        "emoji": "🦪",
        "description": "×10 casts · ×1.75 rarity · −30% wait"},)
    menu = {a.action_id: a for a in spec.actions}["bs_menu"]
    assert menu.label == "↩ Fishing menu"
    assert menu.style is ActionStyle.SECONDARY   # style 2
    assert menu.handler == PanelRef(HUB_PANEL_ID)
    # the golden's four component rows: three selects then the button
    assert spec.layout.pages[0].rows == (
        ("bs_buy",), ("bs_craft",), ("bs_pearl",), ("bs_menu",))


# --- the store spec + refs ---------------------------------------------------------


def test_bait_store_spec_and_erasure_ref():
    from sb.domain.fishing import ops, store
    from sb.spec.refs import WorkflowRef, is_registered
    from sb.spec.versioning import DataClass

    spec = store.FISHING_BAIT_STORE
    assert spec.table == "fishing_bait"
    assert spec.data_class is DataClass.MEMBER_ID
    assert spec.erasure_ref == WorkflowRef("fishing.erase_subject_bait")
    ops.ensure_ops_refs()
    assert is_registered(WorkflowRef("fishing.erase_subject_bait"))
    # the four audited bait/charm write ops registered
    assert is_registered(WorkflowRef("fishing.buy_bait"))
    assert is_registered(WorkflowRef("fishing.craft_bait"))
    assert is_registered(WorkflowRef("fishing.craft_pearl_bait"))
    assert is_registered(WorkflowRef("fishing.craft_charm"))
    assert ops.BAIT_PURCHASE_REASON == "fishing:bait_purchase"


# --- manifest + hub routes ----------------------------------------------------------


def test_manifest_and_hub_route_the_live_lanes():
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import BAIT_PANEL_ID, fishing_hub_spec
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["bait"].route == HandlerRef("fishing.bait_shop")
    assert by_name["bait"].aliases == ("baitshop", "buybait")
    assert by_name["craftbait"].route == HandlerRef(
        "fishing.craftbait_route")
    assert by_name["craftbait"].aliases == ("baitcraft",)
    assert by_name["craftcharm"].route == HandlerRef(
        "fishing.craftcharm_route")
    assert by_name["craftcharm"].aliases == ("charmcraft",)
    assert by_name["craftpearl"].route == HandlerRef(
        "fishing.craftpearl_route")
    assert by_name["craftpearl"].aliases == ("pearlcraft",)
    # the new store is a declared fishing surface (guard-only sweeps —
    # exempt in parity.yml, never covered by an imported golden)
    assert "fishing_bait" in {s.table for s in MANIFEST.stores}
    # the new panel is a declared manifest surface
    assert "fishing.bait_panel" in {p.panel_id for p in MANIFEST.panels}
    # the hub 🪱 Bait button repointed to the live bait shop panel
    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_bait"].handler == PanelRef(BAIT_PANEL_ID)
    # bait/craftbait/craftpearl/craftcharm left PENDING; their *_pending
    # refs no longer register (trap 12a)
    service.ensure_handler_refs()
    for name in ("bait", "craftbait", "craftpearl", "craftcharm"):
        assert name not in service.PENDING
        assert not is_registered(HandlerRef(f"fishing.{name}_pending"))


# --- the buy leg's stack/replace semantics + loaded-state render (delta
# --- tests from the ceded #328/#338 lane — coordinator-adjudicated fill:
# --- the landed slice pins the guards and the component tree; these pin
# --- the LEG's oracle success copy, the same-bait stack / different-bait
# --- replace arithmetic, the defensive insufficient path, and the
# --- loaded-state shop description no golden covers (sweep_bait pins the
# --- fresh bait-less open only) -----------------------------------------------------


def _leg_ctx():
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=P1, actor_type="user"),
        guild_id=GID, params={})


def test_bait_buy_leg_loads_stacks_and_replaces(monkeypatch):
    from sb.domain.fishing import ops, store as fs
    from sb.domain.games import wager

    state = {"bait": ("", 0), "locks": []}

    async def lock_bait_slot(conn, *, user_id, guild_id):
        state["locks"].append((guild_id, user_id))

    async def get_active_bait(uid, gid, conn=None):
        return state["bait"]

    async def set_active_bait(uid, gid, key, charges, conn=None):
        state["bait"] = (key, charges)

    async def debit_in_txn(conn, *, guild_id, user_id, amount, reason,
                           actor_id):
        return 1000 - amount

    monkeypatch.setattr(fs, "lock_bait_slot", lock_bait_slot)
    monkeypatch.setattr(fs, "get_active_bait", get_active_bait)
    monkeypatch.setattr(fs, "set_active_bait", set_active_bait)
    monkeypatch.setattr(wager, "debit_in_txn", debit_in_txn)

    # fresh load — the oracle "Loaded" copy verbatim; the fence precedes
    # the loadout read (#217)
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "worm"
    out = run(ops._record_buy_bait(object(), ctx))
    assert state["locks"] == [(GID, P1)]
    assert state["bait"] == ("worm", 10)
    assert out.after["message"] == (
        "Loaded **Worm Bait** 🪱 (×1.25 rarity) — **10** casts ready "
        "for **150** 🪙. Balance: **850** 🪙.")
    assert ctx.params["_balance_changes"] == [
        (P1, -150, 850, "fishing:bait_purchase")]

    # same bait again stacks — the oracle "Topped up" verb
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "worm"
    out = run(ops._record_buy_bait(object(), ctx))
    assert state["bait"] == ("worm", 20)
    assert out.after["message"].startswith("Topped up **Worm Bait**")

    # a different bait replaces the loadout (never merges)
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "minnow"
    out = run(ops._record_buy_bait(object(), ctx))
    assert state["bait"] == ("minnow", 10)
    assert out.after["message"].startswith("Loaded **Live Minnow**")


def test_bait_buy_leg_insufficient_is_defensive_and_writes_nothing(
        monkeypatch):
    import pytest

    import sb.domain.economy.store as economy_store
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.fishing import ops, store as fs
    from sb.domain.games import wager
    from sb.kernel.interaction.errors import ValidatorError

    state = {"bait": ("", 0)}

    async def lock_bait_slot(conn, *, user_id, guild_id):
        pass

    async def get_active_bait(uid, gid, conn=None):
        return state["bait"]

    async def set_active_bait(uid, gid, key, charges, conn=None):
        state["bait"] = (key, charges)

    async def debit_in_txn(conn, **kw):
        raise InsufficientFundsError("❌ You only have **10** 🪙.")

    async def get_coins(uid, gid, conn=None):
        return 10

    monkeypatch.setattr(fs, "lock_bait_slot", lock_bait_slot)
    monkeypatch.setattr(fs, "get_active_bait", get_active_bait)
    monkeypatch.setattr(fs, "set_active_bait", set_active_bait)
    monkeypatch.setattr(wager, "debit_in_txn", debit_in_txn)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "feast"
    with pytest.raises(ValidatorError) as exc:
        run(ops._record_buy_bait(object(), ctx))
    assert ("A pack of **Royal Feast** 👑 costs **1800** 🪙 — you only "
            "have **10** 🪙.") in str(exc.value)
    assert state["bait"] == ("", 0)  # no load — the txn owner rolls back


def test_bait_shop_renderer_loaded_state_bytes(monkeypatch):
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    import sb.domain.economy.store as economy_store
    import sb.domain.mining.store as mining_store
    import sb.kernel.panels.render as render_mod
    from sb.domain.fishing import panels, store as fs

    async def render_panel(spec, ctx):
        return RenderedPanel(
            panel_id="x", embed=RenderedEmbed(title="t", description=""),
            components=())

    async def get_active_bait(uid, gid, conn=None):
        return "spinner", 7

    async def get_coins(uid, gid, conn=None):
        return 350

    async def get_mining_inventory(uid, gid, conn=None, for_update=False):
        return {"pearl": 3}

    monkeypatch.setattr(render_mod, "render_panel", render_panel)
    monkeypatch.setattr(fs, "get_active_bait", get_active_bait)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)
    monkeypatch.setattr(mining_store, "get_mining_inventory",
                        get_mining_inventory)
    out = run(panels._render_bait_shop(panels.bait_shop_spec(),
                                       _req()))
    # build_bait_embed's LOADED branch, byte-for-byte (no golden pins it
    # — sweep_bait captured only the fresh bait-less open)
    assert out.embed.description == (
        "Loaded: **Flash Spinner** 🌀 — **7** casts left (−40% wait).\n"
        "*Each cast spends one charge and applies these on top of "
        "your rod.*")
    fields = dict((f[0], f[1]) for f in out.embed.fields)
    assert "Craft from pearls (you have 3 🦪)" in fields
    assert fields["Your balance"] == "**350** 🪙"
