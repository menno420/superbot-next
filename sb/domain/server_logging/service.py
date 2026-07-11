"""Server-logging config + fan-out (band 2) — shipped semantics carried.

* CATEGORIES / routing modes verbatim (services/server_logging_config.py):
  `combined` sends every category to the events channel; `per_category`
  falls back to combined when a category channel is unset; an unknown
  routing token DEGRADES to combined (never disables routing).
* ROUTES: the shipped 11-slot route table (disbot cogs/logging/
  select_view.py `_ROUTE_BINDING` @58040c6) in the shipped roots-first
  display order (cogs/logging/routes_panel.py — the two fallback roots
  lead). Severity/audit routes fall back to `mod`; event routes fall back
  to `events` (the shipped fallback chain, pinned in the routes panel
  footer byte — goldens/logging/sweep_logging_routes).
* The fan-out engine subscribes THE bus exactly like the shipped
  ``server_logging.setup(bot)`` did (disbot services/server_logging.py):
  `moderation.action_taken` twice (the staff mod-log feed + the PUBLIC
  moderation log with its disciplinary pre-filter) and
  `audit.action_recorded` (the generic audit feed). Routing goes to the
  bound channels through RC-21's ChannelEmitter (TRUSTED copy —
  bot-authored). Category listeners for the gateway-event families
  (messages/members/roles/…) arm when their feeds port (later bands).
* Process-local counters: the shipped 16-name vocabulary VERBATIM
  (services/server_logging.py `_COUNTERS`; goldens/logging/
  sweep_logging_status pins the full block, zeros included) — in-memory,
  process-lifetime, reset only by restart. In the PARITY world the replay
  runner reconstructs the CAPTURE process's counter state per case
  (sb/adapters/parity/runner.py CAPTURE_WORLD_COUNTERS — the capture's
  own case ordering is not reproducible from the replay ordering, so the
  trajectory is seeded world state, the CAPTURE_WORLD_SETTINGS sibling).
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "CATEGORIES",
    "COUNTER_NAMES",
    "DEFAULT_CHANNEL_NAMES",
    "DISCIPLINARY_ACTIONS",
    "LoggingConfig",
    "ROUTES",
    "ROUTE_BINDING",
    "ROUTE_FALLBACK",
    "bound_channel",
    "counters",
    "load_config",
    "note",
    "reset_counters_for_tests",
    "resolve_route_channel",
    "route_label",
    "seed_counters_for_replay",
    "send_test_event",
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

#: The shipped route table — route kind -> binding name (disbot
#: cogs/logging/select_view.py / provision_view.py `_ROUTE_BINDING`), in the
#: shipped ROOTS-FIRST display order (routes_panel.py: the two fallback
#: roots lead; goldens/logging/sweep_logging_routes pins the order).
ROUTE_BINDING: dict[str, str] = {
    "mod": "mod_channel",
    "events": "events_channel",
    "cleanup": "cleanup_channel",
    "debug": "debug_channel",
    "info": "info_channel",
    "warning": "warning_channel",
    "error": "error_channel",
    "audit": "audit_channel",
    "message_log": "message_channel",
    "member_log": "member_channel",
    "role_log": "role_channel",
}
ROUTES: tuple[str, ...] = tuple(ROUTE_BINDING)

#: The shipped fallback chain (routes panel footer byte: "severity/audit →
#: mod; event routes → events"). Roots fall back to nothing.
ROUTE_FALLBACK: dict[str, str] = {
    "cleanup": "mod",
    "debug": "mod",
    "info": "mod",
    "warning": "mod",
    "error": "mod",
    "audit": "mod",
    "message_log": "events",
    "member_log": "events",
    "role_log": "events",
}

#: Human labels (select_view._label_for) — "moderation log" is pinned by the
#: golden channel-select placeholder; the rest keep the shipped derived
#: "<kind> log" fallback shape.
_ROUTE_LABELS: dict[str, str] = {
    "mod": "moderation log",
    "cleanup": "cleanup log",
    "events": "event log",
    "message_log": "message log",
    "member_log": "member log",
    "role_log": "role log",
}


def route_label(kind: str) -> str:
    """Human label for *kind* — total, never raises (the shipped
    ``_label_for`` posture: explicit labels, derived fallback)."""
    return _ROUTE_LABELS.get(kind, f"{kind.replace('_', ' ')} log")


#: the four shipped NON-KEY constants (channel-NAME defaults, not KV keys —
#: sb/domain/settings/keys.py NOTE) + the per-category log-channel names
#: (disbot utils/settings_keys/logging.py DEFAULT_*_CHANNEL_NAME).
DEFAULT_CHANNEL_NAMES = {
    "mod": "bot-mod-log",
    "cleanup": "bot-cleanup-log",
    "events": "bot-event-log",
    "message_log": "bot-message-log",
    "member_log": "bot-member-log",
    "role_log": "bot-role-log",
}

#: The shipped public-log disciplinary pre-filter (services/
#: server_logging.py: "Only disciplinary actions can ever surface on the
#: public log"; moderation_config.public_log_includes doc: "Only the
#: disciplinary actions warn / timeout / kick / ban are ever eligible;
#: unban, clearwarnings, the post-action sweep, and system auto-deletes
#: never surface publicly").
DISCIPLINARY_ACTIONS: frozenset[str] = frozenset(
    {"warn", "timeout", "kick", "ban"})

#: The shipped public-log policy defaults (services/moderation_config.py:
#: DEFAULT_PUBLIC_LOG_CHANNEL = "" and DEFAULT_PUBLIC_LOG_ACTIONS = "none"
#: — default OFF). The policy EDIT surface is server-management successor
#: work; until it ports, the defaults stand and every disciplinary action
#: lands on the counted mod_public_skipped path, exactly like the capture
#: world did.
DEFAULT_PUBLIC_LOG_ACTIONS = "none"

#: ``public_log_actions`` selector vocabulary (shipped comment: "none" =
#: off · "bans" = ban only · "removals" = kick + ban · "all" = the four
#: disciplinary actions). Fail-safe: an unrecognised selector announces
#: nothing.
_PUBLIC_SELECTOR: dict[str, frozenset[str]] = {
    "none": frozenset(),
    "bans": frozenset({"ban"}),
    "removals": frozenset({"kick", "ban"}),
    "all": DISCIPLINARY_ACTIONS,
}


def public_log_includes(action: str, selector: str) -> bool:
    """Whether *action* is announced publicly under *selector* (pure —
    the shipped moderation_config.public_log_includes)."""
    return action in _PUBLIC_SELECTOR.get(selector, frozenset())


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


async def bound_channel(guild_id: int, binding_name: str) -> int | None:
    """Binding-lane read (subsystem_bindings route-truth) by BINDING name
    (the shipped names: mod_channel / events_channel / …)."""
    from sb.kernel.db.settings import get_binding

    try:
        return await get_binding(guild_id, "logging", binding_name)
    except Exception:  # noqa: BLE001 — no DB (headless) reads as unbound
        return None


async def resolve_route_channel(guild_id: int,
                                kind: str) -> tuple[int | None, str]:
    """(channel_id, source) for a route: its own binding ("binding"), the
    shipped fallback chain ("fallback"), or (None, "unset")."""
    binding = ROUTE_BINDING.get(kind)
    if binding is None:
        return None, "unset"
    own = await bound_channel(guild_id, binding)
    if own is not None:
        return own, "binding"
    target = ROUTE_FALLBACK.get(kind)
    if target is not None:
        via = await bound_channel(guild_id, ROUTE_BINDING[target])
        if via is not None:
            return via, "fallback"
    return None, "unset"


# --- process-local counters (shipped status block) --------------------------------

#: the shipped counter vocabulary VERBATIM (disbot services/
#: server_logging.py `_COUNTERS`) — the status embed renders the FULL
#: block, zeros included (goldens/logging/sweep_logging_status).
COUNTER_NAMES: tuple[str, ...] = (
    "sent_total",
    "skipped_disabled",
    "skipped_no_guild",
    "missing_channel",
    "created_channel",
    "auto_create_error",
    "permission_error",
    "send_error",
    "subscriber_errors",
    "audit_sent",
    "mod_public_sent",
    "mod_public_skipped",
    "event_sent",
    "event_skipped_disabled",
    "event_skipped_ignored",
    "event_missing_channel",
)

_counters: dict[str, int] = {name: 0 for name in COUNTER_NAMES}


def note(counter: str, delta: int = 1) -> None:
    _counters[counter] = _counters.get(counter, 0) + delta


def counters() -> dict[str, int]:
    """Alphabetical full-vocabulary snapshot (the shipped status block's
    render order)."""
    return dict(sorted(_counters.items()))


def reset_counters_for_tests() -> None:
    _counters.clear()
    _counters.update({name: 0 for name in COUNTER_NAMES})


def seed_counters_for_replay(values: dict[str, int]) -> None:
    """Set the process-local counters to a reconstructed CAPTURE state
    (parity runner only — see CAPTURE_WORLD_COUNTERS there)."""
    reset_counters_for_tests()
    for name, value in values.items():
        _counters[name] = int(value)


# --- the fan-out engine ------------------------------------------------------------
#
# The shipped subscriber trio (disbot services/server_logging.py setup():
# EVT_MOD_ACTION -> _on_moderation_action + _on_moderation_action_public,
# EVT_AUDIT_ACTION_RECORDED -> _on_audit_action), counter-for-counter.


async def _send_line(guild_id: int, channel_id: int, body: str) -> None:
    from sb.kernel.interaction.egress import (
        OutboundContent,
        TrustLevel,
        active_channel_emitter,
    )

    emitter = active_channel_emitter()
    result = await emitter.send(
        channel_id, OutboundContent(body=body, trust=TrustLevel.TRUSTED),
        guild_id=guild_id)
    note("sent_total" if result.sent else "send_error")


async def _on_moderation_action(**payload: object) -> None:
    """moderation.action_taken → the STAFF mod-log channel (the shipped
    `_on_moderation_action`): gated by the logging.enabled master switch
    and the bound mod channel; every skip is counted."""
    guild_id = int(payload.get("guild_id", 0) or 0)
    if not guild_id:
        note("skipped_no_guild")
        return
    config = await load_config(guild_id)
    if not config.enabled:
        note("skipped_disabled")
        return
    channel_id = await bound_channel(guild_id, "mod_channel")
    if channel_id is None:
        note("missing_channel")
        return
    action = str(payload.get("action", ""))
    target = payload.get("target_id")
    actor = payload.get("actor_id")
    reason = str(payload.get("reason", "") or "")
    line = f"🛡️ **{action}** — target <@{target}> by <@{actor}>: {reason}"
    await _send_line(guild_id, channel_id, line)


async def _on_moderation_action_public(**payload: object) -> None:
    """moderation.action_taken → the optional PUBLIC moderation log (the
    shipped `_on_moderation_action_public`): pre-filters to disciplinary
    actions BEFORE any config read, independent of logging.enabled, and
    counts every skip (mod_public_sent / mod_public_skipped). The policy
    EDIT surface (public_log_channel / public_log_actions) is
    server-management successor work — until it ports the shipped
    defaults ("" / "none") stand and every disciplinary action skips,
    counted."""
    action = str(payload.get("action", ""))
    if action not in DISCIPLINARY_ACTIONS:
        return                                  # pre-filter: uncounted
    if not public_log_includes(action, DEFAULT_PUBLIC_LOG_ACTIONS):
        note("mod_public_skipped")
        return
    # selector matched but no channel surface exists yet — fail-safe,
    # counted (the shipped channel-unresolvable posture).
    note("mod_public_skipped")


async def _on_audit_action(**payload: object) -> None:
    """audit.action_recorded → the audit route (the shipped
    `_on_audit_action`): guild-less audits are skipped_no_guild
    (server_logging.py:803-805 finding), the logging.enabled master gates
    the rest, and a delivered line counts audit_sent."""
    guild_id = int(payload.get("guild_id", 0) or 0)
    if not guild_id:
        note("skipped_no_guild")
        return
    config = await load_config(guild_id)
    if not config.enabled:
        note("skipped_disabled")
        return
    channel_id, _source = await resolve_route_channel(guild_id, "audit")
    if channel_id is None:
        note("missing_channel")
        return
    subsystem = str(payload.get("subsystem", ""))
    mutation = str(payload.get("mutation_type", ""))
    actor = payload.get("actor_id") or payload.get("actor")
    line = f"📋 **{subsystem}** · `{mutation}` by <@{actor}>"
    await _send_line(guild_id, channel_id, line)
    note("audit_sent")


async def send_test_event(guild_id: int) -> bool:
    """The `!logging test` synthetic event (the shipped log_event drive):
    returns True when the embed was delivered; every miss is counted
    ("disabled / missing channel / send error counted" — the shipped
    reply byte names exactly this)."""
    config = await load_config(guild_id)
    if not config.enabled:
        note("event_skipped_disabled")
        return False
    channel_id, _source = await resolve_route_channel(guild_id, "mod")
    if channel_id is None:
        note("event_missing_channel")
        return False
    from sb.kernel.interaction.egress import (
        OutboundContent,
        TrustLevel,
        active_channel_emitter,
    )

    emitter = active_channel_emitter()
    result = await emitter.send(
        channel_id,
        OutboundContent(body="🧪 logging test — routing OK",
                        trust=TrustLevel.SYSTEM),
        guild_id=guild_id)
    note("event_sent" if result.sent else "send_error")
    return bool(result.sent)


def subscribe(bus: object) -> None:
    """Arm the fan-out on THE bus (composition-root / harness obligation —
    the shipped ``server_logging.setup(bot)`` analog: the subscriber trio)."""
    bus.on("moderation.action_taken", _on_moderation_action)
    bus.on("moderation.action_taken", _on_moderation_action_public)
    bus.on("audit.action_recorded", _on_audit_action)
