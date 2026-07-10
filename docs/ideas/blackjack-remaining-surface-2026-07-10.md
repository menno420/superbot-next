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
settle writes the ledger); **the PvP button surface shipped in the band-6
PvP-on-the-wire PR** (item 1 below, kept for the record); the tournament
orchestration and two `_unmapped` sweeps remain.

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

1. **PvP challenge/accept/move buttons on the wire** — ✅ SHIPPED (band-6
   PvP-on-the-wire PR): `!blackjack @player [bet]` now opens the
   `blackjack.pvp` session panel (audience PUBLIC — the ops enforce the
   peer/own-hand locks) whose Accept/Decline and post-deal Hit/Stand
   buttons carry the restart-safe `g1:` ids; every stage EDITS the one
   challenge message via `refresh_session_view` (challenge → the dealt
   match → the shipped `🃏 Blackjack PvP Result` embed, ECONOMY_COLOR on
   a win / GAME_COLOR on a tie). Deliberate deviations from the shipped
   shape, ledgered here: (a) the shipped `_start_pvp` sent one PUBLIC
   channel table PER PLAYER (`channel.send(content=player.mention,
   embed=_game_embed(...))`) and edited each separately; v1 stages the
   whole match on ONE shared message showing both public hands (the
   clicker's buttons play the clicker's OWN hand — same information
   surface, one message instead of three). (b) Both-dealt-naturals now
   settle INSIDE the accept txn (the shipped `_resolve_pvp` "or both
   natural-blackjack out" branch) — without it the on-the-wire match
   would strand two finished hands; when that branch fires, the four
   balance changes (2× escrow + 2× refund) exceed the op's two
   `economy.balance_changed` emit slots, so two best-effort events are
   skipped (ledger rows are complete — the emit budget is telemetry
   only). (c) The challenge-accept edit skips the transient
   "✅ Challenge accepted — dealing hands…" frame (deal happens in the
   same txn; the match view IS the ack). PvP double-down stays disabled
   (item 2).
2. **PvP double-down** stays disabled (the ledgered deviation in
   `sb/domain/blackjack/ops.py`'s docstring: it needs mid-match re-escrow).
3. **Tournament orchestration** (`!bjtournament`/`!bjstart` pending
   terminals): NO LONGER SEAM-BLOCKED — the reaction seam + the
   registration-panel/self-reaction/flag-row/tournament-flag mechanisms
   shipped with the band-6 RPS tournament-orchestration PR
   (`sb/kernel/interaction/reactions.py`, `RenderedPanel.self_reactions`,
   `guild_settings` migration 0027, `sb/domain/games/tournament_flag.py` —
   the shipped shared-write is intentional). The blackjack successor is
   pure-domain: the `sweep.bjtournament` golden pins its registration
   embed (🃏 Join button + ✅ primer + `active_tournament=blackjack`);
   rounds ride the solo-table seam per entrant instead of the shipped
   private round channels (ledger the deviation, the RPS precedent).
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
