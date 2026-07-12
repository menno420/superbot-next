"""CHANNEL subsystem manifest (band 2) — the shipped channel-ops command
surface DECLARED (names/aliases verbatim, cogs/channel_cog.py); the
still-unported mutations route to the declared-but-port-not-armed
terminal until the channel-ops Discord port lands (named successor
slice, D-0030). The namespace reservation + parity denominator are real
today; the handlers refuse honestly instead of dropping.

``!channelmenu`` opens the REAL shipped hub panel (the parity flip):
``_ChannelManagerView``'s 🛠️ Channel Management Panel
(sb/domain/channel/panels.py; goldens/channel/sweep_channelmenu.json pins
the bytes). ``!slowmode``/``!lock``/``!unlock`` run the shipped
ChannelLifecycleService slice through the channel-state port (the
`_unmapped` strays re-home — goldens/channel/sweep_slowmode +
sweep_lock + sweep_unlock pin the bytes); the remaining ops and the five
sub-panels stay pending terminals until D-0030 arms the rest."""

from __future__ import annotations

from sb.domain.channel import handlers as _handlers
from sb.domain.channel import panels as _panels
from sb.domain.channel.service import EVT_CHANNEL_LIFECYCLE
from sb.domain.operator_spine import pending_handler
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef

_PENDING = pending_handler(
    "channel.ops_pending",
    "Channel operations aren't armed in this build yet — the channel-ops "
    "port lands with the discord adapter slice.")

#: the shipped channel lifecycle event verbatim
#: (services/channel_lifecycle_service.py EVT_CHANNEL_LIFECYCLE —
#: advisory, best-effort, shares its mutation_id with the audit
#: companion; goldens/channel/sweep_slowmode + sweep_lock + sweep_unlock
#: pin the payload shape).
CHANNEL_LIFECYCLE_EVENT = EventSpec(
    name=EVT_CHANNEL_LIFECYCLE,
    payload_schema=(
        FieldSpec("mutation_id", "str"),
        FieldSpec("guild_id", "int"),
        FieldSpec("operation", "str"),   # the service's _OPERATIONS vocabulary
        FieldSpec("outcome", "str"),
        FieldSpec("applied", "list"),
        FieldSpec("failed", "list"),
        FieldSpec("occurred_at", "str"),
    ),
    owner_subsystem="channel",
    delivery=DeliveryClass.BEST_EFFORT,
)

#: commands with REAL handlers (the re-homed golden slice); everything
#: else keeps the pending terminal.
_ROUTES = {
    "slowmode": HandlerRef("channel.slowmode"),
    "lock": HandlerRef("channel.lock"),
    "unlock": HandlerRef("channel.unlock"),
    # the channel-ops sweep re-home: the 13 declared-but-pending mutations
    # leave the pending terminal for real handlers over the
    # ChannelStateActions port + the list/info read ports (goldens/channel/
    # sweep_{bulkcreate,bulkdelete,channelinfo,clone,create,del,evt,list,
    # move,permissions,rename,set,topic} pin the bytes).
    "del": HandlerRef("channel.del"),
    "bulkdelete": HandlerRef("channel.bulkdelete"),
    "bulkcreate": HandlerRef("channel.bulkcreate"),
    "rename": HandlerRef("channel.rename"),
    "topic": HandlerRef("channel.topic"),
    "clone": HandlerRef("channel.clone"),
    "set": HandlerRef("channel.set"),
    "create": HandlerRef("channel.create"),
    "evt": HandlerRef("channel.evt"),
    "permissions": HandlerRef("channel.permissions"),
    "move": HandlerRef("channel.move"),
    "list": HandlerRef("channel.list"),
    "channelinfo": HandlerRef("channel.channelinfo"),
}

_OPS = (
    ("channelmenu", ()), ("set", ()), ("evt", ()), ("create", ()),
    ("bulkdelete", ()), ("del", ()), ("list", ()), ("clone", ()),
    ("move", ()), ("lock", ()), ("unlock", ()), ("channelinfo", ()),
    ("rename", ()), ("slowmode", ("slow",)), ("topic", ("settopic",)),
    ("permissions", ()), ("bulkcreate", ()),
)


def _cmd(name: str, aliases: tuple[str, ...]) -> CommandSpec:
    if name == "channelmenu":
        return CommandSpec(name=name, kind=CommandKind.PREFIX,
                           route=PanelRef("channel.hub"),
                           audience_tier="administrator",
                           summary="Open the channel menu.",
                           capability="channel")
    route = _ROUTES.get(name)
    if route is not None:
        return CommandSpec(name=name, kind=CommandKind.PREFIX, route=route,
                           aliases=aliases, capability="channel",
                           audience_tier="administrator",
                           summary=f"Channel op `{name}`.",
                           usage=f"!{name}")
    return CommandSpec(name=name, kind=CommandKind.PREFIX, route=_PENDING,
                       aliases=aliases, capability="channel",
                       summary=f"Channel op `{name}` (port-armed later).")


MANIFEST = SubsystemManifest(
    key="channel",
    version=1,
    commands=tuple(_cmd(n, a) for n, a in _OPS),
    panels=(_panels.channel_hub_spec(),
            _panels.channel_list_card_spec(),
            _panels.channel_info_card_spec()),
    settings=(), stores=(), events=(CHANNEL_LIFECYCLE_EVENT,),
    capabilities=(),
)

register_event_specs([CHANNEL_LIFECYCLE_EVENT])


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    pending_handler("channel.ops_pending", "")
    register_event_specs([CHANNEL_LIFECYCLE_EVENT])


ENSURE_REFS = _ensure_refs
