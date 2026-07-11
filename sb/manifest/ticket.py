"""TICKET subsystem manifest (band-8 parity slice + the `_unmapped`
ticket-admin re-home) — the shipped support ticket command family verbatim
(cogs/ticket_cog.py): the `!ticket` hub (invoke_without_command →
views/tickets/hub.py TicketHubView), the new/add/remove/claim/close
subcommand lanes (each answering its shipped guard byte at the
ticket-row-absent epoch), and the ticket-admin family — `!ticketpanel`
(views/tickets/launcher.py TicketLauncherView), `!ticketsetup`
(views/tickets/config_panel.py TicketConfigPanelView), `!ticketlimit` and
the `!ticketblacklist add|remove` group over the audited K7 ops
(sb/domain/ticket/ops.py; the oracle's ticket_mutation direct lane).

Under-port boundary (sb/domain/ticket/service.py): the `tickets` store and
the channel-provisioning open flow land with the ticket-mutation slice;
the setup wizard's interactive lanes are honest pending terminals
(sb/domain/ticket/handlers.py ticket.setup_pending).
"""

from __future__ import annotations

from sb.domain.ticket import handlers as _handlers
from sb.domain.ticket.handlers import install_ticket_panels
from sb.domain.ticket.ops import ensure_ops_refs, register_ops
from sb.domain.ticket.store import TICKET_BLACKLIST_STORE, TICKET_CONFIG_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _cmd(name: str, route, *, group: str = "",
         aliases: tuple[str, ...] = (), tier: str = "user",
         summary: str, usage: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group=group,
                       route=route, aliases=aliases, audience_tier=tier,
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
    # --- the ticket-admin family (the `_unmapped` re-home; every command
    # shipped perms_or_owner(manage_guild=True) ⇒ tier "staff", the
    # TIER_DISCORD_PERMISSION manage_guild floor verbatim).
    _cmd("ticketpanel", PanelRef("ticket.launcher"), tier="staff",
         summary="Post the public ticket launcher panel in this channel "
                 "(managers).",
         usage="!ticketpanel"),
    # `!ticketsetup` bare posts the config wizard (cogs/ticket_cog.py:
    # `if staff_role is None: open_ticket_config_panel(...)`) —
    # goldens/ticket/sweep_ticketsetup pins the panel bytes. The shipped
    # positional power-user form (`!ticketsetup @StaffRole [#log]`) is
    # UNPINNED and not ported: the PanelRef route opens the wizard for
    # both forms (ledgered under-port — the wizard-mutation slice).
    _cmd("ticketsetup", PanelRef("ticket.setup"), tier="staff",
         summary="Open the ticket setup wizard (managers).",
         usage="!ticketsetup"),
    _cmd("ticketlimit", HandlerRef("ticket.ticketlimit"), tier="staff",
         summary="Set the max simultaneously-open tickets per member "
                 "(managers).",
         usage="!ticketlimit <n>"),
    # @commands.group(name="ticketblacklist", invoke_without_command=True):
    # the bare invoke answers the shipped usage byte
    # (goldens/ticket/sweep_ticketblacklist pins it).
    _cmd("ticketblacklist", HandlerRef("ticket.ticketblacklist"),
         tier="staff",
         summary="Manage who may open tickets (managers).",
         usage="!ticketblacklist add|remove @user"),
    _cmd("add", HandlerRef("ticket.ticketblacklist_add"),
         group="ticketblacklist", tier="staff",
         summary="Bar a member from opening tickets.",
         usage="!ticketblacklist add @user"),
    _cmd("remove", HandlerRef("ticket.ticketblacklist_remove"),
         group="ticketblacklist", tier="staff",
         summary="Lift a member's ticket blacklist entry.",
         usage="!ticketblacklist remove @user"),
)

MANIFEST = SubsystemManifest(
    key="ticket",
    version=1,
    commands=_COMMANDS,
    panels=install_ticket_panels(),
    settings=(),
    stores=(TICKET_CONFIG_STORE, TICKET_BLACKLIST_STORE),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.ticket import store as _store

    _handlers.ensure_handler_refs()
    _handlers.ensure_panel_refs()
    install_ticket_panels()
    ensure_ops_refs()
    _store.ensure_refs()


ENSURE_REFS = _ensure_refs
