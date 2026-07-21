"""The NEW-bot replay adapter (sb/adapters/parity/) — DB-free unit legs.

The full replay (with Postgres db_delta) runs in the golden-parity workflow;
these tests pin the container-runnable half: case reconstruction from the
golden corpus, deterministic capture documents, the wire vocabulary, and the
Harness contract shape the gate driver binds.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GOLDENS_ROOT = REPO_ROOT / "parity" / "goldens"


@pytest.fixture()
def harness():
    from sb.adapters.parity.boot import Harness

    h = asyncio.run(Harness.start(require_db=False))
    yield h
    asyncio.run(h.close())


# --- case sourcing -------------------------------------------------------------


def test_full_corpus_reconstructs():
    """Every golden on disk yields a replayable case (533/533) — curated
    typed cases first, sweep cases rebuilt from their golden documents
    (465 imported + the 2 D-0073 minted modal-submit cases + the 4 D-0075
    minted kernel-band cases + the 1 minted casino poker play-layer case
    + the 1 D-0079 creature-battle case + the 4 browse-interaction minted
    cases + the 2 minted multi-step tournament-flow cases + the 5 WP-1
    mining write-parity minted cases + the 4 WP-2 mining vault write-parity
    minted cases + the 5 WP-3 mining depth/world/workshop write-parity
    minted cases + the 2 WP-5 mining skill-spend write-parity minted
    cases + the 2 WP-6 mining structure-build write-parity minted
    cases + the 4 WP-7 mining craft/respec write-parity minted
    cases + the 1 minted paid-tournament
    conservation case + the 2 D-0081 creature picker/bot-guard cases
    + the 4 energy-slice-2 mining cook/use minted cases
    + the 1 energy-slice-3 fastmine out-of-energy refusal case
    + the 3 fishing cast-leg reel write cases (2026-07-13 — curated typed
    cases: `!fish` + a Reel click by component_index)
    + the 1 cleanup anti-evasion toggle write case (2026-07-13 —
    `!wordmenu` + the 🛡️ click by component_index)
    + the 1 fishing howtofish rules-card case (2026-07-13 — `!fishing` +
    the hub 📖 How-to-fish click by component_index, a pure read)
    + the 1 cleanup policies-open case (2026-07-13 — `!cleanup` + the 🧹
    Cleanup Policies click by component_index, a pure read)
    + the 4 fishing minigame-timing slice-1 cases (2026-07-14, D-0043 —
    premature spook/grace + trophy fight land/escape; the first cases
    driving Step.advance_s clicks)
    + the 1 fishing cast-again continuation case (2026-07-14, gap 3 —
    reel a catch → click 🎣 Cast again on the CHANNEL_ANCHOR result
    card → a fresh cast panel opens)
    + the 4 curation row-72 + farm-goldens cases (2026-07-14, ORDER 022
    (a)4 — the `!rps 10` quickplay bet-settle click + the farm
    collect/buy-hen/upgrade-coop money-path clicks; the shop-hop cases
    are the first to click a followup-presented child panel)
    − 3 retired: sweep_cog.json, the deploy-ops `!cog`
    capture, plus
    sweep_query_logs.json / sweep_recent_errors.json, the run-order-dependent
    log-ring captures — each retired to the _sweep_skips entry it always
    belonged under — parity.yml source.retired_goldens). The four
    browse-interaction goldens are curated typed cases (their opening hub
    click rides component_index + a fixture_sql seed), so they source from
    CURATED_CASES, not reconstruction."""
    from sb.adapters.parity.cases import load_replay_cases

    cases = load_replay_cases(GOLDENS_ROOT)
    golden_count = sum(1 for _ in GOLDENS_ROOT.glob("*/*.json"))
    # 465 imported (parity.yml source pin) + 2 minted (D-0073) + 4 (D-0075)
    # + 1 (D-0079 creature battle) + 1 minted casino poker play-layer
    # (D-0073 procedure) + 4 (browse-interaction, 2026-07-12) + 2
    # (tournament-flow) + 5 (WP-1 mining write-parity: equip/unequip/loadout
    # save·apply·delete) + 4 (WP-2 mining vault write-parity: stash/unstash/
    # stash-all/vaultupgrade) + 5 (WP-3 mining depth/world/workshop
    # write-parity: descend/ascend/reseed-world/repair/quickcraft)
    # + 2 (WP-5 mining skill-spend write-parity: skill_write /
    # skill_bad_branch, 2026-07-13)
    # + 2 (WP-6 mining structure-build write-parity: build_forge_write /
    # build_forge_insufficient, 2026-07-13)
    # + 4 (WP-7 mining craft/respec write-parity: craft_write /
    # craft_no_recipe / respec_write / respec_insufficient, 2026-07-13)
    # + 1 (paid-tournament conservation, 2026-07-12)
    # + 2 (D-0081 creature picker/bot-guard) + 3 (fishing cast-leg reel
    # writes, 2026-07-13)
    # + 4 (energy-slice-2 mining cook/use: ration restore / full refusal /
    # cook campfire / torch flavour, 2026-07-13)
    # + 1 (energy-slice-3 fastmine out-of-energy refusal, 2026-07-13)
    # + 1 (cleanup anti-evasion toggle write — the completeness-remainders
    # residue port, 2026-07-13)
    # + 1 (fishing howtofish rules card, 2026-07-13)
    # + 1 (cleanup policies open, 2026-07-13)
    # + 4 (fishing minigame timing slice 1: premature spook / premature
    # grace / trophy fight land / trophy fight escape, 2026-07-14)
    # + 1 (fishing cast-again continuation, 2026-07-14)
    # + 2 (mining title-equip write slice: title_equip_write /
    # title_equip_unearned_refusal, 2026-07-14)
    # + 4 (curation row-72 + farm-goldens: rps_tournament_quickplay_bet_
    # settle_write / farm_collect_write / farm_buy_hen_write /
    # farm_upgrade_coop_write, 2026-07-14)
    # + 1 (mining skill-spend button write — backlog B2:
    # mining_skill_spend_write, 2026-07-18)
    # + 1 (help home-message save button write — this branch:
    # help_home_message_save, 2026-07-18)
    # + 1 (mining workshop-craft select write — backlog B3:
    # mining_workshop_craft_write, 2026-07-18)
    # + 2 (settings group-edit page — settings epic S0:
    # settings_group_edit_open / settings_group_edit_bool_write, 2026-07-19)
    # + 1 (settings enum-select write — settings epic S2:
    # settings_group_edit_enum_write, 2026-07-19)
    # + 1 (settings number-modal write — settings epic S3:
    # settings_group_edit_number_write, 2026-07-19)
    # + 1 (settings free-text-modal write — settings epic S4:
    # settings_group_edit_text_write, 2026-07-19)
    # + 1 (settings channel-select write — settings epic S5:
    # settings_group_edit_channel_write, 2026-07-19)
    # + 1 (settings numeric-presets quick-set write — settings epic S7:
    # settings_group_edit_presets_write, 2026-07-19)
    # − 3 retired (sweep_cog.json + sweep_query_logs.json +
    # sweep_recent_errors.json — parity.yml source.retired_goldens)
    assert golden_count == 533
    assert len(cases) == golden_count
    assert len({c.id for c in cases}) == len(cases)


def test_reconstruction_round_trips_inputs():
    from parity.harness.runner import _describe_step
    from sb.adapters.parity.cases import reconstruct_case

    path = GOLDENS_ROOT / "logging" / "sweep_logging_status.json"
    golden = json.loads(path.read_text())
    case = reconstruct_case(golden)
    assert case is not None
    assert case.id == "sweep.logging_status"
    assert case.subsystem == "logging"
    # the rebuilt steps describe back to the golden's own input docs
    described = [_describe_step(s) for s in case.steps]
    assert described == [s["input"] for s in golden["steps"]]


def test_select_click_values_round_trip():
    """A SELECT click round-trips its chosen ``values`` through the
    reconstruct → describe vocabulary — the browse sort/filter selects + the
    dex element filter the browse-interaction goldens arm (the modal-`fields`
    twin on the click kind)."""
    from parity.harness.runner import _describe_step
    from sb.adapters.parity.cases import reconstruct_case

    golden = {
        "case_id": "probe.select", "subsystem": "inventory",
        "steps": [{"input": {
            "kind": "click", "persona": "member",
            "custom_id": "nav:browse:sort:inventory.cat_x:0:0:-1:0",
            "target_message": 1, "values": ["-quantity"]}}],
    }
    case = reconstruct_case(golden)
    assert case is not None
    assert case.steps[0].values == ("-quantity",)
    assert _describe_step(case.steps[0]) == golden["steps"][0]["input"]


def test_value_less_click_stays_value_less():
    """A button click (page next/prev, the blackjack Hit) carries no
    ``values`` — its describe-back omits the key, so the vocabulary growth is
    additive-only for the existing value-less clicks."""
    from parity.harness.runner import _describe_step
    from sb.adapters.parity.cases import reconstruct_case

    golden = {
        "case_id": "probe.button", "subsystem": "inventory",
        "steps": [{"input": {
            "kind": "click", "persona": "member",
            "custom_id": "nav:browse:next:inventory.cat_x:0:0:-1:0",
            "target_message": 1}}],
    }
    case = reconstruct_case(golden)
    assert case is not None
    assert case.steps[0].values is None
    assert "values" not in _describe_step(case.steps[0])


def test_step_advance_s_round_trips():
    """The D-0043 clock-grammar growth: a click carrying a sub-window
    ``advance_s`` (the fishing timing cases' pre-bite Reel) round-trips
    reconstruct → describe like ``values``/``fields`` before it."""
    from parity.harness.runner import _describe_step
    from sb.adapters.parity.cases import reconstruct_case

    golden = {
        "case_id": "probe.timing", "subsystem": "fishing",
        "steps": [{"input": {
            "kind": "click", "persona": "member",
            "custom_id": "fishing.cast_panel.fishing_reel",
            "target_message": 1, "advance_s": 0.5}}],
    }
    case = reconstruct_case(golden)
    assert case is not None
    assert case.steps[0].advance_s == 0.5
    assert _describe_step(case.steps[0]) == golden["steps"][0]["input"]


def test_default_step_stays_advance_less():
    """A step without ``advance_s`` keeps ``None`` (= the fixed 30.0 s
    every existing golden was captured under) and its describe-back
    omits the key — the growth is additive-only for the whole corpus."""
    from parity.harness.cases import Step
    from parity.harness.runner import _describe_step
    from sb.adapters.parity.cases import reconstruct_case

    golden = {
        "case_id": "probe.plain", "subsystem": "fishing",
        "steps": [{"input": {"kind": "command", "persona": "member",
                             "content": "!fish"}}],
    }
    case = reconstruct_case(golden)
    assert case is not None
    assert case.steps[0].advance_s is None
    assert "advance_s" not in _describe_step(case.steps[0])
    assert Step(kind="command", content="!fish").advance_s is None


def test_load_replay_cases_with_report_counts_unreconstructable_goldens(
        tmp_path):
    """F-003 regression: a golden whose case_id fails reconstruction (here,
    a click step carrying a normalized `<...>` custom_id with no CURATED_CASES
    override) must be counted in `dropped`, not just vanish from `cases` —
    that count is what lets run_golden_parity's --gate red on a silent drop
    instead of quietly replaying fewer cases than exist on disk."""
    from sb.adapters.parity.cases import load_replay_cases_with_report

    xp_dir = tmp_path / "xp"
    xp_dir.mkdir()
    (xp_dir / "reconstructable.json").write_text(json.dumps({
        "case_id": "xp.reconstructable_test_case", "subsystem": "xp",
        "seed": 1, "notes": "",
        "steps": [{"input": {"kind": "command", "persona": "member",
                             "content": "!balance"}}],
    }))
    (xp_dir / "unreconstructable.json").write_text(json.dumps({
        "case_id": "xp.unreconstructable_test_case", "subsystem": "xp",
        "seed": 1, "notes": "",
        "steps": [{"input": {"kind": "click", "persona": "member",
                             "custom_id": "<normalized:session>"}}],
    }))

    cases, dropped = load_replay_cases_with_report(tmp_path)
    ids = {c.id for c in cases}
    assert "xp.reconstructable_test_case" in ids
    assert "xp.unreconstructable_test_case" not in ids
    assert dropped == {"xp": 1}


def test_load_replay_cases_with_report_counts_duplicate_case_ids(tmp_path):
    """F-003 regression (adversarial-review finding, reproduced directly):
    two golden FILES sharing one case_id used to be silently absorbed —
    the second file was skipped with no signal at all, so `dropped` stayed
    empty even though only 1 of the 2 on-disk files was ever exercised.
    That self-contradicted the gate's own denominator message (claims 0
    unreconstructable cases while still declaring a count mismatch) and,
    combined with a hypothetical subsystem-field/directory mismatch, could
    let a genuine drop in one subsystem be exactly offset by a same-id
    phantom credit from another — the precise false-GREEN class F-003 was
    written to eliminate. A collision against a CURATED_CASES id stays
    expected (the curated case IS that golden's intended replay, not a
    drop) — only a golden-vs-golden collision counts."""
    from sb.adapters.parity.cases import load_replay_cases_with_report

    xp_dir = tmp_path / "xp"
    xp_dir.mkdir()
    golden = {
        "case_id": "xp.dup_case", "subsystem": "xp", "seed": 1, "notes": "",
        "steps": [{"input": {"kind": "command", "persona": "member",
                             "content": "!balance"}}],
    }
    (xp_dir / "a_first.json").write_text(json.dumps(golden))
    (xp_dir / "b_second.json").write_text(json.dumps(golden))

    cases, dropped = load_replay_cases_with_report(tmp_path)
    ids = [c.id for c in cases]
    assert ids.count("xp.dup_case") == 1        # only ONE case, not two
    assert dropped == {"xp": 1}                 # the second file IS a drop


def test_load_replay_cases_matches_report_cases(tmp_path):
    """load_replay_cases stays the thin (cases-only) projection of the
    report — same cases, dropped count just discarded."""
    from sb.adapters.parity.cases import (
        load_replay_cases,
        load_replay_cases_with_report,
    )

    report_cases, _dropped = load_replay_cases_with_report(GOLDENS_ROOT)
    assert {c.id for c in load_replay_cases(GOLDENS_ROOT)} == {
        c.id for c in report_cases}


def test_mentions_inferred_from_content():
    from sb.adapters.parity.cases import reconstruct_case

    golden = {
        "case_id": "x", "subsystem": "_unmapped", "seed": 42, "notes": "",
        "steps": [{"input": {"kind": "command", "persona": "admin",
                             "content": "!warn <@900000000000000103> spam"}}],
    }
    case = reconstruct_case(golden)
    assert case is not None
    assert case.steps[0].mentions == ("second_member",)


# --- harness contract ------------------------------------------------------------


def test_harness_contract_shape(harness):
    # the gate driver's binding contract (start/close/drive/take_*)
    for name in ("send_command", "invoke_slash", "click", "take_calls",
                 "take_events", "close", "reset_case_state"):
        assert callable(getattr(harness, name))
    assert harness.world is not None
    assert harness.http is not None
    assert harness.db_ready is False


def test_slash_settings_captures_panel(harness):
    asyncio.run(harness.invoke_slash("settings", persona="admin"))
    calls = harness.take_calls()
    assert calls, "the /settings hub open must produce outbound calls"
    first = calls[0]
    assert first.method == "interaction_response"
    assert first.payload["type"] in (4, 5)


def test_prefix_unknown_command_is_silent(harness):
    asyncio.run(harness.send_command("!definitely-not-a-command",
                                     persona="member"))
    assert harness.take_calls() == []


def test_capture_document_shape_and_determinism(harness):
    from parity.harness.cases import GoldenCase, Step
    from sb.adapters.parity.runner import capture_case

    case = GoldenCase(
        id="parityadapter.settings_hub",
        subsystem="settings",
        steps=(Step(kind="slash", name="settings", persona="admin"),),
    )
    doc1 = asyncio.run(capture_case(harness, case))
    doc2 = asyncio.run(capture_case(harness, case))
    assert doc1 == doc2                              # bit-for-bit determinism
    assert doc1["harness_version"] == 1
    assert set(doc1) == {"harness_version", "case_id", "subsystem", "seed",
                         "notes", "steps", "db_delta"}
    assert doc1["db_delta"] == {}                    # db-free leg
    step = doc1["steps"][0]
    assert step["input"] == {"kind": "slash", "name": "settings",
                             "persona": "admin"}
    assert isinstance(step["calls"], list)


def test_replay_reports_honest_diffs(harness):
    """Replaying a real golden against the new bot RUNS and returns problem
    lines (red is expected pre-parity — the honest dashboard, not a crash)."""
    from sb.adapters.parity.cases import load_replay_cases
    from sb.adapters.parity.runner import replay_case

    cases = {c.id: c for c in load_replay_cases(GOLDENS_ROOT)}
    case = cases["settings.hub_open"]
    ok, problems = asyncio.run(replay_case(harness, case, GOLDENS_ROOT))
    assert ok is False
    assert problems and all(isinstance(p, str) for p in problems)


def test_wire_mapping_rendered_panel():
    from sb.adapters.parity.transport import rendered_panel_payload

    class _C:
        kind = "button"; custom_id = "x.y"; label = "Go"; row = 0
        style = "danger"; emoji = ""; disabled = False
        placeholder = ""; min_values = 1; max_values = 1; options = ()

    class _E:
        title = "T"; description = "D"; fields = (("a", "b"),); footer = "f"

    class _P:
        embed = _E(); components = (_C(),)

    payload = rendered_panel_payload(_P())
    assert payload["embeds"][0]["title"] == "T"
    assert payload["embeds"][0]["fields"] == [
        {"name": "a", "value": "b", "inline": False}]
    row = payload["components"][0]
    assert row["type"] == 1
    assert row["components"][0] == {
        "type": 2, "style": 4, "custom_id": "x.y", "label": "Go",
        "disabled": False}


def test_moderation_actions_capture_wire_vocabulary(harness):
    """The GuildModerationActions capture twin records the goldens' wire
    verbs (edit_member/kick/ban/unban/get_user) and is armed by the harness
    boot — the moderation legs must not degrade to PARTIAL in replay.
    timeout_member records the edit_member call then RAISES the
    capture-environment member-edit artifact (fake_http's canned PATCH
    response was unparseable to discord.py, so every captured `!timeout`
    died after the wire call — goldens/moderation/sweep_timeout pins it)."""
    import pytest

    from sb.adapters.parity.transport import (
        CaptureMemberEditParseError,
        ParityModerationActions,
    )
    from sb.domain.moderation.service import active_actions

    assert isinstance(active_actions(), ParityModerationActions)

    actions = active_actions()
    with pytest.raises(CaptureMemberEditParseError):
        asyncio.run(actions.timeout_member(1, 2, minutes=3,
                                           reason="3 minutes"))
    asyncio.run(actions.kick_member(1, 2, reason="No reason provided"))
    asyncio.run(actions.ban_member(1, 2, reason="r", delete_message_days=1))
    asyncio.run(actions.ban_member(1, 2, reason="r", delete_message_days=0))
    asyncio.run(actions.fetch_user(3))
    asyncio.run(actions.unban_member(1, 3, reason="No reason provided"))
    calls = harness.take_calls()
    methods = [c.method for c in calls]
    assert methods == ["edit_member", "kick", "ban", "ban", "get_user",
                       "unban"]
    assert calls[0].payload and "communication_disabled_until" in calls[0].payload
    assert calls[2].args["delete_message_seconds"] == 86400
    assert "delete_message_seconds" not in calls[3].args   # 0 days => omitted
    assert calls[4].args == {"user_id": 3}
    assert calls[5].args == {"guild_id": 1, "user_id": 3,
                             "reason": "No reason provided"}
