"""The SUPPORT-TICKETS section flow (the routing-ticket slice — the
FINAL section-flow slice), ported from the oracle (menno420/superbot,
read from the LOCAL oracle clone: views/setup/sections/ticket.py):

* the THIN WIZARD ADAPTER, verbatim posture: "The interactive UI
  itself lives in the ticket domain … so the wizard and the
  ``!ticketsetup`` command share one fully button/dropdown-driven
  panel. This section is the thin wizard adapter: it opens that panel
  and marks setup progress." The hub button and the wizard's Customize
  both land on the ALREADY-SHIPPED ``ticket.setup`` panel
  (sb/domain/ticket/setup_panel.py — the armed `!ticketsetup` port);
* NO staged draft op, the oracle posture verbatim: "All writes go
  through the audited ``ticket_mutation`` direct lane (ticket config
  is its own table, not the ``set_setting`` pipeline), so this section
  stages no draft op — like the ``suggestions`` / ``server_scan``
  sections." The ported twin: the panel's writes ride the audited K7
  ``ticket.update_config`` / ``ticket.create_log_channel`` ops
  (D-0618); ``sections.py`` declares ``op_kinds=()`` — reconciled
  against the oracle source, they agree;
* NO section card and NO recommended builder (ticket.run opens the
  panel directly — the oracle section never routed through
  ``section_card.show``); the linear wizard step still walks it (the
  registered customize destination is the panel, the skip copy rides
  ``SECTION_SKIP_DESCRIPTIONS``).

Kernel-idiom divergence, ledgered: the oracle marked progress AFTER
sending the panel, best-effort — same order here over the K7
``setup.mark_in_progress`` op (the section_card.py seam).

NO GOLDEN drives the hub click (the panels.py module pin); the
``ticket.setup`` panel's own renders stay exactly as the ticket band
shipped them.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED

__all__ = ["SLUG", "ensure_setup_ticket_refs"]

logger = logging.getLogger("sb.domain.setup")

SLUG = "ticket"


def _ticket_panel_id() -> str:
    """The shipped ticket config panel (sb/domain/ticket/setup_panel.py
    ``SETUP_PANEL_ID`` — read lazily, the guild_directory cross-domain
    precedent)."""
    from sb.domain.ticket.setup_panel import SETUP_PANEL_ID

    return SETUP_PANEL_ID


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.open_section_ticket")):
        return

    @handler("setup.open_section_ticket")
    async def open_section_ticket(req) -> Reply | None:
        """The hub's Support-Tickets section button — gate exactly like
        the shipped hub button, open the shared ticket config panel
        (ticket._open_panel), record the step marker (the shipped
        best-effort order: panel first, marker after)."""
        from sb.domain.setup import section_card, wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        if not int(req.guild_id or 0):
            # shipped copy, verbatim (ticket._open_panel's guild guard).
            return Reply(BLOCKED, "This can only be used in a server.")
        await _open(req, _ticket_panel_id())
        await section_card.mark_step_in_progress(req, SLUG)
        return None


def _register_section() -> None:
    from sb.domain.setup import section_card

    # the wizard Customize destination is the shared panel itself
    # (oracle customize=_open_panel); NO recommended builder, NO card.
    section_card.register_customize_panel(SLUG, _ticket_panel_id())


_register()
_register_section()


def ensure_setup_ticket_refs() -> None:
    _register()
    _register_section()
