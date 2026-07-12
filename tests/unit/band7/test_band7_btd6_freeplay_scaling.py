"""Band 7 — btd6 freeplay MOAB scaling (the #144 parked domain item):
the shipped ``btd6_data_service`` late-game/freeplay block — the
piecewise-linear MOAB-class health curve, the recursive
``bloon_rbe_at_round`` spawn-tree walk (superceramic swap + per-layer
multiplier), the ``round_rbe`` effective recompute, and the scaled RBE /
round / round-range card renders.

Every semantic below is oracle-reconstructed via search_code fragments
(reconstruction ref 1ecc2113 — trap 24: the oracle default branch is
AHEAD of the corpus pin 7f7628e1; fragments were diffed against the
goldens FIRST — the only goldens on this surface pin PRE-scaling round-3
bytes, pinned unchanged below). Expected values are the oracle's OWN
anchors: tests/unit/services/test_btd6_bloon_scaling.py (v(100)=1.40,
BAD r100 = 28,000 HP / 67,200 RBE, BAD r80 = stored 55,760),
test_btd6_round_rbe.py (rounds ≤ 80: group-sum == stored RBE; r81
effective < base), the committed ``bloon_scaling.json`` bracket table +
its validation prose (v(140)=5.00, fortified BAD r140 = 200,000 HP,
superceramic 68/128), and the oracle 2026-06-23 session card's per-unit
chain (MOAB 552 → BFB 3,188 → ZOMG 18,352; 28,000 + 2×18,352 + 3×832).
"""

from __future__ import annotations

import pytest

from sb.domain.btd6 import context, dataset, freeplay, oracle_cards


# --- the multiplier curve (bloon_scaling.json brackets, oracle formula) -------------


@pytest.mark.parametrize(
    ("rnd", "expected"),
    [
        (1, 1.0),
        (80, 1.0),          # last unscaled round
        (81, 1.02),         # ramp start: +2%/round off the round-80 anchor
        (100, 1.4),         # validated anchor: BAD 20,000 → 28,000 HP
        (101, 1.45),        # the curve steepens past 100 (NOT flat 2%)
        (124, 2.6),
        (125, 2.75),
        (140, 5.0),         # validated anchor: fortified BAD 200,000 HP
        (150, 6.5),
        (151, 6.85),
        (250, 41.5),
        (251, 42.5),
        (500, 491.5),
        (1000, 2991.5),     # last bracket end
        (1500, 2991.5),     # rounds past the last bracket clamp to its end
        (0, 1.0),           # below the first bracket → unscaled
    ],
)
def test_moab_class_health_multiplier(rnd: int, expected: float):
    assert freeplay.moab_class_health_multiplier(rnd) == pytest.approx(expected)


def test_multiplier_none_when_fixture_absent(monkeypatch):
    monkeypatch.setattr(freeplay.dataset, "read_blob", lambda name: None)
    assert freeplay.moab_class_health_multiplier(100) is None


# --- bloon_health_at_round ----------------------------------------------------------


def test_bad_scaled_health_standard_and_fortified():
    # oracle test_btd6_bloon_scaling.py anchors, verbatim values
    assert freeplay.bloon_health_at_round("bad", 100) == 28000
    assert freeplay.bloon_health_at_round("bad", 100, fortified=True) == 56000
    # fortified BAD r140 = 200,000 HP (the bloon_scaling.json v(140)=5.00
    # validation anchor)
    assert freeplay.bloon_health_at_round("bad", 140, fortified=True) == 200000
    # unscaled through round 80
    assert freeplay.bloon_health_at_round("bad", 80) == 20000


def test_health_regular_bloons_never_take_the_ramp():
    assert freeplay.bloon_health_at_round("red", 100) == 1
    assert freeplay.bloon_health_at_round("ceramic", 100) == 10
    assert freeplay.bloon_health_at_round("nope", 100) is None


# --- the spawn-tree walk (bloon_rbe_at_round) ---------------------------------------


def test_bad_rbe_at_the_canonical_anchor():
    # ≤ 80 → the stored base RBE is exact (no freeplay band)
    bad = dataset.get_bloon("bad")
    assert bad is not None
    assert freeplay.bloon_rbe_at_round("bad", 80) == bad.rbe  # 55,760
    # the authoritative r100 figure, reproduced to the unit
    assert freeplay.bloon_rbe_at_round("bad", 100) == 67200


def test_walk_per_unit_chain_at_round_100():
    # the oracle session card's chain: MOAB 552 → BFB 3,188 → ZOMG 18,352;
    # BAD = 28,000 + 2×18,352 + 3×832 (DDT) = 67,200
    assert freeplay.bloon_rbe_at_round("moab", 100) == 552
    assert freeplay.bloon_rbe_at_round("bfb", 100) == 3188
    assert freeplay.bloon_rbe_at_round("zomg", 100) == 18352
    assert freeplay.bloon_rbe_at_round("ddt", 100) == 832


def test_ceramic_becomes_superceramic_from_the_start_round():
    # base ceramic 104 through round 80; Super Ceramic 68 (128 fortified)
    # from round 81 — the swap can LOWER effective RBE
    assert freeplay.bloon_rbe_at_round("ceramic", 80) == 104
    assert freeplay.bloon_rbe_at_round("ceramic", 81) == 68
    assert freeplay.bloon_rbe_at_round("ceramic", 81, fortified=True) == 128


def test_walk_unknown_bloon_is_none():
    assert freeplay.bloon_rbe_at_round("nope", 100) is None


def test_non_moab_parent_keeps_stored_rbe_no_child_swap():
    # Oracle quirk PINNED (codex #225 finding 2, declined with citation):
    # a non-MOAB-class parent returns its stored base RBE WITHOUT
    # recursing, so its ceramic child never takes the superceramic swap —
    # the oracle's own fixture prose scopes the recompute to MOAB-class
    # trees ("{MOAB-class bodies x v(r)} + {ceramic leaves ->
    # superceramic}"). diamond (special, 1× fortified ceramic child)
    # stays at its stored 194 on freeplay rounds, never 66 + 128 = 194→208.
    diamond = dataset.get_bloon("diamond")
    assert diamond is not None and diamond.category == "special"
    assert freeplay.bloon_rbe_at_round("diamond", 81) == 194
    assert freeplay.bloon_rbe_at_round("diamond", 140) == 194


def test_methodology_proof_group_sum_reconstructs_stored_rbe_below_81():
    # the oracle test_btd6_round_rbe.py proof: with no freeplay scaling
    # (rounds ≤ 80), summing each group's count × bloon_rbe_at_round must
    # equal the stored base RBE — the 81+ divergence is purely the rules.
    checked = 0
    for n in range(1, 81):
        row = oracle_cards.get_round(n)
        if row is None or row.get("rbe") is None or not row.get("groups"):
            continue
        assert freeplay.effective_round_rbe(row) == int(row["rbe"]), n
        checked += 1
    assert checked > 70  # the default set carries groups on ~all rounds


# --- round_rbe (effective wiring) ---------------------------------------------------


def test_round_rbe_single_round_scaled_anchor():
    res = oracle_cards.round_rbe(100)
    assert res["found"] and res["single_round"]
    assert res["base_rbe"] == 55760
    assert res["effective_rbe"] == 67200  # the canonical anchor
    assert res["scaled"] is True


def test_round_rbe_superceramic_swap_lowers_r81():
    res = oracle_cards.round_rbe(81)
    assert res["effective_rbe"] < res["base_rbe"]  # oracle test, verbatim
    assert res["scaled"] is True


def test_round_rbe_pre_freeplay_round_unscaled():
    res = oracle_cards.round_rbe(3)
    assert res["base_rbe"] == 35
    assert res["effective_rbe"] == 35  # identical through round 80…
    assert res["scaled"] is False      # …so the render never changes


def test_round_rbe_range_totals_and_per_round():
    res = oracle_cards.round_rbe(99, 101)
    assert res["found"] and not res["single_round"]
    assert res["base_rbe_total"] == 123234
    assert res["effective_rbe_total"] == 136894
    assert res["scaled"] is True
    per = {r["round"]: r for r in res["per_round"]}
    assert per[99]["effective_rbe"] == 47424   # swap-dominated: below base
    assert per[100]["effective_rbe"] == 67200
    assert per[101]["effective_rbe"] == 22270


def test_round_rbe_unscaled_range_effective_equals_base():
    res = oracle_cards.round_rbe(1, 3)
    assert res["scaled"] is False
    assert res["effective_rbe_total"] == res["base_rbe_total"] == 90


def test_round_rbe_capped_any_scaled_quirk_pinned():
    # Oracle quirk PINNED (codex #225 finding 1, declined with citation):
    # ``any_scaled`` iterates the CAPPED per_round rows (the oracle builds
    # per_round from ``in_range[:_ROUND_DETAIL_CAP]`` and its any() runs
    # ``for row in per_round``), so a range starting ≥ 40 rounds before
    # the freeplay band reports scaled=False even though the FULL-range
    # effective total (computed over all of in_range, all-or-None)
    # diverges — the render then shows the base total with no scaling
    # note, exactly as the oracle's card does for the same input.
    res = oracle_cards.round_rbe(1, 100)
    assert res["truncated"] is True
    assert len(res["per_round"]) == 40           # rows 1–40, all unscaled
    assert res["scaled"] is False                # the capped-any quirk
    assert res["base_rbe_total"] == 1974355
    assert res["effective_rbe_total"] == 2050213  # full-range, diverging


# --- the card renders ---------------------------------------------------------------


def test_rbe_card_round_3_golden_bytes_unchanged():
    # goldens/btd6/sweep_btd6_rbe.json + sweep_btd6ref_rbe.json pin these
    # bytes exactly (no footer key on the wire).
    card = oracle_cards.rbe_card(3)
    assert card.title == "🐵 BTD6 RBE — round 3"
    assert card.description == "**35** RBE"
    assert card.footer == ""


def test_rbe_card_scaled_single_round_bytes():
    card = oracle_cards.rbe_card(100)
    assert card.title == "🐵 BTD6 RBE — round 100"
    assert card.description == (
        "**67,200** effective RBE (freeplay-scaled)\n"
        "Wiki base (unscaled): **55,760**"
    )
    assert card.footer == (
        "Effective RBE applies freeplay MOAB-class HP scaling + superceramic "
        "swap (our model, verified BAD r100 = 67,200); base is the wiki "
        "composition at base health. Identical through round 80."
    )


def test_rbe_card_scaled_range_two_column_table():
    card = oracle_cards.rbe_card(99, 101)
    assert card.title == "🐵 BTD6 RBE — rounds 99–101"
    lines = card.description.split("\n")
    assert lines[0] == "Totals — base **123,234**, effective **136,894** across 3 rounds."
    assert lines[2] == f"{'round':>5} │ {'base RBE':>12} │ {'effective':>12}"
    assert lines[3] == "──────┼──────────────┼──────────────"
    assert lines[4] == f"{'r99':>5} │ {48264:>12,} │ {47424:>12,}"
    assert lines[5] == f"{'r100':>5} │ {55760:>12,} │ {67200:>12,}"
    assert card.footer.startswith("Effective RBE applies freeplay")


def test_rbe_card_unscaled_range_keeps_one_column_bytes():
    card = oracle_cards.rbe_card(1, 3)
    lines = card.description.split("\n")
    assert lines[0] == "Total RBE — **90** across 3 rounds."
    assert lines[2] == f"{'round':>5} │ {'RBE':>12}"
    assert card.footer == ""


def test_round_range_card_effective_column_and_footer():
    card = oracle_cards._round_range_card(99, 101)
    # the head line totals the EFFECTIVE figure when scaled
    assert card.description.startswith(
        "**Rounds 99–101** — total RBE **136,894**")
    # the single RBE column shows the effective figure where computed
    assert " r100 │      67,200 │" in card.description
    assert card.footer == (
        "Standard/Medium, no income towers · RBE freeplay-scaled (rounds 81+)"
    )


def test_round_range_card_pre_freeplay_footer_unchanged():
    card = oracle_cards._round_range_card(1, 3)
    assert card.footer == "Standard/Medium, no income towers"


def test_round_card_gains_effective_field_only_when_scaled():
    scaled = oracle_cards.round_card(100)
    names = [f[0] for f in scaled.fields]
    assert names[-1] == "Effective RBE (freeplay-scaled)"
    assert scaled.fields[-1][1] == (
        "**67,200** — the round-100 spawn at scaled health (MOAB-class HP "
        "ramp + superceramics). Wiki base (unscaled): 55,760."
    )
    assert scaled.fields[-1][2] is False  # inline=False in the oracle
    plain = oracle_cards.round_card(3)
    assert all(f[0] != "Effective RBE (freeplay-scaled)" for f in plain.fields)


# --- the context grounding note -----------------------------------------------------


def test_moab_class_bloon_gains_the_scaling_note():
    bad = dataset.get_bloon("bad")
    assert bad is not None
    lines = context._render_bloon(bad)
    note = [l for l in lines if "late-game/freeplay scaling" in l]
    assert len(note) == 1
    assert note[0].startswith(
        "[btd6_bloon] BAD — late-game/freeplay scaling: MOAB-class health "
        "ramps from round 81 (×1.4 by round 100, steepening sharply past "
        "100), so 20,000 HP holds only through round 80; it first appears "
        "on round 100 at 28,000 HP, 67,200 RBE."
    )


def test_regular_bloon_gets_no_scaling_note():
    red = dataset.get_bloon("red")
    assert red is not None
    assert not any(
        "late-game/freeplay scaling" in l for l in context._render_bloon(red)
    )


# --- dataset children_list parse ----------------------------------------------------


def test_bloon_children_list_parsed_as_dict_rows():
    moab = dataset.get_bloon("moab")
    assert moab is not None
    assert moab.children_list == ({"bloon_id": "ceramic", "count": 4,
                                   "modifiers": []},)
    red = dataset.get_bloon("red")
    assert red is not None and red.children_list == ()
