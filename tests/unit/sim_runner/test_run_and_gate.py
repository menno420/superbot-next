"""V-3 runner + gate tests: deterministic records (sim/run.py), the overlay
[A]-only patch format (sim/apply.py), and check_sim_gate's pin semantics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sim.space as space_mod
import tools.check_sim_gate as gate
from sb.spec.manifest import SubsystemManifest
from sb.spec.panels import LayoutSpec, PageSpec, PanelActionSpec, PanelSpec
from sim.apply import Exempt, OverlayKeyRejected, SimRef, load_overlay, write_overlay
from sim.run import SpaceDef, clear_spaces_for_tests, register_space, run_space


@pytest.fixture(autouse=True)
def _clean_spaces():
    clear_spaces_for_tests()
    yield
    clear_spaces_for_tests()


def _panel(actions):
    specs = tuple(PanelActionSpec(action_id=a, label=a.title()) for a in actions)
    return PanelSpec(
        panel_id="econ.shop", subsystem="economy", title="Shop", actions=specs,
        layout=LayoutSpec(pages=(PageSpec(rows=(tuple(actions),)),)),
    )


def _register_fixture_space():
    from sim.space import generate_layout_candidates, neighbour_layout

    register_space(SpaceDef(
        sim_id="test-dense",
        oracle="dense_panel",
        candidates=lambda ctx, seed: generate_layout_candidates(
            ("buy", "sell", "audit"), seed=seed),
        context=lambda inputs: {},
        neighbour=neighbour_layout,
    ))


class TestRunner:
    def test_record_shape_and_determinism(self, tmp_path):
        _register_fixture_space()
        out1 = run_space("test-dense", seed=7, records_dir=tmp_path / "r1")
        out2 = run_space("test-dense", seed=7, records_dir=tmp_path / "r2")
        record = json.loads(out1.read_text())
        assert record["sim_id"] == "test-dense"
        assert record["seed"] == 7
        assert record["oracle"] == "dense_panel"
        assert record["input_hashes"]["snapshot"].startswith("sha256:")
        assert record["input_hashes"]["sidecar"].startswith("sha256:")
        assert record["weights_provenance"] == "seeded"
        assert record["confidence"] == "low"
        assert "arrangement" in record["winner"] and "terms" in record["winner"]
        assert len(record["alternatives"]) == 5
        # bit-for-bit reproducible under the same seed (§2.10.5)
        assert out1.read_text() == out2.read_text()

    def test_unknown_space_is_loud(self):
        with pytest.raises(KeyError):
            run_space("never-registered")


class TestOverlay:
    def test_write_and_load_roundtrip(self, tmp_path):
        entries = {
            "economy:econ.shop:PanelSpec.layout": {
                "value": {"pages": [{"rows": [["buy"]]}]},
                "provenance": SimRef("test-dense-2026-07-08", "sha256:abc"),
            }
        }
        path = write_overlay("economy", entries, overlay_dir=tmp_path)
        loaded = load_overlay(path)
        assert loaded["economy:econ.shop:PanelSpec.layout"]["provenance"] == {
            "sim_ref": {"record_id": "test-dense-2026-07-08", "input_hash": "sha256:abc"}
        }

    def test_non_a_key_rejected_both_sides(self, tmp_path):
        semantic = {
            "economy:econ.shop:PanelActionSpec.handler": {
                "value": "evil", "provenance": Exempt("nope"),
            }
        }
        with pytest.raises(OverlayKeyRejected):
            write_overlay("economy", semantic, overlay_dir=tmp_path)
        # a hand-forged file is rejected on load too
        forged = tmp_path / "economy.lock.json"
        forged.write_text(json.dumps({"schema_version": 1, "subsystem": "economy",
                                      "entries": {"economy:econ.shop:PanelSpec.panel_id":
                                                  {"value": "x", "provenance": {"exempt": "r"}}}}))
        with pytest.raises(OverlayKeyRejected):
            load_overlay(forged)

    def test_provenance_is_mandatory(self, tmp_path):
        with pytest.raises(ValueError, match="provenance"):
            write_overlay("economy", {
                "economy:econ.shop:PanelSpec.layout": {"value": {}},
            }, overlay_dir=tmp_path)


class TestSimGate:
    def test_green_on_the_committed_tree(self):
        assert gate.check() == []

    def test_unpinned_assignment_is_red(self, monkeypatch):
        manifest = SubsystemManifest(
            key="economy", panels=(_panel(("buy", "sell", "audit", "gift", "wipe")),))
        monkeypatch.setattr(space_mod, "registered_manifests", lambda: [manifest])
        problems = gate.check()
        assert any("not pinned" in p for p in problems)

    def test_below_floor_panel_auto_exempt(self, monkeypatch):
        manifest = SubsystemManifest(
            key="economy", panels=(_panel(("buy", "sell", "audit")),))  # 3 <= 4
        monkeypatch.setattr(space_mod, "registered_manifests", lambda: [manifest])
        assert gate.check() == []

    def test_floor_is_pre_layout_semantic_size(self, monkeypatch):
        # 5 declared actions paged 3+2 cannot split under the floor
        actions = ("buy", "sell", "audit", "gift", "wipe")
        specs = tuple(PanelActionSpec(action_id=a, label=a.title()) for a in actions)
        panel = PanelSpec(
            panel_id="econ.shop", subsystem="economy", title="Shop", actions=specs,
            layout=LayoutSpec(pages=(
                PageSpec(rows=(("buy", "sell", "audit"),)),
                PageSpec(rows=(("gift", "wipe"),)),
            )),
        )
        manifest = SubsystemManifest(key="economy", panels=(panel,))
        monkeypatch.setattr(space_mod, "registered_manifests", lambda: [manifest])
        assert any("not pinned" in p for p in gate.check())

    def test_stale_baseline_pin_is_red(self, monkeypatch, tmp_path):
        stale = tmp_path / "sim-gate-baseline.json"
        stale.write_text(json.dumps({"schema_version": 1, "assignments": {
            "ghost:panel:PanelSpec.layout": {"value": {}, "provenance": {"exempt": "r"}},
        }}))
        monkeypatch.setattr(gate, "BASELINE", stale)
        problems = gate.check()
        assert any("no live [A] assignment" in p for p in problems)

    def test_sim_ref_must_name_a_real_record_with_matching_hash(
        self, monkeypatch, tmp_path
    ):
        manifest = SubsystemManifest(
            key="economy", panels=(_panel(("buy", "sell", "audit", "gift", "wipe")),))
        monkeypatch.setattr(space_mod, "registered_manifests", lambda: [manifest])
        assignments = gate.current_assignments()
        key = "economy:econ.shop:PanelSpec.layout"
        baseline = tmp_path / "sim-gate-baseline.json"
        baseline.write_text(json.dumps({"schema_version": 1, "assignments": {
            key: {"value": assignments[key],
                  "provenance": {"sim_ref": {"record_id": "missing-record",
                                             "input_hash": "sha256:zzz"}}},
        }}))
        monkeypatch.setattr(gate, "BASELINE", baseline)
        problems = gate.check()
        assert any("missing record" in p for p in problems)

    def test_write_baseline_refuses_without_provenance(
        self, monkeypatch, capsys, tmp_path
    ):
        manifest = SubsystemManifest(
            key="economy", panels=(_panel(("buy", "sell", "audit", "gift", "wipe")),))
        monkeypatch.setattr(space_mod, "registered_manifests", lambda: [manifest])
        monkeypatch.setattr(gate, "BASELINE", tmp_path / "sim-gate-baseline.json")
        assert gate.write_baseline() == 1
        assert "REFUSED" in capsys.readouterr().out
