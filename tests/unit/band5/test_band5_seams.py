"""Band 5 seam findings (D-block for the band-5 testing pass): the
refusal-copy posture on every band-5 raise site (copy-only
ValidatorError — 5th victim family), the one-clock-per-lane rule for
temp grants + proof locks (the band-4 karma two-clocks bug, D-0061),
the rolemenu hub route (the golden captures the shipped
RoleHubPanelView, not a reaction listing), and the proof-channel legs'
panel-path acks (the D-0052 silent-success line)."""

from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace

import pytest

run = asyncio.run
UTC = dt.timezone.utc

PINNED = dt.datetime.fromtimestamp(1_000_000, tz=UTC)


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.proof_channel import service as proof_service
    from sb.domain.role import service as role_service

    role_service.reset_role_ports_for_tests()
    proof_service.reset_proof_ports_for_tests()
    yield
    role_service.reset_role_ports_for_tests()
    proof_service.reset_proof_ports_for_tests()


def _ctx(params, *, uid=42, gid=1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: PINNED)


# --- refusal copy: band-5 raise sites speak their sentences BARE ------------------

def _rendered(exc) -> str:
    from sb.kernel.interaction.errors import from_exception
    from sb.kernel.interaction.request import Surface

    return from_exception(exc, surface=Surface.MAINTENANCE,
                          target=None).user_message


def test_role_verr_renders_bare():
    from sb.domain.role.ops import _verr

    msg = _rendered(_verr("Days/level must be non-negative."))
    assert msg == "Days/level must be non-negative."
    assert "Missing/invalid argument" not in msg


def test_proof_verr_renders_bare_and_matches_golden_copy(monkeypatch):
    from sb.domain.proof_channel import ops, service
    from sb.kernel.interaction.errors import ValidatorError

    async def unbound(gid):
        return None

    monkeypatch.setattr(service, "bound_proof_channel", unbound)
    with pytest.raises(ValidatorError) as ei:
        run(ops._resolve_channel(_ctx({})))
    # the golden's shipped copy VERBATIM (sweep_timedprize / prizestatus)
    assert _rendered(ei.value) == "Channel '#proof' not found."


def test_governance_and_platform_refusals_render_bare():
    from sb.domain.governance.ops import _validator_error
    from sb.kernel.interaction.errors import ValidatorError

    msg = _rendered(_validator_error("scope_id must be an integer"))
    assert msg == "scope_id must be an integer"

    # platform.command_access mode guard (copy-only two-arg form)
    exc = ValidatorError("", "Mode must be one of: open, selected_channels.")
    assert "Missing/invalid argument" not in _rendered(exc)


# --- two clocks: ONE pinnable clock per lane (D-0061) -----------------------------

def test_lane_clocks_ride_the_pinned_seam(monkeypatch):
    """Both band-5 sweeps' `_utcnow` must read through time.time — the
    ONE wall-clock seam the parity harness pins (D-0060). datetime.now
    is invisible to the pin; a lock stamped from ctx.clock() would then
    never match its sweep's due-read."""
    import time

    from sb.domain.proof_channel import service as proof_service
    from sb.domain.role import service as role_service

    monkeypatch.setattr(time, "time", lambda: 1_000_000.0)
    assert role_service._utcnow() == PINNED
    assert proof_service._utcnow() == PINNED


def test_grant_temp_role_expiry_rides_ctx_clock(monkeypatch):
    from sb.domain.role import service
    from sb.kernel.workflow import engine

    seen = {}

    async def fake_run(op, ctx):
        seen["expires_at_iso"] = ctx.params["expires_at_iso"]
        return SimpleNamespace(outcome="success")

    monkeypatch.setattr(engine, "run", fake_run)
    expires = run(service.grant_temp_role(
        _ctx({}), member_id=7, role_id=9, seconds=3600))
    assert expires == PINNED + dt.timedelta(seconds=3600)
    assert seen["expires_at_iso"] == expires.isoformat()


# --- rolemenu = the hub (golden sweep_rolemenu captures RoleHubPanelView) ----------

def test_rolemenu_routes_to_the_role_hub_panel():
    from sb.manifest.role import _COMMANDS
    from sb.spec.refs import PanelRef

    routes = {c.name: c.route for c in _COMMANDS}
    assert routes["rolemenu"] == PanelRef("role.hub")
    # the reaction listing keeps its own command surface
    from sb.spec.refs import HandlerRef

    assert routes["listreactroles"] == HandlerRef("role.reaction_view")


# --- proof legs speak (panel path routes the WorkflowRef directly) ----------------

def test_proof_lock_and_unlock_legs_carry_acks(monkeypatch):
    from sb.domain.proof_channel import ops, service, store

    async def upsert_lock(conn, **kw):
        return None

    async def delete_lock(conn, *, guild_id, channel_id):
        return True

    async def bound(gid):
        return 55

    monkeypatch.setattr(store, "upsert_lock", upsert_lock)
    monkeypatch.setattr(store, "delete_lock", delete_lock)
    monkeypatch.setattr(service, "bound_proof_channel", bound)

    out = run(ops._record_lock(None, _ctx(
        {"winner_id": 7, "duration_minutes": 30})))
    assert out.user_message is not None and "30 minute(s)" in out.user_message
    out = run(ops._record_lock(None, _ctx({"winner_id": 7})))
    assert out.user_message == "<@7> has been granted access to <#55>!"
    out = run(ops._record_unlock(None, _ctx({})))
    assert out.user_message == "<#55> is now read-only for everyone."
