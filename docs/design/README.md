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

All 8 docs are written and committed (each carries a `plan` Status badge); the
Status column below now mirrors that badge, with landed per-doc slice progress
noted inline.

| Doc | Topic | Status | Staged questions settled |
|---|---|---|---|
| [D4](D4-observability-surface.md) | Observability surface (metrics / readiness / structured logs) | plan · P1 outbox metric families armed (#562) | — |
| [D5](D5-e2e-test-harness.md) | End-to-end / live-guild test harness | plan | — |
| [D2](D2-realtime-minigame-framework.md) | Real-time minigame framework | plan | — |
| [D1](D1-themed-card-renderer.md) | Themed card renderer (rank / profile hero cards) | plan · Slice 1 (render band) landed (#560/#561) | Q1/Q2 — bundle DejaVu fonts + adopt Pillow as a hard runtime dep (the render-band Pillow decision; NOTE Pillow shipped at `>=12.3.0`, not `<12`, per the #561 security bump) |
| [D3](D3-access-audit-model.md) | Access-control + audit-log data model (access-matrix / audit dashboard) | plan | Q2 — audit-log retention stays permanent; Q3 — M1 access granularity is per-channel (per-command deferred) |
| [D6](D6-autonomy-apparatus-removal.md) | Autonomy-apparatus removal (safe removal sequence) | plan | Q1 — destructive removal deferred to the recreated Project (post-2026-07-21) |
| [B10](B10-panel-route-origin.md) | Role-hub route-origin back-button (panel-engine signal) | plan |
| [B10 plan](B10-route-origin-implementation-plan.md) | B10 route-origin — execute-on-approval implementation plan (Q2–Q6 resolved; Q1 routed) | plan | — |
| [B8](B8-ux-lab-wings.md) | ux_lab 9-wing foundation-then-per-wing | plan | — |

Decision provenance lives in `docs/decisions.md`; each doc's own footer pins its
settling entries (D1, D3, D6), so the questions above are cited here in prose
only, not re-stamped.

## Beyond D1–D6 — production-readiness tracks

New production-readiness design topics opened outside the D1–D6 planning lanes.
Same rules: **one doc per PR**, grounded evidence-first in real code with
`file:line` citations. Future production-readiness design-doc PRs add their row
+ file here.

| Doc | Topic | Status |
|---|---|---|
| [OWNER DECISIONS (2026-07-18)](OWNER-DECISIONS-2026-07-18.md) | Consolidated morning agenda — every design-doc owner-question + standing gates, prioritized by leverage | owner-guidance |
| [Security](S-security-rotation-and-least-privilege.md) | Secret rotation (zero-downtime) + startup fail-closed + least-privilege | plan |
| [Resilience](R-resilience-delivery-and-db.md) | Outbox→Discord delivery retry-reach + dead-letter replay; DB pool reconnect/backoff + circuit breaker + fast fail-closed | plan |
| [settings group_pending epic](settings-group-pending-epic-plan.md) | Per-group scalar-edit page (S0 frame + S1–S7 widgets) replacing `group_pending` for non-hub groups only — owner option A | plan |

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
