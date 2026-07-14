"""The armed starboard ✏️ Threshold modal (ORDER 017 night-run fix
slice C) — the shipped ``_ThresholdModal`` as a G-10 form over the
existing audited ``starboard.configure`` op (ORACLE menno420/superbot
disbot/views/starboard/config_panel.py, copy verbatim); the pending
terminal retired. goldens/starboard/sweep_starboard_panel pins the
panel's off-state bytes — the button's label/style wire fields are
unchanged (only defer_mode/modal/handler wiring moved)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run

UID, GID = 42, 1


@dataclass
class FakeReq:
    args: dict = field(default_factory=dict)
    actor: object = None
    guild_id: int = GID
    channel_id: int = 9
    origin: object = None
    request_id: str = "r1"
    confirmed: bool = False
    surface: object = None


def _req(args: dict | None = None) -> FakeReq:
    return FakeReq(args=dict(args or {}),
                   actor=SimpleNamespace(user_id=UID, actor_type="user"))


def _handler():
    from sb.domain.starboard import panels
    from sb.spec.refs import HandlerRef, resolve

    panels.ensure_panel_refs()
    return resolve(HandlerRef("starboard.panel_threshold"))


@pytest.fixture()
def _settings(monkeypatch):
    from sb.domain.starboard import service

    async def get_settings(gid):
        return {"channel_id": 555, "threshold": 3, "emoji": "⭐",
                "enabled": True, "self_star": False}

    monkeypatch.setattr(service, "get_settings", get_settings)


@pytest.fixture()
def captured_ops(monkeypatch):
    from sb.kernel.workflow import engine as wf_engine

    calls = []

    async def fake_run(ref, ctx):
        calls.append((ref.name, dict(ctx.params)))
        return SimpleNamespace(ok=True, outcome=SUCCESS, after={},
                               user_message=None)

    monkeypatch.setattr(wf_engine, "run", fake_run)
    return calls


@pytest.fixture()
def captured_opens(monkeypatch):
    from sb.kernel.panels import engine

    opened = []

    async def open_panel(ref, req):
        opened.append(ref.name)
        return "777"

    monkeypatch.setattr(engine, "open_panel", open_panel)
    return opened


def test_threshold_action_declares_the_shipped_modal():
    from sb.domain.starboard.panels import config_panel_spec
    from sb.spec.outcomes import DeferMode
    from sb.spec.refs import HandlerRef

    spec = config_panel_spec()
    action = {a.action_id: a for a in spec.actions}["starboard_threshold"]
    # the golden-pinned wire fields stay put …
    assert action.label == "✏️ Threshold"
    assert action.style.value == "primary"
    # … and the G-10 form arms the click.
    assert action.defer_mode is DeferMode.MODAL
    assert action.modal.modal_id == "starboard.threshold_form"
    assert action.modal.title == "Starboard threshold"
    (fld,) = action.modal.fields
    assert fld.field_id == "threshold"
    assert fld.label == "Stars needed to enter the board"
    assert (fld.required, fld.min_length, fld.max_length) == (True, 1, 4)
    assert action.modal.on_submit == HandlerRef("starboard.panel_threshold")


def test_spec_passes_the_compile_fence():
    from sb.domain.starboard.panels import config_panel_spec
    from sb.kernel.panels.compile import check_panel

    assert check_panel(config_panel_spec()) is None


def test_submit_runs_configure_preserving_channel_and_emoji(
        _settings, captured_ops, captured_opens):
    reply = run(_handler()(_req({"threshold": " 7 "})))
    assert reply.user_message is None
    op, params = captured_ops[-1]
    assert op == "starboard.configure"
    assert params == {"channel_id": 555, "threshold": 7, "emoji": "⭐"}
    # the shipped _rerender → the ledgered fresh-send re-open.
    assert captured_opens == ["starboard.config"]


def test_submit_error_copy_is_shipped_verbatim(_settings, captured_ops):
    reply = run(_handler()(_req({"threshold": "lots"})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == "❌ Threshold must be a whole number."
    assert not captured_ops


def test_unconfigured_guard_copy_is_shipped_verbatim(monkeypatch,
                                                     captured_ops):
    from sb.domain.starboard import service

    async def get_settings(gid):
        return None

    monkeypatch.setattr(service, "get_settings", get_settings)
    reply = run(_handler()(_req({"threshold": "5"})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == ("Set a hall-of-fame channel first "
                                  "(pick one below).")
    assert not captured_ops


def test_op_failure_relays_the_engine_message(_settings, monkeypatch):
    from sb.kernel.workflow import engine as wf_engine

    async def fail_run(ref, ctx):
        return SimpleNamespace(ok=False, outcome=BLOCKED, after={},
                               user_message="nope")

    monkeypatch.setattr(wf_engine, "run", fail_run)
    reply = run(_handler()(_req({"threshold": "5"})))
    assert reply.outcome is BLOCKED
    assert reply.user_message == "nope"
