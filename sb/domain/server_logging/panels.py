"""The shipped logging panels at byte parity (band 2 flip).

Four panels, all SESSION-lifecycle (the shipped views were plain
``discord.ui.View`` sends — never anchored; goldens/logging/* pin ZERO
``panel_anchors`` rows):

* ``logging.hub`` — the shipped ``LoggingPanelView`` (disbot
  cogs/logging/panel.py @58040c6): the 8 STATIC ``logging_panel.*``
  custom_ids ride ``custom_id_override`` (verbatim pins survive the
  session mint), the status embed rides the shared renderer_override,
  and the engine nav row carries nav:help + nav:hub:moderation
  (goldens/logging/sweep_logging pins every byte).
* ``logging.status_card`` — the same status embed with NO components
  (the shipped ``!logging status`` reply; goldens/logging/
  sweep_logging_status pins content:null + components:[]).
* ``logging.routes`` — the shipped Routes panel (cogs/logging/
  routes_panel.py): the 11-route select in ROOTS-FIRST order + the four
  ``logging_routes.*`` buttons; NO engine nav (the shipped ↩ Back button
  replaces it) — goldens/logging/sweep_logging_routes pins every byte.
* ``logging.bind_picker`` — the shipped ``LogChannelSelectView``
  (cogs/logging/select_view.py): a CONTENT-only message carrying a
  Discord-native CHANNEL select (wire type 8, text channels) + the
  "Clear binding" button, both session-minted (``<cid:N>`` — goldens/
  logging/logging_enable_and_bind step 3 pins the wire).
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.domain.server_logging.service import ROUTES as _ROUTES
from sb.spec.refs import HandlerRef, handler, panel

__all__ = [
    "bind_picker_spec",
    "ensure_panel_refs",
    "install_logging_panels",
    "logging_hub_spec",
    "routes_panel_spec",
    "status_card_spec",
]

# --- the shared status embed (logging_cog.py module-level builder) ----------------


async def _build_status_embed(guild_id: int):
    """The shipped status embed (disbot cogs/logging_cog.py): title, the
    six fields (Enabled / Auto-create channels / Mod channel / Cleanup
    channel / Event logging / Counters), SUCCESS color when enabled and
    INFO blue otherwise. goldens/logging/sweep_logging_status pins the
    off-state bytes."""
    from sb.domain.server_logging import service
    from sb.kernel.panels.render import RenderedEmbed

    config = await service.load_config(guild_id)
    mod = await service.bound_channel(guild_id, "mod_channel")
    cleanup = await service.bound_channel(guild_id, "cleanup_channel")
    events = await service.bound_channel(guild_id, "events_channel")
    active = [c for c in service.CATEGORIES
              if config.category_enabled.get(c, False)]
    counter_lines = "\n".join(
        f"`{name}` = {value}"
        for name, value in service.counters().items())
    fields = (
        ("Enabled", "✅ on" if config.enabled else "⚪ off", True),
        ("Auto-create channels",
         "✅ on" if config.auto_create_channels else "⚪ off", True),
        ("Mod channel", f"<#{mod}>" if mod else "*(unset)*", False),
        ("Cleanup channel",
         f"<#{cleanup}>" if cleanup else "*(falls back to mod)*", False),
        ("Event logging",
         f"Categories: {', '.join(active) if active else '*(none)*'}\n"
         f"Routing: `{config.routing}`\n"
         f"Events channel: {f'<#{events}>' if events else '*(unset)*'}",
         False),
        ("Counters (process-local)", counter_lines, False),
    )
    return RenderedEmbed(
        title="📝 Server logging — status",
        description="",
        fields=fields,
        style_token="green" if config.enabled else "blue")


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override for hub + status card: state-dependent copy the
    grammar cannot express (channel mentions, live counters, the
    enabled-keyed color) — the moderation.render_hub precedent. The
    COMPONENTS come from render_panel (declared actions/nav untouched,
    the pinned logging_panel.* ids come from the spec)."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    embed = await _build_status_embed(int(ctx.guild_id or 0))
    return dataclasses.replace(base, embed=embed)


# --- the hub (LoggingPanelView) ---------------------------------------------------


def _hub_action(action_id: str, wire_id: str, label: str, style: ActionStyle,
                ref: str) -> PanelActionSpec:
    """action_id is the K1-unique internal id; ``wire_id`` is the shipped
    STATIC custom_id suffix (``logging_panel.<wire_id>`` — pinned bytes)."""
    return PanelActionSpec(
        action_id=action_id, label=label, style=style,
        handler=HandlerRef(ref),
        custom_id_override=f"logging_panel.{wire_id}")


def logging_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="logging.hub",
        subsystem="logging",
        title="📝 Server logging — status",
        audience=Audience.INVOKER,
        session_lifecycle=True,        # shipped: plain View send, no anchor
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        actions=(
            # the 8 shipped STATIC wire ids (cogs/logging/panel.py),
            # row-exact; internal action_ids are K1-unique renames where a
            # bare shipped token collides cross-subsystem (status/overview).
            _hub_action("refresh_status", "status", "📝 Refresh Status",
                        ActionStyle.PRIMARY, "logging.panel_status"),
            _hub_action("set_mod", "set_mod", "🔗 Set Mod Channel",
                        ActionStyle.PRIMARY, "logging.panel_set_mod"),
            _hub_action("set_cleanup", "set_cleanup", "🔗 Set Cleanup Channel",
                        ActionStyle.PRIMARY, "logging.panel_set_cleanup"),
            _hub_action("create_mod", "create_mod", "🆕 Create Mod Channel",
                        ActionStyle.SUCCESS, "logging.panel_create"),
            _hub_action("create_cleanup", "create_cleanup",
                        "🆕 Create Cleanup Channel",
                        ActionStyle.SUCCESS, "logging.panel_create"),
            _hub_action("test", "test", "🔔 Test",
                        ActionStyle.SECONDARY, "logging.panel_test"),
            _hub_action("routes", "routes", "🗺️ Routes",
                        ActionStyle.PRIMARY, "logging.panel_routes"),
            # ↩ Overview re-renders the status embed — the shipped panel.py
            # docstring: "same as Refresh".
            _hub_action("hub_overview", "overview", "↩ Overview",
                        ActionStyle.SECONDARY, "logging.panel_status"),
        ),
        navigation=NavigationSpec(home_hub="moderation"),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("refresh_status",),
            ("set_mod", "set_cleanup"),
            ("create_mod", "create_cleanup"),
            ("test", "routes"),
            ("hub_overview",),      # row 4 — shares the engine nav row
        )),)),
        renderer_override=HandlerRef("logging.render_status"),
        justification=(
            "the shipped LoggingPanelView carried the status embed built "
            "by logging_cog.py's module-level builder — channel mentions, "
            "the live process-local counter block, and the enabled-keyed "
            "color are state-dependent copy the grammar cannot express; "
            "the override delegates the COMPONENTS to render_panel (the "
            "pinned logging_panel.* ids come from the spec) and composes "
            "the EMBED only (title, the six shipped fields, the "
            "SUCCESS/INFO color key). goldens/logging/sweep_logging + "
            "logging_enable_and_bind pin every off-state byte."),
    )


def status_card_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="logging.status_card",
        subsystem="logging",
        title="📝 Server logging — status",
        audience=Audience.INVOKER,
        session_lifecycle=True,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        navigation=NavigationSpec(show_help=False, show_home=False),
        renderer_override=HandlerRef("logging.render_status"),
        justification=(
            "the shipped `!logging status` reply is the SAME state-"
            "dependent status embed with zero components (goldens/logging/"
            "sweep_logging_status pins content:null + components:[]) — "
            "the karma.error_card zero-component session-panel lane."),
    )


# --- the routes panel (routes_panel.py) -------------------------------------------

_ROUTES_DESCRIPTION = (
    "**Quick start:** set the top two — **`mod`** and **`events`** — and "
    "every route is delivered somewhere (the rest fall back to them). "
    "Split out any route below only when you want it in its own channel."
    "\n\n"
    "Each row shows a route, its binding, and where it resolves today. "
    "Pick one, then **Set Channel** (bind an existing channel) or "
    "**Create Channel** — both route through `BindingMutationPipeline` / "
    "`ResourceProvisioningPipeline` and record an audit row.")

_ROUTES_FOOTER = (
    "Pick a route below, then Set Channel or Create Channel. Routes "
    "without their own binding fall back along their fallback chain "
    "(severity/audit → mod; event routes → events).")


async def _render_routes(spec: PanelSpec, ctx) -> object:
    """renderer_override for the routes panel: the shipped Routes field is
    a per-route resolution walk (own binding → fallback chain → unset) —
    state-dependent copy; components delegate to render_panel."""
    import dataclasses

    from sb.domain.server_logging import service
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    guild_id = int(ctx.guild_id or 0)
    lines = []
    for kind in service.ROUTES:
        binding = service.ROUTE_BINDING[kind]
        channel_id, source = await service.resolve_route_channel(
            guild_id, kind)
        if source == "binding" and channel_id is not None:
            marker = f"→ <#{channel_id}>"
        elif source == "fallback" and channel_id is not None:
            target = service.ROUTE_FALLBACK.get(kind) or "mod"
            marker = f"↪ <#{channel_id}> *(via {target} fallback)*"
        else:
            marker = "*(unset)*"
        lines.append(f"**`{kind}`** ・ `logging.{binding}` {marker}")
    embed = RenderedEmbed(
        title="🗺️ Logging Routes",
        description=_ROUTES_DESCRIPTION,
        fields=(("Routes", "\n".join(lines), False),),
        footer=_ROUTES_FOOTER,
        style_token="red")
    return dataclasses.replace(base, embed=embed)


def routes_panel_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="logging.routes",
        subsystem="logging",
        title="🗺️ Logging Routes",
        audience=Audience.INVOKER,
        session_lifecycle=True,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        selectors=(
            SelectorSpec(
                selector_id="select", kind=SelectorKind.ENUM,
                on_select=HandlerRef("logging.routes_pick"),
                options_source=_ROUTES,   # roots-first shipped order
                placeholder="Choose a route…",
                custom_id_override="logging_routes.select"),
        ),
        actions=(
            PanelActionSpec(
                action_id="routes_bind", label="🔗 Set Channel",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("logging.routes_set"),
                custom_id_override="logging_routes.set"),
            PanelActionSpec(
                action_id="routes_create", label="🆕 Create Channel",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("logging.panel_create"),
                custom_id_override="logging_routes.create"),
            PanelActionSpec(
                action_id="routes_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("logging.panel_routes"),
                custom_id_override="logging_routes.refresh"),
            PanelActionSpec(
                action_id="routes_back", label="↩ Back to Logging",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("logging.panel_open"),
                custom_id_override="logging_routes.back"),
        ),
        # the shipped view carried its own ↩ Back button — no engine nav row
        # (goldens/logging/sweep_logging_routes pins the exact rows).
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("select",),
            ("routes_bind", "routes_create", "routes_refresh"),
            ("routes_back",),
        )),)),
        renderer_override=HandlerRef("logging.render_routes"),
        justification=(
            "the shipped Routes embed (cogs/logging/routes_panel.py "
            "build_routes_embed) walks every route's live resolution "
            "(own binding → fallback chain → unset marker) — "
            "state-dependent copy the grammar cannot express; the "
            "override delegates the COMPONENTS to render_panel (the "
            "pinned logging_routes.* ids come from the spec) and "
            "composes the EMBED only (title, quick-start description, "
            "the Routes field, the fallback-chain footer, ERROR red). "
            "goldens/logging/sweep_logging_routes pins every byte."),
    )


# --- the channel-binding picker (select_view.py LogChannelSelectView) --------------


async def _render_bind_picker(spec: PanelSpec, ctx) -> object:
    """renderer_override: the shipped LogChannelSelectView message is a
    CONTENT-only send (no embed) whose copy names the route being bound
    (goldens/logging/logging_enable_and_bind step 3 pins the bytes); the
    session-minted CHANNEL select + Clear-binding button delegate to
    render_panel."""
    import dataclasses

    from sb.domain.server_logging import service
    from sb.kernel.panels.render import render_panel

    kind = str((ctx.params or {}).get("slot", "mod"))
    base = await render_panel(spec, ctx)
    components = []
    for comp in base.components:
        if comp.kind == "selector":
            placeholder = f"Pick the {service.route_label(kind)} channel…"
            comp = dataclasses.replace(comp, label=placeholder,
                                       placeholder=placeholder)
        components.append(comp)
    content = (f"Pick a channel to bind as the **{kind} log** for this "
               "guild.  All writes route through `BindingMutationPipeline` "
               "and produce an audit row.")
    return dataclasses.replace(base, embed=None, content=content,
                               components=tuple(components))


def bind_picker_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="logging.bind_picker",
        subsystem="logging",
        title="",
        audience=Audience.INVOKER,
        session_lifecycle=True,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        body=(TextBlock(""),),
        selectors=(
            SelectorSpec(
                selector_id="pick", kind=SelectorKind.CHANNEL,
                on_select=HandlerRef("logging.bind_pick"),
                placeholder="Pick the log channel…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="clear", label="Clear binding",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("logging.bind_clear")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("pick",),
            ("clear",),
        )),)),
        renderer_override=HandlerRef("logging.render_bind_picker"),
        justification=(
            "the shipped LogChannelSelectView message is a plain-text "
            "send (no embed) whose content and select placeholder name "
            "the route being bound — per-invocation copy the grammar "
            "cannot express; the override delegates the COMPONENTS to "
            "render_panel (session-minted ids — the goldens' <cid:N> "
            "shape) and replaces embed→None + content + the per-route "
            "placeholder only. goldens/logging/logging_enable_and_bind "
            "step 3 pins the wire."),
    )


# --- registration ------------------------------------------------------------------


@panel("logging.hub")
def _hub_factory() -> PanelSpec:
    return logging_hub_spec()


@panel("logging.status_card")
def _status_factory() -> PanelSpec:
    return status_card_spec()


@panel("logging.routes")
def _routes_factory() -> PanelSpec:
    return routes_panel_spec()


@panel("logging.bind_picker")
def _picker_factory() -> PanelSpec:
    return bind_picker_spec()


handler("logging.render_status")(_render_status)
handler("logging.render_routes")(_render_routes)
handler("logging.render_bind_picker")(_render_bind_picker)


def install_logging_panels() -> None:
    for spec in (logging_hub_spec(), status_card_spec(),
                 routes_panel_spec(), bind_picker_spec()):
        try:
            register_panel(spec)
        except ValueError as exc:
            if "already registered" not in str(exc) and \
                    "duplicate" not in str(exc):
                raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef, is_registered as _is, panel as _panel

    for name, factory in (("logging.hub", _hub_factory),
                          ("logging.status_card", _status_factory),
                          ("logging.routes", _routes_factory),
                          ("logging.bind_picker", _picker_factory)):
        if not _is(PanelRef(name)):
            _panel(name)(factory)
    for name, fn in (("logging.render_status", _render_status),
                     ("logging.render_routes", _render_routes),
                     ("logging.render_bind_picker", _render_bind_picker)):
        if not _is(HandlerRef(name)):
            handler(name)(fn)
