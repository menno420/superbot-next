---
state: captured
origin: lab
shipped_pr: null
shipped_repo: menno420/superbot-next
merged_date: null
outcome: open
---

# Blackjack: the remaining surface after the solo-table flip (2026-07-10)

> **Status:** `ideas`
>
> **State:** captured (ledgered by the band-6 blackjack flip PR — the second
> playable game increment: the solo table on the session-view seam with
> IN-PLACE refresh; this file names exactly what is NOT in that slice, with
> the classify-or-fix classes for the subsystem's red sweeps).

**One line:** solo blackjack is playable end-to-end (`!blackjack [bet]` →
the shipped green table embed + Hit/Stand/Double on minted ids →
invoker-locked clicks run the audited move ops and EDIT the table in place →
settle writes the ledger); PvP buttons, the tournament orchestration, and
two `_unmapped` sweeps remain.

## Shipped in the flip PR (context)

- **Session-view refresh seam** (kernel, reusable band-wide):
  `refresh_session_view` re-renders a live session panel onto its ORIGINAL
  minted ids and presents with `edit_message_ref` set — the presenter edits
  instead of sending (parity twin: deferred-update ack type 6 +
  `edit_followup`, the shipped `safe_defer` + `safe_edit` loop; live twin:
  `interaction.response.defer()` + `message.edit`). Terminal results expire
  the session (the shipped `view.stop()` → polite expiry on late clicks).
- `blackjack.table` session-lifecycle panel + `blackjack.table_click`
  handler (`sb/domain/blackjack/panels.py` / `handlers.py`); the shipped
  `_game_embed` verbatim incl. the mixed-inline field layout and
  result-keyed accent colors.
- `game_state` timestamps back to the SHIPPED types (migration 0026 —
  0019 had silently carried them as BIGINT; the gating golden's `<ts>`
  symbols exposed it); solo rows now store the dealt-in channel and key on
  (user, guild) like the shipped `_active` dict
  (`fetch_user_checkpoint`/`delete_user_checkpoint`).
- The shipped **Daily Reward embed** (`economy.daily_card` panel +
  `economy.daily_view` handler + embed author/inline-field vocabulary in
  the render model) — the gating golden's `!daily` funding step pinned it;
  `sweep.daily` and friends ride the same fix.
- Flag-13 **encoding completion** (delegated, ⚑ owner-reviewable —
  docs/parity/flag-13-disposition-2026-07-10.md "Encoding completion"):
  `economy_audit_log.mutation_id` (kernel spine column on a domain row) and
  `economy_balances` (the ledgered-coins boundary's NEW home) dropped from
  both docs symmetrically; balance behavior stays pinned via the ledger's
  `delta`/`new_balance` bytes.
- `parity/goldens/blackjack/` 2/2 GREEN → `blackjack: ported` (third
  subsystem; ratchet `{events: 2, tables: 5, settings: 0}`).

## Remaining, in rough pull order

1. **PvP challenge/accept/move buttons on the wire** (quick-win, shared
   with rps): `blackjack.record_pvp_challenge`/`_accept` still mint g1
   Accept/Decline/Hit/Stand ids into `after["components"]` that no
   presenter renders — the challenge reply is text-only. Same fix shape as
   the solo table: a session-lifecycle panel per challenge (audience
   PUBLIC — the ops enforce the peer lock) or a presenter lane for
   g1 components. The refresh seam shipped here does the in-hand edits.
2. **PvP double-down** stays disabled (the ledgered deviation in
   `sb/domain/blackjack/ops.py`'s docstring: it needs mid-match re-escrow).
3. **Tournament orchestration** (`!bjtournament`/`!bjstart` pending
   terminals): private round channels + reaction sign-up — blocked on the
   reaction/live-adapter seams (see
   [`reaction-adapter-seam-2026-07-10.md`](reaction-adapter-seam-2026-07-10.md)).
   The entry/payout money legs are already live and tested.
4. **Natural-at-deal shape decision**: v1 renders the terminal table (all
   buttons disabled, result field) for a dealt natural; the shipped cog's
   exact natural-at-deal wire shape is unpinned by any golden — capture one
   at tournament-port time and true it up if it differs.
5. **Hub-button solo flow**: the `blackjack.hub` panel's Solo Free Play /
   Solo Bet actions still route the bare op (RESULT_CARD text) instead of
   opening the table view on the interaction surface — unify once a golden
   pins the shipped panel-click shape.

## Classify-or-fix — the blackjack-family `_unmapped` sweeps (ORDER 004)

| sweep | replay | class |
|---|---|---|
| `sweep.bjstatus` | **GREEN** (this PR) | — (the shipped "No active tournament." copy was already ported; the daily-embed + disposition work removed the residual noise) |
| `sweep.bjstart` | RED | `pending-terminal-copy` — golden says "No pending tournament."; v1 answers the honest pending terminal (tournament orchestration successor) |
| `sweep.bjtournament` | RED | `tournament-orchestration-missing` — golden is the registration announce embed + `add_reaction` sign-up; needs the reaction seam (item 3) |

(Classes named per the phase-2 rps precedent; both reds resolve with item 3.)
