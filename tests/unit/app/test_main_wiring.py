"""The CUT-1 composition root (sb/app/main.py) — cheap wiring facts, no
network, no DB: the module is import-safe without runtime deps (guarded-
import discipline), the subscribe roster names real ``subscribe(bus)``
obligations, the escrow-recovery roster matches the domain constants, and
the drain step terminates on an emptied outbox."""

from __future__ import annotations

import asyncio
import importlib

from sb.app import main as app_main


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


class _RecordingBus:
    def __init__(self) -> None:
        self.subscriptions: list[str] = []

    def on(self, event_name: str, handler) -> None:
        self.subscriptions.append(event_name)


class TestSubscribeRoster:
    def test_every_roster_module_exposes_subscribe(self):
        for module_path in app_main.SUBSCRIBE_ROSTER:
            module = importlib.import_module(module_path)
            assert callable(getattr(module, "subscribe", None)), module_path

    def test_arm_subscribe_roster_arms_every_module(self):
        bus = _RecordingBus()
        armed = app_main.arm_subscribe_roster(bus)
        assert armed == app_main.SUBSCRIBE_ROSTER
        # every fan-out module that bus.on-subscribes did so on THIS bus
        # (role.service holds the bus by reference instead — no on() call).
        assert "xp.level_up" in bus.subscriptions
        assert "economy.balance_changed" in bus.subscriptions
        assert "moderation.action_taken" in bus.subscriptions


class TestModerationTestGuildGate:
    """The live moderation guild-action adapter (D-0049) is DOUBLE-GATED: the
    composition root arms it (main.py step 10a) ONLY under
    ``SB_DATA_PLANE == "test"`` AND an explicit ``SB_APPCMD_SYNC_GUILD_ID``,
    and hands that guild id to the adapter as a hard test-guild allow-list.
    Prod arming is the owner's CUT-3 gate — the prod root leaves the port
    un-installed (a live !ban/!kick writes its row + copy but performs NO
    Discord effect until the owner flips prod)."""

    def test_gate_returns_the_test_guild_only_on_the_test_plane(self):
        from types import SimpleNamespace

        # both gates satisfied → the test-guild id (armed)
        assert app_main.moderation_test_guild(SimpleNamespace(
            SB_DATA_PLANE="test", SB_APPCMD_SYNC_GUILD_ID=4242)) == 4242
        # prod plane → None (un-installed) even with a guild id
        assert app_main.moderation_test_guild(SimpleNamespace(
            SB_DATA_PLANE="prod", SB_APPCMD_SYNC_GUILD_ID=4242)) is None
        # test plane but NO guild id → None (no allow-list, so un-installed)
        assert app_main.moderation_test_guild(SimpleNamespace(
            SB_DATA_PLANE="test", SB_APPCMD_SYNC_GUILD_ID=None)) is None
        assert app_main.moderation_test_guild(SimpleNamespace()) is None

    def test_install_is_guarded_by_the_gate_and_passes_the_allow_list(self):
        # the wiring fact: the step-10a install block is reached ONLY when the
        # gate yields a test guild, and the adapter is constructed WITH that
        # guild id as its hard allow-list (a prod boot never arms it, and a
        # test-plane boot never mutates a non-allowed guild).
        import inspect

        src = inspect.getsource(app_main.run_app)
        assert "test_guild_id = moderation_test_guild(cfg)" in src
        assert "if test_guild_id is not None:" in src
        assert ("DiscordModerationActions(bot, allowed_guild_id=test_guild_id)"
                in src)


class TestRoleEffectPortsGate:
    """The live role EFFECT ports (SLICE 2 of the live-guild-effects lane) ride
    the SAME test-plane + test-guild gate as moderation (main.py step 10a): the
    three ports (add/remove role, create/delete role, reaction-role
    fetch_message/add_reaction) are armed ONLY inside the
    ``if test_guild_id is not None:`` block and each concrete adapter is
    constructed WITH that test guild id as its hard allow-list. Prod arming is
    the owner's CUT-3 gate — the prod root leaves all three ports un-installed."""

    def test_role_ports_install_only_under_the_test_guild_gate(self):
        import inspect

        src = inspect.getsource(app_main.run_app)
        # armed adjacent to moderation, under the SAME single gate
        assert "test_guild_id = moderation_test_guild(cfg)" in src
        # each of the three role ports installed with the allow-list guild id
        assert ("install_role_actions(\n"
                "                DiscordGuildRoleActions(bot, "
                "allowed_guild_id=test_guild_id))") in src
        assert ("install_role_provisioning(\n"
                "                DiscordRoleProvisioning(bot, "
                "allowed_guild_id=test_guild_id))") in src
        assert ("install_message_ops(\n"
                "                DiscordRoleMessageOps(bot, "
                "allowed_guild_id=test_guild_id))") in src
        # the guild-VIEW read seam is armed under the SAME gate — without it
        # service.guild_view returns None and the mutation ports above are
        # inert (every role-effect surface stays blocked before reaching them).
        assert ("install_guild_source(\n"
                "                DiscordGuildSource(bot, "
                "allowed_guild_id=test_guild_id))") in src

    def test_role_installs_sit_inside_the_gate_block(self):
        # the wiring fact: the role installs live BELOW the gate line and the
        # `if test_guild_id is not None:` guard — never at prod-reachable
        # top level of step 10.
        import inspect

        src = inspect.getsource(app_main.run_app)
        gate_at = src.index("if test_guild_id is not None:")
        for needle in ("install_role_actions(", "install_role_provisioning(",
                       "install_message_ops(", "install_guild_source("):
            assert src.index(needle) > gate_at, needle


class TestChannelEffectPortsGate:
    """The live channel EFFECT ports (SLICE 3 of the live-guild-effects lane,
    the final adapter slice) ride the SAME test-plane + test-guild gate as
    moderation + role (main.py step 10a). TWO SEPARATE ports: the channel
    domain's ChannelStateActions (+ the channel-name lookup) and proof_channel's
    OWN ChannelPermActions — all armed ONLY inside the
    ``if test_guild_id is not None:`` block, each concrete adapter constructed
    WITH that test guild id as its hard allow-list. Prod arming is the owner's
    CUT-3 gate — the prod root leaves every channel port un-installed."""

    def test_channel_ports_install_only_under_the_test_guild_gate(self):
        import inspect

        src = inspect.getsource(app_main.run_app)
        # armed adjacent to moderation + role, under the SAME single gate
        assert "test_guild_id = moderation_test_guild(cfg)" in src
        # the channel-state actions + the name lookup, each with the allow-list
        assert ("install_channel_actions(\n"
                "                DiscordChannelStateActions(bot, "
                "allowed_guild_id=test_guild_id))") in src
        assert ("install_channel_lookup(\n"
                "                DiscordChannelLookup(bot, "
                "allowed_guild_id=test_guild_id))") in src
        # proof_channel's OWN install_channel_actions (aliased to avoid the
        # name clash with the channel domain's) with the allow-list
        assert ("install_proof_channel_actions(\n"
                "                DiscordProofChannelActions(bot, "
                "allowed_guild_id=test_guild_id))") in src

    def test_channel_installs_sit_inside_the_gate_block(self):
        # the wiring fact: the channel installs live BELOW the gate line and the
        # `if test_guild_id is not None:` guard — never at prod-reachable top
        # level of step 10.
        import inspect

        src = inspect.getsource(app_main.run_app)
        gate_at = src.index("if test_guild_id is not None:")
        for needle in ("install_channel_actions(", "install_channel_lookup(",
                       "install_proof_channel_actions("):
            assert src.index(needle) > gate_at, needle


class TestEscrowRecoveryRoster:
    def test_roster_matches_the_domain_constants(self):
        from sb.domain.blackjack import ops as blackjack_ops
        from sb.domain.rps import ops as rps_ops

        assert blackjack_ops.PVP_ESCROW_SUBSYSTEM in app_main.ESCROW_RECOVERY_SUBSYSTEMS
        assert rps_ops.PVP_ESCROW_SUBSYSTEM in app_main.ESCROW_RECOVERY_SUBSYSTEMS


class TestSnapshot:
    def test_committed_snapshot_loads(self):
        snapshot = app_main.committed_snapshot()
        assert snapshot.get("stable_hash")
        assert snapshot.get("subsystems")


class TestDrainOutbox:
    def test_drain_returns_zero_when_ticks_empty_the_outbox(self, monkeypatch):
        from sb.kernel.db import pool

        pending = {"n": 2}

        async def fake_fetchone(query, params=(), *, conn=None):
            return dict(pending)

        class _Supervisor:
            def __init__(self) -> None:
                self.ticks = 0

            async def tick_once(self):
                self.ticks += 1
                pending["n"] = max(0, pending["n"] - 1)
                return []

        monkeypatch.setattr(pool, "fetchone", fake_fetchone)
        supervisor = _Supervisor()
        left = run(app_main._drain_outbox(supervisor, grace_s=5.0))
        assert left == 0
        assert supervisor.ticks == 2


class TestGatewayAdapter:
    def test_import_is_guarded(self):
        from sb.adapters.discord import gateway

        if gateway.DISCORD_AVAILABLE:
            assert callable(gateway.build_intents)
        else:
            import pytest

            with pytest.raises(RuntimeError):
                gateway.build_intents(object())


class TestManifestPanelRegistration:
    """The band-1 replay finding: PanelRef-routed commands dispatched into
    `LookupError: no PanelSpec registered` because neither composition root
    registered the manifest-DECLARED panels. `register_manifest_panels` is
    the shared obligation (main.py step 8; the parity harness mirrors it).

    Hermetic on purpose: importing the FULL manifest roster here (directly,
    or transitively via sb.manifest.help's all-manifest projection) would
    front-run the band tests' import-time registrations (rank providers
    reset + re-arm builtins-only mid-suite) — so the integration case uses
    the three band-1 manifests with no transitive roster import; the
    mechanics use synthetic manifests."""

    def _band1_manifests(self):
        return [importlib.import_module(f"sb.manifest.{k}").MANIFEST
                for k in ("settings", "diagnostic", "setup")]

    def test_band1_panelref_routes_resolve_after_registration(self):
        from sb.app.panel_host import register_manifest_panels
        from sb.kernel.panels import registry

        manifests = self._band1_manifests()
        count = register_manifest_panels(manifests)
        assert count == sum(len(m.panels) for m in manifests) and count >= 3
        # the band-1 PanelRef routes resolve (the replay's exact reds)
        for panel_id in ("settings.hub", "diagnostic.hub", "setup.hub"):
            assert registry.get_panel(panel_id).panel_id == panel_id
        # identical re-registration is a no-op, not a PanelCompileError
        assert register_manifest_panels(manifests) == count

    def test_counts_only_declared_panels(self):
        from types import SimpleNamespace

        from sb.app.panel_host import register_manifest_panels

        class _Spy:
            def __init__(self, panel_id: str) -> None:
                self.panel_id = panel_id

        import sb.kernel.panels.registry as reg

        seen: list[str] = []
        original = reg.register_panel
        reg.register_panel = lambda spec: seen.append(spec.panel_id)  # type: ignore[assignment]
        try:
            count = register_manifest_panels([
                SimpleNamespace(panels=(_Spy("a.hub"), _Spy("b.hub"))),
                SimpleNamespace(panels=()),
                SimpleNamespace(),                      # no panels attribute
            ])
        finally:
            reg.register_panel = original  # type: ignore[assignment]
        assert count == 2 and seen == ["a.hub", "b.hub"]


class TestLiveDispatchIndex:
    """The D-0028(2) follow-up: the snapshot projection (RuntimeIndex) is
    leg B's realization, NOT a dispatchable index — its specs are empty
    `_SnapshotSpec` projections (routes serialize as refs; the snapshot's
    `subsystems` mapping is not the list `_build` expects), so the live boot
    stranded every command in "no routable ref". Dispatch resolves on the
    LIVE manifest spec objects instead."""

    def _band1_manifests(self):
        return [importlib.import_module(f"sb.manifest.{k}").MANIFEST
                for k in ("settings", "diagnostic", "setup")]

    def test_live_index_carries_routable_specs(self):
        from sb.app.build_runtime import build_live_index
        from sb.kernel.interaction.request import Surface

        index = build_live_index(self._band1_manifests())
        for key in ("settings", "diagnostics", "setup"):
            for surface in (Surface.PREFIX, Surface.SLASH):
                ref = index.get((key, surface))
                assert ref is not None, (key, surface)
                route = getattr(ref.spec, "route", None)
                assert route is not None and getattr(route, "name", None), key

    def test_snapshot_index_specs_are_not_routable(self):
        # the honest statement of WHY the live index exists: the committed
        # snapshot's RuntimeIndex specs carry no route (leg B only).
        from sb.app.build_runtime import RuntimeIndex
        from sb.app.main import committed_snapshot
        from sb.kernel.interaction.request import Surface

        idx = RuntimeIndex(committed_snapshot())
        ref = idx.lookup("settings", Surface.PREFIX)
        assert ref is not None
        assert getattr(ref.spec, "route", None) is None

    def test_install_live_target_index_wins_the_port(self):
        from sb.app.build_runtime import install_live_target_index
        from sb.kernel.interaction import adapters as adapters_mod
        from sb.kernel.interaction.request import Surface

        count = install_live_target_index(self._band1_manifests())
        try:
            assert count >= 6
            ref = adapters_mod.lookup_target("setup", Surface.PREFIX)
            assert ref is not None
            assert getattr(ref.spec, "route", None) is not None
        finally:
            adapters_mod.reset_adapter_ports_for_tests()

    def test_grouped_command_aliases_are_group_scoped(self):
        # the shipped @group.command(aliases=[...]) semantics: an alias on
        # a grouped subcommand lives INSIDE the group — `!ticket open`
        # routes ticket.new; bare `!open`/`!create` are NOT top-level
        # routes (they'd shadow other subsystems' commands, e.g. the
        # channel op `!create`).
        from types import SimpleNamespace

        from sb.app.build_runtime import build_live_index
        from sb.kernel.interaction.request import Surface
        from sb.spec.commands import CommandKind, CommandSpec

        new = CommandSpec(name="new", kind=CommandKind.PREFIX,
                          group="ticket", aliases=("open", "create"),
                          route=object())
        index = build_live_index([SimpleNamespace(commands=(new,), panels=())])
        assert index[("ticket new", Surface.PREFIX)].spec is new
        assert index[("ticket open", Surface.PREFIX)].spec is new
        assert index[("ticket create", Surface.PREFIX)].spec is new
        assert ("open", Surface.PREFIX) not in index
        assert ("create", Surface.PREFIX) not in index

    def test_ungrouped_aliases_stay_top_level(self):
        from types import SimpleNamespace

        from sb.app.build_runtime import build_live_index
        from sb.kernel.interaction.request import Surface
        from sb.spec.commands import CommandKind, CommandSpec

        thanks = CommandSpec(name="thanks", kind=CommandKind.PREFIX,
                             aliases=("rep", "thank"), route=object())
        index = build_live_index([SimpleNamespace(commands=(thanks,),
                                                  panels=())])
        for key in ("thanks", "rep", "thank"):
            assert index[(key, Surface.PREFIX)].spec is thanks

    def test_parity_boot_shares_the_same_dispatch_keys(self):
        # the parity twin must dispatch on the SAME keys the live index
        # carries — both call sb.spec.commands.command_dispatch_keys.
        from sb.spec.commands import CommandKind, CommandSpec, command_dispatch_keys

        new = CommandSpec(name="new", kind=CommandKind.PREFIX,
                          group="ticket", aliases=("open", "create"),
                          route=object())
        assert command_dispatch_keys(new) == [
            "ticket new", "ticket open", "ticket create"]

    def test_component_custom_ids_indexed(self):
        from types import SimpleNamespace

        from sb.app.build_runtime import build_live_index
        from sb.kernel.interaction.request import Surface

        manifest = SimpleNamespace(
            commands=(),
            panels=(SimpleNamespace(
                panel_id="t.hub",
                actions=(SimpleNamespace(action_id="go",
                                         custom_id_override=None),),
                selectors=(SimpleNamespace(selector_id="pick",
                                           custom_id_override="t:pick"),),
            ),),
        )
        index = build_live_index([manifest])
        assert ("t.hub.go", Surface.COMPONENT) in index
        assert ("t:pick", Surface.COMPONENT) in index
