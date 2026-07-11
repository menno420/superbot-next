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
    ParityAvatarFetcher,
    ParityChannelEmitter,
    ParityHistoryReader,
    ParityLevelupHistoryScanner,
    ParityModerationActions,
    ParityPresenter,
    ParityResponder,
    ParityRoleMessageOps,
    ParityRoleProvisioning,
    ParityTransport,
)
from sb.kernel.interaction.request import Surface, TargetRef
from sb.spec.commands import command_dispatch_keys

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


class _WorldGuildDirectory:
    """The utility guild-directory port over the capture world — the same
    guild state the old harness's real ConnectionState held when the
    goldens were captured (parity/harness/world.py's GUILD_CREATE payload
    plus the shipped bot's own boot-time channel provisioning)."""

    #: world._guild_payload constants (verbatim).
    _GUILD_NAME = "Parity Test Guild"
    _PREMIUM_TIER = 0
    #: The shipped bot ensured its resource channels at boot (counting_cog
    #: / guild_resources.ensure_channel and friends fed discord.py's
    #: "temporarily add to the cache" path), so every capture-time guild
    #: read saw the 4 world channels PLUS 4 bot-created text channels —
    #: every Server Information golden pins "Text Channels: 8"
    #: (utility/sweep_serverinfo, _unmapped/sweep_info). The new bot's
    #: channel-provisioning bands are pending; until they port, the fixture
    #: carries the capture-time count.
    _SHIPPED_BOOT_TEXT_CHANNELS = 4
    _DISCORD_EPOCH_MS = 1_420_070_400_000

    def __init__(self, world: Any) -> None:
        self._world = world

    def _snowflake_time(self, snowflake: int):
        from datetime import datetime, timezone

        ms = (snowflake >> 22) + self._DISCORD_EPOCH_MS
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

    async def guild_info(self, guild_id: int):
        from sb.domain.utility.service import GuildInfo

        return GuildInfo(
            name=self._GUILD_NAME,
            owner_id=int(DEFAULT_PERSONAS["admin"]["id"]),
            member_count=len(DEFAULT_PERSONAS) + 1,      # personas + the bot
            premium_tier=self._PREMIUM_TIER,
            created_at=self._snowflake_time(int(guild_id or self._world.guild_id)),
            text_channels=(len(self._world.channels)
                           + self._SHIPPED_BOOT_TEXT_CHANNELS),
            voice_channels=0,
            # The capture guild's one bot member is the bot user itself
            # (world GUILD_CREATE: the 3 personas are humans) —
            # goldens/counters pins Members: 4 / Humans: 3 / Bots: 1.
            bots=1,
        )

    async def member_info(self, guild_id: int, user_id: int):
        from datetime import datetime, timezone

        from sb.domain.utility.service import MemberInfo

        del guild_id
        name = "GalaxyBotParity" if int(user_id) == World.BOT_USER_ID else next(
            (p["name"] for p in DEFAULT_PERSONAS.values()
             if int(p["id"]) == int(user_id)), f"User{user_id}")
        # avatar=None personas → discord.py's default avatar
        # ((id >> 22) % 6 — the display_avatar the capture recorded:
        # goldens/utility/sweep_avatar pins .../embed/avatars/1.png).
        index = (int(user_id) >> 22) % 6
        return MemberInfo(
            user_id=int(user_id),
            tag=f"{name}#0000",                    # str(member), world payloads
            display_avatar_url=(
                f"https://cdn.discordapp.com/embed/avatars/{index}.png"),
            created_at=self._snowflake_time(int(user_id)),
            joined_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )


class _WorldPerms(SimpleNamespace):
    """Duck guild_permissions — undeclared flags read False."""

    def __getattr__(self, name: str) -> bool:  # noqa: D105
        return False


class _WorldRole(SimpleNamespace):
    """Duck role over the capture world's GUILD_CREATE payload."""


class _WorldColor(SimpleNamespace):
    pass


def _build_world_guild(world: Any):
    """The role guild-view port's duck guild — the SAME guild state the
    old harness's real ConnectionState held at capture time
    (parity/harness/world.py `_guild_payload`: @everyone + the Admin role
    at position 1 with ADMINISTRATOR perms; members = the 3 personas +
    the bot member, the bot and the admin persona both carrying Admin —
    goldens/role/sweep_debugroles pins "Roles: @everyone, Admin",
    sweep_roleinfo pins Members: 2, sweep_deleterole pins the ABOVE_BOT
    hierarchy refusal against the bot's own top role)."""
    from datetime import datetime, timezone

    guild_id = int(world.guild_id)
    admin_role_id = _ADMIN_ROLE_ID

    everyone = _WorldRole(
        id=guild_id, name="@everyone", position=0,
        color=_WorldColor(value=0), hoist=False, mentionable=False,
        managed=False, permissions=_WorldPerms(administrator=False),
        members=(), guild=None)
    admin_role = _WorldRole(
        id=admin_role_id, name="Admin", position=1,
        color=_WorldColor(value=0), hoist=False, mentionable=False,
        managed=False, permissions=_WorldPerms(administrator=True,
                                               manage_roles=True),
        members=(), guild=None)

    def _member(persona_key: str) -> SimpleNamespace:
        persona = DEFAULT_PERSONAS[persona_key]
        return SimpleNamespace(
            id=persona["id"], name=persona["name"],
            display_name=persona["name"], bot=False,
            guild_permissions=_WorldPerms(
                administrator=bool(persona.get("admin")),
                manage_roles=bool(persona.get("admin"))),
            roles=((admin_role,) if persona.get("admin") else ()),
            top_role=(admin_role if persona.get("admin") else everyone),
            joined_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))

    members = tuple(_member(k) for k in DEFAULT_PERSONAS)
    bot_member = SimpleNamespace(
        id=World.BOT_USER_ID, name="GalaxyBotParity",
        display_name="GalaxyBotParity", bot=True,
        guild_permissions=_WorldPerms(administrator=True,
                                      manage_roles=True),
        roles=(admin_role,), top_role=admin_role,
        joined_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    # role.members mirrors the capture cache: admin persona + the bot
    admin_members = tuple(m for m in members
                          if any(r is admin_role for r in m.roles))
    admin_role.members = admin_members + (bot_member,)
    everyone.members = members + (bot_member,)

    guild = SimpleNamespace(
        id=guild_id, roles=(everyone, admin_role),
        members=members + (bot_member,), me=bot_member)
    everyone.guild = guild
    admin_role.guild = guild
    return guild


class Harness:
    """A booted, gateway-free NEW bot plus its capture channels."""

    def __init__(self) -> None:
        self.bot: Any = None                      # contract slot (no discord bot)
        self.world: World | None = None
        self.http: ParityTransport | None = None  # the `.calls`/`.gaps` twin
        self.events: list[dict[str, Any]] = []
        self.db_ready: bool = False
        #: CAPTURE-WORLD LEAKED CHANNELS (runner-seeded per case, cleared
        #: at every case head) — channels an alphabetically-earlier capture
        #: case created that discord.py's gateway cache carried across the
        #: per-case DB truncate (the trap-17 leak, READ-only here). Name →
        #: constant snowflake; the Normalizer knows neither, so the id
        #: renders as `<msg:N>` exactly like the golden's.
        self.leaked_channels: dict[str, int] = {}
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
        # the K0 AI-platform arm (mirrors sb/app/main.py step 2): the
        # policy-bundle/memory/preset readers — without them `!ai policy`
        # replays the not-armed fallback instead of the shipped
        # GUILD_NOT_CONFIGURED resolver trace the goldens pin.
        from sb.domain.ai.readers import install_ai_platform

        install_ai_platform()

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
        self._install_typo_corpus()
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

        # the server-logging fan-out rode the shipped harness for real
        # (parity/harness/boot.py: `server_logging.setup(bot)`), and its
        # process-local counters are golden-rendered state — arm the same
        # subscriber trio here. With the capture guild's logging disabled
        # it only counts skips (no sends, no events); the runner reseeds
        # the CAPTURE trajectory at each observing case
        # (runner.CAPTURE_WORLD_COUNTERS).
        from sb.domain.server_logging import service as _server_logging

        _server_logging.subscribe(bus)
        # the role audit/lifecycle fan-out is on the live root's
        # SUBSCRIBE_ROSTER (sb/app/main.py) — arm the same seam here so
        # the shipped role_lifecycle_service companions reach the tap
        # (goldens/role/sweep_createrole pins audit.action_recorded +
        # role.lifecycle_changed).
        from sb.domain.role import service as _role_service

        _role_service.subscribe(bus)

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
                kind = str(getattr(cmd, "kind", "both") or "both")
                # qualified name + GROUP-SCOPED aliases — the ONE key truth
                # the live index shares (sb/spec/commands.py
                # command_dispatch_keys; shipped @group.command semantics).
                keys = command_dispatch_keys(cmd)
                for key in keys:
                    if kind in ("slash", "both"):
                        self._index[(key, Surface.SLASH)] = TargetRef(key=key, spec=cmd)
                    if kind in ("prefix", "both"):
                        self._index[(key, Surface.PREFIX)] = TargetRef(key=key, spec=cmd)

    def _lookup(self, key: str, surface: Surface) -> TargetRef | None:
        return self._index.get((key, surface))

    def _install_typo_corpus(self) -> None:
        """Arm the shipped CommandNotFound typo ladder over this index —
        the mirror of build_runtime._install_prefix_typo_corpus (one code
        path per root; goldens/moderation/moderation_warn_flow step 2 pins
        the SUGGEST byte)."""
        from sb.kernel.interaction.adapters.fuzzy import install_prefix_typo_corpus
        from sb.spec.refs import PanelRef

        corpus = frozenset(key for (key, surface) in self._index
                           if surface is Surface.PREFIX and " " not in key)

        def _is_read(canonical: str) -> bool:
            target = self._index.get((canonical, Surface.PREFIX))
            route = getattr(getattr(target, "spec", None), "route", None)
            return isinstance(route, PanelRef)

        install_prefix_typo_corpus(lambda: (corpus, _is_read))

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
        if self.db_ready:
            # the shipped panel_anchors registry (channel-sent panels only)
            # — same wiring as the live root's install_panel_runtime.
            from sb.kernel.panels.anchors import record_anchor

            panel_engine.install_panel_anchor_store(record_anchor)
        install_channel_emitter(ParityChannelEmitter(self.http))
        # the moderation EFFECT legs' guild-action port — capture twin, same
        # obligation as the live root's adapter (else every moderation op
        # replays PARTIAL with a not-installed finding: a harness gap).
        install_moderation_actions(
            ParityModerationActions(self.http, self.world.clock))
        # the modmenu 🤖 Bot readiness read seam — the capture world's own
        # guild.me truth (parity/harness/world.py: the bot member carries
        # the "Admin" role, position 1 over @everyone, admin permissions),
        # exactly what evaluate_moderation_readiness saw at capture time
        # (goldens/moderation/sweep_modmenu pins the rendered line).
        from sb.domain.moderation.service import (
            ModerationReadiness,
            install_moderation_readiness,
        )

        async def _world_readiness(guild_id: int) -> ModerationReadiness:
            del guild_id
            return ModerationReadiness(
                can_ban=True, can_kick=True, can_timeout=True,
                top_role_name="Admin", top_role_is_lowest=False)

        install_moderation_readiness(_world_readiness)
        # the cleanup channel-history read port — the goldens' `logs_from`
        # wire verb (goldens/cleanup/sweep_cleanuphistory.json); without it
        # the scan degrades to the not-armed refusal: a harness gap, not
        # bot behavior.
        from sb.domain.cleanup.service import install_history_reader

        install_history_reader(ParityHistoryReader(self.http))
        # the rank-card avatar read port — the goldens' `get_from_cdn`
        # wire verb (goldens/xp/xp_chat_award.json, sweep_xpmenu.json);
        # without it the card renders avatar-less (the shipped
        # any-failure→None fallback) and the CDN read never records:
        # a harness gap, not bot behavior.
        from sb.domain.xp.service import (
            install_avatar_fetcher,
            install_channel_resolver,
            install_levelup_history_scanner,
        )

        install_avatar_fetcher(ParityAvatarFetcher(self.http))
        # the xp `!xpimport` channel-history read port — the goldens'
        # `logs_from` wire verb (goldens/xp/sweep_xpimport.json); without
        # it the scan degrades to the not-armed refusal: a harness gap,
        # not bot behavior (the cleanup history-reader posture).
        install_levelup_history_scanner(ParityLevelupHistoryScanner(self.http))
        # the `!xpimport` channel NAME lookup (TextChannelConverter's name
        # leg over the gateway guild cache) — the capture world's own
        # channels plus any runner-seeded leaked channel (trap 17 at
        # gateway-cache level, READ-only: goldens/xp/sweep_xpimport's
        # "test" was minted by the alphabetically-earlier sweep.create).
        world_channels = dict(self.world.channels)
        leaked = self.leaked_channels

        async def _world_channel_resolver(guild_id: int,
                                          name: str) -> int | None:
            del guild_id
            return world_channels.get(name) or leaked.get(name)

        install_channel_resolver(_world_channel_resolver)
        # the utility read ports: the capture-world guild directory + the
        # no-heartbeat gateway probe (the old harness's bot.latency was nan
        # — goldens/utility/sweep_ping pins "nan ms").
        from sb.domain.utility.service import (
            install_gateway_probe,
            install_guild_directory,
        )

        install_guild_directory(_WorldGuildDirectory(self.world))
        install_gateway_probe(lambda: float("nan"))
        # the role guild-view + effect ports — the capture world's own
        # gateway cache (goldens/role/sweep_debugroles, sweep_roleinfo,
        # sweep_assignroles, sweep_deleterole) plus the create-role and
        # fetch/react wire twins (sweep_createrole, sweep_reactroles).
        from sb.domain.role.service import (
            install_guild_source,
            install_message_ops,
            install_role_provisioning,
        )

        world_guild = _build_world_guild(self.world)

        async def _world_guild_source(guild_id: int):
            del guild_id
            return world_guild

        install_guild_source(_world_guild_source)
        install_role_provisioning(ParityRoleProvisioning(self.http))
        install_message_ops(ParityRoleMessageOps(self.http))
        # the AI operator-surface environment ports — capture-world twins
        # of the live root's installs (sb/adapters/discord/
        # ai_operator_ports.py): the support report's runtime lines are the
        # CAPTURE environment's (the corpus ran under python3.10.20 on the
        # Linux sandbox — goldens/ai/sweep_ai_support-report pins the
        # bytes), and the capture guild granted the bot every permission
        # (world payload app_permissions), so the readiness probe answers
        # "nothing missing".
        from sb.domain.ai.operator_cards import (
            RuntimeIdentity,
            install_channel_permission_probe,
            install_runtime_identity,
        )

        install_runtime_identity(RuntimeIdentity(
            python_version="3.10.20", system="Linux",
            bot_user_id=World.BOT_USER_ID))

        async def _all_perms(guild_id: int, channel_id: int,
                             scan_enabled: bool) -> list[str]:
            del guild_id, channel_id, scan_enabled
            return []

        install_channel_permission_probe(_all_perms)

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
        self.leaked_channels.clear()                     # per-case seed (runner)
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
        typo_reply: str | None = None
        if content.startswith(PREFIX):
            tokens = content[len(PREFIX):].split()
            for n in range(min(3, len(tokens)), 0, -1):
                candidate = " ".join(tokens[:n])
                if self._lookup(candidate, Surface.PREFIX) is not None:
                    target_key, rest = candidate, tokens[n:]
                    break
            else:
                # unknown command: the shipped bot1.py CommandNotFound
                # ladder's SUGGEST half (exact-synonym → edit-distance →
                # did-you-mean; goldens/moderation/moderation_warn_flow
                # step 2 pins `!warnings` → "Did you mean `!warn`?"). The
                # AUTO re-dispatch half stays a named successor — no
                # golden pins it.
                if tokens:
                    from sb.kernel.interaction.adapters.fuzzy import (
                        prefix_typo_reply,
                    )

                    typo_reply = prefix_typo_reply(tokens[0], prefix=PREFIX)
        member = _member_for(persona)
        channel_id = self.world.channels[channel]
        # the K10 chat-memory bystander record — the live feed's leg
        # (message_feed.observe_chat_message owns the shipped visibility
        # rules: command-shaped content is skipped inside), run BEFORE
        # dispatch exactly like arm_message_feed's on_message. The old
        # capture carried this state cross-case (its curated plain-chat
        # case seeded the buffer the ai_forget sweep then cleared).
        from sb.adapters.discord.message_feed import observe_chat_message
        from sb.domain.ai.review import observe_correction_reply

        inbound = SimpleNamespace(
            author=SimpleNamespace(id=member.id, bot=False,
                                   display_name=member.name),
            guild=SimpleNamespace(id=self.world.guild_id),
            channel=SimpleNamespace(id=channel_id),
            content=content, reference=None)
        observe_chat_message(inbound)
        # the review-loop correction observer — the live on_message twin
        # (corpus inputs carry no reply reference, so this is a fidelity
        # no-op, mirrored so both roots run one code path).
        await observe_correction_reply(inbound)
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
        elif typo_reply is not None:
            # the live twin sends this via message_feed's typo branch
            # (message.channel.send(copy, delete_after=15)); the capture
            # recorded the plain-content wire shape — delete_after is a
            # client-side timer fake_http never saw inside a case window.
            self.http.record_send(
                channel_id,
                {"components": [], "content": typo_reply, "tts": False})
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
        if self._lookup(name, Surface.SLASH) is None:
            # the old harness's exact semantics: an interaction naming an
            # app command the tree does not carry was DROPPED by
            # discord.py's ConnectionState (no response, no capture) —
            # every grouped `"ai forget"`-style sweep golden is empty for
            # exactly this reason. The live twin: an unregistered slash
            # command never reaches dispatch_interaction at all.
            return
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

    async def modal_submit(self, *, message_id: int, custom_id: str,
                           fields: dict[str, str],
                           persona: str = "member",
                           channel: str = "general") -> None:
        """One wire-type-5 MODAL SUBMIT through the real pipeline
        (``dispatch_modal`` — the seam the live component feed's armed
        modal lane drives; the ``click`` twin for G-10 forms). Driven by
        the walking-skeleton suites AND, since the D-0073 corpus-schema
        growth, by ``modal``-kind golden steps (goldens/btd6/
        btd6_strategy_form_*) — the D-0063 deletion clause's replay-case
        vocabulary."""
        if self.world is None:
            raise RuntimeError("harness not started")
        self.world.clock.advance()
        interaction_id = self.world.ids.allocate()
        member = _member_for(persona)
        channel_id = self.world.channels[channel]
        data: dict[str, Any] = {
            "custom_id": custom_id,
            "components": [
                {"components": [{"custom_id": key, "value": value}]}
                for key, value in fields.items()],
        }
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
        responder = ParityResponder(self.http, surface=Surface.MODAL,
                                    channel_id=channel_id,
                                    interaction_id=interaction_id)
        from sb.kernel.interaction.adapters.modal import dispatch_modal

        await dispatch_modal(interaction, responder=responder)
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
            from sb.domain.cleanup.service import reset_cleanup_ports_for_tests
            from sb.domain.moderation.service import reset_moderation_ports_for_tests
            from sb.domain.utility.service import reset_utility_ports_for_tests
            from sb.domain.xp.service import reset_xp_ports_for_tests
            from sb.kernel import lifecycle
            from sb.kernel.interaction import cooldown as cooldown_mod
            from sb.kernel.interaction.adapters import reset_adapter_ports_for_tests
            from sb.kernel.interaction.adapters.fuzzy import (
                reset_prefix_typo_corpus_for_tests,
            )
            from sb.kernel.interaction.egress import reset_channel_emitter_for_tests
            from sb.kernel.interaction.resolve import reset_resolver_ports_for_tests
            from sb.kernel.panels import engine as panel_engine

            reset_resolver_ports_for_tests()
            panel_engine.reset_panel_engine_for_tests()
            reset_adapter_ports_for_tests()
            reset_channel_emitter_for_tests()
            reset_prefix_typo_corpus_for_tests()
            reset_moderation_ports_for_tests()
            reset_utility_ports_for_tests()
            reset_cleanup_ports_for_tests()
            reset_xp_ports_for_tests()
            from sb.domain.role.service import reset_role_ports_for_tests

            reset_role_ports_for_tests()
            cooldown_mod.reset_for_tests()
            lifecycle.reset_for_tests()
            # the AI seams this harness armed (K0 platform + operator ports
            # + the process-lifetime conversation buffer).
            from sb.domain.ai.operator_cards import (
                reset_operator_ports_for_tests,
            )
            from sb.kernel.ai import conversation, memory, policy

            reset_operator_ports_for_tests()
            policy.reset_policy_for_tests()
            memory.reset_memory_ports_for_tests()
            conversation.reset_conversation_for_tests()
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
