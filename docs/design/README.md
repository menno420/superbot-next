# superbot-next — design docs

> **Status:** `reference`
>
> Pre-build design records: one doc per designed-but-not-yet-built (or
> in-build) surface, each pinned to its `docs/decisions.md` entry. A design
> doc is a PLAN — the code and the decision ledger win once slices land.

## Planning-mode design series (2026-07-18)

Forward design proposals from the **2026-07-18 planning phase**. The
completeness-reconciliation snapshot
([`../status/completeness-table-2026-07-18.md`](../status/completeness-table-2026-07-18.md),
#525) found the user-facing port surface essentially exhausted and recommended
shifting the loop toward PLANNING mode — turning the D1–D6 forward lanes (and a
couple of decision-sized backlog items) into fuller design docs the owner reacts
to and prioritizes. **One doc per PR**; each is grounded in the completeness
snapshot and cites real code. Future design-doc PRs add their row + file here.

| Doc | Topic | Status |
|---|---|---|
| [D4](D4-observability-surface.md) | Observability surface (metrics / readiness / structured logs) | **this PR** |
| D5 | End-to-end / live-guild test harness | planned |
| [D2](D2-realtime-minigame-framework.md) | Real-time minigame framework | planned |
| [D1](D1-themed-card-renderer.md) | Themed card renderer (rank / profile hero cards) | **this PR** |
| D3 | Access-matrix / audit dashboard | planned |
| D6 | Autonomy-apparatus removal | planned |
| [B10](B10-panel-route-origin.md) | Role-hub route-origin back-button (panel-engine signal) | plan |
| B8 | ux_lab 9-wing foundation-then-per-wing | planned |

## Beyond D1–D6 — production-readiness tracks

New production-readiness design topics opened outside the D1–D6 planning lanes.
Same rules: **one doc per PR**, grounded evidence-first in real code with
`file:line` citations. Future production-readiness design-doc PRs add their row
+ file here.

| Doc | Topic | Status |
|---|---|---|
| [OWNER DECISIONS (2026-07-18)](OWNER-DECISIONS-2026-07-18.md) | Consolidated morning agenda — every design-doc owner-question + standing gates, prioritized by leverage | owner-guidance |
| [Security](S-security-rotation-and-least-privilege.md) | Secret rotation (zero-downtime) + startup fail-closed + least-privilege | plan |

## Index

- [game-sections.md](game-sections.md) — per-guild minigame/casino
  enablement over governance visibility (ORDER 017 item 4). Its §7
  plug-in slot is now filled by
  [`../specs/casino-section-spec.md`](../specs/casino-section-spec.md)
  (ORDER 031 phase 1 — inventory, taxonomy, enablement semantics, panel
  contract; the section BUILD stays a separate order).
- [anchor-refresh-sweep.md](anchor-refresh-sweep.md) — PROPOSED
  (owner-reviewable, no D-entry yet): the game-sections successor
  sweep that would edit anchored channel panels on enablement change;
  four design calls with options and costs.

## Beyond D1–D6 — production-readiness tracks

NEW design topics beyond the D1–D6 forward lanes: operational hardening the
production cutover depends on. Each is a PLAN (`> **Status:** \`plan\``) the
owner reacts to and prioritizes.

| Track | Doc | What it proposes |
|---|---|---|
| Ops runbook | [Ops runbook](O-ops-migration-backup-restore-rollback.md) | The recoverability loop — migrate → backup → restore → rollback → deploy(Railway) — proven green end-to-end in CI: a restore-verify row-level-integrity leg, a rehearsed migrate+rollback drill on ephemeral Postgres, and a consolidated recovery runbook. |
