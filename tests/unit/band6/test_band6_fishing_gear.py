"""Fishing depth slice 2 — the gear shops: the ported rod/bait modules
(shipped ``utils/fishing/rods.py`` + ``bait.py`` verbatim), the ``!rod``
/ ``!bait`` shop renderers (goldens/fishing/sweep_rod + sweep_bait pin
the fresh-player bytes), the audited buy legs (oracle
``buy_rod``/``buy_bait`` messages + reasons verbatim), the new
``fishing_rod``/``fishing_bait`` store specs + erasure refs, and the
manifest/hub route flips."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

run = asyncio.run

GID, P1 = 1, 42


@dataclass(frozen=True)
class _FakeReq:
    actor: object = field(
        default_factory=lambda: SimpleNamespace(user_id=P1,
                                                actor_type="user"))
    guild_id: int = GID
    channel_id: int = 2
    args: dict = field(default_factory=dict)
    origin: object = None
    request_id: str = "r1"
    surface: object = None
    confirmed: bool = False


def _req(uid: int = P1, gid: int = GID, values: tuple = ()):
    return _FakeReq(actor=SimpleNamespace(user_id=uid, actor_type="user"),
                    guild_id=gid, args={"values": values})


# --- the pure rod module (shipped verbatim) ----------------------------------------


def test_rod_ladder_verbatim():
    from sb.domain.fishing import rods

    assert rods.MAX_TIER == 4
    names = [(r.name, r.emoji, r.price) for r in rods.ROD_LADDER]
    assert names == [("Bare Rod", "🎣", 0), ("Bronze Rod", "🥉", 250),
                     ("Silver Rod", "🥈", 750), ("Gold Rod", "🥇", 2000),
                     ("Diamond Rod", "💎", 5000)]
    bronze = rods.ROD_LADDER[1]
    assert (bronze.window_bonus, bronze.bite_speed, bronze.rarity_pull,
            bronze.escape_resist, bronze.premature_grace) == (
        0.4, 0.95, 1.10, 0.10, 0.15)
    # clamps: unknown → starter / top
    assert rods.rod_for_tier(-3) is rods.STARTER
    assert rods.rod_for_tier(99).name == "Diamond Rod"
    # the ladder steps one tier at a time; the top has no next
    assert rods.next_rod(0).tier == 1
    assert rods.next_rod(rods.MAX_TIER) is None
    # the fish→rod craft shelf rides as data (tier-1 line is
    # golden-pinned via the shop embed)
    r1 = rods.rod_recipe(1)
    assert (r1.fish_count, r1.max_size_rank) == (10, 6)
    assert rods.rod_recipe_text(r1) == "10 fish (size ≤ 6)"
    assert rods.rod_recipe(0) is None
    assert {t: (r.fish_count, r.max_size_rank)
            for t, r in rods.ROD_RECIPES.items()} == {
        1: (10, 6), 2: (16, 12), 3: (26, 18), 4: (40, 21)}


# --- the pure bait module (shipped verbatim) ---------------------------------------


def test_bait_catalog_verbatim():
    from sb.domain.fishing import bait

    assert bait.BAIT_KEYS == ("worm", "grub", "lure", "minnow", "spinner",
                              "feast")
    shelf = {b.key: (b.name, b.emoji, b.price, b.charges) for b in
             bait.BAIT_CATALOG}
    assert shelf["worm"] == ("Worm Bait", "🪱", 150, 10)
    assert shelf["feast"] == ("Royal Feast", "👑", 1800, 10)
    # effect_text bytes — the golden pins them in options + shelf lines
    by = bait.bait_by_key
    assert bait.effect_text(by("worm")) == "×1.25 rarity"
    assert bait.effect_text(by("grub")) == "×1.5 rarity"
    assert bait.effect_text(by("lure")) == "×2 rarity"
    assert bait.effect_text(by("minnow")) == "−20% wait"
    assert bait.effect_text(by("spinner")) == "−40% wait"
    assert bait.effect_text(by("feast")) == "×1.75 rarity · −30% wait"
    assert by("nope") is None and by("") is None and by(None) is None
    # craft shelves ride as data (the feast stays coin-only; pearls own it)
    assert bait.CRAFTABLE_KEYS == ("worm", "grub", "lure", "minnow",
                                   "spinner")
    assert bait.recipe_text(bait.craft_recipe("worm")) == (
        "3 fish (size ≤ 3)")
    assert bait.craft_recipe("feast") is None
    assert bait.PEARL_CRAFTABLE_KEYS == ("feast",)
    assert bait.pearl_recipe("feast") == 4
    assert bait.pearl_recipe_text(4) == "4 🦪 pearls"
    # typed-name resolution (the craft* rung's command path)
    assert bait.craftable_key_for("Worm Bait") == "worm"
    assert bait.craftable_key_for(" LURE ") == "lure"
    assert bait.craftable_key_for("royal feast") is None
    assert bait.pearl_craftable_key_for("royal feast") == "feast"


# --- the shop renderers (sweep_rod / sweep_bait bytes) -----------------------------


def _fake_rendered(components=()):
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    return RenderedPanel(
        panel_id="x", embed=RenderedEmbed(title="t", description=""),
        components=tuple(components))


def test_rod_shop_renderer_fresh_player_bytes(monkeypatch):
    import sb.domain.economy.store as economy_store
    import sb.kernel.panels.render as render_mod
    from sb.domain.fishing import panels, store as fs
    from sb.kernel.panels.render import RenderedComponent

    async def render_panel(spec, ctx):
        return _fake_rendered((
            RenderedComponent(kind="button", custom_id="p.rod_upgrade",
                              label="⬆️ Upgrade rod", row=0),
            RenderedComponent(kind="button", custom_id="p.rod_craft",
                              label="🎣 Craft from fish", row=0),
        ))

    async def get_rod_tier(uid, gid, conn=None):
        return 0

    async def get_coins(uid, gid, conn=None):
        return 0

    monkeypatch.setattr(render_mod, "render_panel", render_panel)
    monkeypatch.setattr(fs, "get_rod_tier", get_rod_tier)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)
    out = run(panels._render_rod_shop(panels.rod_shop_spec(), _req()))
    # goldens/fishing/sweep_rod, byte-for-byte
    assert out.embed.description == (
        "You're wielding the **Bare Rod** 🎣\n*the trusty starter — "
        "catches everything, just no bonuses*")
    fields = dict((f[0], f[1]) for f in out.embed.fields)
    assert fields["The ladder"] == (
        "**▶** 🎣 **Bare Rod** (—)\n🔒 🥉 **Bronze Rod** (250 🪙)\n"
        "🔒 🥈 **Silver Rod** (750 🪙)\n🔒 🥇 **Gold Rod** (2000 🪙)\n"
        "🔒 💎 **Diamond Rod** (5000 🪙)")
    assert fields["Next: 🥉 Bronze Rod — 250 🪙"] == (
        "_+0.4s reaction time · bites 5% faster · better catches in "
        "your band · 10% less escape in fights · 15% chance to forgive "
        "an early reel_\nYour balance: **0** 🪙\n🎣 _or craft from "
        "10 fish (size ≤ 6)_ (📋 Recipes shows your live progress)")
    # fresh player is not at max — both buttons stay enabled (the golden)
    assert all(not c.disabled for c in out.components)


def test_rod_shop_renderer_at_max_disables_buys(monkeypatch):
    import sb.domain.economy.store as economy_store
    import sb.kernel.panels.render as render_mod
    from sb.domain.fishing import panels, store as fs
    from sb.kernel.panels.render import RenderedComponent

    async def render_panel(spec, ctx):
        return _fake_rendered((
            RenderedComponent(kind="button", custom_id="p.rod_upgrade",
                              label="⬆️ Upgrade rod", row=0),
            RenderedComponent(kind="button", custom_id="p.rod_craft",
                              label="🎣 Craft from fish", row=0),
            RenderedComponent(kind="button", custom_id="p.rod_back",
                              label="↩ Fishing menu", row=1),
        ))

    async def get_rod_tier(uid, gid, conn=None):
        return 4

    async def get_coins(uid, gid, conn=None):
        return 123

    monkeypatch.setattr(render_mod, "render_panel", render_panel)
    monkeypatch.setattr(fs, "get_rod_tier", get_rod_tier)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)
    out = run(panels._render_rod_shop(panels.rod_shop_spec(), _req()))
    fields = dict((f[0], f[1]) for f in out.embed.fields)
    assert fields["Next upgrade"] == (
        "You wield the finest rod there is. 💎")
    flags = {c.custom_id: c.disabled for c in out.components}
    assert flags == {"p.rod_upgrade": True, "p.rod_craft": True,
                     "p.rod_back": False}


def test_bait_shop_renderer_fresh_player_bytes(monkeypatch):
    import sb.domain.economy.store as economy_store
    import sb.domain.mining.store as mining_store
    import sb.kernel.panels.render as render_mod
    from sb.domain.fishing import panels, store as fs

    async def render_panel(spec, ctx):
        return _fake_rendered()

    async def get_active_bait(uid, gid, conn=None):
        return "", 0

    async def get_coins(uid, gid, conn=None):
        return 0

    async def get_mining_inventory(uid, gid, conn=None, for_update=False):
        return {}

    monkeypatch.setattr(render_mod, "render_panel", render_panel)
    monkeypatch.setattr(fs, "get_active_bait", get_active_bait)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)
    monkeypatch.setattr(mining_store, "get_mining_inventory",
                        get_mining_inventory)
    out = run(panels._render_bait_shop(panels.bait_shop_spec(), _req()))
    # goldens/fishing/sweep_bait, byte-for-byte
    assert out.embed.description == (
        "No bait loaded — you're fishing bare (which catches fine!).\n"
        "*Load a pack for rarer, bigger fish or quicker bites.*")
    fields = dict((f[0], f[1]) for f in out.embed.fields)
    assert fields["The shelf"] == (
        "🪱 **Worm Bait** — 150 🪙 (×10 casts, ×1.25 rarity)\n"
        "🐛 **Glow Grub** — 400 🪙 (×10 casts, ×1.5 rarity)\n"
        "✨ **Shimmer Lure** — 1000 🪙 (×10 casts, ×2 rarity)\n"
        "🐟 **Live Minnow** — 200 🪙 (×10 casts, −20% wait)\n"
        "🌀 **Flash Spinner** — 600 🪙 (×10 casts, −40% wait)\n"
        "👑 **Royal Feast** — 1800 🪙 (×10 casts, ×1.75 rarity · "
        "−30% wait)")
    assert fields["Craft from fish"] == (
        "🪱 **Worm Bait** — 3 fish (size ≤ 3)\n"
        "🐛 **Glow Grub** — 5 fish (size ≤ 6)\n"
        "✨ **Shimmer Lure** — 6 fish (size ≤ 9)\n"
        "🐟 **Live Minnow** — 3 fish (size ≤ 3)\n"
        "🌀 **Flash Spinner** — 5 fish (size ≤ 6)\n"
        "*Turn small catches into bait — no coins needed.*")
    assert fields["Craft from pearls (you have 0 🦪)"] == (
        "👑 **Royal Feast** — 4 🦪 pearls\n"
        "*Pearls drop rarely when you reel in a fish — bigger fish, "
        "better odds.*")
    assert fields["Your balance"] == "**0** 🪙"


def test_bait_option_providers_pin_the_golden_options():
    from sb.domain.fishing import panels
    from sb.spec.refs import resolve

    buy_ref, craft_ref, pearl_ref = panels._ensure_bait_option_providers()
    buy = run(resolve(buy_ref)(None))
    assert buy[0] == {"label": "Worm Bait — 150 coins", "value": "worm",
                      "emoji": "🪱",
                      "description": "×10 casts · ×1.25 rarity"}
    assert [o["value"] for o in buy] == ["worm", "grub", "lure", "minnow",
                                         "spinner", "feast"]
    craft = run(resolve(craft_ref)(None))
    assert [o["value"] for o in craft] == ["worm", "grub", "lure",
                                           "minnow", "spinner"]
    assert craft[0]["label"] == "Worm Bait — 3 fish (size ≤ 3)"
    pearl = run(resolve(pearl_ref)(None))
    assert pearl == ({"label": "Royal Feast — 4 🦪 pearls",
                      "value": "feast", "emoji": "🦪",
                      "description": "×10 casts · ×1.75 rarity · "
                                     "−30% wait"},)


# --- the buy routes (guards as pure reads; oracle refusal copy verbatim) -----------


def test_rod_upgrade_route_guards_and_op(monkeypatch):
    import sb.domain.economy.store as economy_store
    import sb.kernel.workflow.engine as engine_mod
    from sb.domain.fishing import service, store as fs
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.rod_upgrade_route"))

    tier, coins = 0, 0

    async def get_rod_tier(uid, gid, conn=None):
        return tier

    async def get_coins(uid, gid, conn=None):
        return coins

    monkeypatch.setattr(fs, "get_rod_tier", get_rod_tier)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)

    # broke fresh player → the oracle insufficient-funds refusal, no op
    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "The **Bronze Rod** 🥉 costs **250** 🪙 — you only have "
        "**0** 🪙.")

    # maxed player → the oracle finest-rod refusal
    tier = 4
    reply = run(route(_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "You already wield the **Diamond Rod** 💎 — the finest rod "
        "there is!")

    # funded player → the audited op runs and its message is relayed
    tier, coins = 0, 500
    ran = []

    async def fake_run(ref, ctx, **kw):
        ran.append(str(ref))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               after={"rod_upgrade": {"message": "ok!"}})

    monkeypatch.setattr(engine_mod, "run", fake_run)
    reply = run(route(_req()))
    assert reply.outcome is SUCCESS and reply.user_message == "ok!"
    assert ran and "fishing.rod_upgrade" in ran[0]


def test_bait_buy_route_guards_and_op(monkeypatch):
    import sb.domain.economy.store as economy_store
    import sb.kernel.workflow.engine as engine_mod
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED, SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    route = resolve(HandlerRef("fishing.bait_buy_route"))

    coins = 0

    async def get_coins(uid, gid, conn=None):
        return coins

    monkeypatch.setattr(economy_store, "get_coins", get_coins)

    # unknown key → the oracle shelf refusal
    reply = run(route(_req(values=("kelp",))))
    assert reply.outcome is BLOCKED
    assert reply.user_message == "That bait doesn't exist on the shelf."

    # broke player → the oracle insufficient-funds refusal, no op
    reply = run(route(_req(values=("worm",))))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "A pack of **Worm Bait** 🪱 costs **150** 🪙 — you only have "
        "**0** 🪙.")

    # funded pick → the audited op runs with the picked key
    coins = 500
    ran = []

    async def fake_run(ref, ctx, **kw):
        ran.append((str(ref), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               after={"bait_buy": {"message": "loaded"}})

    monkeypatch.setattr(engine_mod, "run", fake_run)
    reply = run(route(_req(values=("worm",))))
    assert reply.outcome is SUCCESS and reply.user_message == "loaded"
    assert ran and ran[0][1]["bait_key"] == "worm"


# --- the buy legs (oracle buy_rod / buy_bait, one leg txn) -------------------------


class _LegStore:
    """In-memory fishing_rod/fishing_bait over the leg's store calls."""

    def __init__(self, monkeypatch, tier=0, bait=("", 0)):
        from sb.domain.fishing import store as fs

        self.tier, self.bait, self.locks = tier, bait, []

        async def lock_rod(conn, *, user_id, guild_id):
            self.locks.append("rod")

        async def lock_bait(conn, *, user_id, guild_id):
            self.locks.append("bait")

        async def get_rod_tier(uid, gid, conn=None):
            return self.tier

        async def set_rod_tier(uid, gid, tier, conn=None):
            self.tier = tier

        async def get_active_bait(uid, gid, conn=None):
            return self.bait

        async def set_active_bait(uid, gid, key, charges, conn=None):
            self.bait = (key, charges)

        monkeypatch.setattr(fs, "lock_rod_upgrade_slot", lock_rod)
        monkeypatch.setattr(fs, "lock_bait_slot", lock_bait)
        monkeypatch.setattr(fs, "get_rod_tier", get_rod_tier)
        monkeypatch.setattr(fs, "set_rod_tier", set_rod_tier)
        monkeypatch.setattr(fs, "get_active_bait", get_active_bait)
        monkeypatch.setattr(fs, "set_active_bait", set_active_bait)


def _leg_ctx():
    return SimpleNamespace(
        actor=SimpleNamespace(user_id=P1, actor_type="user"),
        guild_id=GID, params={})


def test_rod_upgrade_leg_debits_and_bumps(monkeypatch):
    from sb.domain.fishing import ops
    from sb.domain.games import wager

    store = _LegStore(monkeypatch, tier=0)
    debits = []

    async def debit_in_txn(conn, *, guild_id, user_id, amount, reason,
                           actor_id):
        debits.append((guild_id, user_id, amount, reason, actor_id))
        return 250  # balance after the 250-coin bronze debit

    monkeypatch.setattr(wager, "debit_in_txn", debit_in_txn)
    ctx = _leg_ctx()
    out = run(ops._record_rod_upgrade(object(), ctx))
    # the fence precedes the read; the debit is the audited coin move
    assert store.locks == ["rod"]
    assert debits == [(GID, P1, 250, "fishing:rod_purchase", P1)]
    assert store.tier == 1
    # the oracle buy_rod success copy, verbatim
    assert out.after["message"] == (
        "You upgraded to the **Bronze Rod** 🥉 for **250** 🪙! "
        "Balance: **250** 🪙.")
    assert ctx.params["_balance_changes"] == [
        (P1, -250, 250, "fishing:rod_purchase")]


def test_rod_upgrade_leg_insufficient_rolls_back(monkeypatch):
    import pytest

    import sb.domain.economy.store as economy_store
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.fishing import ops
    from sb.domain.games import wager
    from sb.kernel.interaction.errors import ValidatorError

    store = _LegStore(monkeypatch, tier=1)

    async def debit_in_txn(conn, **kw):
        raise InsufficientFundsError("❌ You only have **10** 🪙.")

    async def get_coins(uid, gid, conn=None):
        return 10

    monkeypatch.setattr(wager, "debit_in_txn", debit_in_txn)
    monkeypatch.setattr(economy_store, "get_coins", get_coins)
    with pytest.raises(ValidatorError) as exc:
        run(ops._record_rod_upgrade(object(), _leg_ctx()))
    assert ("The **Silver Rod** 🥈 costs **750** 🪙 — you only have "
            "**10** 🪙.") in str(exc.value)
    assert store.tier == 1  # unchanged — the txn owner rolls back


def test_bait_buy_leg_loads_stacks_and_replaces(monkeypatch):
    from sb.domain.fishing import ops
    from sb.domain.games import wager

    store = _LegStore(monkeypatch, bait=("", 0))

    async def debit_in_txn(conn, *, guild_id, user_id, amount, reason,
                           actor_id):
        return 1000 - amount

    monkeypatch.setattr(wager, "debit_in_txn", debit_in_txn)

    # fresh load — the oracle "Loaded" copy verbatim
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "worm"
    out = run(ops._record_bait_buy(object(), ctx))
    assert store.bait == ("worm", 10)
    assert out.after["message"] == (
        "Loaded **Worm Bait** 🪱 (×1.25 rarity) — **10** casts ready "
        "for **150** 🪙. Balance: **850** 🪙.")
    assert ctx.params["_balance_changes"] == [
        (P1, -150, 850, "fishing:bait_purchase")]

    # same bait again stacks — the oracle "Topped up" verb
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "worm"
    out = run(ops._record_bait_buy(object(), ctx))
    assert store.bait == ("worm", 20)
    assert out.after["message"].startswith("Topped up **Worm Bait**")

    # a different bait replaces the loadout (never merges)
    ctx = _leg_ctx()
    ctx.params["bait_key"] = "minnow"
    out = run(ops._record_bait_buy(object(), ctx))
    assert store.bait == ("minnow", 10)
    assert out.after["message"].startswith("Loaded **Live Minnow**")


# --- the store specs + refs --------------------------------------------------------


def test_gear_store_specs_and_erasure_refs():
    from sb.domain.fishing import ops, store
    from sb.spec.refs import WorkflowRef, is_registered
    from sb.spec.versioning import DataClass

    rod = store.FISHING_ROD_STORE
    assert rod.table == "fishing_rod"
    assert rod.data_class is DataClass.MEMBER_ID
    assert rod.erasure_ref == WorkflowRef("fishing.erase_subject_rod")
    bait = store.FISHING_BAIT_STORE
    assert bait.table == "fishing_bait"
    assert bait.data_class is DataClass.MEMBER_ID
    assert bait.erasure_ref == WorkflowRef("fishing.erase_subject_bait")
    ops.ensure_ops_refs()
    for ref in ("fishing.erase_subject_rod", "fishing.erase_subject_bait",
                "fishing.rod_upgrade", "fishing.bait_buy",
                "fishing.record_rod_upgrade", "fishing.record_bait_buy"):
        assert is_registered(WorkflowRef(ref)), ref


# --- manifest + hub + panel shapes -------------------------------------------------


def test_manifest_hub_and_panels_route_the_live_lanes():
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import (
        BAIT_SHOP_PANEL_ID,
        HUB_PANEL_ID,
        ROD_SHOP_PANEL_ID,
        bait_shop_spec,
        fishing_hub_spec,
        rod_shop_spec,
    )
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["rod"].route == HandlerRef("fishing.rod_view")
    assert by_name["rod"].aliases == ("rodshop", "buyrod")
    assert by_name["bait"].route == HandlerRef("fishing.bait_view")
    assert by_name["bait"].aliases == ("baitshop", "buybait")
    tables = {s.table for s in MANIFEST.stores}
    assert {"fishing_rod", "fishing_bait"} <= tables
    panel_ids = {p.panel_id for p in MANIFEST.panels}
    assert {ROD_SHOP_PANEL_ID, BAIT_SHOP_PANEL_ID} <= panel_ids

    # the hub 🎒 Rod / 🪱 Bait buttons repointed to the live shop panels
    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_rod"].handler == PanelRef(ROD_SHOP_PANEL_ID)
    assert by_id["fishing_bait"].handler == PanelRef(BAIT_SHOP_PANEL_ID)

    # rod/bait left PENDING; their *_pending refs no longer register —
    # while the craft* pending terminals now register at IMPORT (the
    # shop buttons/selects reference them; burn-down pruned)
    service.ensure_handler_refs()
    assert "rod" not in service.PENDING
    assert "bait" not in service.PENDING
    assert not is_registered(HandlerRef("fishing.rod_pending"))
    assert not is_registered(HandlerRef("fishing.bait_pending"))
    for ref in ("fishing.craftrod_pending", "fishing.rodrecipes_pending",
                "fishing.craftbait_pending", "fishing.craftpearl_pending"):
        assert is_registered(HandlerRef(ref)), ref

    # the shop panel shapes the goldens pin: rows, labels, styles, nav
    rod = rod_shop_spec()
    assert [a.label for a in rod.actions] == [
        "⬆️ Upgrade rod", "🎣 Craft from fish", "📋 Recipes",
        "↩ Fishing menu"]
    assert rod.layout.pages[0].rows == (
        ("rod_upgrade", "rod_craft", "rod_recipes"), ("rod_back",))
    assert (rod.navigation.show_help, rod.navigation.show_home) == (
        False, False)
    assert rod.frame.style_token == "gold"     # ECONOMY_COLOR 15844367
    bait = bait_shop_spec()
    assert [s.selector_id for s in bait.selectors] == [
        "bait_buy", "bait_craft", "bait_pearl"]
    assert bait.selectors[0].on_select == HandlerRef(
        "fishing.bait_buy_route")
    assert bait.layout.pages[0].rows == (
        ("bait_buy",), ("bait_craft",), ("bait_pearl",), ("bait_back",))
    assert (bait.navigation.show_help, bait.navigation.show_home) == (
        False, False)
    assert by_id["fishing_sail"].handler == HandlerRef("fishing.sail_route")
