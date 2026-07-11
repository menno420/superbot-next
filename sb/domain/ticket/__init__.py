"""TICKET domain (band-8 parity slice) — the shipped support-ticket
command family's SHIPPED-STATE surfaces (cogs/ticket_cog.py +
views/tickets/hub.py): the `!ticket` hub panel and the guard bytes of the
new/add/remove/claim/close lanes.

v1 scope note (the proof_channel under-port posture): the shipped ticket
CONFIG and ticket ROWS lived in the old bot's own tables
(services/ticket_service.py get_config / get_ticket_for_channel) — that
store, the channel-provisioning open flow, the launcher/control panels and
`!ticketsetup` land with the ticket-mutation slice. Every surface this
package ports answers from the config-absent state those goldens captured.
"""
