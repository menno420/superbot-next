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
surface shipped in the band-6 PvP-on-the-wire PR** (item 1 below, kept for
the record); the tournament orchestration and four `_unmapped` rps sweeps
remain.

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
3. **Tournament orchestration** (`!rpsregister`/`!rpsstart`/`!rpsbot`/
   `!rpsmatchup` — honest pending terminals today): reaction sign-up,
   stage loops, match channels, no-prefix move parsing. Blocked on the live
   adapter / message band / reaction seam
   (`reaction-adapter-seam-2026-07-10.md`).
4. **`!rpssettings` oracle copy**: shipped bare `!rpssettings` answered
   "Invalid setting. Available settings: default_mode, default_best_of";
   v1 shows a read view. Decide verbatim-copy vs deliberate deviation when
   its golden re-homes.

## Classify-or-fix — the band's red goldens (ORDER 004 binding, this flip)

Gating dir `parity/goldens/rps_tournament/`: 1/1 GREEN (`sweep.rps`).
The six rps-family sweeps still live in `_unmapped` (non-gating; re-home as
they green):

| golden | state | class |
| --- | --- | --- |
| `sweep.rpshelp` | GREEN | — (verbatim `_HELP_TEXT`) |
| `sweep.rpsbot` | RED | `pending-terminal-copy` — oracle answered its own guard ("Invalid game mode…"); v1 answers the honest pending terminal (item 3 above) |
| `sweep.rpsstart` | RED | `pending-terminal-copy` (oracle: "Cannot start the tournament while registration is still active.") |
| `sweep.rpsmatchup` | RED | `pending-terminal-copy` (oracle: "Tournament is not active.") |
| `sweep.rpsregister` | RED | `tournament-orchestration-missing` — oracle opened reaction sign-up + wrote `guild_settings`; v1 answers the pending terminal (item 3) |
| `sweep.rpssettings` | RED | `settings-view-copy-deviation` (item 4 above) |
