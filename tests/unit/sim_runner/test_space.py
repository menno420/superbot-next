"""V-3 layer-V tests: the search-space extraction, hard constraints,
candidate generation, and sidecar semantics (sim/space.py)."""

from __future__ import annotations

import json

import pytest

from sb.spec.manifest import SubsystemManifest
from sb.spec.panels import LayoutSpec, PageSpec, PanelActionSpec, PanelSpec
from sim.space import (
    a_tagged_fields,
    arrangement_assignments,
    check_hard_constraints,
    generate_layout_candidates,
    hot_component_ids,
    load_sidecar,
    neighbour_layout,
    stable_hash,
)


def _panel(panel_id="econ.shop", actions=("buy", "sell", "audit")):
    specs = tuple(PanelActionSpec(action_id=a, label=a.title()) for a in actions)
    return PanelSpec(
        panel_id=panel_id,
        subsystem="economy",
        title="Shop",
        actions=specs,
        layout=LayoutSpec(pages=(PageSpec(rows=(tuple(actions),)),)),
    )


class TestATaggedFields:
    def test_grammar_owns_the_classification(self):
        fields = a_tagged_fields()
        assert "PanelSpec.layout" in fields
        assert "PageSpec.rows" in fields
        assert "TableSpec.default_sort" in fields
        # semantics are never [A]
        assert "PanelActionSpec.handler" not in fields
        assert "PanelSpec.panel_id" not in fields


class TestArrangementAssignments:
    def test_assignments_keyed_by_namespace_id(self):
        manifest = SubsystemManifest(key="economy", panels=(_panel(),))
        assignments = arrangement_assignments([manifest])
        assert "economy:econ.shop:PanelSpec.layout" in assignments
        # the layout value serialized plain
        value = assignments["economy:econ.shop:PanelSpec.layout"]
        assert value == {"pages": [{"rows": [["buy", "sell", "audit"]]}]}

    def test_no_manifests_no_assignments(self):
        assert arrangement_assignments([]) == {}

    def test_stable_hash_is_deterministic(self):
        a = stable_hash({"x": (1, 2), "y": "z"})
        b = stable_hash({"y": "z", "x": [1, 2]})
        assert a == b and a.startswith("sha256:")


class TestHardConstraints:
    def test_admissible_layout_passes(self):
        layout = ((("a", "b"), ("c", "d")),)
        assert check_hard_constraints(layout) == []

    def test_destructive_never_row_0(self):
        layout = ((("wipe", "b"),),)
        problems = check_hard_constraints(layout, destructive={"wipe"})
        assert any("row 0" in p for p in problems)

    def test_destructive_never_adjacent_to_hot(self):
        weights = {"hot1": 100.0, "wipe": 1.0, "a": 1.0, "b": 1.0, "c": 1.0}
        # wipe on row 1 next to hot1 (same column, vertically neighbouring)
        layout = ((("hot1", "a"), ("wipe", "b"), ("c",)),)
        problems = check_hard_constraints(
            layout, destructive={"wipe"}, component_weights=weights
        )
        assert any("adjacent to hot" in p for p in problems)

    def test_caps(self):
        too_wide = ((tuple(f"c{i}" for i in range(6)),),)
        assert any("> 5" in p for p in check_hard_constraints(too_wide))
        page = tuple(tuple(f"r{r}c{c}" for c in range(5)) for r in range(5))
        layout = (page, page)  # 50 components across two full pages
        assert any("> 25" in p for p in check_hard_constraints(layout))

    def test_hot_quartile_deterministic_tiebreak(self):
        weights = {"a": 5.0, "b": 5.0, "c": 1.0, "d": 1.0}
        assert hot_component_ids(weights) == {"a"}  # ties break by id sort


class TestCandidateGeneration:
    def test_exhaustive_when_small(self):
        candidates = generate_layout_candidates(("a", "b", "c"), seed=1)
        assert len(candidates) == 6  # 3!
        # coverage exhaustive + exclusive on every candidate
        for candidate in candidates:
            flat = [c for page in candidate for row in page for c in row]
            assert sorted(flat) == ["a", "b", "c"]

    def test_sampled_when_large(self):
        ids = tuple(f"c{i:02d}" for i in range(10))  # 10! >> limit
        candidates = generate_layout_candidates(ids, seed=42, limit=50)
        assert len(candidates) == 50
        again = generate_layout_candidates(ids, seed=42, limit=50)
        assert candidates == again  # fixed-seed determinism

    def test_neighbour_swaps_preserve_coverage(self):
        import random

        base = generate_layout_candidates(("a", "b", "c", "d"), seed=7)[0]
        moved = neighbour_layout(base, random.Random(7))
        flat = sorted(c for page in moved for row in page for c in row)
        assert flat == ["a", "b", "c", "d"]

    def test_row_4_left_free_for_nav(self):
        ids = tuple(f"c{i:02d}" for i in range(20))
        candidate = generate_layout_candidates(ids, seed=1, limit=10)[0]
        for page in candidate:
            assert len(page) <= 4  # nav row stays engine-owned


class TestSidecar:
    def test_committed_sidecar_is_seeded_empty(self):
        usage = load_sidecar()
        assert usage.provenance == "seeded"
        assert usage.confidence == "low"
        assert usage.counts == {} and usage.pairs == {}

    def test_neutral_prior_for_unknown_nodes(self, tmp_path):
        path = tmp_path / "usage.snapshot.json"
        path.write_text(json.dumps({
            "header": {"provenance": "telemetry(2026-06)", "capture_window": "30d",
                       "session_definition": "s"},
            "counts": {"econ.shop.buy": 40},
            "pairs": {"co_use|a|b": 3},
        }))
        usage = load_sidecar(path)
        assert usage.weight("econ.shop.buy") == 40.0
        assert usage.weight("never.seen") == 1.0
        assert usage.confidence == "measured"
