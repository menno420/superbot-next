"""The six adapters (RC-12 actor building, custom_id/confirm parsing, fuzzy
thresholds, nl rung-3/4), the EventBus, build_runtime (boot-gate leg B
arming), tree_sync (leg C), and predicates."""

import asyncio
from types import SimpleNamespace

import pytest

from sb.kernel.events_bus import EventBus
from sb.kernel.interaction.adapters import (
    actor_from_member,
    install_target_index,
)
from sb.kernel.interaction.adapters.component import parse_custom_id, request_from_component
from sb.kernel.interaction.adapters.fuzzy import resolve_token
from sb.kernel.interaction.adapters.nl import request_from_intent, run_plan
from sb.kernel.interaction.predicates import EvalContext, evaluate, install_flag_reader
from sb.kernel.interaction.request import ActorRef, Surface, TargetRef
from sb.spec.refs import PredicateRef, clear_ref_table, predicate
from tests.unit.interaction.conftest import FakeResponder, Spec


# --- RC-12: the actor builder --------------------------------------------------

def _member(user_id=5, owner_id=99, admin=False, mod=False, manage=False,
            roles=(10, 11)):
    return SimpleNamespace(
        id=user_id,
        guild_permissions=SimpleNamespace(administrator=admin,
                                          moderate_members=mod,
                                          manage_guild=manage),
        roles=tuple(SimpleNamespace(id=r) for r in roles),
    )


def test_actor_from_member_computes_tier_and_role_ids():
    actor = actor_from_member(_member(mod=True), guild_owner_id=99)
    assert actor.member_tier == "moderator"          # RC-12 pre-computed
    assert actor.role_ids == frozenset({10, 11})     # A-12, fresh per interaction
    assert actor.is_guild_operator and not actor.is_bot_owner
    owner = actor_from_member(_member(user_id=99), guild_owner_id=99)
    assert owner.member_tier == "owner"
    dm = actor_from_member(_member(), guild_owner_id=None, is_dm=True)
    assert dm.is_dm and dm.member_tier is None


def test_actor_ref_field_order_pins_rc12_batch():
    import dataclasses
    names = [f.name for f in dataclasses.fields(ActorRef)]
    assert names == ["user_id", "is_guild_operator", "is_bot_owner", "is_dm",
                     "actor_type", "member_tier", "role_ids"]


# --- component adapter ----------------------------------------------------------

def test_parse_custom_id_plain_and_confirm():
    assert parse_custom_id("settings.toggle") == ("settings.toggle", False, None)
    key, confirmed, request_id = parse_custom_id("sb.confirm:panel.act:req-9")
    assert (key, confirmed, request_id) == ("panel.act", True, "req-9")


def test_component_request_confirm_reentry():
    target = TargetRef(key="panel.act", spec=Spec())
    install_target_index(lambda key, surface: target if key == "panel.act" else None)
    interaction = SimpleNamespace(
        id=123, data={"custom_id": "sb.confirm:panel.act:req-9"},
        guild=SimpleNamespace(id=1, owner_id=99), channel_id=7,
        user=_member(),
    )
    req = request_from_component(interaction, responder=FakeResponder(Surface.COMPONENT))
    assert req.confirmed and req.request_id == "req-9"
    assert req.target is target and req.surface is Surface.COMPONENT


def test_component_select_values_carried():
    install_target_index(lambda key, surface: TargetRef(key=key, spec=Spec()))
    interaction = SimpleNamespace(
        id=1, data={"custom_id": "panel.pick", "values": ["a", "b"]},
        guild=SimpleNamespace(id=1, owner_id=99), channel_id=7, user=_member(),
    )
    req = request_from_component(interaction, responder=FakeResponder(Surface.COMPONENT))
    assert req.args["values"] == ("a", "b")


# --- fuzzy ---------------------------------------------------------------------

def test_fuzzy_thresholds():
    corpus = frozenset({"balance", "leaderboard", "help"})
    assert resolve_token("balanse", corpus).kind == "auto"
    assert resolve_token("balanse", corpus).match == "balance"
    assert resolve_token("ledbord", corpus).kind == "suggest"
    assert resolve_token("zzzzz", corpus).kind == "none"


# --- nl adapter ------------------------------------------------------------------

def test_nl_intent_builds_request_and_miss_returns_none():
    target = TargetRef(key="balance", spec=Spec())
    install_target_index(lambda key, surface: target if key == "balance" else None)
    actor = ActorRef(1, False, False, False)
    intent = SimpleNamespace(next_command="balance", args={"user": 1},
                             nl_text="what's my balance", intent_key="economy.balance",
                             confidence=0.93)
    req = request_from_intent(intent, responder=FakeResponder(Surface.NL_INTENT),
                              origin=None, guild_id=1, channel_id=2, actor=actor)
    assert req.surface is Surface.NL_INTENT
    assert req.provenance.intent_key == "economy.balance"
    miss = request_from_intent(SimpleNamespace(next_command="nope", args={}),
                               responder=FakeResponder(), origin=None,
                               guild_id=1, channel_id=2, actor=actor)
    assert miss is None


def test_nl_plan_stops_on_first_non_success():
    import sb.kernel.lifecycle as lifecycle
    lifecycle.set_phase(lifecycle.Phase.DRAINING)   # every step will BLOCK
    install_target_index(lambda key, surface: TargetRef(key=key, spec=Spec()))
    actor = ActorRef(1, False, False, False)
    steps = [SimpleNamespace(next_command=f"c{i}", args={}, nl_text="",
                             intent_key=f"k{i}", confidence=1.0) for i in range(3)]
    results = asyncio.run(run_plan(steps, plan_id="plan-1",
                                   responder=FakeResponder(Surface.NL_ORCHESTRATION),
                                   origin=None, guild_id=1, channel_id=2, actor=actor))
    assert len(results) == 1                        # stop on first non-SUCCESS


# --- predicates -------------------------------------------------------------------

def test_predicates_two_forms_and_fail_closed():
    ctx = EvalContext(guild_id=1)
    assert asyncio.run(evaluate("", ctx)) is True   # constant-true

    async def flags(guild_id, key):
        return key == "beta"
    install_flag_reader(flags)
    assert asyncio.run(evaluate("flag:beta", ctx)) is True
    assert asyncio.run(evaluate("flag:alpha", ctx)) is False
    assert asyncio.run(evaluate("binding:log_channel", ctx)) is False  # closed

    clear_ref_table()

    @predicate("probe.always")
    def _always(c):
        return True

    assert asyncio.run(evaluate(PredicateRef("probe.always"), ctx)) is True
    clear_ref_table()


def test_predicate_setting_form_reads_the_k7_seam():
    import sb.kernel.settings as settings
    settings.clear_for_tests()
    try:
        settings.register_setting(settings.SettingDeclaration(
            "logging", "enabled", activation=settings.Activation.ON_BY_DEFAULT))
        ctx = EvalContext(guild_id=1)
        assert asyncio.run(evaluate("setting:logging.enabled", ctx)) is True
        # undeclared setting => fail-closed, never a crash
        assert asyncio.run(evaluate("setting:ghost.key", ctx)) is False
    finally:
        settings.clear_for_tests()


# --- EventBus ----------------------------------------------------------------------

def test_event_bus_per_handler_isolation():
    bus = EventBus()
    seen = []

    async def good(**payload):
        seen.append(payload["x"])

    def boom(**payload):
        raise RuntimeError("subscriber exploded")

    bus.on("e", boom)
    bus.on("e", good)
    delivered = asyncio.run(bus.emit("e", x=1))
    assert delivered == 1 and seen == [1]          # isolation: good still ran


# --- boot-gate leg B/C ---------------------------------------------------------------

def _snapshot():
    return {
        "projections": {
            "namespace": {
                "command": [
                    {"value": "balance", "surface": "slash", "owner": "economy",
                     "parent_group": None},
                    {"value": "give", "surface": "prefix", "owner": "economy",
                     "parent_group": None},
                ],
                "custom_id": [{"value": "economy.panel.claim", "owner": "economy"}],
                "task_prefix": [{"value": "economy:", "owner": "economy"}],
            },
            "events": {},
        },
        "subsystems": [{"key": "economy", "commands": [
            {"name": "balance", "authority_ref": "user", "effect": "read"}]}],
    }


def test_build_runtime_arms_leg_b_and_installs_the_index():
    from sb.app.boot_gate import (
        snapshot_command_paths,
        snapshot_custom_ids,
        snapshot_task_prefixes,
    )
    from sb.app.build_runtime import build_runtime

    snapshot = _snapshot()
    runtime = build_runtime(snapshot)
    assert runtime.command_paths() == snapshot_command_paths(snapshot) == {"balance"}
    assert runtime.custom_ids() == snapshot_custom_ids(snapshot)
    assert runtime.task_prefixes() == snapshot_task_prefixes(snapshot)
    assert runtime.event_names() == set()          # kernel events excluded
    # the adapters' index is live and carries the spec's pinned fields.
    from sb.kernel.interaction.adapters import lookup_target
    target = lookup_target("balance", Surface.SLASH)
    assert target is not None and target.spec.authority_ref == "user"
    assert lookup_target("balance", Surface.PREFIX) is None


def test_leg_c_sync_outcomes():
    from sb.app.tree_sync import SyncOutcome, sync_remote

    snapshot = _snapshot()

    class Tree:
        def __init__(self, remote):
            self._remote = remote
            self.synced = False

        async def fetch_commands(self):
            return [SimpleNamespace(name=n, options=[]) for n in self._remote]

        async def sync(self):
            self.synced = True
            return list(self._remote)

    in_sync = SimpleNamespace(tree=Tree(["balance"]))
    outcome = asyncio.run(sync_remote(in_sync, snapshot, enabled=True))
    assert outcome == SyncOutcome(False, "unchanged")

    lagging = SimpleNamespace(tree=Tree(["oldcmd"]))
    outcome = asyncio.run(sync_remote(lagging, snapshot, enabled=True))
    assert outcome.synced and outcome.reason == "synced"
    assert outcome.added == ("balance",) and outcome.removed == ("oldcmd",)

    disabled = asyncio.run(sync_remote(in_sync, snapshot, enabled=False))
    assert disabled.reason == "disabled"

    broken = SimpleNamespace(tree=None)
    fetch_failed = asyncio.run(sync_remote(broken, snapshot, enabled=True))
    assert fetch_failed.reason == "fetch_failed"    # non-fatal, never raises


def test_run_boot_gate_leg_c_wired():
    from sb.app.boot_gate import run_boot_gate

    committed_result = None
    # leg A will fail against a fabricated snapshot; leg C must still be
    # skipped when bot is None (dormant path preserved).
    report = asyncio.run(run_boot_gate({"stable_hash": "nope",
                                        "field_roles": {}, "subsystems": []}))
    assert report.remote is None
    _ = committed_result


# --- the no-skip fence -----------------------------------------------------------

def test_no_skip_fence_is_clean_and_catches_a_bypass(tmp_path):
    import tools.check_no_skip as fence
    assert fence.check() == []                     # the tree is clean at S9

    rogue = fence.SB / "kernel" / "_rogue_probe.py"
    rogue.write_text("import discord\n\n@bot.event\nasync def on_message(m):\n    pass\n")
    try:
        problems = fence.check()
        assert any("discord import" in p for p in problems)
        assert any("surface-registration" in p for p in problems)
    finally:
        rogue.unlink()
