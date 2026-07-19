"""The `command.dispatched` dispatch-trace seam (spec 02 §3.5).

`sb/kernel/interaction/trace.py` carries the RC-2/RC-5 owner-override
transparency signal (`override_applied` / `base_allowed`) onto an
observability-only event. It is fire-and-forget: a failing bus must NEVER
break command dispatch. These tests pin three contracts that were previously
un-covered:

1. the hand-built payload's keys track `COMMAND_DISPATCHED_SPEC.payload_schema`
   (which evolves additive-only — silent drift is the hazard);
2. `emit_dispatch_trace` never raises — a raising bus and the no-running-loop
   path are both swallowed;
3. the derivation renders enums to `.value` and threads actor/guild/
   orchestration, and the EventSpec is registered observability-only.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import warnings

import pytest

from sb.kernel.authority.decision import AuthorityDecision
from sb.kernel.interaction.request import (
    ActorRef,
    NLProvenance,
    ResolveRequest,
    Surface,
    TargetRef,
)
from sb.kernel.interaction.trace import (
    COMMAND_DISPATCHED_SPEC,
    EVT_COMMAND_DISPATCHED,
    emit_dispatch_trace,
    install_trace_bus,
)
from sb.spec.authority import Lane
from sb.spec.outcomes import DenialReason


@pytest.fixture(autouse=True)
def _reset_trace_bus():
    """The module-global `_bus` is process-wide state — reset around every
    test so a wired bus never leaks into another case."""
    install_trace_bus(None)
    try:
        yield
    finally:
        install_trace_bus(None)


class RecordingBus:
    """Async bus twin: records every emit as (name, payload)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def emit(self, name: str, **payload: object) -> None:
        self.calls.append((name, dict(payload)))


def _decision(**overrides) -> AuthorityDecision:
    kw = dict(
        allowed=False, authority_ref="settings.edit", lane=Lane.CAPABILITY,
        required_tier="administrator", member_tier="user",
        owner_override=True, lane_would_deny=True,
        reason=DenialReason.AUTHORITY, detail="", denial_message=None)
    kw.update(overrides)
    return AuthorityDecision(**kw)


def _request(*, surface=Surface.SLASH, actor_id=111, guild_id=5,
             command_key="settings", provenance=None) -> ResolveRequest:
    actor = ActorRef(user_id=actor_id, is_guild_operator=False,
                     is_bot_owner=False, is_dm=False)
    return ResolveRequest(
        surface=surface,
        target=TargetRef(key=command_key, spec=object()),
        actor=actor,
        guild_id=guild_id,
        channel_id=7,
        args={},
        responder=object(),      # the trace never touches the responder
        origin=object(),
        provenance=provenance,
    )


# --- 1. payload / schema drift guard -----------------------------------------

def test_payload_keys_exactly_match_the_registered_schema() -> None:
    async def scenario() -> RecordingBus:
        bus = RecordingBus()
        install_trace_bus(bus)
        emit_dispatch_trace(_request(), _decision(),
                            override_applied=True, base_allowed=False,
                            outcome="success", reason=DenialReason.AUTHORITY)
        await asyncio.sleep(0)   # let the scheduled emit task run
        return bus

    bus = asyncio.run(scenario())
    assert len(bus.calls) == 1
    name, payload = bus.calls[0]
    assert name == EVT_COMMAND_DISPATCHED == "command.dispatched"

    schema_fields = {f.name for f in COMMAND_DISPATCHED_SPEC.payload_schema}
    # the emitted payload's keys are EXACTLY the declared field set — no extra
    # key (silent drift), no missing field.
    assert set(payload) == schema_fields
    # every REQUIRED schema field carries a value slot (orchestration_id is the
    # sole required=False field, present-but-None here).
    required = {f.name for f in COMMAND_DISPATCHED_SPEC.payload_schema if f.required}
    assert required <= set(payload)


def test_spec_is_observability_only_under_the_reserved_kernel_owner() -> None:
    # The §2.8 owner-rule carve-out: `command.dispatched` is the named
    # observability-only event owned by the reserved `kernel` subsystem.
    # (Registry MEMBERSHIP is not asserted here — `clear_event_registry()` is a
    # shared test seam other suites reset, so the immutable spec IS the contract.)
    assert COMMAND_DISPATCHED_SPEC.name == EVT_COMMAND_DISPATCHED == "command.dispatched"
    assert COMMAND_DISPATCHED_SPEC.observability_only is True
    assert COMMAND_DISPATCHED_SPEC.owner_subsystem == "kernel"
    # the transparency-signal fields are declared on the schema (RC-2/RC-5)
    field_names = {f.name for f in COMMAND_DISPATCHED_SPEC.payload_schema}
    assert {"override_applied", "base_allowed"} <= field_names


# --- 2. never-breaks-dispatch robustness -------------------------------------

def test_a_raising_bus_is_swallowed_never_propagates() -> None:
    class BoomBus:
        def emit(self, name: str, **payload: object):
            raise ValueError("bus is down")

    async def scenario() -> None:
        install_trace_bus(BoomBus())
        # MUST NOT raise — a dead bus can never break dispatch.
        emit_dispatch_trace(_request(), _decision(),
                            override_applied=False, base_allowed=True,
                            outcome="success", reason=DenialReason.ALLOWED)
        await asyncio.sleep(0)

    asyncio.run(scenario())   # no exception escapes => contract holds


def test_no_running_loop_is_swallowed_and_still_logs(caplog) -> None:
    bus = RecordingBus()
    install_trace_bus(bus)
    # Called with NO running loop: get_running_loop() raises RuntimeError, which
    # the seam catches ("the log line stands"). The orphaned coroutine's GC
    # warning is expected and irrelevant to the contract under test.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with caplog.at_level(logging.INFO, logger="sb.kernel.interaction.trace"):
            emit_dispatch_trace(_request(), _decision(),
                                override_applied=True, base_allowed=False,
                                outcome="blocked", reason=DenialReason.AUTHORITY)
        gc.collect()   # fire the unawaited-coroutine warning inside the filter
    # swallowed: never scheduled onto a loop, so nothing recorded ...
    assert bus.calls == []
    # ... but the always-on log line still emitted.
    assert any("command.dispatched" in r.getMessage() for r in caplog.records)


def test_no_bus_installed_only_logs_never_raises(caplog) -> None:
    # _bus is None (fixture reset). The seam logs and returns; no emit attempt.
    with caplog.at_level(logging.INFO, logger="sb.kernel.interaction.trace"):
        emit_dispatch_trace(_request(), _decision(),
                            override_applied=False, base_allowed=True,
                            outcome="success", reason=DenialReason.ALLOWED)
    assert any("command.dispatched" in r.getMessage() for r in caplog.records)


# --- 3. correct derivation ---------------------------------------------------

def test_derivation_renders_enums_and_threads_request_fields() -> None:
    async def scenario() -> None:
        bus = RecordingBus()
        install_trace_bus(bus)
        prov = NLProvenance(nl_text="do it", intent_key="settings.edit",
                            confidence=0.9, orchestration_id="orc-77")
        req = _request(surface=Surface.NL_ORCHESTRATION, actor_id=222,
                       guild_id=9, command_key="settings.edit", provenance=prov)
        decision = _decision(authority_ref="settings.edit", lane=Lane.TIER)
        emit_dispatch_trace(req, decision,
                            override_applied=True, base_allowed=False,
                            outcome="blocked", reason=DenialReason.CHANNEL,
                            note="ignored-by-payload")
        await asyncio.sleep(0)
        return bus

    bus = asyncio.run(scenario())
    _name, payload = bus.calls[0]
    # enums rendered to their .value (never the enum object)
    assert payload["surface"] == "nl_orchestration"
    assert payload["lane"] == "tier"
    assert payload["reason"] == "channel"
    # request fields threaded
    assert payload["actor_id"] == 222
    assert payload["guild_id"] == 9
    assert payload["command_key"] == "settings.edit"
    assert payload["authority_ref"] == "settings.edit"
    assert payload["orchestration_id"] == "orc-77"
    # the RC-2/RC-5 transparency signal rides verbatim
    assert payload["override_applied"] is True
    assert payload["base_allowed"] is False
    assert payload["outcome"] == "blocked"
    # request_id is a non-empty correlation string
    assert isinstance(payload["request_id"], str) and payload["request_id"]


def test_orchestration_id_is_none_without_provenance() -> None:
    async def scenario() -> None:
        bus = RecordingBus()
        install_trace_bus(bus)
        emit_dispatch_trace(_request(provenance=None), _decision(),
                            override_applied=False, base_allowed=True,
                            outcome="success", reason=DenialReason.ALLOWED)
        await asyncio.sleep(0)
        return bus

    bus = asyncio.run(scenario())
    _name, payload = bus.calls[0]
    assert payload["orchestration_id"] is None
