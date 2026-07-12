"""Band 7 — the boss-fight estimator (``sb/domain/btd6/estimator.py``,
the port of shipped ``services/btd6_estimator_service.py``) + its
``estimate_card`` command surface: deterministic kill-time / cost / DPS
arithmetic over the #237 combat-stats seam.

Anchor provenance (the #225/#237 "publish-your-own-anchors" method,
raw-file lane): every constant below was produced by running the
ORACLE'S VERBATIM ``btd6_estimator_service.py`` (fetched whole at the
corpus pin 7f7628e1, byte-identical to oracle head b0713fcd) over this
repo's committed ``sb/domain/btd6/data`` tree, composed with the
oracle-verbatim stats/tier_codes stack and the ported resolver (#208,
itself anchor-verified), BEFORE the port was written. The port re-ran
the identical harness: every value below — including the corpus-wide
census digests — was byte-identical between the two runs (harness
GLOBAL sha256 5193d02961e3a2d1… on both).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pytest

from sb.domain.btd6 import dataset
from sb.domain.btd6 import estimator as est
from sb.domain.btd6 import stats as svc
from sb.domain.btd6 import tier_codes as tc


@pytest.fixture(autouse=True)
def _fresh_cache():
    svc.reset_stats_cache()
    est.reset_cache_for_tests()
    dataset.reset_cache()
    yield
    svc.reset_stats_cache()
    est.reset_cache_for_tests()
    dataset.reset_cache()


# --- cost_for_code / dps_for_code (oracle-run anchors) ----------------------


@pytest.mark.parametrize(
    ("tower_id", "code", "cost", "dps"),
    [
        ("dart_monkey", "300", 860, 1.7),
        ("bomb_shooter", "000", 375, 0.7),
        ("bomb_shooter", "520", 60825, 29.1),
        ("sniper_monkey", "500", 42500, 105.7),
        ("super_monkey", "000", 2500, 22.2),
        ("super_monkey", "024", 71255, 88.9),
        # Druid 005: the 9,999,999 Vine instakill sentinel is excluded by
        # _INSTAKILL_DAMAGE_CAP — 7.3, not millions.
        ("druid", "005", 48750, 7.3),
    ],
)
def test_cost_and_dps_anchors(tower_id, code, cost, dps):
    stats = svc.get_tower_stats(tower_id)
    assert stats is not None
    assert est.cost_for_code(stats, code) == cost
    assert est.dps_for_code(stats, code) == dps


def test_cost_for_code_rejects_malformed():
    stats = svc.get_tower_stats("bomb_shooter")
    assert est.cost_for_code(stats, "0a0") is None
    assert est.cost_for_code(stats, "60") is None


# --- find_boss ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "boss_id"),
    [
        ("bloonarius", "bloonarius"),
        ("Bloonarius t5", "bloonarius"),
        ("counters for lych", "lych"),
        ("vortex please", "vortex"),
        ("BLASTAPOPOULOS", "blastapopoulos"),
        ("dreadbloon tier 3", "dreadbloon"),
        ("phayze", "phayze"),
        ("diamondback", "diamondback"),
        # dataset order wins when two bosses are named (bloonarius first):
        ("lych vs bloonarius", "bloonarius"),
        ("nonexistent boss", None),
        ("", None),
        ("boss", None),
    ],
)
def test_find_boss(query, boss_id):
    boss = est.find_boss(query)
    assert (boss.id if boss else None) == boss_id


# --- find_map_track (greedy longest-name substring) ---------------------------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("monkey meadow", ("Monkey Meadow", 32.745)),
        ("MONKEY MEADOW", ("Monkey Meadow", 32.745)),
        ("on dark castle please", ("Dark Castle", 11.555)),
        ("super monkey vs bloonarius on infernal", ("Infernal", 21.975)),
        ("logs", ("Logs", 60.33)),
        ("quad", ("Quad", 12.68)),
        ("#ouch", ("#Ouch", 4.52)),
        ("nonsense map", None),
        ("", None),
    ],
)
def test_find_map_track(query, expected):
    assert est.find_map_track(query) == expected


def test_track_index_census():
    # 60 committed tracks, longest-canonical-first; full-index digest from
    # the oracle-verbatim run.
    rows = est._track_index()
    assert len(rows) == 60
    digest = hashlib.sha256(
        json.dumps([list(r) for r in rows]).encode()).hexdigest()
    assert digest == (
        "ee069c68e1b9f2d7c504c91c9db4c8e5d950e48211e356335b9f2af62580dc16")


# --- parse_request -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("super monkey 0-4-0 vs bloonarius t5",
         ("single", "super monkey 0-4-0", "bloonarius", 5, "")),
        ("super monkey 0-4-0 vs bloonarius",
         ("single", "super monkey 0-4-0", "bloonarius", 5, "")),
        ("counters for bloonarius tier 3", ("counters", "", "bloonarius", 3, "")),
        ("bloonarius", ("counters", "", "bloonarius", 5, "")),
        ("cheapest to lych t2", ("counters", "", "lych", 2, "")),
        # shipped quirk, carried: " vs " wins before the counters-prefix strip,
        # so "best vs vortex" reads as a SINGLE estimate for tower "best".
        ("best vs vortex", ("single", "best", "vortex", 5, "")),
        ("dart monkey versus phayze tier 1 on monkey meadow",
         ("single", "dart monkey", "phayze", 1, "Monkey Meadow")),
        # "500" in the tower text is a crosspath, not a boss tier — tier
        # stays the default 5.
        ("sniper 500 vs dreadbloon on dark castle",
         ("single", "sniper 500", "dreadbloon", 5, "Dark Castle")),
        ("counters lych", ("counters", "", "lych", 5, "")),
        ("", ("counters", "", "", 5, "")),
        ("  counters   for   BLOONARIUS   T4  ",
         ("counters", "", "BLOONARIUS", 4, "")),
        ("ninja vs bloonarius on logs t3", ("single", "ninja", "bloonarius", 3, "Logs")),
    ],
)
def test_parse_request(text, expected):
    req = est.parse_request(text)
    assert (req.mode, req.tower_query, req.boss_query, req.tier,
            req.map_query) == expected


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("super monkey 0-2-4", "024"),
        ("204 dartling", "204"),
        ("5-2-0 bomb", "520"),
        ("2-2-2 x", "222"),  # extraction is by-shape; legality is not checked
        ("600 thing", "000"),
        ("no code here", "000"),
        ("0 - 4 - 0 sniper", "040"),
        ("025", "025"),
    ],
)
def test_extract_code(text, code):
    assert est._extract_code(text) == code


# --- estimate (full KillEstimate anchors) --------------------------------------


def test_estimate_super_vs_bloonarius_t5():
    ke = est.estimate("super_monkey", "024", "bloonarius", 5)
    assert ke is not None
    assert asdict(ke) == {
        "tower_id": "super_monkey",
        "tower_canonical": "SuperMonkey",
        "crosspath": "0-2-4",
        "cost": 71255,
        "dps": 88.9,
        "damage_type": "Normal",
        "sees_camo": True,
        "boss_id": "bloonarius",
        "boss_canonical": "Bloonarius",
        "boss_tier": 5,
        "boss_hp": 3000000,
        "boss_speed": 1.5,
        "time_to_kill_s": 33745.8,
        "blocked_by_immunity": False,
        "boss_immune_to": (),
        "map_canonical": None,
        "track_rbs": None,
        "boss_cross_s": None,
        "kills_before_exit": None,
        "assumptions": est._ASSUMPTIONS,
    }


def test_estimate_immunity_blocked():
    # Dreadbloon is immune to Sharp — a 0-0-0 DartMonkey cannot damage it.
    ke = est.estimate("dart_monkey", "000", "dreadbloon", 1)
    assert ke is not None
    assert ke.damage_type == "Sharp"
    assert ke.blocked_by_immunity is True
    assert ke.time_to_kill_s is None
    assert ke.boss_immune_to == ("Cold", "Energy", "Sharp", "Shatter")
    assert ke.sees_camo is False


def test_estimate_track_context_kills_before_exit():
    ke = est.estimate("dartling_gunner", "520", "bloonarius", 1, "logs")
    assert ke is not None
    assert (ke.map_canonical, ke.track_rbs, ke.boss_cross_s,
            ke.kills_before_exit) == ("Logs", 60.33, 48.3, True)
    assert (ke.dps, ke.cost, ke.time_to_kill_s) == (1287.9, 93000, 15.5)


def test_estimate_track_context_too_slow():
    ke = est.estimate("druid", "005", "vortex", 5, "monkey meadow")
    assert ke is not None
    assert (ke.map_canonical, ke.track_rbs, ke.boss_cross_s,
            ke.kills_before_exit) == ("Monkey Meadow", 32.745, 7.8, False)
    assert (ke.boss_hp, ke.boss_speed, ke.time_to_kill_s) == (
        2512500, 4.2, 344178.1)


def test_estimate_zero_dps_and_misses():
    ke = est.estimate("banana_farm", "000", "bloonarius", 5)
    assert ke is not None
    assert ke.dps == 0.0 and ke.time_to_kill_s is None
    assert ke.blocked_by_immunity is False
    assert est.estimate("super_monkey", "024", "nosuchboss", 5) is None
    assert est.estimate("nosuchtower", "000", "bloonarius", 5) is None
    assert est.estimate("super_monkey", "024", "bloonarius", 9) is None


def test_resolve_and_estimate():
    ke = est.resolve_and_estimate("super monkey 0-4-0", "bloonarius t5", 5)
    assert ke is not None and ke.tower_id == "super_monkey"
    assert ke.crosspath == "0-4-0"
    assert est.resolve_and_estimate("nonsense tower xyzzy", "bloonarius", 5) is None
    assert est.resolve_and_estimate("dart monkey", "no boss here", 5) is None


# --- cheapest_counters -----------------------------------------------------------


def test_cheapest_counters_bloonarius_t5_full_rows():
    rows = [asdict(r) for r in est.cheapest_counters("bloonarius", 5, limit=5)]
    assert rows == [
        {"tower_id": "monkey_buccaneer", "tower_canonical": "MonkeyBuccaneer",
         "crosspath": "0-3-0", "cost": 2350, "dps": 140.0,
         "dps_per_dollar": 0.0596, "time_to_kill_s": 21428.6},
        {"tower_id": "dartling_gunner", "tower_canonical": "DartlingGunner",
         "crosspath": "5-2-0", "cost": 93000, "dps": 1287.9,
         "dps_per_dollar": 0.0138, "time_to_kill_s": 2329.4},
        {"tower_id": "mermonkey", "tower_canonical": "Mermonkey",
         "crosspath": "3-0-0", "cost": 2500, "dps": 27.4,
         "dps_per_dollar": 0.011, "time_to_kill_s": 109489.1},
        {"tower_id": "monkey_ace", "tower_canonical": "MonkeyAce",
         "crosspath": "1-0-5", "cost": 118250, "dps": 1104.8,
         "dps_per_dollar": 0.0093, "time_to_kill_s": 2715.4},
        {"tower_id": "super_monkey", "tower_canonical": "SuperMonkey",
         "crosspath": "0-0-0", "cost": 2500, "dps": 22.2,
         "dps_per_dollar": 0.0089, "time_to_kill_s": 135135.1},
    ]


def test_cheapest_counters_edges():
    # limit clamps at 1 (oracle `max(1, limit)`);
    rows = est.cheapest_counters("bloonarius", 5, limit=0)
    assert len(rows) == 1 and rows[0].tower_id == "monkey_buccaneer"
    assert est.cheapest_counters("nope", 5) == []
    assert est.cheapest_counters("bloonarius", 9) == []


def test_counters_census_all_bosses_all_tiers():
    """The enumerable ranking surface, corpus-wide: every boss × tier 1–5,
    full rows + full rank text — digests from the oracle-verbatim run."""
    counters = {}
    counters_fmt = {}
    for boss in dataset.bosses():
        for tier in range(1, 6):
            rows = est.cheapest_counters(boss.id, tier, limit=5)
            counters[f"{boss.id}|{tier}"] = [asdict(r) for r in rows]
            counters_fmt[f"{boss.id}|{tier}"] = est.format_counters_text(
                rows, boss.canonical or boss.id, tier)
    assert len(counters) == 35
    digest = hashlib.sha256(
        json.dumps(counters, sort_keys=True).encode()).hexdigest()
    assert digest == (
        "81159c1c9f8e14a628105dd8ce50f18c7b00a4ab297591b6e5a8163403d12036")
    fmt_digest = hashlib.sha256(
        json.dumps(counters_fmt, sort_keys=True).encode()).hexdigest()
    assert fmt_digest == (
        "aa0719f65c78799728876962b168240a79fbadabcf98d62158c5c7bbf75279b4")


def test_cost_dps_census():
    """Every tower × every present valid+legal crosspath: (cost, dps) —
    1600 derivations, digest identical between the oracle-verbatim run
    and the port."""
    rows = []
    for tower in dataset.towers():
        stats = svc.get_tower_stats(tower.id)
        if stats is None or not stats.has_combat_stats:
            continue
        for code in sorted(stats.tiers):
            if not tc.is_valid_code(code) or not tc.is_legal(code):
                continue
            rows.append([tower.id, code, est.cost_for_code(stats, code),
                         est.dps_for_code(stats, code)])
    assert len(rows) == 1600
    digest = hashlib.sha256(
        json.dumps(rows, sort_keys=True).encode()).hexdigest()
    assert digest == (
        "39970a7c32914cfb5a364710ee3322757b2cb25a94e16346196cdcf2a6cb6380")


# --- text formatters (byte anchors from the oracle run) --------------------------


def test_fmt_duration_table():
    assert est._fmt_duration(None) == "—"
    assert est._fmt_duration(0.0) == "~0s"
    assert est._fmt_duration(1.4) == "~1s"
    assert est._fmt_duration(89.9) == "~90s"
    assert est._fmt_duration(90.0) == "~1.5 min"
    assert est._fmt_duration(5399.9) == "~90.0 min"
    assert est._fmt_duration(5400.0) == "~1.5 hr"
    assert est._fmt_duration(123456.0) == "~34.3 hr"


def test_format_estimate_text_plain():
    ke = est.estimate("super_monkey", "024", "bloonarius", 5)
    assert est.format_estimate_text(ke) == (
        "**SuperMonkey (0-2-4)** vs **Bloonarius Tier 5**\n"
        "• Boss HP: **3,000,000** (speed 1.5)\n"
        "• Tower: ~**89 DPS** (Normal damage), cost **$71,255**\n"
        "• Estimated solo kill time: **~9.4 hr** (3,000,000 HP ÷ 89 DPS)\n"
        "_Estimate — base single-target DPS (excludes MOAB/boss bonus "
        "damage, abilities, buffs); ignores targeting, pierce, AoE, uptime, "
        "and boss damage-resistance phases; one tower, no support "
        "(Alchemist/Village) buffs._")


def test_format_estimate_text_immunity_and_camo():
    ke = est.estimate("dart_monkey", "000", "dreadbloon", 1)
    text = est.format_estimate_text(ke)
    assert text.startswith(
        "**DartMonkey (0-0-0)** vs **Dreadbloon Tier 1**\n"
        "• Boss HP: **7,500** (speed 1.25)\n"
        "• Tower: ~**1 DPS** (Sharp damage), cost **$200** — ⚠️ no camo "
        "detection\n"
        "• ⛔ This boss is immune to **Sharp** — that tower can't damage it. "
        "(Immune to: Cold, Energy, Sharp, Shatter.)")


def test_format_estimate_text_track_lines():
    ke = est.estimate("dartling_gunner", "520", "bloonarius", 1, "logs")
    text = est.format_estimate_text(ke)
    assert ("• **Logs** track: ~60s for a red bloon; this boss crosses in "
            "~48s\n"
            "• ✅ Kills it in ~16s — **before** one unobstructed pass "
            "(~48s).") in text
    ke2 = est.estimate("druid", "005", "vortex", 5, "monkey meadow")
    text2 = est.format_estimate_text(ke2)
    assert ("• ⚠️ Solo kill (~95.6 hr) is **slower** than one pass (~8s) — "
            "you'd need more DPS or stalling (bosses do pause at skull "
            "phases, so you usually get longer).") in text2


def test_format_counters_text_bloonarius_t5():
    rows = est.cheapest_counters("bloonarius", 5, limit=5)
    assert est.format_counters_text(rows, "Bloonarius", 5) == (
        "**Most DPS-per-dollar vs Bloonarius Tier 5** (base DPS, single "
        "tower):\n"
        "1. **MonkeyBuccaneer 0-3-0** — ~140 DPS, $2,350 (solo kill ~6.0 hr)\n"
        "2. **DartlingGunner 5-2-0** — ~1,288 DPS, $93,000 (solo kill "
        "~38.8 min)\n"
        "3. **Mermonkey 3-0-0** — ~27 DPS, $2,500 (solo kill ~30.4 hr)\n"
        "4. **MonkeyAce 1-0-5** — ~1,105 DPS, $118,250 (solo kill ~45.3 min)\n"
        "5. **SuperMonkey 0-0-0** — ~22 DPS, $2,500 (solo kill ~37.5 hr)\n"
        "_Estimate — base single-target DPS; excludes "
        "abilities/buffs/bonuses._")


def test_format_counters_text_empty():
    assert est.format_counters_text([], "Bloonarius", 5) == (
        "No tower estimates available for Bloonarius Tier 5.")


# --- the estimate_card command surface -------------------------------------------


def test_estimate_card_single():
    from sb.domain.btd6 import oracle_cards as cards

    card = cards.estimate_card("super monkey 0-2-4 vs bloonarius t5")
    assert card.title == "🎯 BTD6 boss-fight estimate"
    assert card.style_token == "blurple"
    assert card.description == est.format_estimate_text(
        est.estimate("super_monkey", "024", "bloonarius", 5))


def test_estimate_card_counters():
    from sb.domain.btd6 import oracle_cards as cards

    card = cards.estimate_card("counters for bloonarius tier 5")
    rows = est.cheapest_counters("bloonarius", 5, limit=5)
    assert card.description == est.format_counters_text(rows, "Bloonarius", 5)


def test_estimate_card_unresolvable_and_unknown_boss():
    from sb.domain.btd6 import oracle_cards as cards

    card = cards.estimate_card("xyzzy vs bloonarius")
    assert card.description == (
        "I couldn't resolve that — try `<tower> vs <boss> [tier]`. "
        "(Read tower=`xyzzy`, boss=`bloonarius`, tier 5.)")
    card2 = cards.estimate_card("counters for zomg")
    assert card2.description == (
        "I don't have a boss matching `zomg`. Bosses: Bloonarius, Lych, "
        "Vortex, Dreadbloon, Blastapopoulos, Phayze, Diamondback.")


def test_estimate_usage_card_unchanged():
    # the golden-pinned bare-usage bytes (goldens/btd6/sweep_btd6_estimate).
    from sb.domain.btd6 import oracle_cards as cards

    card = cards.estimate_usage_card()
    assert card.title == "🎯 BTD6 boss-fight estimate"
    assert card.description == (
        "Estimate a boss fight from grounded HP/DPS/cost:\n"
        "• `<tower> vs <boss> [tier]` — e.g. "
        "`super monkey 0-4-0 vs bloonarius t5`\n"
        "• `counters <boss> [tier]` — the most cost-efficient towers")
