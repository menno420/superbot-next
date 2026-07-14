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

## 💡 Session idea

Two of this slice's ledgered follow-ups are the same missing read: the
shipped log-channel BOT self-overwrite needs the bot's own identity,
and widening `is_ticket_staff` to the configured staff role needs a
member-roles read the click path doesn't carry (D-0084 ledger). One
guild-census read seam on the channel-state/adapters boundary — bot
member id + a member's role ids — would retire both at once and is a
prerequisite the ticket-open slice (transcripts) needs anyway; landing
it first keeps that slice from smuggling a port change in with domain
work.

## ⟲ Previous-session review

Fix slice A (btd6 paragon, PR #339) landed its one-terminal retirement
with the golden gate green and the deviation ledger fully cited
(D-0086) — the trail this slice rode directly was its per-message
session-state + in-place re-render recipe: the wizard's pending
ROLE/CHANNEL picks are the same overlay pattern (`_render_setup` state
overlay), so the "picks mutate the view, never the DB" shipped
semantics ported without invention. Its footer-honesty call (`local
formula`, no fake unreachable-API warning) set the precedent this
slice's honest new pending-terminal copy for eligible opens follows.
