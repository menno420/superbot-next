# 2026-07-13 — setup on-ready resume sweep + app-boot seam (ORDER 019 item 5a, night lane)

> **Status:** `in-progress`

- **📊 Model:** `Fable (Claude 5 family)` · NIGHT lane · mandate: ORDER 019
  item 5(a), setup row of `docs/status/completeness-table-2026-07-13.md`
  ("the on-ready resume sweep (needs an app-boot seam)"); claim:
  `control/claims/night-setup-followups-windowed-select.md` (PR #431)

## Scope

Land the app-boot seam the setup on-ready resume sweep needs, then the
sweep itself: a kernel-band boot-hook registry (registration + firing
order + per-hook error isolation) the manifest wires — no kernel→domain
import edge — plus the `sb/domain/setup` sweep porting the oracle's
`SetupCog.on_ready` pair (`_resume_launchers` +
`revive_essential_flows`, menno420/superbot @bbc524e4): on boot, find
persisted setup-session rows with workspace/essential message pointers
and re-render them in place to the correct state (vanished essential
message → clear the anchor through the audited K7
`setup.clear_essential_anchor` op, the oracle semantics).

Definition of done: seam + sweep implemented + unit-tested (seam
registration/order/isolation; sweep resumed/re-rendered vs no-op
branches), `python3 -m pytest` green, bootstrap strict check green.

## 💡 Session idea

[[fill: close-out]]

## ⟲ Previous-session review

[[fill: close-out]]
