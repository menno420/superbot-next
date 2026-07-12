"""Band 2 slice 1 (moderation + logging) — seam-level unit legs."""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def _clean_settings_registry():
    from sb.kernel import settings as ksettings

    ksettings.clear_for_tests()
    yield
    ksettings.clear_for_tests()


def _register_declarations():
    import sb.manifest.moderation as m_mod
    import sb.manifest.server_logging as m_log
    from sb.kernel.settings import register_manifest_settings

    for mod in (m_mod, m_log):
        try:
            register_manifest_settings(mod.MANIFEST)
        except ValueError as exc:
            if "already declared" not in str(exc):
                raise


def test_moderation_policy_defaults_are_shipped_values():
    from sb.domain.moderation.service import load_policy

    _register_declarations()
    policy = asyncio.run(load_policy(1))
    assert policy.warn_threshold == 3
    assert policy.warn_timeout_minutes == 10
    assert policy.warn_escalation_action == "timeout"
    assert policy.require_reason is False
    assert policy.max_timeout_minutes == 40320
    assert policy.public_log_actions == "none"


def test_require_reason_blocks_before_side_effects():
    from sb.domain.moderation.service import (
        ModerationPolicy,
        ReasonRequiredError,
        resolve_reason,
    )

    policy = ModerationPolicy(require_reason=True)
    with pytest.raises(ReasonRequiredError):
        resolve_reason("", policy, action="warn")
    # timeout is exempt (its reason carries the duration — shipped rule)
    assert resolve_reason("", policy, action="timeout") == "No reason provided"


def test_parse_target_and_reason_prefix_form():
    from sb.domain.moderation.service import parse_target_and_reason
    from sb.kernel.interaction.errors import ValidatorError

    target, reason = parse_target_and_reason(
        {"argv": ("<@900000000000000103>", "parity", "test")})
    assert target == 900000000000000103
    assert reason == "parity test"
    # bare numeric id — the shipped `!unban <user_id>` contract (a banned
    # user can never be mentioned); band-2 replay found this rejected.
    target, reason = parse_target_and_reason({"argv": ("3", "why not")})
    assert target == 3
    assert reason == "why not"
    # a missing target is a polite user_error (ValidatorError), never a
    # BUG envelope — still a ValueError subclass for legacy call sites.
    with pytest.raises(ValidatorError):
        parse_target_and_reason({"argv": ("not-a-mention",)})
    with pytest.raises(ValueError):
        parse_target_and_reason({"argv": ()})


def test_warn_escalation_ladder(monkeypatch):
    """Threshold reached => escalation recorded + count reset IN the leg
    (shipped WarnOutcome SUCCESS semantics), decision + compensation
    handles threaded to the EFFECT leg. The oracle keeps these writes only
    when the escalation ACTION applies — the Discord-refused path is
    test_warn_escalation_blocked_compensates below (ORDER 004 item 1)."""
    from types import SimpleNamespace

    from sb.domain.moderation import ops, store
    from sb.kernel.workflow.context import WorkflowContext

    _register_declarations()
    rows: list[tuple] = []
    counts = {"n": 2}

    async def fake_add_warning(conn, *, user_id, guild_id):
        counts["n"] += 1
        return counts["n"]

    async def fake_clear(conn, *, user_id, guild_id):
        counts["n"] = 0

    async def fake_log(conn, *, guild_id, action, target_id, moderator_id,
                       reason, at=None):
        rows.append((action, target_id, reason))
        return len(rows)                    # row id handle (RETURNING id)

    monkeypatch.setattr(store, "add_warning", fake_add_warning)
    monkeypatch.setattr(store, "clear_warnings", fake_clear)
    monkeypatch.setattr(store, "log_mod_action", fake_log)

    ctx = WorkflowContext(
        actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
        request_id="r1", confirmed=False,
        params={"argv": ("<@900000000000000103>", "spam")})
    outcome = asyncio.run(ops._record_warn(None, ctx))
    assert outcome.after["escalated"] == "timeout"   # 3rd warn hits threshold
    assert counts["n"] == 0                          # ladder resets the count
    # shipped history vocabulary: warn row, escalation row ("Reached N
    # warnings"), and the reset's own "clearwarnings" row — three rows.
    assert [r[0] for r in rows] == ["warn", "timeout", "clearwarnings"]
    assert rows[1][2] == "Reached 3 warnings"
    assert rows[2][2] == "Warnings cleared"
    assert ctx.params["_escalation"] == "timeout"
    assert ctx.params["_target_id"] == 900000000000000103
    # the compensation handles for a Discord-refused escalation
    assert ctx.params["_escalation_row_ids"] == (2, 3)
    assert ctx.params["_pre_escalation_count"] == 3
    # shipped operator ack, line 1 (render_warn_outcome_lines verbatim)
    assert outcome.user_message == (
        "⚠️ <@900000000000000103> warned (3/3). Reason: spam")


def test_warn_escalation_blocked_compensates(monkeypatch):
    """ORACLE ALIGNMENT (disbot services/moderation_service.py warn,
    discord.Forbidden branch): a Discord-refused escalation keeps the
    warning COUNT and leaves NO escalation/"Warnings cleared" history rows
    (WarnOutcome.escalation_blocked) — the compensator restores the count
    and withdraws the two in-txn rows; the WARN op wires it (fork E)."""
    import contextlib
    from types import SimpleNamespace

    from sb.domain.moderation import ops, store
    from sb.kernel.db import pool
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    _register_declarations()
    restored: list[tuple] = []
    withdrawn: list[tuple] = []

    async def fake_set_warnings(conn, *, user_id, guild_id, count):
        restored.append((user_id, guild_id, count))

    async def fake_withdraw(conn, *, ids):
        withdrawn.append(tuple(ids))
        return len(ids)

    @contextlib.asynccontextmanager
    async def fake_txn():
        yield None

    monkeypatch.setattr(store, "set_warnings", fake_set_warnings)
    monkeypatch.setattr(store, "withdraw_mod_log_rows", fake_withdraw)
    monkeypatch.setattr(pool, "transaction", fake_txn)

    ctx = WorkflowContext(
        actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
        request_id="r2", confirmed=False,
        params={"_escalation": "timeout",
                "_target_id": 900000000000000103,
                "_pre_escalation_count": 3,
                "_escalation_row_ids": (11, 12)})
    out = asyncio.run(ops._compensate_warn_escalation(None, ctx))
    assert restored == [(900000000000000103, 1, 3)]   # count KEPT (oracle)
    assert withdrawn == [(11, 12)]                    # phantom rows gone
    assert out.after["escalation_blocked"] == "timeout"

    # no escalation due => the compensator is a no-op
    ctx2 = WorkflowContext(
        actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
        request_id="r3", confirmed=False, params={})
    out2 = asyncio.run(ops._compensate_warn_escalation(None, ctx2))
    assert out2.after == {"compensated": "nothing"}
    assert restored == [(900000000000000103, 1, 3)]

    # the WARN op declares the compensator on its EFFECT leg (fork E wiring)
    effect = [leg for leg in ops.WARN.legs if leg.leg_id == "apply"][0]
    assert effect.reversibility == "compensatable"
    assert effect.compensator == WorkflowRef(
        "moderation.compensate_warn_escalation")


def test_kick_blocked_compensates(monkeypatch):
    """ORACLE ALIGNMENT (disbot services/moderation_service.py — Discord
    call first, row only after success): a Discord-refused kick leaves NO
    history row claiming the member was kicked — the compensator withdraws
    the committed row; the KICK op wires it (fork E, the compensate_timeout
    shape re-homed at the moderation flip, when timeout itself moved to
    the oracle's call-first sequencing inside its record leg)."""
    import contextlib
    from types import SimpleNamespace

    from sb.domain.moderation import ops, store
    from sb.kernel.db import pool
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    _register_declarations()
    withdrawn: list[tuple] = []

    async def fake_withdraw(conn, *, ids):
        withdrawn.append(tuple(ids))
        return len(ids)

    @contextlib.asynccontextmanager
    async def fake_txn():
        yield None

    monkeypatch.setattr(store, "withdraw_mod_log_rows", fake_withdraw)
    monkeypatch.setattr(pool, "transaction", fake_txn)

    ctx = WorkflowContext(
        actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
        request_id="r4", confirmed=False,
        params={"_kick_row_id": 21, "_target_id": 900000000000000103})
    out = asyncio.run(ops._compensate_kick(None, ctx))
    assert withdrawn == [(21,)]                       # phantom row gone
    assert out.after["withdrawn_rows"] == 1

    # no row handle => the compensator is a no-op
    ctx2 = WorkflowContext(
        actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
        request_id="r5", confirmed=False, params={})
    out2 = asyncio.run(ops._compensate_kick(None, ctx2))
    assert out2.after == {"compensated": "nothing"}
    assert withdrawn == [(21,)]

    # the KICK op declares the compensator on its EFFECT leg
    effect = [leg for leg in ops.KICK.legs if leg.leg_id == "apply"][0]
    assert effect.reversibility == "compensatable"
    assert effect.compensator == WorkflowRef("moderation.compensate_kick")

    # TIMEOUT carries NO effect leg at all: its record leg runs the
    # oracle's call-Discord-first sequencing (a refused timeout aborts the
    # txn — no row, no event; goldens/moderation/sweep_timeout).
    assert [leg.leg_id for leg in ops.TIMEOUT.legs] == ["record"]


def test_ban_never_landed_compensates_by_withdrawal(monkeypatch):
    """ORACLE ALIGNMENT (disbot services/moderation_service.py ban —
    Discord call first, row only after success): a Discord-REFUSED ban
    (apply leg 404, the ORDER 004 live-drive compensator probe) leaves NO
    history row claiming the member was banned. The compensating unban
    itself reports NotFound on a ban that never landed — then the
    compensator falls back to kick's row-withdraw shape over the
    `_ban_row_id` handle the record leg stashes; any OTHER unban failure
    still propagates (the engine's honest `partial`)."""
    import contextlib
    from types import SimpleNamespace

    from sb.domain.moderation import ops, service, store
    from sb.kernel.db import pool
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    _register_declarations()
    withdrawn: list[tuple] = []
    unbans: list[tuple] = []

    async def fake_withdraw(conn, *, ids):
        withdrawn.append(tuple(ids))
        return len(ids)

    @contextlib.asynccontextmanager
    async def fake_txn():
        yield None

    monkeypatch.setattr(store, "withdraw_mod_log_rows", fake_withdraw)
    monkeypatch.setattr(pool, "transaction", fake_txn)

    # name-matched stand-in for discord.NotFound (the guarded band-2
    # pattern — discord is absent in-container, so the domain classifies
    # the port's exception by NAME)
    NotFound = type("NotFound", (Exception,), {})

    class RefusingActions:
        async def unban_member(self, guild_id, user_id, *, reason):
            unbans.append((guild_id, user_id, reason))
            raise NotFound("Unknown Ban")

    def _ctx(params):
        return WorkflowContext(
            actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
            request_id="r6", confirmed=False, params=params)

    service.install_moderation_actions(RefusingActions())
    try:
        out = asyncio.run(ops._compensate_ban(None, _ctx(
            {"_ban_row_id": 21, "_target_id": 900000000000000103})))
        assert withdrawn == [(21,)]                   # phantom row gone
        assert out.after == {"withdrawn_rows": 1,
                             "ban_never_landed": 900000000000000103}

        # no row handle => the withdrawal is a no-op, still a success
        out2 = asyncio.run(ops._compensate_ban(None, _ctx(
            {"_target_id": 900000000000000103})))
        assert withdrawn == [(21,)]                   # no second withdraw
        assert out2.after == {"withdrawn_rows": 0,
                              "ban_never_landed": 900000000000000103}
    finally:
        service.reset_moderation_ports_for_tests()

    # a NON-NotFound unban failure propagates untouched — the compensator
    # never swallows a real Discord error into a fake success
    class BrokenActions:
        async def unban_member(self, guild_id, user_id, *, reason):
            raise RuntimeError("Discord is down")

    service.install_moderation_actions(BrokenActions())
    try:
        with pytest.raises(RuntimeError):
            asyncio.run(ops._compensate_ban(None, _ctx(
                {"_ban_row_id": 21, "_target_id": 900000000000000103})))
        assert withdrawn == [(21,)]                   # no withdrawal either
    finally:
        service.reset_moderation_ports_for_tests()

    # the BAN op declares the compensator on its EFFECT leg
    effect = [leg for leg in ops.BAN.legs if leg.leg_id == "apply"][0]
    assert effect.reversibility == "compensatable"
    assert effect.compensator == WorkflowRef("moderation.compensate_ban")


def test_ban_compensator_restore_path_unbans(monkeypatch):
    """When the ban actually LANDED and a later leg failed, the
    compensator's primary posture is unchanged: the Discord-side
    symmetric restore (unban) — no history row is withdrawn (the ban was
    real; the row is true)."""
    from types import SimpleNamespace

    from sb.domain.moderation import ops, service, store
    from sb.kernel.workflow.context import WorkflowContext

    _register_declarations()
    withdrawn: list[tuple] = []
    unbans: list[tuple] = []

    async def fake_withdraw(conn, *, ids):
        withdrawn.append(tuple(ids))
        return len(ids)

    monkeypatch.setattr(store, "withdraw_mod_log_rows", fake_withdraw)

    class FakeActions:
        async def unban_member(self, guild_id, user_id, *, reason):
            unbans.append((guild_id, user_id, reason))

    service.install_moderation_actions(FakeActions())
    try:
        ctx = WorkflowContext(
            actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
            request_id="r7", confirmed=False,
            params={"_ban_row_id": 21, "_target_id": 900000000000000103})
        out = asyncio.run(ops._compensate_ban(None, ctx))
        assert unbans == [(1, 900000000000000103,
                           "compensating failed ban flow")]
        assert withdrawn == []                        # the row stays — true
        assert out.after == {"compensated": "ban"}
    finally:
        service.reset_moderation_ports_for_tests()


def test_timeout_record_leg_calls_discord_first(monkeypatch):
    """The oracle sequencing inside the record leg: the guild-action port
    runs BEFORE the row write; a port failure marks the ctx.params
    side-channel (`_moderation_generic_error`) and re-raises so the txn
    aborts with no row and no emit."""
    from types import SimpleNamespace

    from sb.domain.moderation import ops, service, store
    from sb.kernel.workflow.context import WorkflowContext

    _register_declarations()
    rows: list[tuple] = []
    calls: list[tuple] = []

    async def fake_log(conn, *, guild_id, action, target_id, moderator_id,
                       reason, at=None):
        rows.append((action, target_id, reason))

    monkeypatch.setattr(store, "log_mod_action", fake_log)

    class RefusingActions:
        async def timeout_member(self, guild_id, user_id, *, minutes, reason):
            calls.append(("timeout", user_id, minutes, reason))
            raise RuntimeError("Discord refused")

    def _ctx(argv):
        return WorkflowContext(
            actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
            request_id="r1", confirmed=False, params={"argv": argv})

    service.install_moderation_actions(RefusingActions())
    try:
        ctx = _ctx(("<@900000000000000103>", "3"))
        with pytest.raises(RuntimeError):
            asyncio.run(ops._record_timeout(None, ctx))
        assert calls == [("timeout", 900000000000000103, 3, "3 minutes")]
        assert rows == []                              # no row on refusal
        assert ctx.params["_moderation_generic_error"] is True
    finally:
        service.reset_moderation_ports_for_tests()


def test_timeout_record_leg_parses_duration(monkeypatch):
    """Shipped `!timeout @member <minutes>`: the duration is REQUIRED and,
    with no explicit reason, IS the reason ("N minutes" — shipped verbatim);
    a missing duration is a polite user_error (raised BEFORE any Discord
    call). The success ack is the shipped ⏳ line (leg copy — the reply the
    op-running handler renders)."""
    from types import SimpleNamespace

    from sb.domain.moderation import ops, service, store
    from sb.kernel.interaction.errors import ValidatorError
    from sb.kernel.workflow.context import WorkflowContext

    _register_declarations()
    rows: list[tuple] = []
    calls: list[tuple] = []

    async def fake_log(conn, *, guild_id, action, target_id, moderator_id,
                       reason, at=None):
        rows.append((action, target_id, reason))

    monkeypatch.setattr(store, "log_mod_action", fake_log)

    class FakeActions:
        async def timeout_member(self, guild_id, user_id, *, minutes, reason):
            calls.append(("timeout", user_id, minutes, reason))

    def _ctx(argv):
        return WorkflowContext(
            actor=SimpleNamespace(user_id=42, actor_type="user"), guild_id=1,
            request_id="r1", confirmed=False, params={"argv": argv})

    service.install_moderation_actions(FakeActions())
    try:
        ctx = _ctx(("<@900000000000000103>", "3"))
        outcome = asyncio.run(ops._record_timeout(None, ctx))
        assert ctx.params["_minutes"] == 3
        assert ctx.params["_reason"] == "3 minutes"
        assert outcome.after["minutes"] == 3
        assert outcome.user_message == ("⏳ <@900000000000000103> timed out "
                                        "for 3 minute(s).")
        assert calls[-1] == ("timeout", 900000000000000103, 3, "3 minutes")
        assert rows[-1] == ("timeout", 900000000000000103, "3 minutes")

        ctx = _ctx(("<@900000000000000103>", "5", "being", "rude"))
        asyncio.run(ops._record_timeout(None, ctx))
        assert ctx.params["_minutes"] == 5
        assert ctx.params["_reason"] == "being rude"

        n_calls = len(calls)
        with pytest.raises(ValidatorError):
            asyncio.run(ops._record_timeout(
                None, _ctx(("<@900000000000000103>",))))
        assert len(calls) == n_calls           # validator fires pre-Discord
    finally:
        service.reset_moderation_ports_for_tests()


def test_apply_legs_carry_shipped_acks(monkeypatch):
    """EFFECT legs speak the shipped operator acks (band-2 finding: op
    success used to render SILENT — no user_message channel existed)."""
    from types import SimpleNamespace

    from sb.domain.moderation import ops, service
    from sb.kernel.workflow.context import WorkflowContext

    applied: list[tuple] = []

    class FakeActions:
        async def timeout_member(self, guild_id, user_id, *, minutes, reason):
            applied.append(("timeout", user_id, minutes, reason))

        async def kick_member(self, guild_id, user_id, *, reason):
            applied.append(("kick", user_id, reason))

        async def ban_member(self, guild_id, user_id, *, reason,
                             delete_message_days):
            applied.append(("ban", user_id, reason, delete_message_days))

        async def unban_member(self, guild_id, user_id, *, reason):
            applied.append(("unban", user_id, reason))

        async def fetch_user(self, user_id):
            applied.append(("fetch_user", user_id))

        async def dm_member(self, user_id, text):
            applied.append(("dm", user_id))

    service.install_moderation_actions(FakeActions())
    try:
        def _ctx(**params):
            return WorkflowContext(
                actor=SimpleNamespace(user_id=42, actor_type="user"),
                guild_id=1, request_id="r1", confirmed=True, params=params)

        out = asyncio.run(ops._apply_kick(
            None, _ctx(_target_id=7, _reason="No reason provided")))
        assert out.user_message == "👢 <@7> kicked. Reason: No reason provided"

        out = asyncio.run(ops._apply_unban(
            None, _ctx(_target_id=3, _reason="No reason provided")))
        assert out.user_message == "✅ <@3> unbanned."
        # shipped cog sequencing: fetch_user BEFORE unban (goldens/
        # moderation/sweep_unban pins get_user then unban)
        assert applied[-2:] == [("fetch_user", 3),
                                ("unban", 3, "No reason provided")]

        out = asyncio.run(ops._apply_warn_effects(
            None, _ctx(_target_id=7, _escalation="timeout",
                       _warn_threshold=3, _timeout_minutes=10)))
        assert out.user_message == ("⏳ <@7> timed out for 10 minutes "
                                    "(3 warnings).")
        assert applied[-1] == ("timeout", 7, 10, "Reached 3 warnings")
    finally:
        service.reset_moderation_ports_for_tests()


def test_op_reversibility_rollup_and_kick_confirmation():
    from sb.domain.moderation.ops import KICK, register_ops
    from sb.kernel.workflow.registry import REGISTRY
    from sb.spec.refs import WorkflowRef

    register_ops()                    # REGISTRY stamps the derived rollup

    def rev(key: str) -> str:
        return REGISTRY.resolve(WorkflowRef(key)).reversibility

    # warn's effect leg declares its escalation compensator (ORDER 004
    # item 1) — the rollup derives compensatable, ban's class. Kick joined
    # the same class at the moderation parity flip (2026-07-11): its
    # compensator withdraws the false history row on a refused kick, and
    # the D-0029 typed-challenge ConfirmationSpec came OFF — the flip
    # review D-0029 itself scheduled resolved ORACLE-WINS (the shipped
    # !kick is no-confirm; goldens/moderation/sweep_kick pins the bytes).
    assert rev("moderation.warn") == "compensatable"
    assert rev("moderation.ban") == "compensatable"
    assert rev("moderation.kick") == "compensatable"
    assert KICK.confirmation is None                # oracle-wins, flip review
    assert rev("moderation.clearwarnings") == "reversible"


def test_logging_config_defaults_and_degrade():
    from sb.domain.server_logging.service import load_config

    _register_declarations()
    config = asyncio.run(load_config(1))
    assert config.enabled is False                  # OFF_UNTIL_OPT_IN
    assert config.routing == "combined"
    assert set(config.category_enabled) == {
        "messages", "members", "roles", "moderation", "channels",
        "server", "voice"}
    assert not any(config.category_enabled.values())


def test_moderation_fanout_routes_to_bound_channel(monkeypatch):
    from sb.domain.server_logging import service
    from sb.kernel.events_bus import EventBus
    from sb.kernel.interaction import egress

    service.reset_counters_for_tests()
    sent: list[tuple] = []

    class FakeEmitter:
        async def send(self, channel_id, content, *, guild_id):
            sent.append((channel_id, content.body, content.trust))
            return egress.EmitResult(sent=True, message_id=1)

    egress.install_channel_emitter(FakeEmitter())

    async def fake_config(guild_id):
        return service.LoggingConfig(
            enabled=True, category_enabled={"moderation": True})

    async def fake_bound(guild_id, name):
        # the flip carries the shipped binding names (mod_channel/…)
        return 555 if name == "mod_channel" else None

    monkeypatch.setattr(service, "load_config", fake_config)
    monkeypatch.setattr(service, "bound_channel", fake_bound)

    bus = EventBus()
    service.subscribe(bus)
    delivered = asyncio.run(bus.emit(
        "moderation.action_taken", guild_id=1, action="warn",
        target_id=2, actor_id=3, reason="spam"))
    # the shipped subscriber PAIR rides moderation.action_taken: the staff
    # mod-log feed delivers, the public-log twin pre-filters + counts
    # (default policy "none" ⇒ mod_public_skipped).
    assert delivered == 2
    assert sent and sent[0][0] == 555
    assert "warn" in sent[0][1]
    assert service.counters().get("sent_total") == 1
    assert service.counters().get("mod_public_skipped") == 1
    egress.reset_channel_emitter_for_tests()


def test_fanout_disabled_counts_skip(monkeypatch):
    from sb.domain.server_logging import service
    from sb.kernel.events_bus import EventBus

    service.reset_counters_for_tests()
    _register_declarations()          # defaults: disabled
    bus = EventBus()
    service.subscribe(bus)
    asyncio.run(bus.emit("moderation.action_taken", guild_id=1,
                         action="ban", target_id=2, actor_id=3, reason=""))
    assert service.counters().get("skipped_disabled") == 1


def test_band2_ai_task_claims():
    from sb.domain.moderation.ai_tasks import register_ai_tasks as reg_mod
    from sb.domain.server_logging.ai_tasks import register_ai_tasks as reg_log
    from sb.kernel.ai import tasks

    tasks.clear_tasks_for_tests()
    try:
        reg_mod()
        reg_log()
        assert tasks.get_task("moderation.assist") is not None
        assert tasks.get_task("logs.triage") is not None
    finally:
        tasks.clear_tasks_for_tests()


def test_qualified_name_and_group_field():
    from sb.spec.commands import CommandKind, CommandSpec

    spec = CommandSpec(name="status", kind=CommandKind.PREFIX, group="logging")
    assert spec.qualified_name == "logging status"
    bare = CommandSpec(name="warn", kind=CommandKind.PREFIX)
    assert bare.qualified_name == "warn"


# --- the logging flip (pending→ported) --------------------------------------------


def test_logging_flip_shipped_command_surface():
    """The shipped logging_cog surface: bare group → the panel; the five
    real subcommands; the D-0029-era enable/disable NEVER shipped (zero
    oracle hits, no sweep golden) and are retired at the flip."""
    import sb.manifest.server_logging as m
    from sb.spec.refs import PanelRef

    names = [c.qualified_name for c in m.MANIFEST.commands]
    assert names == ["logging", "logging status", "logging set",
                     "logging create", "logging routes", "logging test"]
    assert "logging enable" not in names and "logging disable" not in names
    group = m.MANIFEST.commands[0]
    assert isinstance(group.route, PanelRef)
    assert group.route.name == "logging.hub"


def test_logging_flip_route_table_and_bindings():
    """The shipped 11-slot route table (select_view._ROUTE_BINDING) in the
    shipped roots-first order, mirrored by the manifest BindingSpecs."""
    import sb.manifest.server_logging as m
    from sb.domain.server_logging import service

    assert service.ROUTES == (
        "mod", "events", "cleanup", "debug", "info", "warning", "error",
        "audit", "message_log", "member_log", "role_log")
    binding_names = [s.name for s in m.MANIFEST.settings
                     if type(s).__name__ == "BindingSpec"]
    assert sorted(binding_names) == sorted(service.ROUTE_BINDING.values())
    # the shipped usage byte (goldens/logging/sweep_logging_set pins it)
    from sb.domain.server_logging.handlers import SET_USAGE, _sorted_routes

    assert SET_USAGE.format(routes=_sorted_routes()) == (
        "Usage: `!logging set <audit|cleanup|debug|error|events|info|"
        "member_log|message_log|mod|role_log|warning>` — opens the channel "
        "selector for the requested log binding.")


def test_logging_counter_vocabulary_full_block():
    """The shipped 16-name counter vocabulary renders in FULL, zeros
    included, alphabetically (goldens/logging/sweep_logging_status)."""
    from sb.domain.server_logging import service

    service.reset_counters_for_tests()
    snap = service.counters()
    assert len(snap) == 16
    assert list(snap) == sorted(snap)
    assert set(snap) == set(service.COUNTER_NAMES)
    assert all(v == 0 for v in snap.values())


def test_logging_capture_counter_reconstruction():
    """The parity runner's CAPTURE_WORLD_COUNTERS trajectory: the values
    the goldens pin (1 at the curated case; 18/3 at the sweeps) — the
    derivation lives on the constant."""
    from sb.adapters.parity.runner import CAPTURE_WORLD_COUNTERS
    from sb.domain.server_logging import service

    assert CAPTURE_WORLD_COUNTERS["logging.enable_and_bind"] == {
        "skipped_disabled": 1}
    for case_id in ("sweep.logging", "sweep.logging_status",
                    "sweep.logging_test"):
        assert CAPTURE_WORLD_COUNTERS[case_id] == {
            "skipped_disabled": 18, "mod_public_skipped": 3}
    service.seed_counters_for_replay(
        CAPTURE_WORLD_COUNTERS["sweep.logging_status"])
    snap = service.counters()
    assert snap["skipped_disabled"] == 18
    assert snap["mod_public_skipped"] == 3
    assert snap["sent_total"] == 0
    service.reset_counters_for_tests()


def test_logging_public_log_prefilter():
    """The shipped disciplinary pre-filter: warn/timeout/kick/ban are
    counted skips under the default 'none' selector; unban/clearwarnings
    never reach the counter (skipped BEFORE any config read)."""
    from sb.domain.server_logging import service
    from sb.kernel.events_bus import EventBus

    service.reset_counters_for_tests()
    bus = EventBus()
    service.subscribe(bus)
    for action in ("warn", "ban", "kick", "unban", "clearwarnings"):
        asyncio.run(bus.emit("moderation.action_taken", guild_id=1,
                             action=action, target_id=2, actor_id=3,
                             reason=""))
    assert service.counters()["mod_public_skipped"] == 3
    service.reset_counters_for_tests()
