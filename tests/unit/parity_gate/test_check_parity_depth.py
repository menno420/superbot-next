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
        # (D-0073) + 4 minted kernel-band goldens (D-0075) + 1 minted
        # creature-battle golden (D-0079) + 1 minted casino poker play-layer
        # golden (D-0073 procedure) + 4 minted browse-interaction goldens
        # (2026-07-12) + 2 minted multi-step tournament-flow goldens + 5 minted
        # WP-1 mining write-parity goldens (equip/unequip/loadout
        # save·apply·delete) + 1 minted paid-tournament conservation golden
        # + 2 minted creature picker/bot-guard goldens (D-0081) + 3 minted
        # fishing cast-leg reel write goldens + 4 minted energy-slice-2
        # mining cook/use goldens (2026-07-13) + 1 minted cleanup
        # anti-evasion toggle write golden (completeness-remainders residue
        # port, 2026-07-13) + 1 minted fishing howtofish rules-card golden
        # (completeness-remainders fishing row, 2026-07-13) + 4 minted
        # fishing minigame-timing slice-1 goldens (premature spook/grace +
        # trophy fight land/escape — the first Step.advance_s cases,
        # 2026-07-14) (parity.yml
        # source.minted_goldens) − 3 retired (sweep_cog.json, the deploy-ops
        # `!cog` capture, + sweep_query_logs.json / sweep_recent_errors.json,
        # the run-order-dependent log-ring captures — parity.yml
        # source.retired_goldens, the 2026-07-12 corpus rulings).
        goldens = list(GOLDENS_ROOT.glob("*/*.json"))
        assert len(goldens) == 499

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
        # 2 D-0073 modal-submit mints + 4 D-0075 kernel-band mints
        # + 1 D-0079 creature-battle mint + 1 casino poker play-layer mint
        # (D-0073 procedure) + 4 browse-interaction mints (2026-07-12)
        # + 2 multi-step tournament-flow mints
        # + 5 WP-1 mining write-parity mints (equip/unequip/loadout)
        # + 1 paid-tournament conservation mint (2026-07-12)
        # + 2 creature picker/bot-guard mints (D-0081)
        # + 3 fishing cast-leg reel write mints (2026-07-13)
        # + 4 energy-slice-2 mining cook/use mints (2026-07-13)
        # + 1 cleanup anti-evasion toggle write mint (completeness-remainders
        # residue port, 2026-07-13)
        # + 1 fishing howtofish rules-card mint (2026-07-13)
        # + 4 fishing minigame-timing slice-1 mints (2026-07-14)
        # + 1 fishing cast-again continuation mint (2026-07-14)
        assert source["minted_goldens"] == 37
        # sweep_cog.json (the deploy-ops `!cog` capture) +
        # sweep_query_logs.json / sweep_recent_errors.json (the
        # run-order-dependent log-ring captures) — the 2026-07-12 corpus
        # rulings; the `_sweep_skips.json` "cog" / "query_logs" /
        # "recent_errors" entries close the class's leaks past the
        # capture skip list.
        assert source["retired_goldens"] == 3


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
        # the kernel coverage home flipped with the D-0075 kernel-band
        # goldens — same one-way door, same mandatory ratchet row.
        assert parity["kernel"]["status"] == "ported"
        assert "kernel" in ratchet

    def test_roster_matches_golden_dirs_both_directions(self):
        # parity/goldens/kernel/ is the kernel coverage home's dir
        # (D-0075) — the ONE golden dir that is never a subsystems row.
        parity = load_parity_yml()
        dirs = {d.name for d in GOLDENS_ROOT.iterdir() if d.is_dir()}
        assert set(parity["subsystems"]) | {"kernel"} == dirs
        assert "kernel" not in parity["subsystems"]


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


# ------------------------------------------------ the kernel coverage home
def _kernel_fixture(status="ported"):
    """A parity doc + docs tree for the kernel home (A-16 clause 3 as a
    pseudo-subsystem, D-0075)."""
    parity = _parity_fixture()
    parity["kernel"] = {
        "status": status,
        "events": ["audit.action_recorded", "command.dispatched"],
        "tables": ["audit_log", "event_outbox", "idempotency_keys"],
    }
    docs = _docs_fixture()
    docs["kernel"] = [
        {
            "steps": [{"events": [{"event": "audit.action_recorded"},
                                  {"event": "command.dispatched"}]}],
            "db_delta": {"audit_log": {"added": []},
                         "event_outbox": {"added": []}},
        }
    ]
    return parity, docs


class TestKernelHome:
    def test_kernel_dir_without_home_section_is_r1(self):
        parity = _parity_fixture()
        docs = _docs_fixture()
        docs["kernel"] = []
        problems = check(parity, docs, _snapshot_fixture())
        assert any("R1" in p and "coverage-home section" in p
                   for p in problems)

    def test_kernel_dir_never_needs_a_subsystems_row(self):
        parity, docs = _kernel_fixture(status="pending")
        problems = check(parity, docs, _snapshot_fixture())
        assert not any("parity/goldens/kernel/" in p and "subsystems row" in p
                       for p in problems)

    def test_kernel_bad_status_is_r1(self):
        parity, docs = _kernel_fixture(status="porting")
        problems = check(parity, docs, _snapshot_fixture())
        assert any("R1 kernel" in p and "porting" in p for p in problems)

    def test_kernel_r2_floor_over_its_own_lists(self):
        # idempotency_keys is declared in the kernel home, covered by no
        # kernel-band golden, and not exempt — the flip reds.
        parity, docs = _kernel_fixture()
        parity["depth"]["ratchet"]["kernel"] = {
            "events": 2, "tables": 2, "settings": 0}
        problems = check(parity, docs, _snapshot_fixture())
        assert any("R2 kernel" in p and "table:idempotency_keys" in p
                   for p in problems)
        assert not any("R2 kernel" in p and "event:" in p for p in problems)

    def test_kernel_r2_exemption_satisfies_the_floor(self):
        parity, docs = _kernel_fixture()
        parity["depth"]["exemptions"] = {
            "kernel": [{"surface": "table:idempotency_keys",
                        "reason": "time-driven: task-lane writers only"}]
        }
        parity["depth"]["ratchet"]["kernel"] = {
            "events": 2, "tables": 2, "settings": 0}
        problems = check(parity, docs, _snapshot_fixture())
        assert problems == []

    def test_kernel_r3_ported_requires_ratchet_row(self):
        parity, docs = _kernel_fixture()
        parity["depth"]["exemptions"] = {
            "kernel": [{"surface": "table:idempotency_keys",
                        "reason": "time-driven: task-lane writers only"}]
        }
        problems = check(parity, docs, _snapshot_fixture())
        assert any("R3 kernel" in p and "no depth.ratchet row" in p
                   for p in problems)

    def test_kernel_r3_counts_never_decrease(self):
        parity, docs = _kernel_fixture()
        parity["depth"]["ratchet"]["kernel"] = {
            "events": 5, "tables": 2, "settings": 0}
        problems = check(parity, docs, _snapshot_fixture())
        assert any("R3 kernel" in p and "5 -> 2" in p for p in problems)

    def test_kernel_r4_ratchet_row_on_pending_is_a_reverted_flip(self):
        parity, docs = _kernel_fixture(status="pending")
        parity["depth"]["ratchet"]["kernel"] = {
            "events": 2, "tables": 2, "settings": 0}
        problems = check(parity, docs, _snapshot_fixture())
        assert any("R4 kernel" in p and "one-way door" in p for p in problems)

    def test_write_ratchet_mints_the_kernel_row(self):
        parity, docs = _kernel_fixture()
        updated = write_ratchet(parity, docs)
        assert updated["depth"]["ratchet"]["kernel"] == {
            "events": 2, "tables": 2, "settings": 0}

    def test_write_ratchet_skips_a_pending_kernel(self):
        parity, docs = _kernel_fixture(status="pending")
        updated = write_ratchet(parity, docs)
        assert "kernel" not in updated["depth"]["ratchet"]

    def test_real_tree_kernel_floor_is_satisfied(self):
        """The committed tree: every kernel.events/tables surface is either
        exercised by a kernel-band golden or exempt under an existing
        reason class (the real-tree green test checks this too — this one
        names the dimension)."""
        parity = load_parity_yml()
        docs = golden_docs()
        covered = covered_surfaces(docs.get("kernel", []))
        exempt = {row["surface"]
                  for row in parity["depth"]["exemptions"]["kernel"]}
        for event in parity["kernel"]["events"]:
            assert event in covered["events"], event
        for table in parity["kernel"]["tables"]:
            assert (table in covered["tables"]
                    or f"table:{table}" in exempt), table

    def test_gate_driver_includes_a_ported_kernel(self, capsys, monkeypatch):
        """run_gate treats the kernel home as a pseudo-subsystem: a ported
        kernel's goldens are REQUIRED-green (denominator-checked), a
        pending kernel is expected-red reported."""
        import tools.run_golden_parity as rgp

        monkeypatch.setattr(rgp, "_load_parity_yml", lambda: {
            "subsystems": {"xp": "pending"},
            "kernel": {"status": "ported"},
        })
        monkeypatch.setattr(rgp, "_replay_binding", lambda: (object(), ""))
        kernel_count = rgp._golden_counts()["kernel"]
        assert kernel_count >= 1

        async def _fake_replay_corpus(only_subsystems, *, verbose_failures=8):
            assert only_subsystems == {"kernel"}
            results = {f"kernel.case{i}": ("kernel", True, [])
                       for i in range(kernel_count)}
            return results, {}

        monkeypatch.setattr(rgp, "_replay_corpus", _fake_replay_corpus)
        assert run_gate() == 0
        out = capsys.readouterr().out
        assert "gate: GREEN" in out


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

    # the three codex #199 P2s (comment 4948021173 triage), each pinned:
    def test_interstitial_comment_is_consumed_with_the_block(self):
        """A shallow comment BETWEEN ratchet rows must not stop the extent
        scan — leaving the post-comment rows in place duplicated the keys
        and let a stale count win (codex P2, splice extent)."""
        text = (
            "depth:\n"
            "  ratchet:\n"
            "    admin: {events: 1, tables: 1, settings: 0}\n"
            "  # hand comment between rows\n"
            "    ai: {events: 2, tables: 2, settings: 0}\n"
        )
        out = splice_ratchet_text(
            text, {"admin": {"events": 1, "tables": 1, "settings": 0}},
        )
        assert out == (
            "depth:\n"
            "  ratchet:\n"
            "    admin: {events: 1, tables: 1, settings: 0}\n"
        )
        assert yaml.safe_load(out)["depth"]["ratchet"] == {
            "admin": {"events": 1, "tables": 1, "settings": 0},
        }

    def test_trailing_blank_plus_sibling_comment_is_preserved(self):
        """A blank line then a deeper-indented comment that belongs to the
        NEXT section must not be swallowed by the splice (codex P2,
        following-sibling comments)."""
        text = (
            "depth:\n"
            "  ratchet:\n"
            "    xp: {events: 1, tables: 1, settings: 0}\n"
            "\n"
            "    # exemption note below (belongs to exemptions)\n"
            "  exemptions: {}\n"
        )
        out = splice_ratchet_text(
            text, {"xp": {"events": 2, "tables": 1, "settings": 0}},
        )
        assert out == (
            "depth:\n"
            "  ratchet:\n"
            "    xp: {events: 2, tables: 1, settings: 0}\n"
            "\n"
            "    # exemption note below (belongs to exemptions)\n"
            "  exemptions: {}\n"
        )

    def test_crlf_line_endings_survive_the_splice(self):
        """A CRLF-shaped file keeps CRLF everywhere — the splice never
        silently renormalizes bytes outside the block (codex P2; the repo's
        .gitattributes leaves parity.yml eol unspecified, so nothing else
        would restore it)."""
        text = (
            "# header\r\n"
            "depth:\r\n"
            "  ratchet:\r\n"
            "    xp: {events: 1, tables: 1, settings: 0}\r\n"
        )
        out = splice_ratchet_text(
            text, {"xp": {"events": 2, "tables": 1, "settings": 0}},
        )
        assert out == (
            "# header\r\n"
            "depth:\r\n"
            "  ratchet:\r\n"
            "    xp: {events: 2, tables: 1, settings: 0}\r\n"
        )
        # and the identity property holds in CRLF shape too
        assert splice_ratchet_text(
            text, {"xp": {"events": 1, "tables": 1, "settings": 0}},
        ) == text


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

    def test_report_leg_prints_full_corpus_banner(self, capsys):
        # No replay binding in the unit env, so the leg exits nonzero;
        # the banner is the neutral full-corpus report wording (the leg
        # is live-green in CI since 2026-07-13).
        assert run_report() == 1
        out = capsys.readouterr().out
        assert "full-corpus parity report" in out
        assert "499 goldens" in out

    def test_gate_leg_reds_on_silently_dropped_ported_golden(self, capsys,
                                                              monkeypatch):
        """F-003 regression: a golden that fails reconstruction for a
        `ported` subsystem must RED the gate, not quietly shrink the
        replayed set under a GREEN banner. Before the fix, `run_gate` never
        compared `_golden_counts()` (goldens on disk) against the replayed
        case count — it only iterated `results`, which by construction never
        contains an entry for a case that failed to reconstruct."""
        import tools.run_golden_parity as rgp

        monkeypatch.setattr(rgp, "_load_parity_yml",
                            lambda: {"subsystems": {"help": "ported"}})
        monkeypatch.setattr(rgp, "_replay_binding", lambda: (object(), ""))
        real_count = rgp._golden_counts()["help"]
        assert real_count >= 1

        async def _fake_replay_corpus(only_subsystems, *, verbose_failures=8):
            # one fewer than the real golden count — the injected drop.
            results = {f"help.case{i}": ("help", True, [])
                       for i in range(real_count - 1)}
            return results, {"help": 1}

        monkeypatch.setattr(rgp, "_replay_corpus", _fake_replay_corpus)
        assert run_gate() == 1
        out = capsys.readouterr().out
        assert f"replayed {real_count - 1}/{real_count}" in out
        assert "silently dropped" in out
        assert "gate: GREEN" not in out

    def test_gate_leg_green_when_replayed_count_matches_golden_count(
            self, capsys, monkeypatch):
        """The counterpart pin: when every golden on disk replayed (green or
        not), the denominator check itself must NOT false-red."""
        import tools.run_golden_parity as rgp

        monkeypatch.setattr(rgp, "_load_parity_yml",
                            lambda: {"subsystems": {"help": "ported"}})
        monkeypatch.setattr(rgp, "_replay_binding", lambda: (object(), ""))
        real_count = rgp._golden_counts()["help"]

        async def _fake_replay_corpus(only_subsystems, *, verbose_failures=8):
            results = {f"help.case{i}": ("help", True, [])
                       for i in range(real_count)}
            return results, {}

        monkeypatch.setattr(rgp, "_replay_corpus", _fake_replay_corpus)
        assert run_gate() == 0
        out = capsys.readouterr().out
        assert "gate: GREEN" in out

    def test_parity_yml_is_valid_yaml_with_kernel_home(self):
        parity = yaml.safe_load(PARITY_YML.read_text())
        assert "audit.action_recorded" in parity["kernel"]["events"]
        assert "event_outbox" in parity["kernel"]["tables"]
