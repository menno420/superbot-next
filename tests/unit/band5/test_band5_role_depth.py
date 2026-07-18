"""Band 5 (role) depth — the handler layer's refusal ladders and DB-truth
views, none of which the band-5/band-6 slices reach:

* ``role.deleterole`` — the FULL feasibility gate ladder (usage → guild
  view → role lookup → feasibility verdict → provisioning refusal) plus
  the success path's shared-mutation_id audit/lifecycle pair.
* ``role.reactroles_bind`` — usage guard + the two ``fetch_message``
  refusal forks + the reaction-add warn branch that keeps the saved row.
* ``role.temprole`` — usage / missing-token / invalid-duration refusals,
  plus a direct table over ``_parse_duration`` boundaries.
* ``feasibility.evaluate_role`` — the ABOVE_ACTOR actor-hierarchy verdict.
* the six DB-truth text views — populated render + empty-state copy each.
* ``assignroles``/``debugroles``/``refreshmembers`` — unarmed-adapter
  BLOCKED copy.
* the authority floors + the hub audience-tier floor.

All DB-free: ``asyncio.run``, ``SimpleNamespace`` ducks, monkeypatched
``store`` readers, the ``reset_role_ports_for_tests`` autouse fixture.
"""

from __future__ import annotations

import asyncio
import dataclasses
from types import SimpleNamespace

import pytest

from sb.spec.outcomes import BLOCKED, SUCCESS

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.role import service

    service.reset_role_ports_for_tests()
    yield
    service.reset_role_ports_for_tests()


@dataclasses.dataclass
class Req:
    args: dict
    guild_id: int | None = 42
    channel_id: int | None = 7
    request_id: str = "req-1"
    confirmed: bool = False
    actor: object = dataclasses.field(
        default_factory=lambda: SimpleNamespace(
            user_id=7, actor_type="user", member_tier="administrator"))


def _handler(name: str):
    from sb.domain.role import handlers
    from sb.spec.refs import HandlerRef, resolve

    handlers.ensure_handler_refs()
    return resolve(HandlerRef(name))


def _role(rid, name, position=1, managed=False, guild_id=42):
    return SimpleNamespace(id=rid, name=name, position=position,
                           managed=managed,
                           guild=SimpleNamespace(id=guild_id))


def _me(manage_roles=True, top_position=100):
    return SimpleNamespace(
        guild_permissions=SimpleNamespace(manage_roles=manage_roles),
        top_role=SimpleNamespace(position=top_position, id=1))


def _guild(roles=(), me=None, gid=42):
    return SimpleNamespace(id=gid, roles=list(roles), me=me)


def _install_guild(monkeypatch, guild):
    from sb.domain.role import service

    async def source(_gid):
        return guild

    service.install_guild_source(source)


# --- P1.1  role.deleterole — the full feasibility gate ladder ----------------------


def test_deleterole_usage_guard():
    reply = run(_handler("role.deleterole")(Req(args={"argv": ()})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Usage: `!deleterole <role>`"


def test_deleterole_blocks_without_guild_view():
    # no guild source installed → guild_view() returns None (honest wait)
    reply = run(_handler("role.deleterole")(Req(args={"argv": ("VIP",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "📝 Role deletion needs the live guild view "
        "(arms with the live adapter).")


def test_deleterole_role_not_found(monkeypatch):
    _install_guild(monkeypatch, _guild(roles=[_role(9, "Other")], me=_me()))
    reply = run(_handler("role.deleterole")(Req(args={"argv": ("Ghost",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "❌ Role not found."


def test_deleterole_feasibility_blocked_speaks_first(monkeypatch):
    # role sits ABOVE the bot's top role → ABOVE_BOT verdict, refused with
    # the shipped "❌ Could not delete **{name}**: {reason}" byte before any
    # provisioning call.
    high = _role(5, "Admins", position=200)
    _install_guild(monkeypatch, _guild(roles=[high], me=_me(top_position=100)))
    reply = run(_handler("role.deleterole")(Req(args={"argv": ("Admins",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "❌ Could not delete **Admins**: above my highest role — "
        "I can't manage it")


def test_deleterole_provisioning_runtimeerror_blocks(monkeypatch):
    # feasible role, but the provisioning port is unarmed → its RuntimeError
    # rides the same refusal shape (nothing is emitted).
    ok_role = _role(4, "Temp", position=1)
    _install_guild(monkeypatch, _guild(roles=[ok_role], me=_me()))
    facts = []

    class Bus:
        async def emit(self, name, **payload):
            facts.append(name)

    from sb.domain.role import service
    service.subscribe(Bus())
    reply = run(_handler("role.deleterole")(Req(args={"argv": ("Temp",)})))
    assert reply.outcome == BLOCKED
    assert reply.user_message.startswith("❌ Could not delete **Temp**:")
    assert facts == []            # no audit / lifecycle on the refusal


def test_deleterole_success_emits_shared_mutation_id_pair(monkeypatch):
    from sb.domain.role import service

    ok_role = _role(4, "Temp", position=1)
    _install_guild(monkeypatch, _guild(roles=[ok_role], me=_me()))

    deleted = []

    class FakeProvisioning:
        async def create_guild_role(self, *a, **k):
            raise AssertionError("unused")

        async def delete_role(self, guild_id, role_id, *, reason):
            deleted.append((guild_id, role_id, reason))

    service.install_role_provisioning(FakeProvisioning())

    facts = []

    class Bus:
        async def emit(self, name, **payload):
            facts.append((name, payload))

    service.subscribe(Bus())
    reply = run(_handler("role.deleterole")(Req(args={"argv": ("Temp",)})))
    assert reply.outcome == SUCCESS
    assert reply.user_message == "🗑️ Deleted role **Temp**."
    assert deleted == [(42, 4, None)]
    names = [n for n, _ in facts]
    assert names == ["audit.action_recorded", "role.lifecycle_changed"]
    # the audit + lifecycle companions share ONE mutation_id (the shipped
    # RoleLifecycleService twin invariant).
    mids = {p["mutation_id"] for _, p in facts}
    assert len(mids) == 1


# --- P1.2  role.reactroles_bind — usage + fetch refusals + warn branch -------------


def _install_message_ops(monkeypatch, *, fetch=None, add=None):
    from sb.domain.role import service

    class FakeMessageOps:
        async def fetch_message(self, channel_id, message_id):
            if fetch is not None:
                raise fetch

        async def add_reaction(self, channel_id, message_id, emoji):
            if add is not None:
                raise add

    service.install_message_ops(FakeMessageOps())


def test_reactroles_bind_usage_guard():
    reply = run(_handler("role.reactroles_bind")(
        Req(args={"argv": ("123", "😀")})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Usage: `!reactroles <message_id> <emoji> <@role>`")


def test_reactroles_bind_message_not_found(monkeypatch):
    _install_message_ops(monkeypatch, fetch=LookupError("404"))
    reply = run(_handler("role.reactroles_bind")(
        Req(args={"argv": ("123", "😀", "<@&5>")})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "❌ Message not found in this channel."


def test_reactroles_bind_fetch_runtimeerror_warns(monkeypatch):
    _install_message_ops(monkeypatch, fetch=RuntimeError("rate limited"))
    reply = run(_handler("role.reactroles_bind")(
        Req(args={"argv": ("123", "😀", "<@&5>")})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == "⚠️ rate limited"


def test_reactroles_bind_reaction_failure_keeps_saved_row(monkeypatch):
    from sb.kernel.workflow import engine

    _install_message_ops(monkeypatch, add=ValueError("bad emoji"))

    async def fake_run(ref, ctx):
        return SimpleNamespace(outcome=SUCCESS, user_message="bound")

    monkeypatch.setattr(engine, "run", fake_run)
    reply = run(_handler("role.reactroles_bind")(
        Req(args={"argv": ("123", "😀", "<@&5>")})))
    # the row is written (engine.run succeeded); only the reaction add failed
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "⚠️ Role saved, but I couldn't add the reaction (invalid emoji?).")


# --- P1.3  role.temprole — refusal ladder + _parse_duration table ------------------


def test_temprole_usage_guard():
    reply = run(_handler("role.temprole")(Req(args={"argv": ("<@7>", "2h")})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Usage: `!temprole @member <duration> <@role>`")


def test_temprole_missing_member_or_role_id():
    # three tokens, but none resolves to an id
    reply = run(_handler("role.temprole")(
        Req(args={"argv": ("nobody", "2h", "norole")})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "Usage: `!temprole @member <duration> <@role>` — "
        "duration like `2h`, `30m`, `1d`.")


def test_temprole_invalid_duration():
    reply = run(_handler("role.temprole")(
        Req(args={"argv": ("<@7>", "xyz", "<@&5>")})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "❌ Invalid duration — try `30m`, `2h`, or `7d` (max 1 year).")


def test_parse_duration_boundaries():
    from sb.domain.role.handlers import _parse_duration

    assert _parse_duration("30") == 1800        # bare number = minutes
    assert _parse_duration("2h") == 7200
    assert _parse_duration("7d") == 604800
    assert _parse_duration("400d") is None       # > 1 year MAX
    assert _parse_duration("0") is None          # zero rejected
    assert _parse_duration("abc") is None        # non-digit body
    assert _parse_duration("") is None


# --- P1.4  feasibility.evaluate_role — the ABOVE_ACTOR verdict ---------------------


def test_evaluate_role_above_actor():
    from sb.domain.role import feasibility as f

    role = _role(9, "Staff", position=50)
    actor = SimpleNamespace(top_role=SimpleNamespace(position=10, id=2))
    verdict = f.evaluate_role(role, actor=actor)
    assert verdict.code == f.ABOVE_ACTOR
    assert not verdict.ok
    assert verdict.reason == "above your highest role"
    # a role UNDER the actor is selectable
    low = _role(3, "Member", position=1)
    assert f.evaluate_role(low, actor=actor).ok


# --- P2.5  the six DB-truth text views — populated + empty each --------------------


def test_time_roles_view(monkeypatch):
    from sb.domain.role import store

    rows = [{"role_name": "Bronze", "days_required": 10}]
    monkeypatch.setattr(store, "get_thresholds",
                        lambda gid, conn=None: _async(rows))
    out = run(_handler("role.time_roles_view")(Req(args={})))
    assert out.user_message == "⏱️ **Time role tiers**\n• **Bronze** — 10 day(s)"

    monkeypatch.setattr(store, "get_thresholds",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.time_roles_view")(Req(args={})))
    assert out.user_message.startswith(
        "⏱️ No time-based role tiers configured.")


def test_xp_roles_view_sorts_by_level(monkeypatch):
    from sb.domain.role import store

    rows = [
        {"role_name": "Lv10", "xp_auto_assign": True, "level_required": 10,
         "days_required": 0},
        {"role_name": "Lv5", "xp_auto_assign": True, "level_required": 5,
         "days_required": 0},
    ]
    monkeypatch.setattr(store, "get_thresholds",
                        lambda gid, conn=None: _async(rows))
    out = run(_handler("role.xp_roles_view")(Req(args={})))
    assert out.user_message == (
        "⚡ **XP role tiers**\n"
        "• **Lv5** — level 5\n• **Lv10** — level 10")   # sorted by level

    monkeypatch.setattr(store, "get_thresholds",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.xp_roles_view")(Req(args={})))
    assert out.user_message == "⚡ No XP role tiers configured."


def test_reaction_view(monkeypatch):
    from sb.domain.role import store

    binds = [{"message_id": 123, "emoji": "😀", "role_id": 5}]
    monkeypatch.setattr(store, "list_reaction_bindings",
                        lambda gid, conn=None: _async(binds))
    monkeypatch.setattr(store, "list_menus",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.reaction_view")(Req(args={})))
    assert out.user_message.startswith("💬 **Reaction roles**")

    monkeypatch.setattr(store, "list_reaction_bindings",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.reaction_view")(Req(args={})))
    assert out.user_message == "No reaction roles configured."


def test_exemptions_view(monkeypatch):
    from sb.domain.role import store

    rows = [{"role_id": 5, "exempt_xp": True, "exempt_time": False}]
    monkeypatch.setattr(store, "get_exemptions",
                        lambda gid, conn=None: _async(rows))
    out = run(_handler("role.exemptions_view")(Req(args={})))
    assert out.user_message.startswith("🚫 **Automation exemptions**")

    monkeypatch.setattr(store, "get_exemptions",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.exemptions_view")(Req(args={})))
    assert out.user_message == "🚫 No automation-exempt roles."


def test_manage_view(monkeypatch):
    from sb.domain.role import store

    stats = [{"role_id": 5, "picked": 3, "removed": 1}]
    monkeypatch.setattr(store, "pickup_stats",
                        lambda gid, conn=None: _async(stats))
    out = run(_handler("role.manage_view")(Req(args={})))
    assert out.user_message.startswith("🗂️ **Role pickup stats**")
    assert "3 picked / 1 removed" in out.user_message

    monkeypatch.setattr(store, "pickup_stats",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.manage_view")(Req(args={})))
    assert out.user_message == (
        "🗂️ **Role pickup stats**\nNo pickup activity recorded yet.")


def test_diagnostics_view_both_forks(monkeypatch):
    from sb.domain.role import store

    # fork 1: no guild view → live preflight unavailable
    monkeypatch.setattr(store, "get_thresholds",
                        lambda gid, conn=None: _async([]))
    out = run(_handler("role.diagnostics_view")(Req(args={})))
    assert "live preflight unavailable (guild view port unarmed)" in \
        out.user_message

    # fork 2: armed guild view whose hierarchy clears → the preflight line
    rows = [{"role_name": "Bronze", "days_required": 10, "role_id": 1}]
    monkeypatch.setattr(store, "get_thresholds",
                        lambda gid, conn=None: _async(rows))
    _install_guild(monkeypatch,
                   _guild(roles=[_role(1, "Bronze", position=1)], me=_me()))
    out = run(_handler("role.diagnostics_view")(Req(args={})))
    assert "unavailable" not in out.user_message
    assert "✅ preflight OK" in out.user_message


# --- P2.6  unarmed-adapter BLOCKED refusals ---------------------------------------


def test_assignroles_blocks_without_guild_view():
    reply = run(_handler("role.assignroles")(Req(args={"argv": ()})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⏱️ The role check needs the live guild view "
        "(arms with the live adapter).")


def test_debugroles_blocks_without_guild_view():
    reply = run(_handler("role.debugroles")(Req(args={"argv": ()})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "🔧 Live role diagnostics need the gateway cache "
        "(arms with the live adapter).")


def test_refreshmembers_is_the_capture_artifact_literal():
    reply = run(_handler("role.refreshmembers")(Req(args={"argv": ()})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "⚠️ An unexpected error occurred. Please try again.")


# --- P2.7 / P2.8  authority + audience-tier floors --------------------------------


def test_authority_ref_floors():
    from sb.domain.role import ops

    assert ops.GRANT_TEMP_ROLE.authority_ref == "moderator"
    assert ops.SET_THRESHOLD.authority_ref == "administrator"
    assert ops.CREATE_MENU.authority_ref == "administrator"
    assert ops.SET_EXEMPTION.authority_ref == "administrator"
    # the expire lane is the unattended sweep body — no interactive floor
    assert ops.EXPIRE_TEMP_ROLE.authority_ref == ""


def test_hub_actions_all_administrator_tier():
    from sb.domain.role.panels import role_hub_spec

    actions = role_hub_spec().actions
    assert len(actions) == 7
    assert all(a.audience_tier == "administrator" for a in actions)


# --- shared async helper -----------------------------------------------------------


def _async(value):
    async def _coro():
        return value

    return _coro()
