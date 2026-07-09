"""The composition root — CUT-1 test-mode ``main()`` (``python3 -m sb``).

Boot order (completion report §4.5, verbatim; panel_host docstring is the
same sequence): preflight → install_owner_config → install_secret_presence →
flags.install_ai_config → install_ai_platform() → boot-gate leg A → db.init
→ build_registry → start_health_server → build_runtime (LIVE manifests —
snapshot-index gap D-0028 stands) → error handlers → lifecycle STARTING →
gateway connect → RUNNING + boot-gate legs B/C → poll supervisor +
subscribe rosters + recover_escrow + intent-degrade markers before
capability registration.

Test-mode postures (this root boots container-only on the test-bot token):
  - AI stays DORMANT (``AI_ENABLED`` defaults false; the deterministic
    provider needs no key) — install_ai_platform() arms the readers only.
  - Privileged intents DEGRADE, never refuse: absent ``SB_INTENT_*_OK``
    yields DegradedCapability markers, read BEFORE any message-band
    capability registration. The ONE message-band consumer this root arms
    is the prefix-command feed (sb/adapters/discord/message_feed.py), and
    only when the ``prefix`` class is NOT degraded; fuzzy/passive-hook/NL
    feeds stay the ledgered successors (report §4.2).
  - The local app-command tree is populated from the LIVE manifests
    (sb/adapters/discord/command_tree.py). GLOBAL sync stays COMPARE-ONLY
    (``sync_enabled=False`` + an explicit drift log): the remote GLOBAL
    set is still the OLD bot's until CUT-3 and a global ``tree.sync()``
    would replace it. The safe leg is the GUILD-scoped sync to the test
    guild — armed only on ``SB_DATA_PLANE=test`` + the explicit
    ``SB_APPCMD_SYNC_GUILD_ID`` opt-in (never touches the global set).
  - CUT-1 items deliberately NOT armed here: rotation schedule (owner flag
    10), prod-attest custody (flag 4), NL shell/review-feed/role-proof-
    channel action ports (§4.2).

Shutdown: SIGTERM/SIGINT → request_shutdown → DRAINING (supervisor stops
claiming) → explicit outbox drain ticks → SHUTTING_DOWN → gateway closed,
supervisor + health server stopped, pool closed → STOPPED, exit 0.

``SB_VERIFY_BOOT=true`` delegates to the side-effect-free profile
(sb/app/verify_boot.py) — one entrypoint, both profiles, rails intact.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import uuid
from pathlib import Path

logger = logging.getLogger("sb.app.main")

__all__ = ["ESCROW_RECOVERY_SUBSYSTEMS", "SUBSCRIBE_ROSTER", "cli",
           "guild_sync_target", "run_app"]

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: How long the drain step keeps ticking the relay for undelivered rows.
DRAIN_GRACE_S = 10.0

#: The stranded-escrow stores recover_escrow sweeps at boot (the shipped
#: cog_load recovery): the two wager escrows that hold staked coins while a
#: PvP challenge awaits accept (blackjack/ops.py, rps/ops.py constants).
ESCROW_RECOVERY_SUBSYSTEMS: tuple[str, ...] = (
    "blackjack_pvp_escrow",
    "rps_pvp_escrow",
)

#: The band-2..band-5 fan-out roster: every domain module exposing the
#: ``subscribe(bus)`` composition-root obligation.
SUBSCRIBE_ROSTER: tuple[str, ...] = (
    "sb.domain.community.spotlight",
    "sb.domain.economy.service",
    "sb.domain.role.service",
    "sb.domain.server_logging.service",
    "sb.domain.xp.service",
)


def committed_snapshot() -> dict:
    """The committed manifest snapshot (boot-gate input, build_runtime input)."""
    return json.loads((_REPO_ROOT / "manifest.snapshot.json").read_text())


def load_live_manifests() -> list[object]:
    """Import every sb.manifest module (declaring IS reserving — the import
    also registers handlers/panels) and return the MANIFEST objects."""
    import importlib
    import pkgutil

    import sb.manifest as manifest_pkg

    manifests: list[object] = []
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda m: m.name):
        if info.ispkg or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"sb.manifest.{info.name}")
        manifest = getattr(module, "MANIFEST", None)
        if manifest is not None:
            manifests.append(manifest)
        manifests.extend(getattr(module, "MANIFESTS", ()) or ())
    return manifests


def guild_sync_target(cfg: object) -> int | None:
    """The guild id the app-command tree may GUILD-scope-sync to, or None.
    Two gates, both explicit: the test data plane AND the opt-in env
    (SB_APPCMD_SYNC_GUILD_ID) — the global command set is never synced by
    this root (it is still the OLD bot's until CUT-3)."""
    guild_id = getattr(cfg, "SB_APPCMD_SYNC_GUILD_ID", None)
    if not guild_id:
        return None
    if str(getattr(cfg, "SB_DATA_PLANE", "") or "") != "test":
        logger.warning("SB_APPCMD_SYNC_GUILD_ID set but SB_DATA_PLANE != test "
                       "— guild sync NOT armed")
        return None
    return int(guild_id)


def arm_subscribe_roster(bus: object) -> tuple[str, ...]:
    """Arm every domain ``subscribe(bus)`` on THE bus; returns what was armed."""
    import importlib

    armed: list[str] = []
    for module_path in SUBSCRIBE_ROSTER:
        module = importlib.import_module(module_path)
        module.subscribe(bus)
        armed.append(module_path)
    return tuple(armed)


async def _enqueue_boot_canary() -> str:
    """Enqueue ONE durable audit.action_recorded row for this boot — the
    kernel-smoke canary the relay must deliver (report §5 step 1). Rides
    ``enqueue_audit_action`` (the outbox durable twin); no audit_log row —
    that table's sole writer is the K7 engine."""
    import datetime as dt

    from sb.kernel import lifecycle
    from sb.kernel.db import pool
    from sb.kernel.outbox.enqueue import enqueue_audit_action

    mutation_id = str(uuid.uuid4())
    async with pool.transaction() as conn:
        await enqueue_audit_action(
            conn,
            mutation_id=mutation_id,
            subsystem="platform",
            mutation_type="boot_canary",
            target="sb.app.main",
            scope="global",
            guild_id=None,
            prev_value=None,
            new_value=lifecycle.get_phase().value,
            actor_id=None,
            actor_type="system",
            occurred_at=dt.datetime.now(tz=dt.timezone.utc),
        )
    return mutation_id


async def _drain_outbox(supervisor: object, *, grace_s: float = DRAIN_GRACE_S) -> int:
    """DRAINING step: the supervisor's ready-gate stops claiming once the
    phase leaves RUNNING, so drive bounded explicit ticks until no
    deliverable PENDING rows remain (or the grace window closes). Returns
    the rows still pending when the drain ended (0 = drained)."""
    from sb.kernel.db import pool

    loop = asyncio.get_running_loop()
    deadline = loop.time() + grace_s
    pending = -1
    while loop.time() < deadline:
        row = await pool.fetchone(
            "SELECT count(*) AS n FROM event_outbox "
            "WHERE status='pending' AND available_at <= now()")
        pending = int(row["n"]) if row else 0
        if pending == 0:
            return 0
        await supervisor.tick_once()
        await asyncio.sleep(0.2)
    return max(pending, 0)


def _fail_startup(reason: str, detail: list[str]) -> int:
    from sb.kernel import lifecycle

    lifecycle.set_phase(lifecycle.Phase.FAILED_STARTUP, reason=reason)
    logger.error("FAILED_STARTUP (%s): %s", reason, "; ".join(detail) or reason)
    return 1


async def run_app(env=None) -> int:  # noqa: PLR0911, PLR0915 — the boot script
    """The live boot. Returns the process exit code (0 = clean STOPPED)."""
    from sb.kernel.config import StartupError, intent_degradations, preflight

    # 1. preflight — coerce/validate ALL config; the data-plane + intent rails.
    try:
        cfg = preflight(env)
    except StartupError as exc:
        return _fail_startup("preflight", [str(e) for e in exc.errors])

    # SB_VERIFY_BOOT delegates to the side-effect-free profile (spec 13 §2.2).
    if getattr(cfg, "SB_VERIFY_BOOT", False):
        from sb.app.verify_boot import run_verify_boot

        report = await run_verify_boot(env)
        print(json.dumps(report, indent=2, default=str))
        return 0 if report.get("verified") else 1

    # 2. the K0 installs (owner identity, secret presence, AI config+platform).
    from sb.domain.ai.readers import install_ai_platform
    from sb.kernel.ai import flags as ai_flags
    from sb.kernel.authority.owner import install_owner_config
    from sb.kernel.settings import install_secret_presence

    install_owner_config(cfg)
    install_secret_presence(cfg)
    ai_flags.install_ai_config(cfg)
    install_ai_platform()

    # 3. boot-gate leg A — recompile parity against the committed snapshot.
    from sb.app.boot_gate import gate_recompile, run_boot_gate

    committed = committed_snapshot()
    violations = gate_recompile(committed)
    if violations:
        return _fail_startup("boot_gate_leg_a", [str(v) for v in violations])

    # 4. db.init — pool + migrations + verify_applied_checksums.
    from sb.kernel.db import pool

    try:
        await pool.init(cfg)
    except Exception as exc:  # noqa: BLE001 — DBUnavailable/MigrationDrift
        return _fail_startup("db_init", [str(exc)])

    from sb.kernel import lifecycle
    from sb.kernel.observability.metrics import build_registry

    health_task: asyncio.Task | None = None
    supervisor_task: asyncio.Task | None = None
    gateway_task: asyncio.Task | None = None
    bot = None
    try:
        # 5. metrics registry (the /metrics families, lifecycle mirrors).
        build_registry()

        # 6. health server — /ready serves gateway_not_ready until connect.
        from sb.adapters.http.health import start_health_server

        bot_ref: dict[str, object] = {}

        def _gateway_ready() -> bool:
            b = bot_ref.get("bot")
            return bool(b is not None and b.is_ready())

        bind_ok = asyncio.Event()
        health_task = asyncio.create_task(
            start_health_server(cfg, gateway_ready=_gateway_ready,
                                ready_event=bind_ok),
            name="sb-health")
        done, _ = await asyncio.wait({health_task,
                                      asyncio.create_task(bind_ok.wait())},
                                     timeout=10.0,
                                     return_when=asyncio.FIRST_COMPLETED)
        if health_task in done or not bind_ok.is_set():
            exc = health_task.exception() if health_task.done() else None
            detail = repr(exc) if exc is not None else "bind timeout"
            return _fail_startup("health_bind", [detail])

        # 7. build_runtime — the snapshot realization ARMS leg B; DISPATCH
        #    resolves on the LIVE manifest spec objects (routes intact) via
        #    install_live_target_index, installed after it so the live
        #    lookup wins the port (the D-0028(2) follow-up: dispatching on
        #    the snapshot projection strands every command in a
        #    "no routable ref" user_error — band-1 live-exercise finding).
        from sb.app.build_runtime import build_runtime, install_live_target_index
        from sb.domain.settings.service import (
            install_platform_state_store,
            install_read_ports,
        )
        from sb.kernel.settings import register_manifest_settings

        runtime = build_runtime(committed)
        manifests = load_live_manifests()
        index_size = install_live_target_index(manifests)
        logger.info("live dispatch index installed: %d target(s)", index_size)
        for manifest in manifests:
            try:
                register_manifest_settings(manifest)
            except ValueError as exc:
                if "already declared" not in str(exc):
                    raise
        install_read_ports()
        install_platform_state_store()

        # 8. panel runtime + THE one bus threaded into engine/trace. The
        #    manifest-declared PanelSpecs register FIRST (a PanelRef-routed
        #    command dispatching against an empty registry is a LookupError
        #    → BUG envelope — the band-1 replay found exactly that).
        from sb.app.panel_host import install_panel_runtime, register_manifest_panels

        panel_count = register_manifest_panels(manifests)
        logger.info("panel registry armed: %d manifest-declared panel(s)",
                    panel_count)
        from sb.kernel.events_bus import EventBus
        from sb.kernel.interaction import trace as trace_mod
        from sb.kernel.workflow import engine as workflow_engine

        install_panel_runtime()
        bus = EventBus()
        workflow_engine.install_bus(bus)
        trace_mod.install_trace_bus(bus)

        # 9. boot-gate leg B — snapshot vs built runtime, FAILED_STARTUP
        #    BEFORE gateway connect (spec 01 §3.3).
        report = await run_boot_gate(committed, runtime=runtime)
        if not (report.recompile_ok and report.build_ok):
            return _fail_startup("boot_gate_leg_b",
                                 [str(v) for v in report.violations])

        # 9b. the plugin host — installed out-of-tree game plugins join the
        #     SAME live seams (docs/game-plugin-contract.md): entry-point
        #     discovery, committed-pin verify (the plugin twin of leg A),
        #     one joint compile over host+plugins, THEN the union re-installs
        #     the live dispatch index and registers plugin settings/panels.
        #     Deliberately AFTER legs A/B: both hash the in-tree corpus, and
        #     a plugin import before the recompile would leak its refs into
        #     the snapshot's refs projection and red a green tree.
        from sb.app.plugin_host import load_plugins

        plugin_report = load_plugins(manifests)
        for dist_name in plugin_report.skipped:
            logger.warning("plugin pinned but not installed — skipped: %s",
                           dist_name)
        if plugin_report.violations:
            return _fail_startup("plugin_gate",
                                 list(plugin_report.violations))
        if plugin_report.manifests:
            manifests = list(manifests) + list(plugin_report.manifests)
            index_size = install_live_target_index(manifests)
            for manifest in plugin_report.manifests:
                try:
                    register_manifest_settings(manifest)
                except ValueError as exc:
                    if "already declared" not in str(exc):
                        raise
            plugin_panels = register_manifest_panels(
                list(plugin_report.manifests))
            logger.info(
                "plugin host: %d plugin(s) admitted (%s) — live index "
                "re-installed: %d target(s), +%d plugin panel(s)",
                len(plugin_report.loaded), "; ".join(plugin_report.loaded),
                index_size, plugin_panels)

        # 10. the gateway client + the K8 error shims + the live emitter.
        from sb.adapters.discord import gateway as gw

        if not gw.DISCORD_AVAILABLE:
            return _fail_startup("gateway", ["discord.py is not installed"])
        bot = gw.build_bot(cfg)
        bot_ref["bot"] = bot

        from sb.adapters.discord.egress import DiscordChannelEmitter
        from sb.app.error_handlers import register_error_handlers
        from sb.kernel.interaction.egress import install_channel_emitter

        register_error_handlers(bot)
        install_channel_emitter(DiscordChannelEmitter(bot))

        # 10b. the local app-command tree, from the SAME live manifests
        #      dispatch resolves on (D-0050) — populated before connect;
        #      whether anything syncs is step 13's gated decision.
        from sb.adapters.discord import command_tree

        tree_count = command_tree.register_app_commands(bot, manifests)
        logger.info("app-command tree built: %d slash command(s) "
                    "from the live manifests", tree_count)

        # 10c. the component feed — buttons/selects re-enter the kernel
        #      spine (custom_id → dispatch_component → resolve()/panel
        #      engine), the interaction-band twin of step 14b's message
        #      feed. No intent gate: components ride the interaction band
        #      (spec 14 §2.B degrades message-band classes only). Without
        #      this listener every nav:*/panel/confirm click dies in the
        #      view's no-op default (owner-feedback triage, 2026-07-09).
        from sb.adapters.discord.component_feed import arm_component_feed

        arm_component_feed(bot)
        logger.info("component feed armed: button/select dispatch "
                    "(custom_id → resolve(); modal submits stay dormant)")

        # 11. lifecycle STARTING (explicit intent record) → gateway connect.
        lifecycle.set_phase(lifecycle.Phase.STARTING, reason="composition root boot")
        try:
            gateway_task = await gw.connect_gateway(
                bot, cfg.DISCORD_BOT_TOKEN_PRODUCTION)
        except gw.GatewayConnectError as exc:
            return _fail_startup("gateway_connect", [str(exc)])

        # 12. RUNNING — /ready flips 200 (gateway up + RUNNING + DB up).
        lifecycle.set_phase(lifecycle.Phase.RUNNING, reason="gateway ready")

        # 13. boot-gate leg C — GLOBAL sync stays compare-only in the
        #     test-mode root (module docstring): the remote GLOBAL set is
        #     the OLD bot's until CUT-3; drift is logged, never fatal.
        from sb.app.tree_sync import sync_remote

        outcome = await sync_remote(bot, committed, enabled=False)
        try:
            from sb.app.boot_gate import snapshot_command_paths
            from sb.app.tree_sync import _remote_paths

            local = snapshot_command_paths(committed)
            remote = _remote_paths(await bot.tree.fetch_commands())
            logger.info(
                "leg C compare-only (%s): %d snapshot slash paths, "
                "%d local tree, %d remote GLOBAL, global drift=%d "
                "(REMOTE_LAG stands until the CUT-3 global sync)",
                outcome.reason, len(local), tree_count, len(remote),
                len(local ^ remote))
        except Exception:  # noqa: BLE001 — leg C is non-fatal by contract
            logger.warning("leg C compare-only fetch failed (non-fatal)",
                           exc_info=True)

        # 13b. the SAFE sync leg: GUILD-scoped, test plane + explicit
        #      opt-in only (guild_sync_target) — writes the test guild's
        #      command scope, never the global set. Non-fatal like leg C.
        sync_guild_id = guild_sync_target(cfg)
        if sync_guild_id is not None:
            try:
                synced = await command_tree.sync_guild_commands(
                    bot, sync_guild_id)
                logger.info("guild app-command sync: %d command(s) → guild "
                            "%d: %s", len(synced), sync_guild_id,
                            ", ".join(synced))
            except Exception:  # noqa: BLE001 — opt-in test leg, never fatal
                logger.warning("guild app-command sync failed (non-fatal)",
                               exc_info=True)

        # 14. intent-degrade markers BEFORE capability registration (spec 14
        #     §2.B): read the live set, latch the operator notice; a
        #     degraded message-band capability class is simply never
        #     registered in this root.
        from sb.kernel.platform_governance import emit_degrade_notices

        markers = intent_degradations(cfg)
        for marker in markers:
            logger.info("intent DEGRADE: %s → %s not registered",
                        marker.intent, ", ".join(marker.degrades))
        emit_degrade_notices(markers)

        # 14b. the message feed — prefix-command dispatch + the passive XP
        #      chat award (band 4, D-0061; report §4.2's other feeds stay
        #      dormant successors). Registered AFTER the markers per spec
        #      14 §2.B: a degraded ``prefix`` class means no registration.
        degraded_classes = {cls for m in markers for cls in m.degrades}
        if "prefix" in degraded_classes:
            logger.info("message feed NOT armed: prefix class degraded "
                        "(message_content unapproved)")
        else:
            from sb.adapters.discord.message_feed import arm_message_feed

            arm_message_feed(bot, prefix=str(cfg.BOT_PREFIX or "!"))
            logger.info("message feed armed: prefix dispatch on %r "
                        "+ passive XP chat award (bot/self messages "
                        "ignored; fuzzy/NL/counting/chain feeds stay "
                        "dormant)", str(cfg.BOT_PREFIX or "!"))

        # 15. the ONE PollSupervisor (outbox relay/reaper + durability lanes).
        from sb.app.poll_host import build_poll_supervisor

        supervisor = build_poll_supervisor(bus=bus)
        supervisor_task = asyncio.create_task(
            supervisor.run_forever(poll_interval_s=5), name="sb-poll")

        # 16. subscribe rosters + escrow recovery + the boot canary.
        armed = arm_subscribe_roster(bus)
        logger.info("bus rosters armed: %s", ", ".join(armed))

        canary_delivered = asyncio.Event()

        async def _canary_tap(**payload: object) -> None:
            if payload.get("mutation_type") == "boot_canary":
                logger.info("audit canary delivered: mutation_id=%s",
                            payload.get("mutation_id"))
                canary_delivered.set()

        bus.on("audit.action_recorded", _canary_tap)

        from sb.domain.games.service import recover_escrow

        for subsystem in ESCROW_RECOVERY_SUBSYSTEMS:
            refunded = await recover_escrow(subsystem,
                                            reason="boot:recover_escrow")
            if refunded:
                logger.info("recover_escrow(%s): refunded %d stranded row(s)",
                            subsystem, refunded)

        canary_id = await _enqueue_boot_canary()
        logger.info("boot complete: RUNNING (canary enqueued %s)", canary_id)

        # 17. serve until a shutdown request or gateway death.
        stop = asyncio.Event()

        def _on_signal(signame: str) -> None:
            lifecycle.request_shutdown(f"signal:{signame}", actor="signal")
            stop.set()

        loop = asyncio.get_running_loop()
        for signame in ("SIGTERM", "SIGINT"):
            loop.add_signal_handler(getattr(signal, signame),
                                    _on_signal, signame)

        stop_task = asyncio.create_task(stop.wait(), name="sb-stop")
        done, _ = await asyncio.wait({stop_task, gateway_task},
                                     return_when=asyncio.FIRST_COMPLETED)
        for signame in ("SIGTERM", "SIGINT"):
            loop.remove_signal_handler(getattr(signal, signame))
        gateway_died = gateway_task in done
        if gateway_died:
            exc = gateway_task.exception()
            logger.error("gateway task ended while RUNNING: %r", exc)
            lifecycle.request_shutdown("gateway task ended", actor="gateway")
        stop_task.cancel()

        # 18. drain → close (DRAINING was set by request_shutdown).
        pending = lifecycle.get_pending()
        if pending is not None:
            lifecycle.record_close_executing(pending)
        started = asyncio.get_running_loop().time()
        left = await _drain_outbox(supervisor)
        if left:
            logger.warning("outbox drain window closed with %d pending row(s)",
                           left)
        lifecycle.set_phase(lifecycle.Phase.SHUTTING_DOWN,
                            reason=(pending.reason if pending else "shutdown"))
        if pending is not None:
            lifecycle.record_close_completed(
                pending,
                duration_seconds=asyncio.get_running_loop().time() - started)
        return 1 if gateway_died else 0
    finally:
        for task in (supervisor_task, health_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        if bot is not None:
            try:
                await bot.close()
            except Exception:  # noqa: BLE001 — close is best-effort
                pass
        if gateway_task is not None:
            try:
                await gateway_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        try:
            await pool.close()
        except Exception:  # noqa: BLE001 — close is best-effort
            pass
        if lifecycle.get_phase() is not lifecycle.Phase.FAILED_STARTUP:
            lifecycle.set_phase(lifecycle.Phase.STOPPED, reason="process exit")
            logger.info("lifecycle STOPPED — clean exit")


def cli() -> int:
    """`python3 -m sb` / `python3 -m sb.app.main` — the process entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return asyncio.run(run_app())


if __name__ == "__main__":
    sys.exit(cli())
