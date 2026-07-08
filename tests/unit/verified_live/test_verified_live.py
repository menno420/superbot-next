"""V-5 layer-V tests: the verified_live schema (§3.3), the A-18 tier rules
with Q-0244 encoded, the debt-list model, and the committed registry."""

from __future__ import annotations

import pytest

import tools.check_verified_live as gate
from verification.verified_live import (
    CutoverStatus,
    EvidenceKind,
    EvidenceRow,
    Status,
    SurfaceKind,
    Tier,
    VerifiedLiveRecord,
    debt_list,
    load_registry,
    validate_record,
)


def _record(**overrides) -> VerifiedLiveRecord:
    defaults = dict(
        record_id="economy.balance.slash",
        subsystem="economy",
        surface_kind=SurfaceKind.COMMAND,
        surface_id="/balance",
        tier=Tier.AUTOMATED,
        scenario_steps=("invoke /balance as member persona",),
        expected_visible="balance embed with coin total",
        expected_effects=("no db delta",),
    )
    defaults.update(overrides)
    return VerifiedLiveRecord(**defaults)


def _signed(**overrides):
    defaults = dict(
        status=Status.VERIFIED,
        signer="owner",
        signed_at="2026-07-08T12:00:00Z",
        build_sha="c7defbc8",
        evidence=(
            EvidenceRow(EvidenceKind.PREFIX_TWIN_LIVE, "transcript://balance-prefix"),
            EvidenceRow(EvidenceKind.PIPELINE_REPLAY, "parity://economy/sweep_balance"),
        ),
    )
    defaults.update(overrides)
    return _record(**defaults)


class TestSchema:
    def test_unverified_row_is_valid_with_scenario(self):
        assert validate_record(_record()) == []

    def test_never_a_bare_checkbox(self):
        problems = validate_record(_record(scenario_steps=(), expected_visible=""))
        assert any("scenario_steps" in p for p in problems)
        assert any("expected_visible" in p for p in problems)

    def test_verified_is_a_signed_fact(self):
        problems = validate_record(
            _record(status=Status.VERIFIED)  # unsigned
        )
        assert any("signer" in p for p in problems)
        assert any("build_sha" in p for p in problems)
        assert any("evidence" in p for p in problems)

    def test_roundtrip_from_data(self):
        record = VerifiedLiveRecord.from_data({
            "record_id": "x", "subsystem": "economy",
            "surface_kind": "custom_id", "surface_id": "econ.shop.buy",
            "tier": "human_required",
            "scenario_steps": ["open shop", "click buy"],
            "expected_visible": "purchase card",
            "cutover_status": "cut1",
        })
        assert record.surface_kind is SurfaceKind.CUSTOM_ID
        assert record.tier is Tier.HUMAN_REQUIRED
        assert record.cutover_status is CutoverStatus.CUT1


class TestQ0244TierRules:
    def test_slash_needs_prefix_twin_plus_replay(self):
        incomplete = _signed(evidence=(
            EvidenceRow(EvidenceKind.PREFIX_TWIN_LIVE, "t://x"),
        ))
        problems = validate_record(incomplete)
        assert any("Q-0244" in p and "pipeline_replay" in p for p in problems)

    def test_slash_with_both_lanes_verifies(self):
        assert validate_record(_signed()) == []

    def test_component_surface_counts_as_slash_lane(self):
        component = _signed(
            surface_kind=SurfaceKind.CUSTOM_ID, surface_id="econ.shop.buy",
            evidence=(EvidenceRow(EvidenceKind.PIPELINE_REPLAY, "t://x"),),
        )
        assert any("Q-0244" in p for p in validate_record(component))

    def test_prefix_command_needs_lane_a_only(self):
        prefix = _signed(
            surface_id="!balance",
            evidence=(EvidenceRow(EvidenceKind.PREFIX_TWIN_LIVE, "t://x"),),
        )
        assert validate_record(prefix) == []

    def test_human_tier_verifies_via_walk_or_judgment(self):
        wrong_evidence = _signed(
            tier=Tier.HUMAN_REQUIRED,
            evidence=(EvidenceRow(EvidenceKind.PIPELINE_REPLAY, "t://x"),),
        )
        assert any("human walk" in p for p in validate_record(wrong_evidence))
        walked = _signed(
            tier=Tier.HUMAN_REQUIRED,
            evidence=(EvidenceRow(EvidenceKind.HUMAN_WALK, "t://walk"),),
        )
        assert validate_record(walked) == []


class TestDebtListModel:
    def test_unverified_human_rows_flow_to_debt_never_red(self):
        human_pending = _record(record_id="setup.wizard.walk", tier=Tier.HUMAN_REQUIRED)
        automated_pending = _record(record_id="econ.auto")
        debt = debt_list([human_pending, automated_pending])
        assert [r.record_id for r in debt] == ["setup.wizard.walk"]
        # the pending human row is schema-valid — it never reds the gate
        assert validate_record(human_pending) == []

    def test_explicit_debt_rows_published(self):
        row = _record(record_id="legacy.thing", status=Status.DEBT)
        assert debt_list([row]) == [row]


class TestCommittedRegistry:
    def test_gate_green_on_the_committed_tree(self):
        assert gate.check() == []

    def test_every_subsystem_starts_unverified(self):
        subsystems, records = load_registry()
        assert set(subsystems.values()) == {"unverified"}
        assert records == []

    def test_roster_is_the_parity_spine_plus_kernel(self):
        import yaml
        from pathlib import Path

        subsystems, _ = load_registry()
        parity = yaml.safe_load(Path("parity/parity.yml").read_text())
        assert set(subsystems) == set(parity["subsystems"]) | {"kernel"}

    def test_debt_list_mode_exits_zero(self, capsys):
        assert gate.print_debt_list() == 0
        assert "NEVER a CUT-3 blocker" in capsys.readouterr().out


class TestGateRules:
    def test_verified_dashboard_needs_records(self, monkeypatch, tmp_path):
        import verification.verified_live as vl

        registry = tmp_path / "verified_live.yml"
        registry.write_text("schema_version: 1\nsubsystems:\n  economy: verified\nrecords: []\n")
        monkeypatch.setattr(vl, "REGISTRY_PATH", registry)
        problems = gate.check()
        assert any("V3 economy" in p and "zero records" in p for p in problems)

    def test_verified_dashboard_blocked_by_unverified_automated_row_only(
        self, monkeypatch, tmp_path
    ):
        import verification.verified_live as vl

        registry = tmp_path / "verified_live.yml"
        registry.write_text(
            "schema_version: 1\n"
            "subsystems:\n  economy: verified\n"
            "records:\n"
            "  - record_id: econ.auto\n"
            "    subsystem: economy\n"
            "    surface_kind: command\n"
            "    surface_id: '!balance'\n"
            "    tier: automated\n"
            "    scenario_steps: [invoke]\n"
            "    expected_visible: embed\n"
            "    status: unverified\n"
            "  - record_id: econ.walk\n"
            "    subsystem: economy\n"
            "    surface_kind: flow\n"
            "    surface_id: economy-judgment-walk\n"
            "    tier: human_required\n"
            "    scenario_steps: [walk]\n"
            "    expected_visible: works logical self-explanatory\n"
            "    status: unverified\n"
        )
        monkeypatch.setattr(vl, "REGISTRY_PATH", registry)
        problems = gate.check()
        # the automated pending row blocks the flip; the human row never does
        assert any("econ.auto" in p for p in problems)
        assert not any("econ.walk" in p and "V3" in p for p in problems)
        # V4 roster problems are expected with this tiny fixture; V3 is the point
        assert all(not p.startswith("V2") for p in problems)
