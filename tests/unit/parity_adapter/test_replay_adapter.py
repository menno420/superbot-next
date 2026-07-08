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
    """Every golden on disk yields a replayable case (465/465) — curated
    typed cases first, sweep cases rebuilt from their golden documents."""
    from sb.adapters.parity.cases import load_replay_cases

    cases = load_replay_cases(GOLDENS_ROOT)
    golden_count = sum(1 for _ in GOLDENS_ROOT.glob("*/*.json"))
    assert golden_count == 465          # the imported corpus (parity.yml source)
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
