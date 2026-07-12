"""Band 7 — the per-crosspath combat-stats derivation (the stats
normal-view slice the boss estimator needs): ``tier_codes`` +
``TowerStats``/``HeroStats`` + ``normal_stats`` + ``attack_breakdown``.

Anchor provenance (the #225 "publish-your-own-anchors" method): every
constant below was produced by running the ORACLE's VERBATIM
``btd6_stats_service.py`` / ``tier_codes.py`` / ``paragon_degrees.py``
(fetched at oracle head b0713fcd, byte-identical to the corpus pin
7f7628e1) over this repo's committed ``sb/domain/btd6/data`` tree
(spot-verified byte-identical to the oracle's data at the same ref),
BEFORE the port was written. The oracle's own unit suites
(``tests/unit/services/test_btd6_stats_service.py``,
``tests/unit/utils/test_btd6_tier_codes.py`` @b0713fcd) pin the same
figures. The census test at the bottom pins a sha256 over EVERY tier's
full normal-view derivation corpus-wide — the oracle run and the port
produced identical digests.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from sb.domain.btd6 import stats as svc
from sb.domain.btd6 import tier_codes as tc

DATA_ROOT = Path(__file__).resolve().parents[3] / "sb" / "domain" / "btd6" / "data"


@pytest.fixture(autouse=True)
def _fresh_cache():
    svc.reset_stats_cache()
    yield
    svc.reset_stats_cache()


# --- tier_codes: the canonical crosspath-code logic (oracle suite) ----------


def test_is_valid_code():
    assert tc.is_valid_code("000")
    assert tc.is_valid_code("520")
    assert not tc.is_valid_code("00")  # too short
    assert not tc.is_valid_code("0a0")  # non-digit
    assert not tc.is_valid_code("060")  # 6 is out of range
    assert not tc.is_valid_code(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "code",
    ["000", "500", "050", "005", "520", "250", "220", "202", "022", "140", "014"],
)
def test_legal_codes(code):
    assert tc.is_legal(code)


@pytest.mark.parametrize(
    "code", ["111", "530", "350", "055", "333", "225", "252", "115"]
)
def test_illegal_codes(code):
    # >2 nonzero paths, or a second path above tier 2 — impossible in-game.
    assert not tc.is_legal(code)


def test_classification():
    assert tc.is_base("000")
    assert tc.is_single_path("500") and not tc.is_crosspath("500")
    assert tc.is_crosspath("520") and not tc.is_single_path("520")
    assert tc.nonzero_count("202") == 2


def test_primary_path_highest_tier_then_lowest_index():
    assert tc.primary_path("000") is None
    assert tc.primary_path("050") == 2
    assert tc.primary_path("025") == 3  # tier-5 path 3 is the main
    assert tc.primary_path("520") == 1  # tier-5 path 1
    assert tc.primary_path("202") == 1  # tie at tier 2 -> lowest index
    assert tc.primary_tier("025") == 5


def test_format_code():
    assert tc.format_code("202") == "2-0-2"
    assert tc.format_code("000") == "0-0-0"


def test_candidate_and_preferred_parent():
    assert set(tc.candidate_parents("220")) == {"200", "020"}
    assert set(tc.candidate_parents("025")) == {"020", "005"}
    assert tc.preferred_parent(["200", "020"]) == "200"  # tie tier -> lower path
    assert tc.preferred_parent(["005", "050"]) == "050"  # tie tier-5 -> lower path
    assert tc.preferred_parent(["500", "010"]) == "500"  # higher tier wins
    with pytest.raises(ValueError):
        tc.preferred_parent([])


def test_digits_rejects_invalid():
    with pytest.raises(ValueError):
        tc.digits("0a0")


def test_ordered_codes_canonical_first():
    ordered = tc.ordered_codes(["202", "000", "500", "210"])
    assert ordered[0] == "000"
    assert ordered.index("500") < ordered.index("202")  # canonical before crosspaths
    assert set(ordered) == {"202", "000", "500", "210"}


# --- tower stats: loader + accessors (oracle suite + oracle-run anchors) ----


def test_loads_bomb_shooter():
    stats = svc.get_tower_stats("bomb_shooter")
    assert stats is not None
    assert stats.has_combat_stats
    assert stats.canonical == "BombShooter"  # game-native canonical in the data
    assert stats.base_cost == 375
    assert stats.paragon_cost == 600000
    assert len(stats.upgrades) == 15
    codes = stats.tier_codes()
    # The 16 single-path tiers come first (in canonical order), then crosspaths.
    assert codes[:16] == tc.SINGLE_PATH_CODES
    assert len(codes) == 64  # crosspath tiers are reconstructed and kept


def test_missing_tower_returns_none():
    assert svc.get_tower_stats("does_not_exist") is None


def test_normal_stats_base_bomb_shooter():
    stats = svc.get_tower_stats("bomb_shooter")
    ns = svc.normal_stats(stats.tier("000"))
    assert ns.damage == 1
    assert ns.damage_type == "Explosion"
    assert ns.cannot_pop == "Cannot damage Black"
    assert ns.pierce == 22
    assert ns.cooldown == 1.5
    assert ns.attack_range == 40
    assert ns.can_see_camo is False  # bomb can't see camo
    assert ns.specials == ()


def test_normal_stats_bloon_crush_flips_to_normal_and_stuns():
    stats = svc.get_tower_stats("bomb_shooter")
    ns = svc.normal_stats(stats.tier("500"))
    assert ns.damage == 24
    assert ns.damage_type == "Normal"
    # Oracle-run anchor: the full specials tuple, order included.
    assert ns.specials == ("Knockback", "Stun 2s")


def test_normal_stats_excludes_reanimated_minions_for_prince_of_darkness():
    # Prince of Darkness (wizard 0-0-5) fires reanimated "MOAB"/"BFB" projectiles
    # (40/100 dmg). Those are minions, not the tower's hit, so the headline must
    # not report 100 — it reports the highest own-attack projectile instead.
    stats = svc.get_tower_stats("wizard_monkey")
    ns = svc.normal_stats(stats.tier("005"))
    assert ns.damage == 2  # the Reanimate hit, not the reanimated BFB's 100
    assert ns.pierce == 1
    assert ns.cooldown == 0.275


def test_normal_stats_surfaces_moab_bonus_and_ability():
    stats = svc.get_tower_stats("bomb_shooter")
    ns = svc.normal_stats(stats.tier("040"))  # MOAB Assassin
    # Oracle-run anchor: exact bytes and order.
    assert ns.specials == ("+30 vs MOAB-Class", "Ability (30s cooldown)")


def test_normal_stats_surfaces_income():
    # Druid: Spirit of the Forest (0-5-0) gives passive income.
    druid = svc.get_tower_stats("druid")
    ns = svc.normal_stats(druid.tier("050"))
    assert ns.specials == ("Income $1,000/round", "Ability (30s cooldown)")
    # Sniper: Supply Drop (0-4-0) drops a cash crate.
    sniper = svc.get_tower_stats("sniper_monkey")
    ns = svc.normal_stats(sniper.tier("040"))
    assert ns.specials == ("Ability (90s cooldown)", "Cash crate $1,100")


def test_economy_tower_has_costs_and_tiers_but_no_attacks():
    # Since the oracle's Q-0067 cutover the Farm has full game-native tiers
    # (abilities, buffs, income) — but its nominal banana "attack" is
    # suppressed, so no tier carries combat numbers.
    farm = svc.get_tower_stats("banana_farm")
    assert farm is not None
    assert farm.base_cost == 1250
    assert farm.has_combat_stats is True
    assert farm.tier_codes()[0] == "000"
    base = svc.normal_stats(farm.tier("000"))
    assert base.damage is None and base.cooldown is None
    assert all(t.get("attacks") == [] for t in farm.tiers.values())


def test_farm_economy_specials_surface():
    # Oracle's post-cutover decode wave (2026-06-10): banana value / bonus /
    # bank terms lift off the suppressed banana attack and surface as specials.
    farm = svc.get_tower_stats("banana_farm")
    base = svc.normal_stats(farm.tier("000"))
    assert "Bananas worth $20" in base.specials
    bank = svc.normal_stats(farm.tier("030"))
    # Oracle-run anchor: exact tuple, order included.
    assert bank.specials == (
        "Bananas worth $45",
        "+25% banana value",
        "Bank $7,000 capacity, +15% interest/round",
    )


# --- crosspaths (reconstructed) + back-compat --------------------------------


def test_crosspaths_for_returns_tier_crosspaths():
    stats = svc.get_tower_stats("bomb_shooter")
    cps = stats.crosspaths_for("200")
    # Oracle-run anchor: the full display-ordered tuple.
    assert cps == (
        "201", "202", "203", "204", "205",
        "210", "220", "230", "240", "250",
    )  # fmt: skip
    assert all(tc.digits(c)[0] == 2 for c in cps)
    assert all(tc.is_crosspath(c) for c in cps)


def test_crosspaths_for_base_or_crosspath_is_empty():
    stats = svc.get_tower_stats("bomb_shooter")
    assert stats.crosspaths_for("000") == ()  # base has none
    assert stats.crosspaths_for("220") == ()  # not a single-path code


def test_old_style_16_tier_file_back_compat():
    # No committed file is 16-tier any more (the cutover gave Beast Handler its
    # full 64, incl. dual-beast crosspaths) — keep the degrade path pinned with
    # a synthetic single-path-only stats object.
    bh = svc.get_tower_stats("beast_handler")
    assert bh is not None and bh.has_combat_stats
    assert bh.tier_codes()[0] == "000"
    assert "320" in bh.tiers  # dual-beast crosspaths are real data
    sparse = dataclasses.replace(
        bh,
        tiers={c: t for c, t in bh.tiers.items() if not tc.is_crosspath(c)},
    )
    assert sparse.crosspaths_for("100") == ()


def test_normal_stats_works_on_a_crosspath_node():
    stats = svc.get_tower_stats("bomb_shooter")
    node = stats.tier("202")
    assert node is not None
    ns = svc.normal_stats(node)  # must not crash on a crosspath tier
    assert ns.damage is not None


# --- heroes: per-level stats --------------------------------------------------


def test_loads_quincy_hero_stats():
    stats = svc.get_hero_stats("quincy")
    assert stats is not None
    assert stats.has_combat_stats
    assert stats.base_cost == 540
    assert len(stats.level_codes()) == 20
    assert stats.level_codes()[0] == "1"
    assert stats.level_codes()[-1] == "20"


def test_unknown_hero_returns_none():
    # A hero id with no committed stats file degrades to None, not a crash.
    assert svc.get_hero_stats("does_not_exist") is None


def test_game_data_closed_the_obyn_stats_gap():
    # Obyn attacks in-game but bloonswiki never had a stats module for him; the
    # oracle's BTD Mod Helper game-data export does, so he has per-level stats.
    stats = svc.get_hero_stats("obyn_greenfoot")
    assert stats is not None
    assert stats.level("1") is not None


def test_hero_level_progression_uses_normal_stats():
    stats = svc.get_hero_stats("quincy")
    # normal_stats consumes a hero level node exactly like a tower tier.
    l1 = svc.normal_stats(stats.level("1"))
    l20 = svc.normal_stats(stats.level("20"))
    assert (l1.pierce, l1.cooldown, l1.can_see_camo) == (3, 0.95, False)
    assert (l20.pierce, l20.cooldown, l20.can_see_camo) == (9, 0.2, True)
    assert l20.cooldown < l1.cooldown  # attacks faster at max level


# --- per-attack breakdown (towers at base; paragons scaled by degree) --------


def test_attack_breakdown_tower_base_values():
    # Oracle-run anchor: bomb base = one attack, one projectile, base values.
    bomb = svc.get_tower_stats("bomb_shooter")
    bb = svc.attack_breakdown(bomb.tier("000").get("attacks") or [])
    assert bb == (
        svc.DegreeAttack(name="Attack", cooldown=1.5, projectiles=(("Explosion", 1.0, 22.0),)),
    )
    # The estimator's own consumption shape: super monkey 2-0-4.
    sm = svc.get_tower_stats("super_monkey")
    sm_bd = svc.attack_breakdown(sm.tier("204").get("attacks") or [])
    assert sm_bd == (
        svc.DegreeAttack(name="Attack", cooldown=0.015, projectiles=(("Projectile", 2.0, 9.0),)),
    )


def test_paragon_stats_at_degree_gives_nonlinear_per_attack_breakdown():
    pid = svc.resolve_paragon_id("Goliath Doomship")
    assert pid == "goliath_doomship"
    s = svc.paragon_stats_at_degree(pid, 65)
    # Authoritative breakdown: 3 attacks, each with its real projectiles — the
    # main bomb keeps BOTH its direct projectile AND its explosion (the exact
    # components that a single "DPS" number hides).
    assert len(s.attacks) == 3
    main = s.attacks[0]
    # Oracle-run anchors (game-native names since the cutover).
    assert main.cooldown == 0.4215  # sqrt curve, NOT linear interpolation
    assert main.projectiles == (
        ("MainProjectile", 334.0, 63.4),
        ("Projectile", 498.0, 7.4),
    )
    assert s.rough_dps == 7532.4
    assert s.boss_multiplier == 1.75
    assert s.power == 77910
    # Degree-100 jump: a projectile's damage = base*2 + 10, not a linear trend.
    d1 = svc.paragon_stats_at_degree(pid, 1).attacks[0].projectiles[0][1]
    d100 = svc.paragon_stats_at_degree(pid, 100).attacks[0].projectiles[0][1]
    assert (d1, d100) == (200.0, 410.0)
    assert d100 == round(d1 * 2 + 10, 1)


def test_paragon_stats_at_degree_clamps_and_degrades():
    # Degree clamps into 1..100; unknown paragon degrades to None.
    s = svc.paragon_stats_at_degree("goliath_doomship", 0)
    assert s is not None and s.degree == 1
    s = svc.paragon_stats_at_degree("goliath_doomship", 999)
    assert s is not None and s.degree == 100
    assert svc.paragon_stats_at_degree("does_not_exist", 50) is None


def test_rough_attack_dps_sums_all_projectiles_and_is_none_for_economy():
    # Goliath's main bomb = direct + explosion per shot, so the rough DPS
    # counts both, not just the highest.
    goliath = svc.get_paragon_stats("goliath_doomship").base["attacks"]
    assert svc.main_projectile_stats(goliath, 1) == (300.0, 1.0)
    main_only = svc.main_projectile_stats(goliath, 1)[0] / 0.66  # explosion / cd
    rough = svc.rough_attack_dps(goliath[:1], 1)  # just the main attack
    assert rough == 757.6  # oracle-run anchor
    assert rough > main_only  # summing both projectiles beats the single highest
    # No damaging attack (e.g. an economy tower's tier) -> None.
    assert svc.rough_attack_dps([]) is None


# --- corpus-wide census: the port == the oracle's verbatim code --------------


def test_normal_view_census_matches_oracle_run():
    """Full-corpus equivalence pin.

    The ORACLE's verbatim ``btd6_stats_service`` (fetched @b0713fcd,
    byte-identical to the corpus pin @7f7628e1) was executed over this
    repo's committed data tree; hashing every tower's every tier's full
    normal view produced exactly this census + digest. The port must
    reproduce it byte-for-byte.
    """
    towers_json = json.loads((DATA_ROOT / "towers.json").read_text(encoding="utf-8"))
    ids = sorted(t.get("id") for t in (towers_json.get("towers") or []) if t.get("id"))
    census = {"towers": 0, "tiers": 0, "camo_true": 0, "specials_total": 0}
    digest = hashlib.sha256()
    for tid in ids:
        st = svc.get_tower_stats(tid)
        if st is None or not st.tiers:
            continue
        census["towers"] += 1
        for code in st.tier_codes():
            n = svc.normal_stats(st.tier(code))
            census["tiers"] += 1
            census["camo_true"] += 1 if n.can_see_camo else 0
            census["specials_total"] += len(n.specials)
            digest.update(
                repr(
                    (
                        tid,
                        code,
                        n.damage,
                        n.damage_type,
                        n.cannot_pop,
                        n.pierce,
                        n.cooldown,
                        n.attack_range,
                        n.can_see_camo,
                        n.specials,
                    ),
                ).encode(),
            )
    assert census == {
        "towers": 25,
        "tiers": 1600,
        "camo_true": 627,
        "specials_total": 818,
    }
    assert (
        digest.hexdigest()
        == "c80965540c6f0f552ae10680ff3c92a908c09a0e3aa52bb01cb05114ac758741"
    )
