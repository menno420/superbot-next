"""Pure unit tests for the WP-6 structure-build PORT constants + copy
(`sb/domain/mining/structures.py`, `market.py`) — the oracle
`services/mining_workflow.py::build_structure` / `_build_success_suffix` and
`utils/mining/market.structure_build_reason`, pinned byte-for-byte.

The `mining.build_forge_write` golden drives ONLY the forge level 0->1 success
face; these tests pin the branches a single golden can't reach — the Forge-II
suffix, the Home suffix, the maxed level, the campfire (generic, no suffix), the
build-ladder costs, and the economy-audit reason tag — so the ported copy is
frozen against the oracle end to end. Pure: no DB, no Discord, no clock.
"""

from __future__ import annotations

from sb.domain.mining import market, structures
from sb.domain.mining.workshop import describe_materials


def test_structure_build_reason_is_generic():
    # oracle utils/mining/market.structure_build_reason: mining:{structure}_build
    assert market.structure_build_reason("forge") == "mining:forge_build"
    assert market.structure_build_reason("home") == "mining:home_build"
    assert market.structure_build_reason("campfire") == "mining:campfire_build"


def test_forge_success_suffix_advertises_unlocked_tier():
    # tiers_unlocked_at(1) = ("gold",) -> "gold"; (2) adds diamond -> "diamond".
    assert structures.build_success_suffix(structures.FORGE, 1) == (
        " Now crafts **gold-tier** gear.")
    assert structures.build_success_suffix(structures.FORGE, 2) == (
        " Now crafts **diamond-tier** gear.")


def test_home_success_suffix_is_the_backdrop_line():
    assert structures.build_success_suffix(structures.HOME, 1) == (
        " It now frames your Character card.")
    assert structures.build_success_suffix(structures.HOME, 3) == (
        " It now frames your Character card.")


def test_generic_structure_has_no_suffix():
    # Campfire is a generic sink with no reward line (oracle: the fall-through "").
    assert structures.build_success_suffix(structures.CAMPFIRE, 1) == ""


def test_forge_build_ladder_and_max():
    forge_i = structures.build_cost(structures.FORGE, 0)
    forge_ii = structures.build_cost(structures.FORGE, 1)
    assert forge_i.coins == 3000 and forge_i.materials == {"iron": 25, "stone": 15}
    assert forge_ii.coins == 8000 and forge_ii.materials == {"gold": 20, "iron": 10}
    # maxed -> None (the oracle "already at its maximum level" guard face).
    assert structures.build_cost(structures.FORGE, structures.MAX_FORGE_LEVEL) is None
    assert structures.level_name(structures.FORGE, 1) == "Forge I"
    assert structures.level_name(structures.FORGE, 2) == "Forge II"


def test_forge_i_materials_render_matches_the_golden_reply():
    # The mining.build_forge_write golden reply's material list; describe_materials
    # sorts (iron < stone), so the Forge-I cost renders "25× iron, 15× stone".
    cost = structures.build_cost(structures.FORGE, 0)
    assert describe_materials(cost.materials) == "25× iron, 15× stone"


def test_full_forge_build_success_message_is_oracle_verbatim():
    # Reconstruct the exact build_structure success sentence the leg composes for
    # the forge level 0->1 build funded at 3500 -> 500 (the golden's face) — the
    # byte contract the write golden freezes.
    cost = structures.build_cost(structures.FORGE, 0)
    new_name = structures.level_name(structures.FORGE, 1)
    suffix = structures.build_success_suffix(structures.FORGE, 1)
    message = (f"Forge built to **{new_name}** for "
               f"{describe_materials(cost.materials)} + {cost.coins} 🪙."
               f"{suffix} Balance: **500** 🪙.")
    assert message == (
        "Forge built to **Forge I** for 25× iron, 15× stone + 3000 🪙. "
        "Now crafts **gold-tier** gear. Balance: **500** 🪙.")
