"""Server-logging config + fan-out (band 2) — shipped semantics carried.

* CATEGORIES / routing modes verbatim (services/server_logging_config.py):
  `combined` sends every category to the events channel; `per_category`
  falls back to combined when a category channel is unset; an unknown
  routing token DEGRADES to combined (never disables routing).
* The fan-out engine subscribes to domain events on THE bus and routes
  operator-facing lines to the bound channels through RC-21's
  ChannelEmitter (TRUSTED copy — bot-authored). v1 subscribes the
  moderation feed (`moderation.action_taken`); category listeners for the
  gateway-event families (messages/members/roles/…) arm when their feeds
  port (the message/member pipelines are later bands).
* Process-local counters (the shipped `!logging status` counter block) —
  in-memory, reset per process, verbatim counter names where exercised.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

__all__ = [
    "CATEGORIES",
    "DEFAULT_CHANNEL_NAMES",
    "LoggingConfig",
    "counters",
    "load_config",
    "note",
    "reset_counters_for_tests",
    "subscribe",
]

# shipped verbatim (services/server_logging_config.py:53)
CATEGORY_MESSAGES = "messages"
CATEGORY_MEMBERS = "members"
CATEGORY_ROLES = "roles"
CATEGORY_MODERATION = "moderation"
CATEGORY_CHANNELS = "channels"
CATEGORY_SERVER = "server"
CATEGORY_VOICE = "voice"
CATEGORIES: tuple[str, ...] = (
    CATEGORY_MESSAGES, CATEGORY_MEMBERS, CATEGORY_ROLES, CATEGORY_MODERATION,
    CATEGORY_CHANNELS, CATEGORY_SERVER, CATEGORY_VOICE,
)

ROUTING_COMBINED = "combined"
ROUTING_PER_CATEGORY = "per_category"
VALID_ROUTING = (ROUTING_COMBINED, ROUTING_PER_CATEGORY)

#: the four shipped NON-KEY constants (channel-NAME defaults, not KV keys —
#: sb/domain/settings/keys.py NOTE) + the per-category log-channel names.
DEFAULT_CHANNEL_NAMES = {
    "mod": "bot-mod-log",
    "cleanup": "bot-cleanup-log",
    "events": "bot-event-log",
    "messages": "bot-message-log",
    "members": "bot-member-log",
    "roles": "bot-role-log",
}


@dataclass(frozen=True)
class LoggingConfig:
    enabled: bool = False
    auto_create_channels: bool = False
    routing: str = ROUTING_COMBINED
    category_enabled: dict = field(default_factory=dict)
    ignored_channels: tuple[int, ...] = ()
    ignored_users: tuple[int, ...] = ()

    @property
    def per_category(self) -> bool:
        return self.routing == ROUTING_PER_CATEGORY


def _as_bool(value: object, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("1", "true", "yes", "on"):
        return True
    if token in ("0", "false", "no", "off"):
        return False
    return fallback


def _as_id_tuple(value: object) -> tuple[int, ...]:
    out = []
    for token in str(value or "").replace(";", ",").split(","):
        token = token.strip().lstrip("<#@&").rstrip(">")
        if token.isdigit():
            out.append(int(token))
    return tuple(out)


_CATEGORY_KEY = {
    CATEGORY_MESSAGES: "messages_enabled",
    CATEGORY_MEMBERS: "members_enabled",
    CATEGORY_ROLES: "roles_enabled",
    CATEGORY_MODERATION: "moderation_enabled",
    CATEGORY_CHANNELS: "channels_enabled",
    CATEGORY_SERVER: "server_enabled",
    CATEGORY_VOICE: "voice_enabled",
}


async def load_config(guild_id: int) -> LoggingConfig:
    from sb.kernel.settings import resolve

    routing = str(await resolve(guild_id, "logging", "event_routing")
                  or ROUTING_COMBINED)
    if routing not in VALID_ROUTING:
        routing = ROUTING_COMBINED          # shipped: degrade, never disable
    category_enabled = {}
    for category, name in _CATEGORY_KEY.items():
        category_enabled[category] = _as_bool(
            await resolve(guild_id, "logging", name), False)
    return LoggingConfig(
        enabled=_as_bool(await resolve(guild_id, "logging", "enabled"), False),
        auto_create_channels=_as_bool(
            await resolve(guild_id, "logging", "auto_create_channels"), False),
        routing=routing,
        category_enabled=category_enabled,
        ignored_channels=_as_id_tuple(
            await resolve(guild_id, "logging", "ignored_channels")),
        ignored_users=_as_id_tuple(
            await resolve(guild_id, "logging", "ignored_users")),
    )


async def bound_channel(guild_id: int, name: str) -> int | None:
    """Binding-lane read (subsystem_bindings route-truth): mod / cleanup /
    events / per-category channel pointers."""
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "logging", name)
    except Exception:  # noqa: BLE001 — no DB (headless) reads as unbound
        return None


# --- process-local counters (shipped status block) --------------------------------

_counters: dict[str, int] = defaultdict(int)


def note(counter: str, delta: int = 1) -> None:
    _counters[counter] += delta


def counters() -> dict[str, int]:
    return dict(sorted(_counters.items()))


def reset_counters_for_tests() -> None:
    _counters.clear()


# --- the fan-out engine ------------------------------------------------------------

async def _route_moderation(**payload: object) -> None:
    """moderation.action_taken → the mod-log channel (shipped server_logging
    moderation fan-out; TRUSTED copy through the RC-21 emitter)."""
    from sb.kernel.interaction.egress import (
        OutboundContent,
        TrustLevel,
        active_channel_emitter,
    )

    guild_id = int(payload.get("guild_id", 0) or 0)
    config = await load_config(guild_id)
    if not config.enabled:
        note("skipped_disabled")
        return
    if not config.category_enabled.get(CATEGORY_MODERATION, False):
        note("event_skipped_disabled")
        return
    channel_id = await bound_channel(guild_id, "mod")
    if channel_id is None:
        note("missing_channel")
        return
    action = str(payload.get("action", ""))
    target = payload.get("target_id")
    actor = payload.get("actor_id")
    reason = str(payload.get("reason", "") or "")
    line = f"🛡️ **{action}** — target <@{target}> by <@{actor}>: {reason}"
    emitter = active_channel_emitter()
    result = await emitter.send(
        channel_id, OutboundContent(body=line, trust=TrustLevel.TRUSTED),
        guild_id=guild_id)
    note("sent_total" if result.sent else "send_error")


def subscribe(bus: object) -> None:
    """Arm the fan-out on THE bus (composition-root / harness obligation —
    the shipped `server_logging.setup(bot)` analog)."""
    bus.on("moderation.action_taken", _route_moderation)
