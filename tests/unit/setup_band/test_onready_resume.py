"""The setup on-ready resume sweep (sb/domain/setup/resume.py — ORDER 019
item 5a) + its boot-hook wiring.

DB-free like the essential-steps suite: the roster read
(``store.list_resumable_sessions``), the panel-engine edit lane
(``edit_anchored_panel``) and the K7 write seam
(``sb.kernel.workflow.engine.run``) are monkeypatched at their module
functions; the assertions pin the ORACLE semantics (no golden drives the
sweep — the panels.py module pin; oracle sources:
disbot/cogs/setup_cog.py ``_resume_launchers`` +
disbot/views/setup/essential_setup.py ``revive_essential_flows``
@bbc524e4)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.domain.setup import resume
from sb.kernel.lifecycle import boot_hooks
from sb.kernel.panels import engine as panel_engine

run = asyncio.run

HUB = "setup.hub"
RESUME = "setup.essential_resume"


@pytest.fixture(autouse=True)
def _fresh_hooks():
    boot_hooks.reset_boot_hooks_for_tests()
    yield
    boot_hooks.reset_boot_hooks_for_tests()


def _row(*, guild_id=99, status="in_progress", channel_id=555,
         message_id=777, essential_message_id=888, essential_step=3):
    return {
        "guild_id": guild_id, "setup_status": status,
        "setup_channel_id": channel_id, "setup_message_id": message_id,
        "essential_message_id": essential_message_id,
        "essential_step": essential_step,
    }


@pytest.fixture()
def rows(monkeypatch):
    from sb.domain.setup import store

    data: list[dict] = []

    async def fake_list():
        return list(data)

    monkeypatch.setattr(store, "list_resumable_sessions", fake_list)
    return data


class _EditRecorder:
    """Monkeypatch target for panel_engine.edit_anchored_panel."""

    def __init__(self):
        self.calls: list[dict] = []
        self.outcomes: dict[str, str] = {}
        self.raises: set[str] = set()

    async def __call__(self, ref, *, guild_id, channel_id, message_id,
                       actor, params=None):
        key = f"{ref.name}:{guild_id}"
        self.calls.append({"panel": ref.name, "guild_id": guild_id,
                           "channel_id": channel_id,
                           "message_id": message_id, "actor": actor})
        if key in self.raises:
            raise RuntimeError(f"edit blew up for {key}")
        return self.outcomes.get(key, panel_engine.EDIT_EDITED)

    def panels(self):
        return [c["panel"] for c in self.calls]


@pytest.fixture()
def edits(monkeypatch):
    rec = _EditRecorder()
    monkeypatch.setattr(panel_engine, "edit_anchored_panel", rec)
    return rec


@pytest.fixture()
def k7(monkeypatch):
    from sb.kernel.workflow import engine as workflow_engine
    from sb.spec.outcomes import SUCCESS

    calls: list[tuple[str, int]] = []

    async def fake_run(ref, ctx):
        calls.append((str(getattr(ref, "name", ref)), int(ctx.guild_id)))
        return SimpleNamespace(outcome=SUCCESS, ok=True, user_message=None)

    monkeypatch.setattr(workflow_engine, "run", fake_run)
    return calls


# --- the sweep ---------------------------------------------------------------------


def test_no_rows_is_a_counted_noop(rows, edits, k7) -> None:
    counts = run(resume.run_resume_sweep())
    assert counts == {"rows": 0, "launchers_resumed": 0,
                      "essential_revived": 0, "errors": 0}
    assert edits.calls == []
    assert k7 == []


def test_in_progress_row_resumes_both_surfaces(rows, edits, k7) -> None:
    rows.append(_row())
    counts = run(resume.run_resume_sweep())

    # leg 1 refreshed the workspace anchor at ITS persisted pointer, leg 2
    # edited the interrupted flow message to the Resume bridge at ITS —
    # the oracle order (launchers first, then the revive sweep).
    assert edits.panels() == [HUB, RESUME]
    launcher, revive = edits.calls
    assert (launcher["channel_id"], launcher["message_id"]) == (555, 777)
    assert (revive["channel_id"], revive["message_id"]) == (555, 888)
    # bot-initiated recovery rides the system actor, never a member.
    assert launcher["actor"].actor_type == "system"
    assert counts["launchers_resumed"] == 1
    assert counts["essential_revived"] == 1
    assert counts["errors"] == 0
    assert k7 == []          # nothing vanished — no anchor clear


def test_complete_row_without_essential_anchor_refreshes_launcher_only(
        rows, edits, k7) -> None:
    # a completed flow cleared its essential anchor (persist_progress) —
    # only the workspace anchor refresh remains (the oracle's status-aware
    # launcher leg refreshed complete sessions too: "Re-run Setup").
    rows.append(_row(status="complete", essential_message_id=None,
                     essential_step=None))
    counts = run(resume.run_resume_sweep())
    assert edits.panels() == [HUB]
    assert counts["launchers_resumed"] == 1
    assert counts["essential_revived"] == 0
    assert k7 == []


def test_vanished_essential_message_clears_anchor_through_k7(
        rows, edits, k7) -> None:
    rows.append(_row())
    edits.outcomes[f"{RESUME}:99"] = panel_engine.EDIT_MISSING

    counts = run(resume.run_resume_sweep())

    # the oracle NotFound branch: clear the anchor so the sweep stops
    # retrying — through the audited op, never the bare store write.
    assert k7 == [("setup.clear_essential_anchor", 99)]
    assert counts["essential_revived"] == 0
    assert counts["launchers_resumed"] == 1
    assert counts["errors"] == 0


def test_vanished_launcher_message_never_clears_pointers(
        rows, edits, k7) -> None:
    rows.append(_row(essential_message_id=None))
    edits.outcomes[f"{HUB}:99"] = panel_engine.EDIT_MISSING

    counts = run(resume.run_resume_sweep())

    # the oracle launcher leg logs and SKIPS a gone message — no write.
    assert k7 == []
    assert counts["launchers_resumed"] == 0
    assert counts["errors"] == 0


def test_per_guild_failures_are_isolated(rows, edits, k7) -> None:
    rows.append(_row(guild_id=1, channel_id=10, message_id=11,
                     essential_message_id=12))
    rows.append(_row(guild_id=2, channel_id=20, message_id=21,
                     essential_message_id=22))
    edits.raises.add(f"{HUB}:1")
    edits.raises.add(f"{RESUME}:1")

    counts = run(resume.run_resume_sweep())

    # guild 1 blew up on both legs; guild 2 still resumed on both —
    # the oracle's per-guild try/except.
    assert counts["errors"] == 2
    assert counts["launchers_resumed"] == 1
    assert counts["essential_revived"] == 1
    assert [c["guild_id"] for c in edits.calls] == [1, 2, 1, 2]


def test_headless_editor_degrades_to_counted_noop(rows, edits, k7) -> None:
    rows.append(_row())
    edits.outcomes[f"{HUB}:99"] = panel_engine.EDIT_UNAVAILABLE
    edits.outcomes[f"{RESUME}:99"] = panel_engine.EDIT_UNAVAILABLE

    counts = run(resume.run_resume_sweep())
    assert counts["launchers_resumed"] == 0
    assert counts["essential_revived"] == 0
    assert counts["errors"] == 0
    assert k7 == []


# --- the boot-hook wiring ------------------------------------------------------------


def test_register_setup_boot_hook_is_idempotent() -> None:
    resume.register_setup_boot_hook()
    resume.register_setup_boot_hook()
    assert boot_hooks.registered_boot_hooks() == (resume.BOOT_HOOK_NAME,)


def test_manifest_ensure_refs_registers_the_hook() -> None:
    import sb.manifest.setup as m

    m.ENSURE_REFS()
    assert resume.BOOT_HOOK_NAME in boot_hooks.registered_boot_hooks()


def test_fired_hook_runs_the_sweep(rows, edits, k7) -> None:
    rows.append(_row())
    resume.register_setup_boot_hook()

    results = run(boot_hooks.run_boot_hooks())

    assert [r.name for r in results] == [resume.BOOT_HOOK_NAME]
    assert results[0].ok
    assert edits.panels() == [HUB, RESUME]
