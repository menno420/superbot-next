"""TICKET subsystem manifest (band-8 parity slice) — the shipped support
ticket command family verbatim (cogs/ticket_cog.py): the `!ticket` hub
(invoke_without_command → views/tickets/hub.py TicketHubView) and the
new/add/remove/claim/close subcommand lanes, each answering its shipped
guard byte at the v1 config-absent schema epoch.

Under-port boundary (sb/domain/ticket/service.py): the ticket config +
ticket-row stores, the channel-provisioning open flow, the persistent
launcher/control panels and `!ticketsetup`/`!ticketpanel`/
`!ticketblacklist` land with the ticket-mutation slice — hence
``stores=()`` / ``settings=()`` / ``events=()`` here: this slice declares
only the surfaces it fully carries.
"""

from __future__ import annotations

from sb.domain.ticket import handlers as _handlers
from sb.domain.ticket.handlers import install_ticket_panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _cmd(name: str, route, *, group: str = "",
         aliases: tuple[str, ...] = (), summary: str, usage: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group=group,
                       route=route, aliases=aliases, audience_tier="user",
                       capability="ticket", summary=summary, usage=usage)


_COMMANDS = (
    # @commands.group(name="ticket", invoke_without_command=True): the bare
    # invoke opened the hub (open_ticket_hub → embed + TicketHubView) —
    # goldens/ticket/sweep_ticket.json pins the panel bytes.
    _cmd("ticket", PanelRef("ticket.hub"),
         summary="Open the ticket hub — open a ticket or view your open "
                 "tickets.",
         usage="!ticket"),
    # the shipped subcommands verbatim (aliases included — ticket_cog.py
    # @ticket.command(name="new", aliases=["open", "create"])).
    _cmd("new", HandlerRef("ticket.new"), group="ticket",
         aliases=("open", "create"),
         summary="Open a ticket directly.",
         usage="!ticket new <subject>"),
    _cmd("add", HandlerRef("ticket.add"), group="ticket",
         summary="Add a member to this ticket (staff).",
         usage="!ticket add @member"),
    _cmd("remove", HandlerRef("ticket.remove"), group="ticket",
         summary="Remove a member from this ticket (staff).",
         usage="!ticket remove @member"),
    _cmd("claim", HandlerRef("ticket.claim"), group="ticket",
         summary="Claim this ticket (staff).",
         usage="!ticket claim"),
    _cmd("close", HandlerRef("ticket.close"), group="ticket",
         summary="Close the ticket in this channel (staff or the opener).",
         usage="!ticket close [reason]"),
)

MANIFEST = SubsystemManifest(
    key="ticket",
    version=1,
    commands=_COMMANDS,
    panels=install_ticket_panels(),
    settings=(),
    stores=(),
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    _handlers.ensure_handler_refs()
    _handlers.ensure_panel_refs()
    install_ticket_panels()


ENSURE_REFS = _ensure_refs
