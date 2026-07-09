"""Boot the NEW bot in-process, gateway-free — the replay composition root.

Satisfies the SAME driving contract as the old-bot harness
(``parity/harness/boot.Harness``): ``await Harness.start()`` →
``send_command`` / ``invoke_slash`` / ``click`` → ``take_calls`` /
``take_events`` → ``await close()``. tools/run_golden_parity.py's
``_replay_binding`` binds THIS module.

Included (the behavior-relevant composition, mirroring what main() will do):
    preflight → owner/secret/AI-config installs → db.init (migrations, when
    a database is reachable) → live-manifest target index (the adapters'
    port) → manifest settings registration + read ports → panel runtime with
    the capture presenter → RC-21 capture emitter → ONE EventBus threaded
    into the workflow engine + dispatch trace, tapped for every KNOWN_EVENT
    → lifecycle RUNNING.

Deliberately skipped (ops, not behavior — the old harness's own deviations
ledger): health server, poll supervisor lanes, boot-gate legs (CI owns
recompile parity), gateway anything.

Determinism: ids + timestamps come from the imported harness's `World`
(parity/harness/world.py, reused verbatim — same guild/channel/persona ids,
same logical clock), and `time.time` is pinned to the logical clock exactly
like the old capture did.
"""

from __future__ import annotations

import importlib
import json
import os
import pkgutil
import time as _time_mod
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from parity.harness.fake_http import drain_dispatch_tasks
from parity.harness.world import DEFAULT_PERSONAS, World

from sb.adapters.parity.transport import (
    ParityChannelEmitter,
    ParityModerationActions,
    ParityPresenter,
    ParityResponder,
    ParityTransport,
)
from sb.kernel.interaction.request import Surface, TargetRef

__all__ = ["Harness", "HarnessBootError", "PREFIX"]

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

PREFIX = "!"

#: the same placeholder/env convention as the old harness (its boot.py):
#: config must parse without real credentials; the admin persona is the
#: platform owner so owner-gated surfaces are drivable.
_ENV_DEFAULTS = {
    "DISCORD_BOT_TOKEN_PRODUCTION": "PARITY_PLACEHOLDER_TOKEN",
    "DATABASE_URL": "postgresql://parity:parity@localhost:5432/parity_replay",
    "SB_DATA_PLANE": "test",
    "SB_TEST_DB_HOSTS": "localhost",
    "BOT_OWNER_USER_ID": str(DEFAULT_PERSONAS["admin"]["id"]),
}

_ADMIN_ROLE_ID = 800_000_000_000_000_201  # parity/harness/world.py's constant


class HarnessBootError(RuntimeError):
    """The harness could not boot the new bot (env problem, not a golden)."""


class _StubState:
    """Absorbs World.install()'s gateway feed (no discord.py here); the
    side effect we want is World's deterministic channel/id allocation."""

    def parse_ready(self, payload: dict[str, Any]) -> None:
        return None

    def parse_guild_create(self, payload: dict[str, Any]) -> None:
        return None


class _Perms(SimpleNamespace):
    pass


def _member_for(persona_key: str) -> SimpleNamespace:
    persona = DEFAULT_PERSONAS[persona_key]
    admin = bool(persona.get("admin"))
    return SimpleNamespace(
        id=persona["id"],
        name=persona["name"],
        guild_permissions=_Perms(
            administrator=admin, moderate_members=admin, manage_guild=admin),
        roles=[SimpleNamespace(id=_ADMIN_ROLE_ID)] if admin else [],
    )


class Harness:
    """A booted, gateway-free NEW bot plus its capture channels."""

    def __init__(self) -> None:
        self.bot: Any = None                      # contract slot (no discord bot)
        self.world: World | None = None
        self.http: ParityTransport | None = None  # the `.calls`/`.gaps` twin
        self.events: list[dict[str, Any]] = []
        self.db_ready: bool = False
        self._index: dict[tuple[str, Surface], TargetRef] = {}
        self._real_time: Any = None
        self._bus: Any = None

    # ------------------------------------------------------------------ boot

    @classmethod
    async def start(cls, *, require_db: bool = True) -> "Harness":
        self = cls()
        for key, value in _ENV_DEFAULTS.items():
            os.environ.setdefault(key, value)

        from sb.kernel.config import preflight

        try:
            cfg = preflight()
        except Exception as exc:  # noqa: BLE001 — env failure, not behavior
            raise HarnessBootError(f"preflight failed: {exc}") from exc

        from sb.kernel.ai import flags as ai_flags
        from sb.kernel.authority.owner import install_owner_config
        from sb.kernel.settings import install_secret_presence

        install_owner_config(cfg)
        install_secret_presence(cfg)
        ai_flags.install_ai_config(cfg)

        # --- the fake world (verbatim reuse: same ids, same clock) ----------
        world = World(SimpleNamespace(_connection=_StubState()))
        self.world = world
        world.install(DEFAULT_PERSONAS)
        self._real_time = _time_mod.time
        _time_mod.time = lambda: world.clock.now.timestamp()  # type: ignore[assignment]

        transport = ParityTransport(ids=world.ids, clock=world.clock)
        self.http = transport

        # --- database (the CI Postgres service; behavior is DB-backed) ------
        if require_db:
            from sb.kernel.db import pool as db_pool

            try:
                await db_pool.init(cfg)
                self.db_ready = True
            except Exception as exc:  # noqa: BLE001 — env failure, not behavior
                raise HarnessBootError(f"Postgres unavailable: {exc}") from exc

        # --- live manifests → dispatch index + settings registration --------
        manifests = _load_manifests()
        self._build_index(manifests)

        from sb.kernel.interaction.adapters import install_target_index
        from sb.kernel.settings import register_manifest_settings

        install_target_index(self._lookup)
        for manifest in manifests:
            try:
                register_manifest_settings(manifest)
            except ValueError as exc:
                if "already declared" not in str(exc):
                    raise         # second start in one process re-registers

        # Manifest-declared PanelSpecs must reach the K8 registry exactly
        # like the live root (sb/app/main.py step 8): most manifests only
        # CONSTRUCT their panels — without registration every PanelRef-routed
        # command (settings.hub, help.home, ...) dispatches into a
        # LookupError BUG envelope instead of a render.
        from sb.kernel.panels.registry import register_panel

        for manifest in manifests:
            for spec in getattr(manifest, "panels", ()) or ():
                register_panel(spec)
        if self.db_ready:
            from sb.domain.settings.service import (
                install_platform_state_store,
                install_read_ports,
            )

            install_read_ports()
            install_platform_state_store()

        # --- panel runtime + egress with the capture seams -------------------
        self._arm_capture_ports()

        # --- ONE bus, tapped for every catalogued event ----------------------
        from sb.kernel.events_bus import EventBus
        from sb.kernel.interaction import trace as trace_mod
        from sb.kernel.workflow import engine as workflow_engine
        from sb.spec.events import KNOWN_EVENTS

        bus = EventBus()
        self._bus = bus
        workflow_engine.install_bus(bus)
        trace_mod.install_trace_bus(bus)

        def _make_tap(event_name: str):
            async def _tap(**payload: Any) -> None:
                self.events.append({"event": event_name, "payload": payload})
            return _tap

        for event_name in sorted(KNOWN_EVENTS):
            bus.on(event_name, _make_tap(event_name))

        from sb.kernel import lifecycle

        lifecycle.set_phase(lifecycle.Phase.RUNNING, reason="parity harness boot")

        await drain_dispatch_tasks()
        transport.calls.clear()      # boot noise is not case output
        self.events.clear()
        return self

    # -------------------------------------------------------------- indexing

    def _build_index(self, manifests: list[Any]) -> None:
        for manifest in manifests:
            for cmd in getattr(manifest, "commands", ()) or ():
                name = str(getattr(cmd, "name", "") or "")
                if not name:
                    continue
                qualified = str(getattr(cmd, "qualified_name", "") or name)
                kind = str(getattr(cmd, "kind", "both") or "both")
                keys = [qualified] + [str(a) for a in (getattr(cmd, "aliases", ()) or ())]
                for key in keys:
                    if kind in ("slash", "both"):
                        self._index[(key, Surface.SLASH)] = TargetRef(key=key, spec=cmd)
                    if kind in ("prefix", "both"):
                        self._index[(key, Surface.PREFIX)] = TargetRef(key=key, spec=cmd)

    def _lookup(self, key: str, surface: Surface) -> TargetRef | None:
        return self._index.get((key, surface))

    def _arm_capture_ports(self) -> None:
        """(Re-)install the capture seams — also the post-reset re-arm."""
        from sb.domain.moderation.service import install_moderation_actions
        from sb.kernel.interaction.egress import install_channel_emitter
        from sb.kernel.interaction.resolve import install_panel_engine
        from sb.kernel.panels import engine as panel_engine

        assert self.http is not None
        assert self.world is not None
        install_panel_engine(panel_engine.open_panel)
        panel_engine.install_panel_presenter(ParityPresenter(self.http))
        install_channel_emitter(ParityChannelEmitter(self.http))
        # the moderation EFFECT legs' guild-action port — capture twin, same
        # obligation as the live root's adapter (else every moderation op
        # replays PARTIAL with a not-installed finding: a harness gap).
        install_moderation_actions(
            ParityModerationActions(self.http, self.world.clock))

    # ------------------------------------------------------- per-case resets

    def reset_case_state(self) -> None:
        """Reset cross-case in-memory state WITHOUT tearing down the
        composition (the runner calls this at each case head; the DB reset
        is the runner's own step)."""
        from sb.kernel.interaction import cooldown as cooldown_mod
        from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests
        from sb.kernel.panels import engine as panel_engine

        cooldown_mod.reset_for_tests()
        panel_engine.reset_panel_engine_for_tests()      # sessions + presenter
        reset_resolver_ports_for_tests()                 # seen ids + ports
        self._arm_capture_ports()                        # re-arm what we own

    # ------------------------------------------------------------------ drive

    async def send_command(self, content: str, *, persona: str = "member",
                           channel: str = "general",
                           mentions: tuple[int, ...] = ()) -> None:
        """A member message: prefix-command dispatch through the REAL
        pipeline, then the passive XP chat award (band 4 — the shipped
        listener awarded on EVERY human message, commands included; the
        captures carry its ``xp.awarded`` on command goldens, dispatch
        events first). The still-unported message-pipeline surfaces
        (counting/chain/fuzzy/NL) stay no-ops here, honestly diffed."""
        if self.world is None:
            raise RuntimeError("harness not started")
        self.world.clock.advance()
        message_id = self.world.ids.allocate()
        target_key = None
        rest: list[str] = []
        if content.startswith(PREFIX):
            tokens = content[len(PREFIX):].split()
            for n in range(min(3, len(tokens)), 0, -1):
                candidate = " ".join(tokens[:n])
                if self._lookup(candidate, Surface.PREFIX) is not None:
                    target_key, rest = candidate, tokens[n:]
                    break
            # unknown command: the old bot's typo re-dispatch is the fuzzy
            # adapter's surface — not driven until its band ports the corpus.
        member = _member_for(persona)
        channel_id = self.world.channels[channel]
        if target_key is not None:
            ctx = SimpleNamespace(
                command=SimpleNamespace(qualified_name=target_key),
                author=member,
                guild=SimpleNamespace(id=self.world.guild_id,
                                      owner_id=DEFAULT_PERSONAS["admin"]["id"]),
                channel=SimpleNamespace(id=channel_id),
                message=SimpleNamespace(id=message_id),
                kwargs={"argv": tuple(rest), "text": " ".join(rest)},
            )
            responder = ParityResponder(self.http, surface=Surface.PREFIX,
                                        channel_id=channel_id)
            from sb.kernel.interaction.adapters.prefix import dispatch_prefix

            await dispatch_prefix(ctx, responder=responder)
        if self.db_ready:
            # the DB-backed passive award (cooldown row + settings reads);
            # the db-free contract harness stays award-silent by design.
            from sb.domain.xp.service import handle_chat_message

            await handle_chat_message(int(member.id), self.world.guild_id,
                                      now=int(_time_mod.time()))
        await self._settle()

    async def invoke_slash(self, name: str,
                           options: list[dict[str, Any]] | None = None, *,
                           persona: str = "member",
                           channel: str = "general") -> None:
        if self.world is None:
            raise RuntimeError("harness not started")
        self.world.clock.advance()
        interaction_id = self.world.ids.allocate()
        member = _member_for(persona)
        channel_id = self.world.channels[channel]
        namespace = SimpleNamespace(
            **{str(o.get("name")): o.get("value") for o in (options or [])})
        interaction = SimpleNamespace(
            id=interaction_id,
            user=member,
            guild=SimpleNamespace(id=self.world.guild_id,
                                  owner_id=DEFAULT_PERSONAS["admin"]["id"]),
            channel_id=channel_id,
            command=SimpleNamespace(qualified_name=name),
            namespace=namespace,
        )
        responder = ParityResponder(self.http, surface=Surface.SLASH,
                                    channel_id=channel_id,
                                    interaction_id=interaction_id)
        from sb.kernel.interaction.adapters.slash import dispatch_interaction

        await dispatch_interaction(interaction, responder=responder)
        await self._settle()

    async def click(self, *, message_id: int, custom_id: str,
                    component_type: int = 2,
                    values: list[str] | None = None,
                    persona: str = "member", channel: str = "general") -> None:
        if self.world is None:
            raise RuntimeError("harness not started")
        self.world.clock.advance()
        interaction_id = self.world.ids.allocate()
        member = _member_for(persona)
        channel_id = self.world.channels[channel]
        data: dict[str, Any] = {"custom_id": custom_id,
                                "component_type": component_type}
        if values is not None:
            data["values"] = list(values)
        interaction = SimpleNamespace(
            id=interaction_id,
            user=member,
            guild=SimpleNamespace(id=self.world.guild_id,
                                  owner_id=DEFAULT_PERSONAS["admin"]["id"]),
            channel_id=channel_id,
            channel=SimpleNamespace(id=channel_id),
            message=SimpleNamespace(id=message_id),
            data=data,
        )
        responder = ParityResponder(self.http, surface=Surface.COMPONENT,
                                    channel_id=channel_id,
                                    interaction_id=interaction_id)
        from sb.kernel.interaction.adapters.component import dispatch_component

        await dispatch_component(interaction, responder=responder)
        await self._settle()

    async def _settle(self) -> None:
        """Wait out fire-and-forget tasks (bus fan-out) — same drain engine
        as the old harness, so attribution semantics match."""
        await drain_dispatch_tasks()

    # ---------------------------------------------------------------- output

    def take_calls(self) -> list[Any]:
        if self.http is None:
            raise RuntimeError("harness not started")
        calls = list(self.http.calls)
        self.http.calls.clear()
        return calls

    def take_events(self) -> list[dict[str, Any]]:
        events = list(self.events)
        self.events.clear()
        return events

    # ----------------------------------------------------------------- close

    async def close(self) -> None:
        if self._real_time is not None:
            _time_mod.time = self._real_time
            self._real_time = None
        if self.db_ready:
            try:
                from sb.kernel.db import pool as db_pool

                await db_pool.close()
            except Exception:  # noqa: BLE001 — close is best-effort
                pass
            self.db_ready = False
        # release the process-global seams we armed (same-process test hygiene)
        try:
            from sb.domain.moderation.service import reset_moderation_ports_for_tests
            from sb.kernel import lifecycle
            from sb.kernel.interaction import cooldown as cooldown_mod
            from sb.kernel.interaction.adapters import reset_adapter_ports_for_tests
            from sb.kernel.interaction.egress import reset_channel_emitter_for_tests
            from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests
            from sb.kernel.panels import engine as panel_engine

            reset_resolver_ports_for_tests()
            panel_engine.reset_panel_engine_for_tests()
            reset_adapter_ports_for_tests()
            reset_channel_emitter_for_tests()
            reset_moderation_ports_for_tests()
            cooldown_mod.reset_for_tests()
            lifecycle.reset_for_tests()
        except Exception:  # noqa: BLE001 — close is best-effort
            pass


def _load_manifests() -> list[Any]:
    """Import every sb.manifest module (declaring IS reserving) and return
    the MANIFEST objects — the live composition truth build_runtime's
    snapshot index projects structurally (its specs are projections; the
    harness dispatches on the REAL spec objects, PanelRef routes intact)."""
    import sb.manifest as manifest_pkg

    manifests: list[Any] = []
    for info in sorted(pkgutil.iter_modules(manifest_pkg.__path__),
                       key=lambda m: m.name):
        if info.ispkg or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"sb.manifest.{info.name}")
        manifest = getattr(module, "MANIFEST", None)
        if manifest is not None:
            manifests.append(manifest)
        for attr in getattr(module, "MANIFESTS", ()) or ():
            manifests.append(attr)
    return manifests


def committed_snapshot() -> dict[str, Any]:
    """The committed manifest snapshot (handy for callers wiring leg-B)."""
    return json.loads((_REPO_ROOT / "manifest.snapshot.json").read_text())
