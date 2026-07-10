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
click → audited `rps.solo_play` → result + money row); the PvP button surface,
the tournament orchestration, and four `_unmapped` rps sweeps remain.

## Shipped in the flip PR (context)

- Session-lifecycle views (kernel): engine-minted 32-hex custom ids bound in
  memory to declared component specs + opening args; invoker lock; polite
  expiry; never anchored (`sb/kernel/panels/engine.py`,
  `sb/kernel/interaction/adapters/component.py`).
- `rps_tournament.quickplay` panel (`sb/domain/rps/panels.py`) — the shipped
  `views/rps/solo_play._RpsView` shape; `parity/goldens/rps_tournament/`
  gating golden green; `rps_tournament` flipped `ported`.

## Remaining, in rough pull order

1. **PvP challenge buttons on the wire** (quick-win): `rps.pvp_challenge`
   already mints g1 Accept/Decline ids into `after["components"]` but the
   challenge reply is text-only — no button ever renders. Re-shape the
   challenge as a session-lifecycle panel (audience PUBLIC — the ops enforce
   the peer lock) or teach the presenter to render g1 components; the
   post-accept move buttons need the same treatment from inside a workflow
   result (needs a "workflow result presents components" decision).
   Blackjack has the identical gap (`blackjack.solo_start` components).
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
