"""Slice-1 equipment/skills/character port — the pure gear→stats read model
(ported verbatim from the oracle utils/equipment.py + utils/mining/*).

The load-bearing safety property for the D-0045 deferral: ``compute_stats({})``
and ``character_stats({}, {})`` are all-zero, so deathmatch/casino read the
shipped baseline and no golden moves. The set-bonus / durability / branch
mappings are pinned verbatim.
"""

from __future__ import annotations

from dataclasses import astuple

from sb.domain.mining import character, equipment, loadout, skills, workshop


def test_effective_stats_default_all_zero():
    assert astuple(equipment.EffectiveStats()) == (0,) * 10


def test_effective_stats_additive():
    a = equipment.EffectiveStats(mining_power=2, damage=3)
    b = equipment.EffectiveStats(mining_power=1, defense=4)
    assert a + b == equipment.EffectiveStats(mining_power=3, damage=3,
                                             defense=4)


def test_compute_stats_empty_is_all_zero():
    # D-0045: gearless personas duel at the shipped baseline.
    assert equipment.compute_stats({}) == equipment.EffectiveStats()


def test_gear_catalog_spot_values():
    assert equipment.item_stats("iron pickaxe") == equipment.EffectiveStats(
        mining_power=4)
    assert equipment.item_stats("diamond lantern") == equipment.EffectiveStats(
        light_radius=3, depth_access=3)
    assert equipment.item_stats("master angler charm") == \
        equipment.EffectiveStats(fishing_power=6, bite_luck=3)
    # unknown item contributes nothing
    assert equipment.item_stats("banana") == equipment.EffectiveStats()


def test_slot_for_lowercases():
    assert equipment.slot_for("Iron Pickaxe") == equipment.TOOL
    assert equipment.slot_for("diamond chestplate") == equipment.CHESTPLATE
    assert equipment.slot_for("banana") is None


def test_slots_order_is_byte_load_bearing():
    # the !unequip guard string enumerates SLOTS in this exact order.
    assert equipment.SLOTS == (
        "tool", "light", "charm", "weapon", "shield", "helmet",
        "chestplate", "leggings", "boots")


def test_full_diamond_set_bonus():
    equipped = {
        "weapon": "diamond sword", "shield": "diamond shield",
        "helmet": "diamond helmet", "chestplate": "diamond chestplate",
        "leggings": "diamond leggings", "boots": "diamond boots",
    }
    assert equipment.active_set_tier(equipped) == "diamond"
    # idx=5 → damage +5, max_health +15 on top of the piece sums.
    bonus = equipment.set_bonus(equipped)
    assert bonus == equipment.EffectiveStats(damage=5, max_health=15)


def test_partial_set_progress_and_no_bonus():
    equipped = {"weapon": "bronze sword", "shield": "bronze shield"}
    assert equipment.active_set_tier(equipped) is None
    assert equipment.set_bonus(equipped) == equipment.EffectiveStats()
    assert equipment.set_progress(equipped) == ("bronze", 2)


def test_max_durability_ladder():
    assert equipment.max_durability("pickaxe") == 60
    assert equipment.max_durability("bronze sword") == 80
    assert equipment.max_durability("diamond boots") == 320
    assert equipment.max_durability("banana") is None


def test_branch_stats_mapping():
    assert skills.branch_stats("mining", 5) == equipment.EffectiveStats(
        mining_power=5)
    assert skills.branch_stats("combat", 5) == equipment.EffectiveStats(
        damage=2, max_health=10)
    assert skills.branch_stats("fortune", 5) == equipment.EffectiveStats(
        luck=5, loot_bonus=2)
    assert skills.branch_stats("crafting", 5) == equipment.EffectiveStats(
        loot_bonus=5)
    assert skills.branch_stats("mining", 0) == equipment.EffectiveStats()
    assert skills.branch_stats("bogus", 5) == equipment.EffectiveStats()


def test_skill_caps():
    assert skills.PER_BRANCH_CAP == 10
    assert skills.SOFT_TOTAL_CAP == 20
    assert skills.SOFT_TOTAL_CAP < len(skills.BRANCHES) * skills.PER_BRANCH_CAP


def test_character_stats_empty_alloc_equals_gear_only():
    equipped = {"tool": "iron pickaxe", "light": "lantern"}
    assert character.character_stats(equipped, {}) == \
        equipment.compute_stats(equipped)
    assert character.character_stats(equipped, None) == \
        equipment.compute_stats(equipped)


def test_character_stats_adds_skills():
    equipped = {"tool": "pickaxe"}
    got = character.character_stats(equipped, {"mining": 3})
    assert got == equipment.EffectiveStats(mining_power=5)  # 2 gear + 3 skill


def test_best_loadout_prefers_full_set_over_greedy():
    # owning a full bronze set + one stronger iron chestplate: the set bonus
    # must not be broken for the single higher-tier piece.
    inv = {
        "bronze sword": 1, "bronze shield": 1, "bronze helmet": 1,
        "bronze chestplate": 1, "bronze leggings": 1, "bronze boots": 1,
        "iron chestplate": 1,
    }
    picked = loadout.best_loadout(inv)
    assert picked["chestplate"] == "bronze chestplate"
    assert equipment.active_set_tier(picked) == "bronze"


def test_durability_bar_shape():
    assert workshop.durability_bar(23, 60) == "▰▰▱▱▱ 23/60"
    assert workshop.durability_bar(60, 60) == "▰▰▰▰▰ 60/60"
    assert workshop.durability_bar(5, 0) == "5/0"
