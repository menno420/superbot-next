"""Band 7 — the D-0073 slice's walking skeleton: the replay-case MODAL
vocabulary (the D-0063 deletion clause's named successor) + the shipped
StrategySubmitModal twin.

Corpus half: a golden document whose step input is ``kind: "modal"``
reconstructs to a drivable case (sb/adapters/parity/cases.py) and
describes back to the same input doc (parity/harness/runner._describe_step)
— the lossless round trip every other step kind already had.

Form half: the G-10 ``btd6.strategy_form`` (ORACLE disbot
views/btd6/strategy_submit.py @8214200a, search_code fragment
reconstruction — trap-24 sha caveat in D-0073) — the open click issues
the form (wire type 9), the wire-type-5 submit re-enters through
``dispatch_modal`` and writes on the audited ``btd6.submit_strategy`` K7
lane with the shipped ephemeral followups, byte for byte. DB-free: the
workflow-engine seam is recorded like the sibling band-7 suites."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


# --- the corpus vocabulary (reconstruction round trip) ----------------------------


def _modal_golden(fields: dict[str, str]) -> dict:
    return {
        "case_id": "x.modal", "subsystem": "btd6", "seed": 42, "notes": "",
        "steps": [{"input": {"kind": "modal", "persona": "member",
                             "custom_id": "btd6.strategy_form",
                             "fields": fields}}],
    }


def test_modal_step_reconstructs_and_round_trips():
    from parity.harness.runner import _describe_step
    from sb.adapters.parity.cases import reconstruct_case

    golden = _modal_golden({"title": "t", "summary": "s", "map": ""})
    case = reconstruct_case(golden)
    assert case is not None
    step = case.steps[0]
    assert step.kind == "modal"
    assert step.custom_id == "btd6.strategy_form"
    assert step.fields == (("map", ""), ("summary", "s"), ("title", "t"))
    described = [_describe_step(s) for s in case.steps]
    assert described == [s["input"] for s in golden["steps"]]


def test_modal_step_with_session_minted_id_is_not_reconstructable():
    from sb.adapters.parity.cases import reconstruct_case

    golden = _modal_golden({"title": "t"})
    golden["steps"][0]["input"]["custom_id"] = "<cid:1>"
    assert reconstruct_case(golden) is None


def test_committed_modal_goldens_reconstruct():
    """The two minted goldens are replayable cases (the D-0073 deliverable:
    corpus schema growth is only real if the on-disk documents ride it)."""
    import json
    from pathlib import Path

    from sb.adapters.parity.cases import reconstruct_case

    root = Path(__file__).resolve().parents[3] / "parity" / "goldens" / "btd6"
    for name in ("btd6_strategy_form_submit.json",
                 "btd6_strategy_form_submit_minimal.json"):
        case = reconstruct_case(json.loads((root / name).read_text()))
        assert case is not None, name
        assert case.steps[0].kind == "modal", name


# --- the form (issue + submit through the real pipeline) --------------------------


@pytest.fixture()
def skeleton():
    from sb.adapters.parity.boot import Harness
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    yield h
    run(h.close())


@pytest.fixture()
def engine_recorder(monkeypatch):
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls: list = []

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               after={"submit_strategy": {"strategy_id": 7}},
                               before={})

    monkeypatch.setattr(engine, "run", fake_run)
    return calls


def test_open_click_issues_the_strategy_form(skeleton, engine_recorder):
    run(skeleton.click(message_id=920,
                       custom_id="btd6.strategy_submit.open_strategy_form",
                       persona="member"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["interaction_response"]
    assert calls[0].payload["type"] == 9
    assert calls[0].payload["data"]["custom_id"] == "btd6.strategy_form"
    assert engine_recorder == []             # the open NEVER dispatches


def test_submit_writes_and_speaks_the_shipped_ack(skeleton, engine_recorder):
    """StrategySubmitModal.on_submit, byte for byte: strip title/summary,
    strip-or-None map/mode/hero, the shipped ephemeral defer+followup
    (flags 64 — safe_defer(interaction, ephemeral=True)), and the shipped
    success copy with the oracle's submit-path action value."""
    run(skeleton.modal_submit(
        message_id=0, custom_id="btd6.strategy_form",
        fields={"title": "  CHIMPS Bloody Puddles  ", "summary": "Boats.",
                "map": "", "mode": " CHIMPS ", "hero": ""},
        persona="member"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["interaction_response",
                                         "followup_send"]
    assert calls[0].payload == {"type": 5, "data": {"flags": 64}}
    assert calls[1].payload["flags"] == 64
    assert calls[1].payload["content"] == (
        "✅ Submitted as strategy `#7` (`submitted`). "
        "Staff can review with `!btd6 pending`.")
    (op_name, params), = engine_recorder
    assert op_name == "btd6.submit_strategy"
    assert params["title"] == "CHIMPS Bloody Puddles"
    assert params["summary"] == "Boats."
    assert params["map"] is None            # strip-or-None
    assert params["mode"] == "CHIMPS"
    assert params["hero"] is None
    assert params["_display_name"] == "MemberActor"


def test_submit_missing_required_speaks_the_shipped_refusal(skeleton,
                                                            engine_recorder):
    """The shipped `❌ {InvalidStrategyValueError}` echo ("title and
    summary are required") rides the handler pre-check — refused BEFORE
    any write (real clients cannot reach it: both fields are required=True
    on the form)."""
    run(skeleton.modal_submit(
        message_id=0, custom_id="btd6.strategy_form",
        fields={"title": "   ", "summary": "s"}, persona="member"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == "❌ title and summary are required"
    assert calls[-1].payload["flags"] == 64
    assert engine_recorder == []


def test_guild_guard_speaks_the_shipped_copy():
    """The shipped pre-defer guard, verbatim (handler-level: the harness
    always drives guild interactions)."""
    from sb.domain.btd6.oracle_surface import strategy_form_submit

    req = SimpleNamespace(guild_id=None, args={}, origin=None)
    reply = run(strategy_form_submit(req))
    assert reply.user_message == (
        "❌ Submitting a strategy requires a guild context.")
