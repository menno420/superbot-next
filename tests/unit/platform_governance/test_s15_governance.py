"""S15 — platform governance: the IntentPosture DEGRADE contract, the
degrade-notice latch, the guild-cap lead-time alert, survivability +
slash-cap gates, the permission census (frozen L0 spec 14)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

import sb.kernel.platform_governance as pg
from sb.spec.config import INTENT_CONTRACT, IntentPosture
from sb.spec.governance import check_manifest_survival, slash_cap_violations
from tools.permission_census import (
    Disposition,
    admin_notice_lines,
    carry_verify,
    partition,
)


# --- the seam-corrected INTENT_CONTRACT (spec 14 §2.B / PG-2 = DEGRADE) -----------

class TestIntentContract:
    def test_both_privileged_intents_degrade(self):
        for intent in INTENT_CONTRACT:
            assert intent.privileged
            assert intent.required is False
            assert intent.posture is IntentPosture.DEGRADE
            assert intent.degrades  # never an empty degrade set

    def test_mirror_invariant_holds_on_the_shipped_contract(self):
        for intent in INTENT_CONTRACT:
            assert intent.required == (intent.posture is IntentPosture.REQUIRED)

    def test_message_content_degrade_set(self):
        mc = next(i for i in INTENT_CONTRACT if i.name == "message_content")
        assert set(mc.degrades) == {"prefix", "fuzzy", "triggers",
                                    "nl_message", "passive_onmessage"}


# --- the once-per-state-change degrade notice (spec 14 §2.B item 3) ----------------

@pytest.fixture
def findings(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr(pg, "record_operator_finding",
                        lambda **kw: out.append(kw))
    pg.reset_platform_governance_for_tests()
    yield out
    pg.reset_platform_governance_for_tests()


def _marker(intent="message_content", degrades=("prefix",)):
    from sb.kernel.config import DegradedCapability
    return DegradedCapability(intent=intent, degrades=tuple(degrades))


class TestDegradeNotice:
    def test_fires_once_per_state_not_per_deploy(self, findings):
        markers = (_marker(),)
        assert pg.emit_degrade_notices(markers) is True
        # the redeploy under the SAME denial (Q-0193): no re-fire
        assert pg.emit_degrade_notices(markers) is False
        assert len(findings) == 1

    def test_restore_fires_a_change_notice(self, findings):
        pg.emit_degrade_notices((_marker(),))
        assert pg.emit_degrade_notices(()) is True   # denial cleared
        assert any("restored" in f["summary"] for f in findings)
        # steady full-surface state: no further notice
        assert pg.emit_degrade_notices(()) is False

    def test_clean_first_boot_writes_latch_silently(self, findings):
        assert pg.emit_degrade_notices(()) is True   # latch write, no finding
        assert findings == []


# --- the guild-cap lead-time alert (spec 14 §2.C) ----------------------------------

class TestGuildCap:
    def test_below_threshold_never_fires(self, findings):
        assert pg.evaluate_guild_cap(50) == ()
        assert findings == []

    def test_thresholds_fire_exactly_once(self, findings):
        assert pg.evaluate_guild_cap(76) == (75,)
        assert pg.evaluate_guild_cap(82) == ()      # restart at 82: latched
        assert pg.evaluate_guild_cap(91) == (90,)
        assert len(findings) == 2

    def test_one_way_latch_survives_a_count_drop(self, findings):
        pg.evaluate_guild_cap(76)
        pg.evaluate_guild_cap(60)   # dropped below — latch stays
        assert pg.evaluate_guild_cap(80) == ()

    def test_both_fire_when_crossed_together(self, findings):
        assert pg.evaluate_guild_cap(95) == (75, 90)


# --- check_intent_survival / check_slash_cap cores (spec 14 §2.A) ------------------

@dataclass(frozen=True)
class Cmd:
    name: str
    surface: str = "slash"
    slash_common: bool = False
    capability: str = ""


@dataclass(frozen=True)
class Entry:
    action_id: str = "a"
    slash_common: bool = False
    capability: str = ""


@dataclass(frozen=True)
class Panel:
    actions: tuple = ()
    selectors: tuple = ()


@dataclass(frozen=True)
class Manifest:
    key: str = "test"
    commands: tuple = ()
    panels: tuple = ()


class TestSurvival:
    def test_prefix_only_essential_is_red(self):
        m = Manifest(commands=(Cmd("balance", surface="prefix",
                                   slash_common=True),))
        problems = check_manifest_survival(m)
        assert len(problems) == 1 and "goes dark" in problems[0]

    def test_slash_twin_survives(self):
        m = Manifest(commands=(
            Cmd("balance", surface="prefix", slash_common=True,
                capability="economy.balance"),
            Cmd("balance", surface="slash", capability="economy.balance")))
        assert check_manifest_survival(m) == []

    def test_panel_rooted_essential_survives_by_presence(self):
        m = Manifest(panels=(Panel(actions=(
            Entry(action_id="open_shop", slash_common=True),)),))
        assert check_manifest_survival(m) == []

    def test_untagged_prefix_longtail_is_fine(self):
        m = Manifest(commands=(Cmd("obscure", surface="prefix"),))
        assert check_manifest_survival(m) == []


class TestSlashCap:
    def test_under_cap_clean(self):
        cmds = [Cmd(f"c{i}") for i in range(100)]
        assert slash_cap_violations(cmds) == []

    def test_over_100_top_level_red(self):
        cmds = [Cmd(f"c{i}") for i in range(101)]
        assert any("top-level" in p for p in slash_cap_violations(cmds))

    def test_over_25_group_children_red(self):
        cmds = [Cmd(f"grp sub{i}") for i in range(26)]
        assert any("group 'grp'" in p for p in slash_cap_violations(cmds))

    def test_deep_nesting_red(self):
        assert any("nests deeper" in p
                   for p in slash_cap_violations([Cmd("a b c d")]))

    def test_prefix_commands_exempt(self):
        cmds = [Cmd(f"p{i}", surface="prefix") for i in range(200)]
        assert slash_cap_violations(cmds) == []


# --- the permission census (spec 14 §2.D) ------------------------------------------

CENSUS = {
    "1": [
        {"command_id": "100", "command_name": "purge",
         "permissions": [{"id": "9", "type": "role", "permission": True}]},
        {"command_id": "101", "command_name": "balance",
         "permissions": [{"id": "8", "type": "channel", "permission": False}]},
        {"command_id": "102", "command_name": "oldthing",
         "permissions": [{"id": "7", "type": "user", "permission": True}]},
    ],
}
RENAMES = {"purge": "mod purge", "oldthing": None}


class TestCensus:
    def test_partition(self):
        records = partition(CENSUS, RENAMES)
        by_name = {r.command_name: r for r in records}
        assert by_name["purge"].disposition is Disposition.RENAMED
        assert by_name["purge"].successor == "mod purge"
        assert by_name["balance"].disposition is Disposition.PRESERVED
        assert by_name["oldthing"].disposition is Disposition.DROPPED

    def test_new_application_id_preserves_nothing(self):
        records = partition(CENSUS, RENAMES, same_application_id=False)
        assert all(r.disposition is not Disposition.PRESERVED for r in records)

    def test_carry_verify_flags_vanished_override(self):
        records = partition(CENSUS, RENAMES)
        preserved = [r for r in records if r.disposition is Disposition.PRESERVED]
        ok = carry_verify(preserved, {"1": [
            {"command_name": "balance",
             "permissions": [{"id": "8", "type": "channel", "permission": False}]}]})
        assert ok == []
        bad = carry_verify(preserved, {"1": []})
        assert any("VANISHED" in p for p in bad)

    def test_admin_notice_covers_renamed_and_dropped_only(self):
        records = partition(CENSUS, RENAMES)
        lines = admin_notice_lines(records)
        assert len(lines) == 2
        assert any("purge" in l and "mod purge" in l for l in lines)
        assert not any("balance" in l for l in lines)
