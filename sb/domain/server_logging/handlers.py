"""The `!logging …` operator command handlers (band 2) — thin HandlerRef
routes over the K7 seams: scalar toggles + channel pointers go through the
band-1 settings ops (design-spec §4.1: ONE write path — logging never
touches the KV/bindings tables itself); status/routes are reads."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]

_BIND_NAMES = ("mod", "cleanup", "events", "messages", "members", "roles")


async def _set_scalar(req, key: str, value: str):
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    return await engine.run(WorkflowRef("settings.set_scalar"),
                            _ctx_from_req(req, {"key": key, "value": value}))


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("logging.status_view")):
        return

    @handler("logging.status_view")
    async def status_view(req) -> Reply:
        from sb.domain.server_logging import service

        config = await service.load_config(int(req.guild_id or 0))
        mod = await service.bound_channel(int(req.guild_id or 0), "mod")
        cleanup = await service.bound_channel(int(req.guild_id or 0), "cleanup")
        events = await service.bound_channel(int(req.guild_id or 0), "events")
        categories = [c for c, on in sorted(config.category_enabled.items()) if on]
        counter_lines = "\n".join(f"`{k}` = {v}"
                                  for k, v in service.counters().items())
        lines = [
            "📝 Server logging — status",
            f"Enabled: {'🟢 on' if config.enabled else '⚪ off'}",
            f"Auto-create channels: "
            f"{'🟢 on' if config.auto_create_channels else '⚪ off'}",
            f"Mod channel: {f'<#{mod}>' if mod else '*(unset)*'}",
            f"Cleanup channel: "
            f"{f'<#{cleanup}>' if cleanup else '*(falls back to mod)*'}",
            f"Event logging — categories: "
            f"{', '.join(categories) if categories else '*(none)*'} · "
            f"routing: `{config.routing}` · events channel: "
            f"{f'<#{events}>' if events else '*(unset)*'}",
        ]
        if counter_lines:
            lines.append("Counters (process-local):\n" + counter_lines)
        return Reply(SUCCESS, "\n".join(lines))

    @handler("logging.enable")
    async def enable(req) -> Reply:
        result = await _set_scalar(req, "logging_enabled", "true")
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not enable logging.")
        return Reply(SUCCESS, "Server logging **enabled**.")

    @handler("logging.disable")
    async def disable(req) -> Reply:
        result = await _set_scalar(req, "logging_enabled", "false")
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not disable logging.")
        return Reply(SUCCESS, "Server logging **disabled**.")

    @handler("logging.set_channel")
    async def set_channel(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if len(argv) < 2:
            return Reply(BLOCKED,
                         f"Usage: `!logging set <{'|'.join(_BIND_NAMES)}> "
                         f"#channel`")
        name = str(argv[0]).lower()
        if name not in _BIND_NAMES:
            return Reply(BLOCKED,
                         f"Unknown log slot {name!r} — one of "
                         f"{', '.join(_BIND_NAMES)}.")
        token = str(argv[1]).lstrip("<#").rstrip(">")
        if not token.isdigit():
            return Reply(BLOCKED, "That doesn't look like a channel mention.")
        result = await engine.run(
            WorkflowRef("settings.bind"),
            _ctx_from_req(req, {"subsystem": "logging", "name": name,
                                "kind": "channel", "resource_id": int(token)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not bind the channel.")
        return Reply(SUCCESS, f"Log slot **{name}** → <#{int(token)}>.")

    @handler("logging.routes_view")
    async def routes_view(req) -> Reply:
        from sb.domain.server_logging import service

        config = await service.load_config(int(req.guild_id or 0))
        lines = [f"Routing mode: `{config.routing}`"]
        for category in service.CATEGORIES:
            enabled = config.category_enabled.get(category, False)
            channel = await service.bound_channel(int(req.guild_id or 0),
                                                  category)
            target = (f"<#{channel}>" if channel and config.per_category
                      else "combined events channel")
            lines.append(f"• {category}: "
                         f"{'on' if enabled else 'off'} → {target}")
        return Reply(SUCCESS, "\n".join(lines))

    @handler("logging.test_send")
    async def test_send(req) -> Reply:
        from sb.domain.server_logging import service
        from sb.kernel.interaction.egress import (
            OutboundContent,
            TrustLevel,
            active_channel_emitter,
        )

        guild_id = int(req.guild_id or 0)
        config = await service.load_config(guild_id)
        if not config.enabled:
            return Reply(BLOCKED, "Server logging is disabled — "
                                  "`!logging enable` first.")
        channel_id = await service.bound_channel(guild_id, "mod")
        if channel_id is None:
            return Reply(BLOCKED, "No mod channel bound — "
                                  "`!logging set mod #channel` first.")
        emitter = active_channel_emitter()
        result = await emitter.send(
            channel_id,
            OutboundContent(body="🧪 logging test — routing OK",
                            trust=TrustLevel.SYSTEM),
            guild_id=guild_id)
        service.note("sent_total" if result.sent else "send_error")
        return Reply(SUCCESS if result.sent else BLOCKED,
                     "Test line sent." if result.sent
                     else f"Send failed: {result.error}")

    @handler("logging.create_channels")
    async def create_channels(req) -> Reply:
        # channel PROVISIONING is a Discord state mutation — rides the
        # resource-provision port when the server_management slice arms it
        # (A-8/G-2 family). Declared now, refused politely until installed.
        return Reply(BLOCKED,
                     "Channel auto-provisioning isn't armed yet — bind an "
                     "existing channel with `!logging set mod #channel`.")


_register()


def ensure_handler_refs() -> None:
    _register()
