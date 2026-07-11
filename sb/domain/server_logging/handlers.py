"""The `!logging …` operator handlers (band 2, flipped to shipped shape).

Command surface = the shipped logging_cog.py @58040c6: the bare group
opens the panel (invoke_without_command — an unknown token like the
retired `enable` falls through to the SAME panel; goldens/logging/
logging_enable_and_bind pins both), `status` is the zero-component
status card, `set`/`create` parse a route token (usage bytes pinned by
sweep_logging_set / sweep_logging_create), `routes` opens the Routes
panel and `test` drives the synthetic event. Channel writes go through
the band-1 settings ops ONLY (design-spec §4.1 — the shipped
BindingMutationPipeline analog); channel PROVISIONING stays a polite
refusal until the resource-provision port arms (D-0029(4))."""

from __future__ import annotations

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs"]

#: the shipped usage token list — the 11 route kinds SORTED (logging_cog.py;
#: goldens/logging/sweep_logging_set + sweep_logging_create pin the bytes).
def _sorted_routes() -> str:
    from sb.domain.server_logging.service import ROUTES

    return "|".join(sorted(ROUTES))


SET_USAGE = ("Usage: `!logging set <{routes}>` — opens the channel "
             "selector for the requested log binding.")
CREATE_USAGE = ("Usage: `!logging create <{routes}>` — opens a preview + "
                "Confirm view for the requested channel.")

#: the shipped `!logging test` reply pair (logging_cog.py verbatim).
TEST_OK = "✅ Test embed delivered to the configured log channel."
TEST_MISS = ("ℹ️ No embed sent — see `!logging status` for the cause "
             "(disabled / missing channel / send error counted).")

#: the routes panel's pick memory — the shipped view kept the chosen route
#: on the view instance; the port keys it per (guild, invoker), in-memory
#: (process-local UI state, same class as the shipped View attribute).
_route_choice: dict[tuple[int, int], str] = {}


async def _open(req, panel_id: str, **args: object):
    import dataclasses

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    merged = {**dict(req.args or {}), **args}
    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=merged))
    return Reply(SUCCESS, None)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("logging.set_channel")):
        return

    # --- prefix subcommands --------------------------------------------------

    @handler("logging.set_channel")
    async def set_channel(req) -> Reply:
        from sb.domain.server_logging.service import ROUTES

        argv = tuple(req.args.get("argv", ()) or ())
        kind = str(argv[0]).lower() if argv else ""
        if kind not in ROUTES:
            # bare/unknown → the shipped usage byte (extra args beyond the
            # kind are ignored — the shipped `set` took only the kind and
            # opened the selector regardless).
            return Reply(BLOCKED, SET_USAGE.format(routes=_sorted_routes()))
        return await _open(req, "logging.bind_picker", slot=kind)

    @handler("logging.create_channels")
    async def create_channels(req) -> Reply:
        from sb.domain.server_logging.service import ROUTES

        argv = tuple(req.args.get("argv", ()) or ())
        kind = str(argv[0]).lower() if argv else ""
        if kind not in ROUTES:
            return Reply(BLOCKED,
                         CREATE_USAGE.format(routes=_sorted_routes()))
        # channel PROVISIONING is a Discord state mutation — rides the
        # resource-provision port when the server_management slice arms it
        # (A-8/G-2 family; D-0029(4)). Declared, refused politely.
        return Reply(BLOCKED,
                     "Channel auto-provisioning isn't armed yet — bind an "
                     "existing channel with `!logging set "
                     f"{kind} #channel`.")

    @handler("logging.routes_view")
    async def routes_view(req) -> Reply:
        return await _open(req, "logging.routes")

    @handler("logging.test_send")
    async def test_send(req) -> Reply:
        from sb.domain.server_logging.service import send_test_event

        sent = await send_test_event(int(req.guild_id or 0))
        return Reply(SUCCESS if sent else BLOCKED,
                     TEST_OK if sent else TEST_MISS)

    # --- panel actions (the shipped LoggingPanelView callbacks) ---------------

    @handler("logging.panel_open")
    async def panel_open(req) -> Reply:
        return await _open(req, "logging.hub")

    @handler("logging.panel_status")
    async def panel_status(req) -> Reply:
        # 📝 Refresh Status / ↩ Overview — re-renders the status embed
        # (the shipped panel.py: "same as Refresh").
        return await _open(req, "logging.status_card")

    @handler("logging.panel_set_mod")
    async def panel_set_mod(req) -> Reply:
        return await _open(req, "logging.bind_picker", slot="mod")

    @handler("logging.panel_set_cleanup")
    async def panel_set_cleanup(req) -> Reply:
        return await _open(req, "logging.bind_picker", slot="cleanup")

    @handler("logging.panel_create")
    async def panel_create(req) -> Reply:
        return Reply(BLOCKED,
                     "Channel auto-provisioning isn't armed yet — bind an "
                     "existing channel with `!logging set mod #channel`.")

    @handler("logging.panel_test")
    async def panel_test(req) -> Reply:
        return await test_send(req)

    @handler("logging.panel_routes")
    async def panel_routes(req) -> Reply:
        return await _open(req, "logging.routes")

    # --- routes panel ----------------------------------------------------------

    @handler("logging.routes_pick")
    async def routes_pick(req) -> Reply:
        from sb.domain.server_logging.service import ROUTES

        values = tuple(req.args.get("values", ()) or ())
        kind = str(values[0]).lower() if values else ""
        if kind not in ROUTES:
            return Reply(BLOCKED, "Unknown route.")
        _route_choice[(int(req.guild_id or 0),
                       int(req.actor.user_id or 0))] = kind
        return Reply(SUCCESS, f"Route **`{kind}`** selected — now "
                              "**Set Channel** or **Create Channel**.")

    @handler("logging.routes_set")
    async def routes_set(req) -> Reply:
        kind = _route_choice.get((int(req.guild_id or 0),
                                  int(req.actor.user_id or 0)))
        if kind is None:
            return Reply(BLOCKED, "Pick a route first.")
        return await _open(req, "logging.bind_picker", slot=kind)

    # --- the channel-binding picker (LogChannelSelectView) ---------------------

    @handler("logging.bind_pick")
    async def bind_pick(req) -> Reply:
        from sb.domain.server_logging.service import ROUTE_BINDING
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        kind = str(req.args.get("slot", "mod"))
        binding = ROUTE_BINDING.get(kind)
        if binding is None:
            return Reply(BLOCKED, "Unknown route.")
        values = tuple(req.args.get("values", ()) or ())
        token = str(values[0]) if values else ""
        if not token.isdigit():
            return Reply(BLOCKED, "That doesn't look like a channel.")
        result = await engine.run(
            WorkflowRef("settings.bind"),
            _ctx_from_req(req, {"subsystem": "logging", "name": binding,
                                "kind": "channel",
                                "resource_id": int(token)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not bind the channel.")
        return Reply(SUCCESS, f"Log route **{kind}** → <#{int(token)}>.")

    @handler("logging.bind_clear")
    async def bind_clear(req) -> Reply:
        from sb.domain.server_logging.service import ROUTE_BINDING
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        kind = str(req.args.get("slot", "mod"))
        binding = ROUTE_BINDING.get(kind)
        if binding is None:
            return Reply(BLOCKED, "Unknown route.")
        result = await engine.run(
            WorkflowRef("settings.unbind"),
            _ctx_from_req(req, {"subsystem": "logging", "name": binding}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not clear the binding.")
        return Reply(SUCCESS, f"Log route **{kind}** binding cleared.")


_register()


def ensure_handler_refs() -> None:
    _register()
