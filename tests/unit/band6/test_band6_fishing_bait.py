"""Fishing bait fill (coordinated, lane #324) — the ported bait module
(shipped ``utils/fishing/bait.py`` verbatim), the ``!bait`` shop panel
spec + renderer (goldens/fishing/sweep_bait pins the fresh bait-less
bytes), the provider-fed select options, the audited buy leg (oracle
``buy_bait`` messages + reason verbatim, same-bait stack /
different-bait replace), the new ``fishing_bait`` store spec + erasure
ref, and the manifest/hub route flips. NO rod assertions here — the rod
ladder is #330's (tests/unit/band6/test_band6_fishing_rod.py)."""

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
    confirmed: bool = False


def _req(uid: int = P1, gid: int = GID, values: tuple = ()):
    return _FakeReq(actor=SimpleNamespace(user_id=uid, actor_type="user"),
                    guild_id=gid, args={"values": values})


# --- the pure bait module (shipped verbatim) ---------------------------------------


def test_bait_catalog_verbatim():
    from sb.domain.fishing import bait

    assert bait.BAIT_KEYS == ("worm", "grub", "lure", "minnow", "spinner",
                              "feast")
    shelf = {b.key: (b.name, b.emoji, b.price, b.charges) for b in
             bait.BAIT_CATALOG}
    assert shelf["worm"] == ("Worm Bait", "🪱", 150, 10)
    assert shelf["grub"] == ("Glow Grub", "🐛", 400, 10)
    assert shelf["lure"] == ("Shimmer Lure", "✨", 1000, 10)
    assert shelf["minnow"] == ("Live Minnow", "🐟", 200, 10)
    assert shelf["spinner"] == ("Flash Spinner", "🌀", 600, 10)
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


# --- the shop renderer (sweep_bait bytes) ------------------------------------------


def _fake_rendered(components=()):
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    return RenderedPanel(
        panel_id="x", embed=RenderedEmbed(title="t", description=""),
        components=tuple(components))


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


def test_bait_shop_renderer_loaded_state(monkeypatch):
    import sb.domain.economy.store as economy_store
    import sb.domain.mining.store as mining_store
    import sb.kernel.panels.render as render_mod
    from sb.domain.fishing import panels, store as fs

    async def render_panel(spec, ctx):
        return _fake_rendered()

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
    out = run(panels._render_bait_shop(panels.bait_shop_spec(), _req()))
    assert out.embed.description == (
        "Loaded: **Flash Spinner** 🌀 — **7** casts left (−40% wait).\n"
        "*Each cast spends one charge and applies these on top of "
        "your rod.*")
    fields = dict((f[0], f[1]) for f in out.embed.fields)
    assert "Craft from pearls (you have 3 🦪)" in fields
    assert fields["Your balance"] == "**350** 🪙"


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


# --- the buy route (guards as pure reads; oracle refusal copy verbatim) ------------


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
                               after={"buy_bait": {"message": "loaded"}})

    monkeypatch.setattr(engine_mod, "run", fake_run)
    reply = run(route(_req(values=("worm",))))
    assert reply.outcome is SUCCESS and reply.user_message == "loaded"
    assert ran and "fishing.buy_bait" in ran[0][0]
    assert ran[0][1]["bait_key"] == "worm"


# --- the buy leg (oracle buy_bait, one leg txn) ------------------------------------


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
    # the loadout read
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


def test_bait_buy_leg_insufficient_rolls_back(monkeypatch):
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
    assert state["bait"] == ("", 0)  # unchanged — the txn owner rolls back


# --- the store spec + refs ---------------------------------------------------------


def test_bait_store_spec_and_erasure_ref():
    from sb.domain.fishing import ops, store
    from sb.spec.refs import WorkflowRef, is_registered
    from sb.spec.versioning import DataClass, ForwardMapKind

    bait = store.FISHING_BAIT_STORE
    assert bait.table == "fishing_bait"
    assert bait.data_class is DataClass.MEMBER_ID
    assert bait.forward_map_kind is ForwardMapKind.NAME_STABLE
    assert bait.erasure_ref == WorkflowRef("fishing.erase_subject_bait")
    ops.ensure_ops_refs()
    for ref in ("fishing.erase_subject_bait", "fishing.buy_bait",
                "fishing.record_buy_bait"):
        assert is_registered(WorkflowRef(ref)), ref


# --- manifest + hub + panel shapes -------------------------------------------------


def test_manifest_hub_and_panel_route_the_live_bait_lane():
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import (
        BAIT_PANEL_ID,
        bait_shop_spec,
        fishing_hub_spec,
    )
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["bait"].route == HandlerRef("fishing.bait_shop")
    assert by_name["bait"].aliases == ("baitshop", "buybait")
    tables = {s.table for s in MANIFEST.stores}
    assert "fishing_bait" in tables
    panel_ids = {p.panel_id for p in MANIFEST.panels}
    assert BAIT_PANEL_ID in panel_ids

    # the hub 🪱 Bait button repointed to the live shop panel
    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_bait"].handler == PanelRef(BAIT_PANEL_ID)

    # bait left PENDING; its *_pending ref no longer registers — while
    # the craftbait/craftpearl pending terminals now register at IMPORT
    # (the shop's craft selects reference them; burn-down pruned)
    service.ensure_handler_refs()
    assert "bait" not in service.PENDING
    assert not is_registered(HandlerRef("fishing.bait_pending"))
    for ref in ("fishing.craftbait_pending", "fishing.craftpearl_pending"):
        assert is_registered(HandlerRef(ref)), ref

    # the shop panel shape the golden pins: selects, rows, nav, frame
    bait = bait_shop_spec()
    assert [s.selector_id for s in bait.selectors] == [
        "bs_buy", "bs_craft", "bs_pearl"]
    assert bait.selectors[0].on_select == HandlerRef(
        "fishing.bait_buy_route")
    assert bait.selectors[1].on_select == HandlerRef(
        "fishing.craftbait_pending")
    assert bait.selectors[2].on_select == HandlerRef(
        "fishing.craftpearl_pending")
    assert [s.placeholder for s in bait.selectors] == [
        "Buy a pack of bait…", "Craft a pack from caught fish…",
        "Craft a pack from pearls…"]
    assert [a.label for a in bait.actions] == ["↩ Fishing menu"]
    assert bait.layout.pages[0].rows == (
        ("bs_buy",), ("bs_craft",), ("bs_pearl",), ("bs_menu",))
    assert (bait.navigation.show_help, bait.navigation.show_home) == (
        False, False)
    assert bait.frame.style_token == "gold"    # ECONOMY_COLOR 15844367
    assert bait.session_lifecycle is True
