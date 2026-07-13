# 2026-07-13 — game sections slice 3: hub renders the enabled set (ORDER 017 item 4)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · NIGHT-RUN lane · mandate: ORDER 017 item 4, slice c of D-0082

## Scope

Slice 3 (final) of `docs/design/game-sections.md` (D-0082 §6): the games
hub consumes the per-guild enabled set — the `games.hub_fields` provider
filters through the slice-1 `enabled_games(guild_id)` read seam, the hub
buttons gain `visible_when` enablement predicates (render-time drop +
resolve.py dispatch-time stale-click deny), sections with zero enabled
games drop, and fully-default guilds render BYTE-IDENTICAL to the ported
games goldens (fail-open all-enabled). Update contract = next-interaction
consistency (click-time re-resolution, §6.1); NO anchor sweep (named
successor). Stacked on `claude/minigame-sections-2` (PR #337, head
274dd56, unmerged at branch time). Covered by the existing lane claim
`control/claims/minigame-sections.md`. Excludes the peer fishing /
mining-WP / energy lanes.

## What shipped

_(in progress)_

## 💡 Session idea

_(in progress)_

## ⟲ Previous-session review

Newest card (`2026-07-13-minigame-sections-2.md`) is a complete, honest
close-out: its shipped list matches the branch head diff (sections panel
+ settings-hub group routing + golden re-cut, all flagged), its layout
budget note is verifiable against the spec, and it adopted slice 1's
guard recipe as a pre-push gate — this session adopts the same gate
order. Its PL-001 flag (dedicated `_GROUP_PANELS` mapping because
`games.hub` is the player hub) is honest and correctly scoped. Its 💡
(governance `enabled_map` batch read to make the submit diff atomic)
targets exactly this slice's provider work — evaluated this session:
still no batch read in governance; the provider keeps per-key reads
(the slice-1 seam shape) and the idea stays open for a governance-lane
follow-up rather than minting a cross-lane API here.
