"""CHANNEL subsystem manifest (band 2) — the shipped channel-ops command
surface (names/aliases verbatim, cogs/channel_cog.py), FULLY armed: the
D-0030 channel-ops batch routed every declared prefix command onto its
real handler (goldens/channel/ pins all 17 lanes' bytes).

``!channelmenu`` opens the REAL shipped hub panel
(``_ChannelManagerView``'s 🛠️ Channel Management Panel —
sb/domain/channel/panels.py; goldens/channel/sweep_channelmenu.json pins
the bytes; the five interactive sub-panels behind its buttons stay on
their honest pending terminals). Every other command runs the shipped
ChannelLifecycleService slice through the channel-state/directory ports
(sb/domain/channel/handlers.py; goldens/channel/sweep_slowmode +
sweep_lock + sweep_unlock + the 13 wave-9 re-homes pin the bytes).
``!channelinfo``/``!list`` open the two read-only info cards
(sb/domain/channel/panels.py)."""

from __future__ import annotations

from sb.domain.channel import handlers as _handlers
from sb.domain.channel import panels as _panels
from sb.domain.channel.service import EVT_CHANNEL_LIFECYCLE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef

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

#: every prefix command's REAL handler (the D-0030 batch armed the
#: full roster; goldens/channel/ pins each lane).
_ROUTES = {
    "slowmode": HandlerRef("channel.slowmode"),
    "lock": HandlerRef("channel.lock"),
    "unlock": HandlerRef("channel.unlock"),
    "bulkcreate": HandlerRef("channel.bulkcreate"),
    "bulkdelete": HandlerRef("channel.bulkdelete"),
    "channelinfo": HandlerRef("channel.channelinfo"),
    "clone": HandlerRef("channel.clone"),
    "create": HandlerRef("channel.create"),
    "del": HandlerRef("channel.del"),
    "evt": HandlerRef("channel.evt"),
    "list": HandlerRef("channel.list"),
    "move": HandlerRef("channel.move"),
    "permissions": HandlerRef("channel.permissions"),
    "rename": HandlerRef("channel.rename"),
    "set": HandlerRef("channel.set"),
    "topic": HandlerRef("channel.topic"),
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
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       route=_ROUTES[name],
                       aliases=aliases, capability="channel",
                       audience_tier="administrator",
                       summary=f"Channel op `{name}`.",
                       usage=f"!{name}")


MANIFEST = SubsystemManifest(
    key="channel",
    version=1,
    commands=tuple(_cmd(n, a) for n, a in _OPS),
    panels=(_panels.channel_hub_spec(), _panels.info_card_spec(),
            _panels.list_card_spec(),
            # the five shipped sub-panels + the visibility toggle grid
            # (operator-hub edits B — the D-0030 named successor).
            _panels.create_spec(), _panels.delete_spec(),
            _panels.restrict_spec(), _panels.move_spec(),
            _panels.visibility_spec(), _panels.visibility_grid_spec()),
    settings=(), stores=(), events=(CHANNEL_LIFECYCLE_EVENT,),
    capabilities=(),
)

register_event_specs([CHANNEL_LIFECYCLE_EVENT])


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    register_event_specs([CHANNEL_LIFECYCLE_EVENT])


ENSURE_REFS = _ensure_refs
