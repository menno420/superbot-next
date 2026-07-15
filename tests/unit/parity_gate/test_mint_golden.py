"""External pins for tools/mint_golden.py — the D-0073 mint procedure as a
tool. DB-free: everything here exercises the pure text/pathing/disposition
layers; no harness boots, no captures (a capture needs Postgres — the CI
gate lane owns that posture).

Covered: the five-site count-pin roster (four mutable sites move + the
minted_goldens source assert; the IMPORT pin never moves), exactly-once
anchor failure, count arithmetic from disk, refuse-overwrite (#193),
kernel vs non-kernel disposition routing (D-0075's inversion via the
reused apply_dispositions), case resolution, and the corpus JSON
byte-form.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools.mint_golden import (
    DEPTH_TEST,
    GOLDENS_ROOT,
    PARITY_YML,
    REPLAY_ADAPTER_TEST,
    CorpusCounts,
    MintError,
    check_overwrite,
    compute_counts,
    count_goldens_on_disk,
    docs_byte_identical,
    dropped_surfaces,
    golden_target,
    main,
    planned_pin_edits,
    prepare_golden_doc,
    resolve_case,
    rewrite_depth_test_pins,
    rewrite_parity_yml_pins,
    rewrite_replay_adapter_pins,
    serialize_golden,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _current_counts() -> CorpusCounts:
    return compute_counts(GOLDENS_ROOT, PARITY_YML.read_text())


def _bumped(counts: CorpusCounts) -> CorpusCounts:
    return CorpusCounts(imported=counts.imported, retired=counts.retired,
                        total=counts.total + 1)


# --------------------------------------------------------- count arithmetic
class TestCounts:
    def test_identity(self):
        counts = CorpusCounts(imported=465, retired=3, total=494)
        assert counts.minted == 32          # total − imported + retired

    def test_disk_count_ignores_root_files(self, tmp_path):
        (tmp_path / "karma").mkdir()
        (tmp_path / "karma" / "a.json").write_text("{}")
        (tmp_path / "karma" / "b.json").write_text("{}")
        (tmp_path / "_sweep_skips.json").write_text("{}")   # root, not a golden
        assert count_goldens_on_disk(tmp_path) == 2

    def test_real_tree_pins_cohere(self):
        # The committed tree's own coherence: disk corpus == every pin.
        counts = _current_counts()
        assert counts.total == count_goldens_on_disk(GOLDENS_ROOT)
        assert f"minted_goldens: {counts.minted}" in PARITY_YML.read_text()
        assert (f"assert golden_count == {counts.total}"
                in REPLAY_ADAPTER_TEST.read_text())

    def test_missing_source_pins_red(self):
        with pytest.raises(MintError):
            compute_counts(GOLDENS_ROOT, "source:\n  goldens: oops\n")


# ----------------------------------------------------------- pin rewriting
class TestPinRewriting:
    """All five sites, on copies of the REAL files: the four mutable
    anchors move to the bumped counts; the import pin stays byte-stable."""

    def test_parity_yml_sites_move_import_pin_does_not(self):
        old = PARITY_YML.read_text()
        counts = _bumped(_current_counts())
        new = rewrite_parity_yml_pins(old, counts)
        assert f"minted_goldens: {counts.minted}" in new
        assert f"imported + minted − retired = {counts.total}" in new
        # the two pins a mint NEVER moves, byte-checked:
        assert f"goldens: {counts.imported}" in new
        assert f"retired_goldens: {counts.retired}" in new
        assert re.findall(r"(?m)^\s*goldens:\s*\d+", old) == \
            re.findall(r"(?m)^\s*goldens:\s*\d+", new)

    def test_replay_adapter_sites_move(self):
        counts = _bumped(_current_counts())
        new = rewrite_replay_adapter_pins(REPLAY_ADAPTER_TEST.read_text(),
                                          counts)
        assert f"assert golden_count == {counts.total}" in new
        assert f"replayable case ({counts.total}/{counts.total})" in new

    def test_depth_test_sites_move_import_pin_does_not(self):
        old = DEPTH_TEST.read_text()
        counts = _bumped(_current_counts())
        new = rewrite_depth_test_pins(old, counts)
        assert f"assert len(goldens) == {counts.total}" in new
        assert f'assert "{counts.total} goldens" in out' in new
        assert f'assert source["minted_goldens"] == {counts.minted}' in new
        # the IMPORT pin line survives verbatim (test_check_parity_depth:72):
        import_line = next(l for l in old.splitlines()
                           if 'assert source["goldens"] ==' in l)
        assert import_line in new.splitlines()

    def test_same_counts_is_a_no_op(self):
        counts = _current_counts()
        for path, rewrite in ((PARITY_YML, rewrite_parity_yml_pins),
                              (REPLAY_ADAPTER_TEST, rewrite_replay_adapter_pins),
                              (DEPTH_TEST, rewrite_depth_test_pins)):
            text = path.read_text()
            assert rewrite(text, counts) == text, path

    def test_missing_anchor_is_red_not_partial(self):
        counts = _bumped(_current_counts())
        drifted = PARITY_YML.read_text().replace("minted_goldens:",
                                                 "minted_gold3ns:")
        with pytest.raises(MintError, match="minted_goldens"):
            rewrite_parity_yml_pins(drifted, counts)

    def test_duplicated_anchor_is_red(self):
        counts = _bumped(_current_counts())
        text = REPLAY_ADAPTER_TEST.read_text()
        with pytest.raises(MintError, match="golden_count"):
            rewrite_replay_adapter_pins(
                text + "\nassert golden_count == 494\n", counts)

    def test_touched_import_pin_is_red(self):
        # A rewrite that WOULD move a guarded pin must refuse: feed a file
        # where the guarded anchor is ambiguous (two `retired_goldens:`).
        counts = _bumped(_current_counts())
        text = PARITY_YML.read_text() + "\nretired_goldens: 99\n"
        with pytest.raises(MintError, match="retired_goldens"):
            rewrite_parity_yml_pins(text, counts)

    def test_planned_edits_cover_exactly_the_three_pin_files(self):
        plans = planned_pin_edits(_bumped(_current_counts()))
        assert [p for p, _o, _n in plans] == [PARITY_YML,
                                              REPLAY_ADAPTER_TEST, DEPTH_TEST]
        assert all(old != new for _p, old, new in plans)
        # and at the CURRENT counts every file is a no-op (inert-tool pin:
        # this PR ships the tool with the corpus untouched at its counts).
        assert all(old == new
                   for _p, old, new in planned_pin_edits(_current_counts()))


# --------------------------------------------------------- refuse-overwrite
class TestOverwrite:
    def test_existing_golden_refused_without_force(self, tmp_path):
        target = tmp_path / "karma" / "karma_thanks_grant.json"
        target.parent.mkdir()
        target.write_text("{}")
        with pytest.raises(MintError, match="--force"):
            check_overwrite(target, force=False)
        check_overwrite(target, force=True)         # deliberate re-mint

    def test_fresh_target_needs_no_force(self, tmp_path):
        check_overwrite(tmp_path / "new" / "case.json", force=False)


# ------------------------------------------------- disposition routing (D-0075)
def _doc(subsystem: str) -> dict:
    return {
        "harness_version": 1,
        "case_id": f"{subsystem}.case",
        "subsystem": subsystem,
        "seed": 42,
        "notes": "",
        "steps": [{
            "input": {"kind": "command", "content": "!x",
                      "persona": "member", "channel": "general"},
            "calls": [],
            "events": [{"event": "command.dispatched"},
                       {"event": "karma.granted"}],
        }],
        "db_delta": {"audit_log": {"added": [{"verb": "x"}]},
                     "event_outbox": {"added": [{"event": "y"}]},
                     "karma": {"added": [{"points": 1}]}},
    }


class TestDispositionRouting:
    def test_domain_doc_loses_the_spine(self):
        prepared = prepare_golden_doc(_doc("karma"))
        assert set(prepared["db_delta"]) == {"karma"}
        assert [e["event"] for e in prepared["steps"][0]["events"]] == \
            ["karma.granted"]
        tables, events = dropped_surfaces(_doc("karma"), prepared)
        assert tables == ["audit_log", "event_outbox"]
        assert events == ["command.dispatched"]

    def test_kernel_doc_keeps_the_spine(self):
        prepared = prepare_golden_doc(_doc("kernel"))
        assert set(prepared["db_delta"]) == {"audit_log", "event_outbox",
                                             "karma"}
        assert [e["event"] for e in prepared["steps"][0]["events"]] == \
            ["command.dispatched", "karma.granted"]

    def test_byte_compare_flags_drift(self):
        a, b = _doc("kernel"), _doc("kernel")
        assert docs_byte_identical(a, b)
        b["db_delta"]["audit_log"]["added"][0]["verb"] = "drifted"
        assert not docs_byte_identical(a, b)


# ------------------------------------------------------------ case sourcing
class TestCaseResolution:
    def test_curated_case_resolves_typed(self):
        case = resolve_case("karma.thanks_grant")
        assert case.subsystem == "karma"
        assert golden_target(case) == \
            GOLDENS_ROOT / "karma" / "karma_thanks_grant.json"

    def test_sweep_case_reconstructs_from_its_golden(self):
        case = resolve_case("sweep.logging_status")
        assert case.subsystem == "logging"
        assert golden_target(case).exists()

    def test_unknown_case_is_red_with_the_curated_pointer(self):
        with pytest.raises(MintError, match="parity/cases/curated.py"):
            resolve_case("nope.never_existed")

    def test_main_reds_before_any_boot_on_unknown_case(self, capsys):
        assert main(["nope.never_existed"]) == 1
        assert "mint_golden: RED" in capsys.readouterr().out

    def test_main_refuses_existing_golden_before_any_boot(self, capsys):
        # karma.thanks_grant's golden exists → the #193 refusal fires
        # BEFORE capture (no harness, no DB — proof: this test is DB-free).
        assert main(["karma.thanks_grant"]) == 1
        assert "--force" in capsys.readouterr().out


# ------------------------------------------------------------ serialization
class TestSerialization:
    def test_matches_the_corpus_byte_form(self):
        # A round-trip through serialize_golden reproduces the committed
        # bytes of a real (non-kernel) golden — the mint writes what the
        # corpus already looks like. (The four kernel goldens are the
        # known ascii-escaped historical exception.)
        path = GOLDENS_ROOT / "karma" / "karma_thanks_grant.json"
        raw = path.read_text()
        assert serialize_golden(json.loads(raw)) == raw
