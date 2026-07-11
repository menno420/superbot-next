# 2026-07-11 — substrate-kit upgrade v1.10.0 → v1.10.1 (distribution wave)

> **Status:** `in-progress`

- **📊 Model:** fable-5 · high · maintenance kit upgrade (Q-0261.3)

## Scope

Kit-seat distribution session (owner directive Q-0261.3): upgrade the
vendored substrate-kit from v1.10.0 to v1.10.1 using the pinned,
sha256-verified release asset (tag v1.10.1 @ kit commit `7e361bb`,
release run 29146372884 green, asset sha256
`fbe83ce35d1fb3b544ac58fc60ee2609eaa6c69c13d77883e9fdc5da6bbad158` —
three-way verified: coordinator-stated == GitHub asset digest ==
release.json == local sha256). Kit-owned files only; no domain work.
Payload: session-gate `tail -1` multi-card shadowing fix (every card in
the diff graded) + `_MODEL_DOCTRINE_PHRASE` emphasis-blind presence
check.
