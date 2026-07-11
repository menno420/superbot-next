# 2026-07-11 — status heartbeat post-#215 (kit v1.12.1, parity 39/50)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable 5 · high · maintenance (Q-0194)

## Scope

Docs/status-only slice: bring control/status.md current at HEAD `977bb27b`
(#215's merge). status.md was last written at 2026-07-11T20:20Z by #212
(commit `c3037d5`) and predated three merged PRs: #213 (`f71d60b`,
F-001/F-002 wallet-race + F-003 parity-gate false-green fixes), #214
(`827b134`, treasury pending→ported — parity 39/50, gate 266/266), #215
(`977bb27`, substrate-kit v1.12.0→v1.12.1 — the kit line's heartbeat bump
was explicitly lane-owed per the #215 commit body and card). No runtime
code. control/inbox.md untouched.

## What was updated (every claim cites its commit)

- `updated:` 2026-07-11T20:20Z → 2026-07-11T23:10Z.
- kit line: v1.10.1 → v1.12.1, citing #215 (merge `977bb27`, `kit_version`
  1.12.1 pinned in substrate.config.json:47); the prior v1.10.1 #166 check
  record kept verbatim as history.
- health line: new POST-#215 waypoint prepended — parity **39/50**
  subsystems ported (#214 `827b134` flipped treasury; 39 ported / 11
  pending / 50 rows in parity/parity.yml), gate **266/266** goldens across
  the 39 ported per the #214 merge body; the WAVE-5 END waypoint kept
  verbatim, still valid at its shas.
- last-shipped: #215 (`977bb27`), with #214/#213 named; the WAVE-5 wrap-up
  fold kept verbatim as PRIOR FOLD.
- New dated round record "Coordinator round 2026-07-11T23:00Z
  (post-#213/#214/#215 heartbeat)" at the top of the lane-record area:
  #213/#214/#215 facts as above, plus the owner-directed money-race
  priority — farm/mining same-class sites
  (control/claims/codex-risk-review-prs-196-206.md) verified UNFIXED at
  `977bb27b` (grep for FOR UPDATE / with_for_update in sb/domain/farm and
  sb/domain/mining: no matches), child fix session dispatched; band-7
  successor lane nudged to resume.
- The four OWNER-ACTION entries and the orders acked/done line carried
  forward VERBATIM (untouched).

## 💡 Session idea

The `kit:` heartbeat bump keeps going stale because kit-upgrade PRs
hard-scope-exclude control/status.md and no lane durably owns the bump
(the v1.12.1 card flags this for the second wave running). A one-line
`owner:` field on the kit heartbeat line itself — naming the lane that owes
the bump — would turn the per-wave directive into a durable contract the
next coordinator round can grep for.

## ⟲ Previous-session review

The #212 heartbeat's WAVE-5 END waypoint was exact — its 38/50 and 264/264
counts, merge SHAs and CI job quotes all still reconcile as the immediate
pre-#213/#214/#215 baseline, which made this fold a pure prepend instead of
a rewrite. The improvement it enabled and this session kept: waypoints
marked "verbatim, still valid at its shas" let a successor add the new
current waypoint without touching history.
