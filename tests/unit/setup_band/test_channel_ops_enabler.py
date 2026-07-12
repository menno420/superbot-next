"""The channel-ops enabler slice (D-0077) — port surface + compensator.

Pins the three seams the setup/quicksetup flip lane will stand on:

* the ChannelStateActions create/delete extension keeps the fail-loud
  uninstalled default (an unarmed port is an honest refusal, never a
  silent success) and the install path routes calls to the adapter;
* ``setup.compensate_create_channel`` registers (import-time decorator
  + the ensure_ops_refs re-arm seam) and resolves;
* the compensator's ruling semantics: id-guarded (no stash → no-op,
  never a guessed delete), best-effort (a Discord-refused delete
  completes the compensation with ``deleted: False`` instead of
  raising), and the delete rides the channel-state port with the
  stashed id."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


class FakeActions:
    def __init__(self, fail: Exception | None = None) -> None:
        self.creates: list[tuple] = []
        self.deletes: list[tuple] = []
        self._fail = fail

    async def create_text_channel(self, guild_id, *, name, overwrites,
                                  parent_id, reason):
        if self._fail:
            raise self._fail
        self.creates.append((guild_id, name, overwrites, parent_id, reason))
        return 900_777

    async def delete_channel(self, channel_id, *, reason):
        if self._fail:
            raise self._fail
        self.deletes.append((channel_id, reason))


def _ctx(params):
    return SimpleNamespace(params=dict(params), guild_id=42)


def test_uninstalled_port_refuses_create_and_delete_loudly():
    from sb.domain.channel import service

    service.reset_channel_ports_for_tests()
    with pytest.raises(RuntimeError, match="ChannelStateActions not installed"):
        run(service.active_actions().create_text_channel(
            42, name="superbot-setup", overwrites=(), parent_id=None,
            reason=None))
    with pytest.raises(RuntimeError, match="ChannelStateActions not installed"):
        run(service.active_actions().delete_channel(1, reason=None))


def test_installed_port_routes_create_and_delete_to_the_adapter():
    from sb.domain.channel import service

    service.reset_channel_ports_for_tests()
    actions = FakeActions()
    service.install_channel_actions(actions)
    overwrites = (service.ChannelOverwrite(42, 0, 0, 1024),)
    cid = run(service.active_actions().create_text_channel(
        42, name="superbot-setup", overwrites=overwrites, parent_id=None,
        reason=None))
    assert cid == 900_777
    assert actions.creates == [(42, "superbot-setup", overwrites, None, None)]
    run(service.active_actions().delete_channel(900_777, reason="cleanup"))
    assert actions.deletes == [(900_777, "cleanup")]
    service.reset_channel_ports_for_tests()


def test_compensator_ref_registers_and_resolves():
    from sb.domain.setup import ops
    from sb.spec.refs import WorkflowRef, is_registered, resolve

    ops.ensure_ops_refs()
    ref = WorkflowRef("setup.compensate_create_channel")
    assert is_registered(ref)
    assert callable(resolve(ref))


def test_compensator_is_a_noop_without_the_stashed_id():
    """ID-GUARDED: the create leg never stashed a channel id — the
    compensator must not guess (a name lookup or session pointer could
    delete an operator's channel)."""
    from sb.domain.channel import service
    from sb.domain.setup import ops
    from sb.spec.refs import WorkflowRef, resolve

    service.reset_channel_ports_for_tests()   # a delete attempt would raise
    ops.ensure_ops_refs()
    handler = resolve(WorkflowRef("setup.compensate_create_channel"))
    outcome = run(handler(None, _ctx({})))
    assert outcome.after == {"compensated": "nothing"}
    assert outcome.step.ok is True


def test_compensator_deletes_exactly_the_stashed_channel():
    from sb.domain.channel import service
    from sb.domain.setup import ops
    from sb.spec.refs import WorkflowRef, resolve

    service.reset_channel_ports_for_tests()
    actions = FakeActions()
    service.install_channel_actions(actions)
    ops.ensure_ops_refs()
    handler = resolve(WorkflowRef("setup.compensate_create_channel"))
    outcome = run(handler(None, _ctx({"_created_channel_id": 900_777})))
    assert actions.deletes == [
        (900_777,
         "setup channel create compensated — a later leg failed")]
    assert outcome.after == {"compensated": "create_channel",
                             "channel_id": 900_777, "deleted": True}
    service.reset_channel_ports_for_tests()


def test_compensator_is_best_effort_when_the_delete_is_refused():
    """A Discord-refused delete must not raise out of fork E — the
    compensation completes with ``deleted: False`` (the orphan channel
    is visible + harmless; NotFound-as-success lives in the LIVE
    adapter's port contract, so only real refusals reach here)."""
    from sb.domain.channel import service
    from sb.domain.setup import ops
    from sb.spec.refs import WorkflowRef, resolve

    service.reset_channel_ports_for_tests()
    service.install_channel_actions(FakeActions(fail=RuntimeError("403")))
    ops.ensure_ops_refs()
    handler = resolve(WorkflowRef("setup.compensate_create_channel"))
    outcome = run(handler(None, _ctx({"_created_channel_id": 900_777})))
    assert outcome.after == {"compensated": "create_channel",
                             "channel_id": 900_777, "deleted": False}
    assert outcome.step.ok is True
    service.reset_channel_ports_for_tests()
