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
    capability registration (none is armed in this root — the message-feed
    consumers are the ledgered live-adapter successors, report §4.2).
  - Boot-gate leg C runs COMPARE-ONLY (``sync_enabled=False`` +
    an explicit drift log): the local app-command tree is EMPTY until the
    app-command registration successor lands, and ``tree.sync()`` pushes
    the TREE, not the snapshot — syncing here would erase the remote tree
    instead of resolving REMOTE_LAG.
  - CUT-1 items deliberately NOT armed here: rotation schedule (owner flag
    10), prod-attest custody (flag 4), live-adapter ports/NL shell (§4.2).

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

__all__ = ["ESCROW_RECOVERY_SUBSYSTEMS", "SUBSCRIBE_ROSTER", "cli", "run_app"]

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

        # 7. build_runtime — the snapshot-realized dispatch index (leg B arm)
        #    + the LIVE manifest imports and their settings registration.
        from sb.app.build_runtime import build_runtime
        from sb.domain.settings.service import (
            install_platform_state_store,
            install_read_ports,
        )
        from sb.kernel.settings import register_manifest_settings

        runtime = build_runtime(committed)
        for manifest in load_live_manifests():
            try:
                register_manifest_settings(manifest)
            except ValueError as exc:
                if "already declared" not in str(exc):
                    raise
        install_read_ports()
        install_platform_state_store()

        # 8. panel runtime + THE one bus threaded into engine/trace.
        from sb.app.panel_host import install_panel_runtime
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

        # 11. lifecycle STARTING (explicit intent record) → gateway connect.
        lifecycle.set_phase(lifecycle.Phase.STARTING, reason="composition root boot")
        try:
            gateway_task = await gw.connect_gateway(
                bot, cfg.DISCORD_BOT_TOKEN_PRODUCTION)
        except gw.GatewayConnectError as exc:
            return _fail_startup("gateway_connect", [str(exc)])

        # 12. RUNNING — /ready flips 200 (gateway up + RUNNING + DB up).
        lifecycle.set_phase(lifecycle.Phase.RUNNING, reason="gateway ready")

        # 13. boot-gate leg C — compare-only in the test-mode root (module
        #     docstring): sync stays off until app-command registration
        #     populates the local tree; drift is logged, never fatal.
        from sb.app.tree_sync import sync_remote

        outcome = await sync_remote(bot, committed, enabled=False)
        try:
            from sb.app.boot_gate import snapshot_command_paths
            from sb.app.tree_sync import _remote_paths

            local = snapshot_command_paths(committed)
            remote = _remote_paths(await bot.tree.fetch_commands())
            logger.info(
                "leg C compare-only (%s): %d snapshot slash paths, %d remote, "
                "drift=%d (REMOTE_LAG expected until app-command registration)",
                outcome.reason, len(local), len(remote),
                len(local ^ remote))
        except Exception:  # noqa: BLE001 — leg C is non-fatal by contract
            logger.warning("leg C compare-only fetch failed (non-fatal)",
                           exc_info=True)

        # 14. intent-degrade markers BEFORE capability registration (spec 14
        #     §2.B): read the live set, latch the operator notice; the
        #     degraded message-band capability classes are simply never
        #     registered in this root.
        from sb.kernel.platform_governance import emit_degrade_notices

        markers = intent_degradations(cfg)
        for marker in markers:
            logger.info("intent DEGRADE: %s → %s not registered",
                        marker.intent, ", ".join(marker.degrades))
        emit_degrade_notices(markers)

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
