"""Fishing depth slice 4 (FINAL) — the coral sinks + structures: the
ported curio module (shipped ``utils/fishing/curios.py`` verbatim), the
four fishing structures on the shared mining structures registry
(shipped ``utils/mining/structures.py`` keys/names/ladders/mults
verbatim), the ``!curios`` card + ``!craftcurio`` guard bytes
(goldens/fishing/sweep_curios + sweep_craftcurio pin them), the four
structure panel specs (goldens/fishing/sweep_tidepool / sweep_dock /
sweep_boathouse / sweep_fishery pin the component trees + embeds), the
structures sub-hub, the build/carve write ops, and the manifest/hub
route flips that EMPTY the fishing PENDING roster (20/20 live)."""

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


# --- the pure curio module (shipped verbatim) --------------------------------------


def test_curio_catalog_verbatim_numbers():
    from sb.domain.fishing import curios

    shelf = [(c.key, c.item, c.name, c.emoji, c.coral_cost, c.rarity)
             for c in curios.CURIO_CATALOG]
    assert shelf == [
        ("coral shell", "coral shell", "Carved Coral Shell", "🐚", 2,
         "Uncommon"),
        ("coral seahorse", "coral seahorse", "Coral Seahorse", "🌊", 4,
         "Rare"),
        ("coral idol", "coral idol", "Coral Idol", "🗿", 8, "Epic"),
        ("coral leviathan", "coral leviathan", "Coral Leviathan", "🐉",
         16, "Legendary"),
    ]
    assert curios.CURIO_KEYS == ("coral shell", "coral seahorse",
                                 "coral idol", "coral leviathan")
    assert curios.CURIO_ITEMS == curios.CURIO_KEYS
    assert curios.curio_by_key("coral idol").name == "Coral Idol"
    assert curios.curio_by_key("") is None
    assert curios.curio_by_key("kraken") is None
    assert curios.cost_text(curios.CURIO_CATALOG[1]) == "4 🪸 coral"
    # the shipped craftable_key_for (renamed curio_craftable_key_for —
    # bait.py owns the package's craftable_key_for): key OR display name,
    # case-insensitive; a partial like "idol" does NOT resolve
    assert curios.curio_craftable_key_for("coral idol") == "coral idol"
    assert curios.curio_craftable_key_for("Coral Idol") == "coral idol"
    assert curios.curio_craftable_key_for("CORAL LEVIATHAN") == \
        "coral leviathan"
    assert curios.curio_craftable_key_for("idol") is None
    assert curios.curio_craftable_key_for("") is None
    assert curios.curio_craftable_key_for(None) is None


def test_collection_progress_counts_distinct_owned():
    from sb.domain.fishing import curios

    assert curios.collection_progress({}) == (0, 4)
    assert curios.collection_progress({"coral idol": 2}) == (1, 4)
    assert curios.collection_progress(
        {c: 1 for c in curios.CURIO_ITEMS}) == (4, 4)
    assert curios.collection_progress({"coral shell": 0}) == (0, 4)


# --- the fishing structures on the shared mining registry (verbatim) ---------------


def test_fishing_structure_defs_verbatim():
    from sb.domain.mining import structures as st

    assert (st.TIDE_POOL, st.DOCK, st.BOATHOUSE, st.FISHERY) == (
        "tide_pool", "dock", "boathouse", "fishery")
    for key in ("tide_pool", "dock", "boathouse", "fishery"):
        assert st.is_structure(key)
    assert st.display_name(st.TIDE_POOL) == "Tide Pool"
    assert st.display_name(st.DOCK) == "Dock"
    assert st.display_name(st.BOATHOUSE) == "Boathouse"
    assert st.display_name(st.FISHERY) == "Fishery"
    # level names (goldens pin the "(not built)" byte)
    assert [st.level_name(st.TIDE_POOL, i) for i in range(4)] == [
        "(not built)", "Reef Pool", "Tidal Basin", "Grand Reef"]
    assert [st.level_name(st.DOCK, i) for i in range(3)] == [
        "(not built)", "Fishing Dock", "Deepwater Pier"]
    assert [st.level_name(st.BOATHOUSE, i) for i in range(3)] == [
        "(not built)", "Boathouse", "Grand Boathouse"]
    assert [st.level_name(st.FISHERY, i) for i in range(3)] == [
        "(not built)", "Fishery", "Grand Fishery"]
    assert (st.MAX_TIDE_POOL_LEVEL, st.MAX_DOCK_LEVEL,
            st.MAX_BOATHOUSE_LEVEL, st.MAX_FISHERY_LEVEL) == (3, 2, 2, 2)


def test_fishing_structure_ladders_verbatim():
    from sb.domain.mining import structures as st

    def costs(key):
        return [(c.coins, c.materials)
                for c in (st.build_cost(key, i)
                          for i in range(st.max_level(key)))]

    assert costs(st.TIDE_POOL) == [
        (1_500, {"coral": 3}), (4_000, {"coral": 6}),
        (9_000, {"coral": 10})]
    assert costs(st.DOCK) == [
        (1_200, {"coral": 2, "wood": 15}),
        (3_500, {"coral": 5, "wood": 30})]
    assert costs(st.BOATHOUSE) == [
        (2_000, {"coral": 3, "wood": 20}),
        (5_000, {"coral": 6, "wood": 40})]
    assert costs(st.FISHERY) == [
        (2_500, {"coral": 4, "wood": 25}),
        (6_000, {"coral": 8, "wood": 45})]
    # maxed → None
    assert st.build_cost(st.TIDE_POOL, 3) is None
    assert st.build_cost(st.DOCK, 2) is None


def test_fishing_structure_mults_verbatim():
    from sb.domain.mining import structures as st

    # unbuilt ⇒ byte-identical casts (the additive-safety property)
    assert st.tide_pool_pull_mult(0) == 1.0
    assert st.dock_bite_speed_mult(0) == 1.0
    assert st.boathouse_regen_mult(0) == 1.0
    assert st.fishery_bonus_chance(0) == 0.0
    # the pinned per-level steps (pull 0.04 · bite 0.06 · regen 0.12 ·
    # bonus 0.05)
    assert [st.tide_pool_pull_mult(i) for i in (1, 2, 3)] == [
        1.04, 1.08, 1.12]
    assert [st.dock_bite_speed_mult(i) for i in (1, 2)] == [0.94, 0.88]
    assert [st.boathouse_regen_mult(i) for i in (1, 2)] == [0.88, 0.76]
    assert [st.fishery_bonus_chance(i) for i in (1, 2)] == [0.05, 0.10]
    # clamped — out-of-range never over-rewards
    assert st.tide_pool_pull_mult(99) == 1.12
    assert st.dock_bite_speed_mult(-1) == 1.0
    assert st.fishery_bonus_chance(99) == 0.10


# --- the fresh-player guard bytes (sweep_craftcurio / sweep_curios) ----------------


def _install_inventory(monkeypatch, items: dict[str, int]):
    from sb.domain.mining import store as ms

    async def get_mining_inventory(user_id, guild_id, conn=None, *,
                                   for_update=False):
        return dict(items)

    monkeypatch.setattr(ms, "get_mining_inventory", get_mining_inventory)


def test_craftcurio_no_arg_guard_is_the_golden_byte():
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    reply = run(resolve(HandlerRef("fishing.craftcurio_route"))(_req()))
    assert reply.outcome is BLOCKED
    # goldens/fishing/sweep_craftcurio, byte-for-byte
    assert reply.user_message == (
        "That isn't a carvable curio. Carvable: Carved Coral Shell, "
        "Coral Seahorse, Coral Idol, Coral Leviathan. See `!curios` for "
        "your collection.")


def test_craftcurio_no_coral_guard_is_a_pure_read(monkeypatch):
    from sb.domain.fishing import service
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    _install_inventory(monkeypatch, {})
    reply = run(resolve(HandlerRef("fishing.craftcurio_route"))(
        _req(argv=("coral", "idol"))))
    assert reply.outcome is BLOCKED
    # services/fishing_workflow.py craft_curio, oracle-source-verbatim
    assert reply.user_message == (
        "You need **8** 🪸 coral to carve **Coral Idol** 🗿 — you have "
        "**0**. Coral drops rarely when you reel in a fish out in "
        "**deepwater** (`!sail` to the boat first).")


def test_curios_card_renders_the_golden_bytes(monkeypatch):
    """The fresh 0-coral shelf read — goldens/fishing/sweep_curios pins
    the embed byte-for-byte (all four 🔒 marks, the cost·rarity values,
    the carve footer, _FISHING_COLOR blue)."""
    from sb.domain.fishing import service
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    _install_inventory(monkeypatch, {})
    captured = {}

    async def open_panel(ref, req):
        captured["embed"] = req.args.get("_card")

    import sb.kernel.panels.engine as engine

    monkeypatch.setattr(engine, "open_panel", open_panel)
    reply = run(resolve(HandlerRef("fishing.curios_view"))(_req()))
    assert reply.outcome is SUCCESS
    embed = captured["embed"]
    assert embed.title == "🪸 Coral Curios"
    assert embed.style_token == "blue"           # _FISHING_COLOR 3447003
    assert embed.description == (
        "You have **0** 🪸 coral · collection **0/4** carved.\n"
        "Coral drops rarely on a **deepwater** reel (`!sail` to the "
        "boat).")
    assert embed.fields == (
        ("🔒 🐚 Carved Coral Shell", "2 🪸 coral · Uncommon"),
        ("🔒 🌊 Coral Seahorse", "4 🪸 coral · Rare"),
        ("🔒 🗿 Coral Idol", "8 🪸 coral · Epic"),
        ("🔒 🐉 Coral Leviathan", "16 🪸 coral · Legendary"),
    )
    assert embed.footer == "Carve with !craftcurio <name>"


def test_structure_build_guards_are_pure_reads(monkeypatch):
    from sb.domain.economy import store as es
    from sb.domain.fishing import service
    from sb.domain.mining import store as ms
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()

    async def get_structures(user_id, guild_id, conn=None):
        return {}

    async def get_coins(user_id, guild_id, conn=None):
        return 0

    monkeypatch.setattr(ms, "get_structures", get_structures)
    monkeypatch.setattr(es, "get_coins", get_coins)
    _install_inventory(monkeypatch, {})
    # short on materials (services/mining_workflow.py build_structure,
    # oracle-source-verbatim)
    reply = run(resolve(HandlerRef("fishing.tidepool_build_route"))(
        _req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "Building the Tide Pool needs 3× coral plus 1500 🪙 — you're "
        "short on materials.")
    # stocked but broke → the coin refusal
    _install_inventory(monkeypatch, {"coral": 3})
    reply = run(resolve(HandlerRef("fishing.tidepool_build_route"))(
        _req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "Building the Tide Pool costs **1500** 🪙 — you only have "
        "**0** 🪙.")

    # maxed (the ladder-top refusal)
    async def maxed(user_id, guild_id, conn=None):
        return {"dock": 2}

    monkeypatch.setattr(ms, "get_structures", maxed)
    reply = run(resolve(HandlerRef("fishing.dock_build_route"))(_req()))
    assert reply.outcome is BLOCKED
    assert reply.user_message == (
        "Your Dock is already at its maximum level "
        "(**Deepwater Pier**).")


# --- the panel specs (the four structure sweeps' component trees) ------------------


def test_structure_panel_specs_pin_the_golden_component_trees():
    from sb.domain.fishing.panels import (
        STRUCTURES_PANEL_ID,
        boathouse_spec,
        dock_spec,
        fishery_spec,
        tide_pool_spec,
    )
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import HandlerRef, PanelRef

    for spec, title, token, emoji, prefix, route in (
        (tide_pool_spec(), "🪸 Tide Pool", "teal", "🪸", "tp",
         "fishing.tidepool_build_route"),
        (dock_spec(), "⚓ Dock", "dark_teal", "⚓", "dk",
         "fishing.dock_build_route"),
        (boathouse_spec(), "🛖 Boathouse", "dark_teal", "🛖", "bh",
         "fishing.boathouse_build_route"),
        (fishery_spec(), "🐟 Fishery", "dark_teal", "🐟", "fy",
         "fishing.fishery_build_route"),
    ):
        assert spec.title == title
        assert spec.frame.style_token == token
        assert spec.session_lifecycle is True
        # the shipped HubView children DO carry the nav row (the goldens
        # pin nav:help + nav:hub:games — unlike the rod/bait BaseViews)
        assert spec.navigation.show_help is True
        assert spec.navigation.show_home is True
        assert spec.navigation.home_hub == "games"
        by_id = {a.action_id: a for a in spec.actions}
        build = by_id[f"{prefix}_build"]
        assert build.label == f"{emoji} Build"   # emoji-in-label, style 3
        assert build.style is ActionStyle.SUCCESS
        assert build.handler == HandlerRef(route)
        back = by_id[f"{prefix}_back"]
        assert back.label == "↩ Structures"
        assert back.style is ActionStyle.SECONDARY
        assert back.handler == PanelRef(STRUCTURES_PANEL_ID)
        assert spec.layout.pages[0].rows == (
            (f"{prefix}_build", f"{prefix}_back"),)


def test_structures_hub_spec_is_the_shipped_sub_hub():
    from sb.domain.fishing.panels import (
        BOATHOUSE_PANEL_ID,
        DOCK_PANEL_ID,
        FISHERY_PANEL_ID,
        HUB_PANEL_ID,
        TIDE_POOL_PANEL_ID,
        structures_hub_spec,
    )
    from sb.spec.panels import ActionStyle
    from sb.spec.refs import PanelRef

    spec = structures_hub_spec()
    assert spec.title == "🏗 Fishing structures"
    assert spec.frame.style_token == "purple"    # GAME_COLOR 10181046
    by_id = {a.action_id: a for a in spec.actions}
    for action_id, label, emoji, target in (
        ("st_tidepool", "Tide Pool", "🪸", TIDE_POOL_PANEL_ID),
        ("st_dock", "Dock", "⚓", DOCK_PANEL_ID),
        ("st_boathouse", "Boathouse", "🛖", BOATHOUSE_PANEL_ID),
        ("st_fishery", "Fishery", "🐟", FISHERY_PANEL_ID),
    ):
        act = by_id[action_id]
        assert act.label == label                # emoji SEPARATE (trap 15a)
        assert act.emoji == emoji
        assert act.style is ActionStyle.SECONDARY
        assert act.handler == PanelRef(target)
    assert by_id["st_menu"].label == "↩ Fishing menu"
    assert by_id["st_menu"].handler == PanelRef(HUB_PANEL_ID)
    assert spec.layout.pages[0].rows == (
        ("st_tidepool", "st_dock", "st_boathouse", "st_fishery"),
        ("st_menu",))


def test_structure_render_composes_the_golden_embed(monkeypatch):
    """The fresh not-built Tide Pool render — goldens/fishing/
    sweep_tidepool pins the field + footer bytes."""
    from sb.domain.fishing.panels import _render_tide_pool, tide_pool_spec
    from sb.domain.mining import store as ms
    from sb.kernel.interaction.locale import LocaleContext

    async def get_structures(user_id, guild_id, conn=None):
        return {}

    monkeypatch.setattr(ms, "get_structures", get_structures)
    ctx = SimpleNamespace(actor=SimpleNamespace(user_id=P1), guild_id=GID,
                          params={}, args={}, locale=LocaleContext())
    rendered = run(_render_tide_pool(tide_pool_spec(), ctx))
    assert rendered.embed.fields == (
        ("Level", "**(not built)** (0/3)"),
        ("Current bonus", "no bonus yet"),
        ("Next: Reef Pool → +4% pull toward rarer fish",
         "3× coral + **1500** 🪙"),
    )
    assert rendered.embed.footer == "🪸 Build  •  ↩ Structures"
    assert rendered.embed.description == (
        "Stock a reef pool with **coral** to nudge your casts toward "
        "rarer fish. Coral drops on a **deepwater** reel (`!sail`) — "
        "the same coral you can carve into curios, now with a second, "
        "*useful* home.")


# --- the write ops + fences --------------------------------------------------------


def test_slice4_ops_registered_and_reasons():
    from sb.domain.fishing import ops
    from sb.domain.mining import market
    from sb.spec.refs import WorkflowRef, is_registered

    ops.ensure_ops_refs()
    assert is_registered(WorkflowRef("fishing.craft_curio"))
    assert is_registered(WorkflowRef("fishing.build_structure"))
    assert ops.CORAL_ITEM == "coral"
    # the shipped generic reason derivation (BUG-0031: never a KeyError)
    assert market.structure_build_reason("tide_pool") == \
        "mining:tide_pool_build"
    assert market.structure_build_reason("  Dock ") == "mining:dock_build"


# --- manifest + hub routes (the PENDING roster EMPTIES) ----------------------------


def test_manifest_and_hub_route_the_live_lanes():
    from sb.domain.fishing import service
    from sb.domain.fishing.panels import (
        STRUCTURES_PANEL_ID,
        fishing_hub_spec,
    )
    from sb.manifest.fishing import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["curios"].route == HandlerRef("fishing.curios_view")
    assert by_name["curios"].aliases == ("curio", "carvings")
    assert by_name["craftcurio"].route == HandlerRef(
        "fishing.craftcurio_route")
    assert by_name["craftcurio"].aliases == ("carve", "curiocraft")
    assert by_name["tidepool"].route == PanelRef("fishing.tide_pool_panel")
    assert by_name["tidepool"].aliases == ("reef", "tidepools")
    assert by_name["dock"].route == PanelRef("fishing.dock_panel")
    assert by_name["dock"].aliases == ("pier", "fishingdock")
    assert by_name["boathouse"].route == PanelRef(
        "fishing.boathouse_panel")
    assert by_name["boathouse"].aliases == ("moorings", "boat")
    assert by_name["fishery"].route == PanelRef("fishing.fishery_panel")
    assert by_name["fishery"].aliases == ("hatchery", "fishfarm")
    # the five new panels are declared manifest surfaces; NO new store
    # (mining_structures / mining_inventory stay mining-declared)
    panel_ids = {p.panel_id for p in MANIFEST.panels}
    for pid in ("fishing.structures_panel", "fishing.tide_pool_panel",
                "fishing.dock_panel", "fishing.boathouse_panel",
                "fishing.fishery_panel"):
        assert pid in panel_ids
    assert {s.table for s in MANIFEST.stores} == {
        "fishing_catch_log", "fishing_energy", "fishing_venue",
        "fishing_rod", "fishing_bait"}
    # the hub 🏗 Structures button repointed to the live sub-hub
    hub = fishing_hub_spec()
    by_id = {a.action_id: a for a in hub.actions}
    assert by_id["fishing_structures"].handler == PanelRef(
        STRUCTURES_PANEL_ID)
    # label/emoji/style unchanged — byte-neutral vs sweep_fishing
    assert by_id["fishing_structures"].label == "Structures"
    assert by_id["fishing_structures"].emoji == "🏗"
    # the PENDING roster is EMPTY (all 20 fishing commands live); no
    # *_pending ref registers any more (trap 12a) — including the
    # retired hub structures_pending terminal
    service.ensure_handler_refs()
    assert service.PENDING == {}
    for name in ("curios", "craftcurio", "tidepool", "dock", "boathouse",
                 "fishery", "structures"):
        assert not is_registered(HandlerRef(f"fishing.{name}_pending"))
