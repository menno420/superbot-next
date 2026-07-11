"""CHANNEL subsystem manifest (band 2) — the shipped channel-ops command
surface DECLARED (names/aliases verbatim, cogs/channel_cog.py); every
mutation routes to the declared-but-port-not-armed terminal until the
channel-ops Discord port lands (named successor slice, D-0030). The
namespace reservation + parity denominator are real today; the handlers
refuse honestly instead of dropping.

``!channelmenu`` opens the REAL shipped hub panel (the parity flip):
``_ChannelManagerView``'s 🛠️ Channel Management Panel
(sb/domain/channel/panels.py; goldens/channel/sweep_channelmenu.json pins
the bytes). The five sub-panels stay pending terminals until D-0030 arms
the Discord channel mutations."""

from __future__ import annotations

from sb.domain.channel import handlers as _handlers
from sb.domain.channel import panels as _panels
from sb.domain.operator_spine import pending_handler
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

_PENDING = pending_handler(
    "channel.ops_pending",
    "Channel operations aren't armed in this build yet — the channel-ops "
    "port lands with the discord adapter slice.")

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
    return CommandSpec(name=name, kind=CommandKind.PREFIX, route=_PENDING,
                       aliases=aliases, capability="channel",
                       summary=f"Channel op `{name}` (port-armed later).")


MANIFEST = SubsystemManifest(
    key="channel",
    version=1,
    commands=tuple(_cmd(n, a) for n, a in _OPS),
    panels=(_panels.channel_hub_spec(),),
    settings=(), stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    pending_handler("channel.ops_pending", "")


ENSURE_REFS = _ensure_refs
