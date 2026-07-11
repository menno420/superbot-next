"""V-1 layer-V tests: the imported golden corpus, the A-16 depth floor
(tools/check_parity_depth.py), and the golden-parity gate driver
(tools/run_golden_parity.py). DB-free — nothing here boots a bot.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

import pytest

from tools.check_parity_depth import (
    GOLDENS_ROOT,
    PARITY_YML,
    SNAPSHOT,
    check,
    covered_surfaces,
    declared_surfaces,
    golden_docs,
    load_parity_yml,
    splice_ratchet_text,
    write_ratchet,
)
from tools.run_golden_parity import run_gate, run_report

REPO_ROOT = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------- the corpus
class TestImportedCorpus:
    def test_corpus_golden_count(self):
        # 465 imported at the source pin + 2 minted modal-submit goldens
        # (D-0073 corpus-schema growth; parity.yml source.minted_goldens).
        goldens = list(GOLDENS_ROOT.glob("*/*.json"))
        assert len(goldens) == 467

    def test_sweep_skips_carry_reasons(self):
        skips = json.loads((GOLDENS_ROOT / "_sweep_skips.json").read_text())
        assert skips and all(
            isinstance(k, str) and isinstance(v, str) and v for k, v in skips.items()
        )

    def test_every_golden_parses_and_has_steps(self):
        for path in GOLDENS_ROOT.glob("*/*.json"):
            doc = json.loads(path.read_text())
            assert "steps" in doc, path
            assert "case_id" in doc, path

    def test_source_pin_recorded(self):
        parity = load_parity_yml()
        source = parity["source"]
        assert source["repo"] == "menno420/superbot"
        assert source["sha"] == "7f7628e12f3b89c5c2a1fbdcfb039787df269e20"
        assert source["goldens"] == 465     # the IMPORT pin (verbatim corpus)
        assert source["minted_goldens"] == 2  # D-0073 modal-submit mints


# ----------------------------------------------------- real-tree gate state
class TestRealTreeIsGreen:
    def test_checker_green_on_the_committed_tree(self):
        problems = check(
            load_parity_yml(),
            golden_docs(),
            json.loads(SNAPSHOT.read_text()),
        )
        assert problems == []

    def test_statuses_within_the_one_way_door(self):
        parity = load_parity_yml()
        assert set(parity["subsystems"].values()) <= {"pending", "ported"}
        # the first flip (ORDER-004 item 2): help is ported, one-way — and
        # every ported row carries its mandatory A-16 ratchet row.
        assert parity["subsystems"]["help"] == "ported"
        ratchet = parity["depth"]["ratchet"]
        for name, status in parity["subsystems"].items():
            if status == "ported":
                assert name in ratchet, name
        assert parity["kernel"]["status"] == "pending"

    def test_roster_matches_golden_dirs_both_directions(self):
        parity = load_parity_yml()
        dirs = {d.name for d in GOLDENS_ROOT.iterdir() if d.is_dir()}
        assert set(parity["subsystems"]) == dirs


# ------------------------------------------------------- coverage extraction
class TestCoverageExtraction:
    def test_events_tables_settings_extracted(self):
        docs = [
            {
                "steps": [
                    {"events": [{"event": "xp.awarded"}]},
                    {"events": []},
                ],
                "db_delta": {
                    "xp": {"added": [{"user_id": "<@m>"}]},
                    "settings": {"added": [{"key": "xp.enabled", "value": "1"}]},
                },
            }
        ]
        covered = covered_surfaces(docs)
        assert covered["events"] == {"xp.awarded"}
        assert covered["tables"] == {"xp", "settings"}
        assert covered["settings"] == {"xp.enabled"}

    def test_real_corpus_touches_surfaces(self):
        docs = golden_docs()
        all_docs = [d for group in docs.values() for d in group]
        covered = covered_surfaces(all_docs)
        assert len(covered["tables"]) > 10
        assert len(covered["events"]) > 0

    def test_declared_surfaces_duck_typed_from_snapshot(self):
        snapshot = {
            "subsystems": {
                "xp": {
                    "events": [{"name": "xp.level_up"}],
                    "stores": [{"table": "xp"}],
                    "settings": [{"key": "xp.enabled"}],
                }
            }
        }
        declared = declared_surfaces(snapshot, "xp")
        assert declared == {
            "events": {"xp.level_up"},
            "tables": {"xp"},
            "settings": {"xp.enabled"},
        }


# ------------------------------------------------------------ the A-16 rules
def _parity_fixture(**overrides):
    base = {
        "schema_version": 1,
        "subsystems": {"xp": "pending"},
        "depth": {
            "reason_classes": ["time-driven", "env-keyed-integration"],
            "exemptions": {},
            "ratchet": {},
        },
    }
    base.update(overrides)
    return base


def _docs_fixture():
    return {
        "xp": [
            {
                "steps": [{"events": [{"event": "xp.awarded"}]}],
                "db_delta": {"xp": {"added": []}},
            }
        ]
    }


def _snapshot_fixture():
    return {
        "subsystems": {
            "xp": {
                "events": [{"name": "xp.awarded"}, {"name": "xp.level_up"}],
                "stores": [{"table": "xp"}],
                "settings": [],
            }
        }
    }


class TestDepthRules:
    def test_r1_bad_status(self):
        parity = _parity_fixture(subsystems={"xp": "porting"})
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        assert any("R1" in p and "porting" in p for p in problems)

    def test_r1_roster_drift_both_directions(self):
        parity = _parity_fixture(subsystems={"xp": "pending", "ghost": "pending"})
        docs = _docs_fixture()
        docs["orphan_dir"] = []
        problems = check(parity, docs, _snapshot_fixture())
        assert any("ghost" in p for p in problems)
        assert any("orphan_dir" in p for p in problems)

    def test_r1_exemption_reason_class_enforced(self):
        parity = _parity_fixture(subsystems={"xp": "ported"})
        parity["depth"]["exemptions"] = {
            "xp": [{"surface": "event:xp.level_up", "reason": "flaky"}]
        }
        parity["depth"]["ratchet"] = {"xp": {"events": 1, "tables": 1, "settings": 0}}
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        assert any("reason class" in p for p in problems)

    def test_r2_ported_flip_needs_full_coverage_or_exempt(self):
        parity = _parity_fixture(subsystems={"xp": "ported"})
        parity["depth"]["ratchet"] = {"xp": {"events": 1, "tables": 1, "settings": 0}}
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        # xp.level_up is declared but neither covered nor exempt
        assert any("R2" in p and "event:xp.level_up" in p for p in problems)

    def test_r2_exemption_satisfies_the_floor(self):
        parity = _parity_fixture(subsystems={"xp": "ported"})
        parity["depth"]["exemptions"] = {
            "xp": [
                {
                    "surface": "event:xp.level_up",
                    "reason": "time-driven: fires from the tasks loop only",
                }
            ]
        }
        parity["depth"]["ratchet"] = {"xp": {"events": 1, "tables": 1, "settings": 0}}
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        assert problems == []

    def test_r3_ported_requires_ratchet_row(self):
        parity = _parity_fixture(subsystems={"xp": "ported"})
        parity["depth"]["exemptions"] = {
            "xp": [{"surface": "event:xp.level_up", "reason": "time-driven: loop"}]
        }
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        assert any("R3" in p and "no depth.ratchet row" in p for p in problems)

    def test_r3_counts_never_decrease(self):
        parity = _parity_fixture()
        parity["depth"]["ratchet"] = {"xp": {"events": 5, "tables": 1, "settings": 0}}
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        assert any("R3" in p and "5 -> 1" in p for p in problems)

    def test_r4_ratchet_row_on_pending_is_a_reverted_flip(self):
        parity = _parity_fixture()
        parity["depth"]["ratchet"] = {"xp": {"events": 0, "tables": 0, "settings": 0}}
        problems = check(parity, _docs_fixture(), _snapshot_fixture())
        assert any("R4" in p and "one-way door" in p for p in problems)

    def test_write_ratchet_is_upward_only(self):
        parity = _parity_fixture(subsystems={"xp": "ported"})
        parity["depth"]["ratchet"] = {"xp": {"events": 9, "tables": 0, "settings": 0}}
        updated = write_ratchet(parity, _docs_fixture())
        row = updated["depth"]["ratchet"]["xp"]
        assert row["events"] == 9  # committed floor kept
        assert row["tables"] == 1  # grew to the measured count


# ------------------------------------------- the comment-preserving writer
class TestWriteRatchetPreservesComments:
    """--write-ratchet is a text splice: only the machine-minted
    `depth.ratchet` block is rewritten. The old `yaml.safe_dump` full
    rewrite destroyed the ~130-line comment header on every run (the
    run-learn-restore-hand-apply pain across the flip PRs)."""

    def test_real_file_identity_round_trip_is_byte_identical(self):
        """Splicing the committed values back in reproduces the whole
        file byte-for-byte — the header, the exemption prose, and the
        `# ratchet:` schema comment (which must never be mistaken for
        the real key) all survive."""
        text = PARITY_YML.read_text()
        ratchet = load_parity_yml()["depth"]["ratchet"]
        assert splice_ratchet_text(text, ratchet) == text

    def test_header_survives_a_value_bump_byte_identical(self):
        text = PARITY_YML.read_text()
        parity = load_parity_yml()
        ratchet = {k: dict(v) for k, v in parity["depth"]["ratchet"].items()}
        ratchet["xp"]["events"] += 1
        out = splice_ratchet_text(text, ratchet)
        # every byte up to the spliced block is untouched
        block_at = text.index("\n  ratchet:\n") + 1
        assert out[:block_at] == text[:block_at]
        # and the parsed document changed ONLY in depth.ratchet
        reparsed = yaml.safe_load(out)
        assert reparsed["depth"]["ratchet"] == ratchet
        reparsed["depth"]["ratchet"] = parity["depth"]["ratchet"]
        assert reparsed == parity

    def test_minted_values_match_the_old_writer(self):
        """Semantics pin: the splice writes exactly the rows the old
        destructive `yaml.safe_dump(write_ratchet(...))` path minted —
        same upward-only values, nothing else moved."""
        parity = load_parity_yml()
        updated = write_ratchet(parity, golden_docs())
        old_doc = yaml.safe_load(
            yaml.safe_dump(updated, sort_keys=True, allow_unicode=True)
        )
        new_doc = yaml.safe_load(
            splice_ratchet_text(PARITY_YML.read_text(),
                                updated["depth"]["ratchet"])
        )
        assert new_doc == old_doc

    def test_missing_ratchet_key_is_a_loud_error(self):
        text = "depth:\n  reason_classes: []\nother: 1\n"
        with pytest.raises(SystemExit, match="no `ratchet:` key"):
            splice_ratchet_text(text, {"xp": {"events": 1}})

    def test_synthetic_splice_replaces_only_the_block(self):
        text = (
            "# header comment survives\n"
            "depth:\n"
            "  # ratchet:\n"
            "  #   <subsystem>: {events: N, tables: N, settings: N}\n"
            "  ratchet:\n"
            "    old_row: {events: 1, tables: 1, settings: 1}\n"
            "tail: kept\n"
        )
        out = splice_ratchet_text(
            text, {"xp": {"events": 2, "tables": 3, "settings": 0}},
        )
        assert out == (
            "# header comment survives\n"
            "depth:\n"
            "  # ratchet:\n"
            "  #   <subsystem>: {events: N, tables: N, settings: N}\n"
            "  ratchet:\n"
            "    xp: {events: 2, tables: 3, settings: 0}\n"
            "tail: kept\n"
        )

    def test_empty_ratchet_renders_the_flow_empty_mapping(self):
        text = "depth:\n  ratchet:\n    xp: {events: 1, tables: 0, settings: 0}\n"
        assert splice_ratchet_text(text, {}) == "depth:\n  ratchet: {}\n"


# ------------------------------------------------------------- the two legs
class TestGateDriver:
    def test_gate_leg_vacuous_only_at_zero_ported(self, capsys, monkeypatch):
        """The birth semantics, kept as a fixture pin: zero ported rows ⇒
        vacuously green (the check could be marked required from day one)."""
        import tools.run_golden_parity as rgp

        monkeypatch.setattr(rgp, "_load_parity_yml",
                            lambda: {"subsystems": {"xp": "pending"}})
        assert run_gate() == 0
        out = capsys.readouterr().out
        assert "vacuously GREEN" in out
        assert "PENDING (expected-red, reported not failing)" in out

    def test_gate_leg_gates_ported_rows_for_real(self, capsys, monkeypatch):
        """Post-flip (help is ported) the gate is NEVER vacuous: with no
        replay binding (the DB-free unit env) it reds honestly instead of
        false-greening a flipped row."""
        import tools.run_golden_parity as rgp

        monkeypatch.setattr(
            rgp, "_replay_binding",
            lambda: (None, "no bot-under-test binding (unit env)"))
        assert run_gate() == 1
        out = capsys.readouterr().out
        assert "vacuously" not in out
        assert "flipped `ported` but no replay is possible" in out

    def test_report_leg_is_born_red_by_design(self, capsys):
        assert run_report() == 1
        out = capsys.readouterr().out
        assert "RED BY DESIGN" in out
        assert "467 goldens" in out

    def test_parity_yml_is_valid_yaml_with_kernel_home(self):
        parity = yaml.safe_load(PARITY_YML.read_text())
        assert "audit.action_recorded" in parity["kernel"]["events"]
        assert "event_outbox" in parity["kernel"]["tables"]
