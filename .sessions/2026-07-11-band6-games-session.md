# 2026-07-11 — band-6 games lane (seven slices: ports, PvP, tournaments, polish)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

The band-6 games lane, run CONTINUOUS per Q-0265 across 2026-07-10/11:
take the two game subsystems (rps_tournament, blackjack) from
pending-terminal shells to fully playable ports — solo, PvP, and
tournament — with every game-family golden green, plus the
cross-cutting composition-parity invariant that opened the lane.
Oracle: menno420/superbot `disbot/cogs/rps_tournament_cog.py` /
`blackjack_cog.py` + their views/services (search_code fragments;
get_file_contents ACL-denied as known). Seven merged-on-green PRs
(#114, #117, #120, #124, #130, #133, #138) plus lane heartbeats #127
and #136 and this wrap-up.

## What shipped

1. **#114 — the composition-parity invariant** (`tests/unit/
   invariants/test_composition_parity.py`): both roots' registered ref
   sets diffed in a clean subprocess — unregistered pending terminals
   now fail CI for EVERY plugin (the BUG A class-killer), plus the
   blackjack/rps register-at-import fix and the 99-ref ensure-only
   burn-down ledger. Merge `385df11`.
2. **#117 — rps_tournament pending→ported**: `!rps` quick-play on a
   NEW session-view kernel seam (minted 32-hex component ids +
   invoker-lock). Merge `ec2bcf2`.
3. **#120 — blackjack pending→ported**: `!blackjack` solo
   (hit/stand/double) on an edit-in-place refresh seam; carried the
   flag-13 encoding completion. Merge `4c1882b`.
4. **#124 — PvP for BOTH games**: challenge → accept
   (escrow-in-one-txn) → play → resolve on one staged message. Merge
   `2958224`.
5. **#130 — rps tournament + THE REACTION SEAM**: three plugin-agnostic
   kernel seams (reaction ingress registry/dispatch + live adapter
   twin, `RenderedPanel.self_reactions`, click-driven CHANNEL_ANCHOR
   opens as fresh sends); full register → button+✅ sign-up → bracket →
   champion-payout flow. Merge `c3f7a02`.
6. **#133 — blackjack tournament**: the #130 shape pure-domain (zero
   new kernel seams) + SETTLE-ONCE in both games' champion-payout ops
   (flag-row delete first as the check-and-set — closes the #130
   review question's double-payout race). Merge `9923151`.
7. **#138 — copy-parity polish**: flipped `sweep.rpssettings` (the
   LAST red game-family golden) on the shipped settings command
   verbatim, riding band-1 `settings.set_scalar`; plus the render-once
   `state.settled` guard in both games' tournament finish paths
   (closes the #133 question's cosmetic half). Merge `9ea90e9`.

Parity movement across the session (all lanes at main `9ea90e9`):
1 → 12 subsystems ported; report leg 15 → 45 of 465 goldens green
(465/465 replayable); gate GREEN 33/33 across the 12 ported (CI gate
job 86496962174); rps_tournament 6/6, blackjack 5/5 — no red
game-family golden remains. Units 1272 passed / 4 skipped in CI at
`9ea90e9` (run 29134819997).

## Notes

- **Key seams built (reusable band-wide):** session-view minted
  component ids + invoker-lock (#117), the edit-in-place refresh seam
  (#120), reaction ingress + self_reactions + channel-anchor-off-click
  (#130). #133 and #138 rode them with ZERO new kernel seams — the
  seam curve bent the right way.
- **Money hardening:** settle-once by atomic flag-row delete count
  (#133, both games) + render-once by in-memory `state.settled`
  check-and-set (#138, both games); direct-leg double-call tests pin
  both.
- **Remaining game surface is unpinned polish only**, ledgered with
  classes in docs/ideas/rps-tournament-remaining-surface-2026-07-10.md
  and docs/ideas/blackjack-remaining-surface-2026-07-10.md (rpsbot
  deep flow, natural-at-deal wire shape, time-driven depth, private
  round channels, autostart timer, PvP double-down, hub-button solo).
  Per the Q-0265 honesty guard the lane stops here: next wake starts
  band-7 per the canonical order or takes owner direction.
- **Codex came back online mid-wrap:** full review on #138 (comments
  4941074976 + 4941104857, "no major issues"; it ran the PR's 4 new
  tests itself) — OWNER-ACTION 4 retired in control/status.md. Six
  earlier lane questions stay codex-unanswered; #130's was
  self-answered by #133's guard.
- **Pre-existing test-order flake flagged** (not this lane's): app +
  authority + band6 in non-canonical order fails 3 old tests at clean
  main (spec-refs registries cleared without re-arming ENSURE_REFS);
  canonical order and CI green. Successor hygiene slice.

## 💡 Session idea

Every tournament race this lane closed (#130 double-payout, #133
double-render, #138 altitude question) traces to ONE root shape:
in-memory orchestration state mutated across await points with the
claim and the stage-decision in different functions. A tiny
`claim_once(state, "field")` helper in the kernel (check-and-set, no
await, returns bool) plus a lint that flags any `state.<flag> = True`
not behind it would turn a recurring review-question class into a
grep — the settled/active flags in both games would be its first two
consumers, and every future game port inherits the discipline for
free.

## ⟲ Previous-session review

The prior session's parked note ("blackjack/rps ensure-only
registration") converted cleanly into this lane's opener — #114 not
only fixed the two named plugins but killed the class with an
invariant test, which then caught real drift twice during the
tournament slices; parking-notes-as-next-openers is working. What it
under-delivered: nothing warned that the ORACLE's own capture leaks
in-memory state across cases (sweep.rpsstart is corpus-order green by
construction — #130 had to discover, reproduce, and ledger that
honesty class from scratch), and no predecessor documented the
rebase-regen dance for `manifest.snapshot.json` as a RULE (three
slices re-learned "take main's + manifest_compile --write" before the
phase-3 lesson finally stuck in the lane notes).
