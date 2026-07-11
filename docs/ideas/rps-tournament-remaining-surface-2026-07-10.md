---
state: captured
origin: lab
shipped_pr: null
shipped_repo: menno420/superbot-next
merged_date: null
outcome: open
---

# RPS: the remaining surface after the quick-play flip (2026-07-10)

> **Status:** `ideas`
>
> **State:** captured (ledgered by the band-6 rps_tournament flip PR — the
> first playable game increment shipped the session-view seam + the solo
> quick-play loop; this file names exactly what is NOT in that slice, with
> the classify-or-fix classes for the band's red goldens).

**One line:** solo quick-play is playable end-to-end (picker → invoker-locked
click → audited `rps.solo_play` → result + money row); **the PvP button
surface shipped in the band-6 PvP-on-the-wire PR** (item 1); **the
tournament orchestration core + the reaction seam shipped in the band-6
tournament-orchestration PR** (item 3 below, deviations recorded); the
`!rpsbot` bot-match flow and the `rpssettings` copy decision remain.

## Shipped in the flip PR (context)

- Session-lifecycle views (kernel): engine-minted 32-hex custom ids bound in
  memory to declared component specs + opening args; invoker lock; polite
  expiry; never anchored (`sb/kernel/panels/engine.py`,
  `sb/kernel/interaction/adapters/component.py`).
- `rps_tournament.quickplay` panel (`sb/domain/rps/panels.py`) — the shipped
  `views/rps/solo_play._RpsView` shape; `parity/goldens/rps_tournament/`
  gating golden green; `rps_tournament` flipped `ported`.

## Remaining, in rough pull order

1. **PvP challenge buttons on the wire** — ✅ SHIPPED (band-6
   PvP-on-the-wire PR): `!rps @player [bet]` now opens the
   `rps_tournament.pvp` session panel (audience PUBLIC — the ops enforce
   the peer/turn locks) whose Accept/Decline and post-accept move buttons
   carry the restart-safe `g1:` ids; every stage EDITS the one challenge
   message via `refresh_session_view` (challenge → accepted → the shipped
   `✂️ RPS PvP Result` embed). Deliberate deviations from the shipped
   multi-message shape, ledgered here: (a) the shipped bot EDITED the
   challenge message and then SENT a separate `_RpsPvpPlayView` message
   ("Pick your move" → an EPHEMERAL `_RpsMovePickerView` per player);
   v1 stages the whole loop on the challenge message with three public
   move buttons — move secrecy is preserved (a click's identity is never
   broadcast; moves stay hidden until both are in), and the ephemeral
   picker hop disappears. (b) The shipped terminal posted a result view
   with a back-to-hub button; v1 disables the move buttons in place
   (hub re-entry stays one `!rps` away). Copy is otherwise
   oracle-verbatim (challenge embed, "✅ Challenge accepted — both
   players, choose your move!", "❌ <player> declined the challenge.",
   "🎉 <winner> wins!" / "🤝 Tie! No coins exchanged.",
   SUCCESS_COLOR/GAME_COLOR accents).
2. **Solo result view edit-in-place**: the shipped view EDITED the picker
   message into the result embed + a "play again" view; v1 sends a follow-up
   text. Needs a message-edit presenter seam.
3. **Tournament orchestration** — ✅ SHIPPED (band-6
   tournament-orchestration PR): `!rpsregister` sends the golden-pinned
   registration embed + green **Join Tournament** button (run-minted
   session id) + the shipped ✅ self-reaction primer, writes the shipped
   `guild_settings` `active_tournament=rps` flag row (audited op,
   migration 0027 imports the shipped table NAME_STABLE); sign-up rides
   BOTH the button and the ✅ reaction (the new kernel reaction seam —
   `sb/kernel/interaction/reactions.py` + the live
   `sb/adapters/discord/reaction_feed.py`, the seam
   `reaction-adapter-seam-2026-07-10.md` named); entry fees debit through
   `rps.tournament_enter` (reason `rps:entry_fee`, refund-on-boot via the
   escrow recovery roster); `!rpsstart` runs the shipped guards verbatim,
   shuffles, pairs, runs best-of rounds, byes advance; the champion settles
   through `rps.tournament_payout` (`rps:tournament_win` pot /
   `rps:tournament_free_reward` 100 🪙 consolation, flag cleared in the
   SAME txn) with the shipped champion copy. HARDENED (blackjack
   tournament PR, closing the #130 review's free-branch race): the
   payout leg's `active_tournament` flag-row delete now runs FIRST as a
   check-and-set — the free branch has no escrow rows to consume, so
   two racing champion resolutions could both have paid the 100 🪙
   consolation; keying settle on the atomic row-deletion count makes it
   fire exactly once. Match stats land through the
   audited `rps.tournament_result` op. `!rpsmatchup` creates manual
   matches (shipped guards verbatim). **Deliberate deviations, ledgered:**
   (a) matches are BUTTON views in the tournament's home channel (the #124
   PvP seam) instead of the shipped private match channels + no-prefix
   message parsing — channel provisioning rides the resource-provision
   port (the counting-band precedent); per-throw moves reveal on the one
   match message with a score line; (b) the 10-minute close is LAZY
   (checked when `!rpsstart` runs — the shipped background sleep task and
   the 5-minute role-ping reminder loop are time-driven class); the
   close-collect of reaction users is replaced by live incremental
   sign-up through the reaction feed (same roster, no batch read);
   (c) orchestration state stays in memory like the shipped cog — a
   restart forfeits the bracket and boot REFUNDS every entry row
   (`rps_tournament_entry` joined ESCROW_RECOVERY_SUBSYSTEMS); (d) the
   round/bye/champion announce lines ride the RC-21 channel emitter
   (plain sends), copy adapted where the oracle's was channel-scoped.
   **Corpus-order note (honesty):** `sweep.rpsstart`'s golden captured the
   oracle's in-memory cross-case leak (registration was still open when
   the sweep recorded); the replay reproduces it identically in corpus
   order (`sweep.rpsregister` precedes it in the sorted case list) and is
   RED in isolation by construction — same class as the recorded oracle.
4. **`!rpssettings` oracle copy**: shipped bare `!rpssettings` answered
   "Invalid setting. Available settings: default_mode, default_best_of";
   v1 shows a read view. Decide verbatim-copy vs deliberate deviation when
   its golden re-homes.
5. **`!rpsbot` bot-match flow**: the mode guard now answers the shipped
   copy verbatim (its sweep is green); a VALID mode still gets the honest
   pending terminal — the shipped bot match ran in a private match channel
   with no-prefix typed moves (message band + channel provisioning). A
   bounded successor could ride the quickplay button view per opponent.
6. **Tournament depth not carried (time-driven class)**: the 5-minute
   registration reminder loop (role ping), the timed auto-close announce,
   and the shipped `end_registration` batch collection of reaction users
   (replaced by live incremental reaction sign-up).

## Classify-or-fix — the band's red goldens (ORDER 004 binding, this flip)

Gating dir `parity/goldens/rps_tournament/` (after the tournament-
orchestration PR re-homed the four newly-green sweeps): 5/5 GREEN.

| golden | state | class |
| --- | --- | --- |
| `sweep.rps` | GREEN | — (quick-play flip) |
| `sweep.rpshelp` | GREEN | — (verbatim `_HELP_TEXT`; lives in goldens/help) |
| `sweep.rpsbot` | GREEN (re-homed) | fixed — the shipped "Invalid game mode…" guard is real behavior; the deeper bot-match flow stays an honest pending terminal (item 5 below) |
| `sweep.rpsstart` | GREEN (re-homed) | fixed in corpus order — the shipped registration-active guard verbatim; isolated replay is red by construction (the golden itself captured the oracle's in-memory cross-case leak — see item 3's corpus-order note) |
| `sweep.rpsmatchup` | GREEN (re-homed) | fixed — the shipped "Tournament is not active." guard verbatim |
| `sweep.rpsregister` | GREEN (re-homed) | fixed — the golden-pinned registration embed + Join button + ✅ primer + the `guild_settings` flag row, byte-for-byte |
| `sweep.rpssettings` | RED (stays `_unmapped`) | `settings-view-copy-deviation` (item 4 above, unchanged) |
