# 2026-07-13 — ticket setup panel port (ORDER 017 night-run fix slice B)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice B · mandate: ORDER 017
  (PR #323), gap row 8 of `docs/status/completeness-table-2026-07-13.md`

## Scope

Retire the `ticket.setup_pending` terminal: arm the `!ticketsetup` wizard's
3 pending actions (🪄 Auto-create log channel · ✅ Enable tickets ·
📋 Post open-ticket panel here) + 2 native selectors (staff-role ROLE pick ·
transcript-log CHANNEL pick) as a faithful port of the oracle's
`views/tickets/config_panel.py` TicketConfigPanelView + the audited
`ticket_mutation.update_config` / `create_log_channel` seams
(menno420/superbot). The command twins (`!ticketlimit` /
`!ticketblacklist`) are already live; adjacent honesty: the hub embed's
configured branch + the open lane's eligibility copy stop lying once a
guild can actually enable tickets.

Definition of done: implemented + tested + golden-parity
(goldens/ticket/sweep_ticketsetup initial-open bytes unchanged) + real
error copy + final user-facing copy.
