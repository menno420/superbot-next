# control/status.md — coordinator heartbeat

> ⚠️ **RETIRED (2026-07-17) — control-plane message bus wind-down.** This
> heartbeat and the `control/` inbox/outbox bus are retired ahead of the Claude
> Code Projects EAP going read-only Tue 2026-07-21; the Project will be recreated
> fresh. Kept as historical record — the live "what is true now" ledger is
> [`docs/current-state.md`](../docs/current-state.md); the forward task list is
> [`docs/NEXT-TASKS.md`](../docs/NEXT-TASKS.md).

updated: 2026-07-17T13:30:00Z
phase: EAP wind-down — autonomous apparatus retired, awaiting Project recreation
health: green
kit: v1.17.0 · check: green · engaged: no
last-shipped: #506 — coordinator close-out 2026-07-17 (heartbeat + card)
blockers: none — the fleet-wide PR backlog was cleared 2026-07-17 (#499 / #500 / #503 / #505 / #506 landed)
orders: acked=001-023 done=001-023
⚑ needs-owner: (1) disarm the residual failsafe wake triggers via the routines UI — both enabled duplicates of "SuperBot 2.0 failsafe wake": trig_01E86nBnXqesQTwm6WA4mSUD + trig_01UC7wiV3n5Vgs3RpSQt4gWz (no standing wake chain in the recreated Project); (2) delete 4 orphan merged branches (blocked agent-side by the GitHub 403 ref-delete wall, recorded 2026-07-17): #385 claude/energy-slice-2, #473 claude/title-equip-write, #476 claude/curation-row72, #424 claude/wp-stack-reconcile.
notes: Suite 3160 passed / 29 skipped; golden-parity 523/523; check_parity_depth 49/49 ported (kernel ported); run_golden_parity 50/50 subsystems ported (#501/#500/#506 close). The autonomous apparatus (self-wake / pacemaker / message bus) is retired — no standing wake trigger should be re-armed. Forward work: docs/NEXT-TASKS.md.
