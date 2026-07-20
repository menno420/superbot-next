# control/status.md — coordinator heartbeat

> ⚠️ **RETIRED (2026-07-17) — control-plane message bus wind-down.** This
> heartbeat and the `control/` inbox/outbox bus are retired ahead of the Claude
> Code Projects EAP going read-only Tue 2026-07-21; the Project will be recreated
> fresh. Kept as historical record — the live "what is true now" ledger is
> [`docs/current-state.md`](../docs/current-state.md); the forward task list is
> [`docs/NEXT-TASKS.md`](../docs/NEXT-TASKS.md).

updated: 2026-07-20T04:17:50Z
phase: EAP wind-down — decision-ledger audit complete (question-router fully answered)
health: green (~3531 tests, 7 required checks incl pip-audit)
kit: v1.17.0 · check: green · engaged: no
last-shipped: #600
open-prs: #576 parked (owner-attended); decision-audit PR open on claude/decision-audit-2026-07-20
next-2: owner-gated prod/backup/creds provisioning · design engines (D4/D5/R) at real consumer
blockers: none (owner agenda trimmed to genuine owner-only remainder)
orders: unchanged (ORDER 024 executed; task ledger = docs/NEXT-TASKS.md)
⚑ needs-owner: (1) disarm the residual failsafe wake triggers via the routines UI — both enabled duplicates of "SuperBot 2.0 failsafe wake": trig_01E86nBnXqesQTwm6WA4mSUD + trig_01UC7wiV3n5Vgs3RpSQt4gWz (no standing wake chain in the recreated Project); (2) delete 4 orphan merged branches (blocked agent-side by the GitHub 403 ref-delete wall, recorded 2026-07-17): #385 claude/energy-slice-2, #473 claude/title-equip-write, #476 claude/curation-row72, #424 claude/wp-stack-reconcile.
notes: Help Home-message builder (Q-0059) ported behind the audited seam — migration 0056 (additive), HomeMessage read model + set_home_message write lane, editor_home_message builder panel with mandatory-preview Save gate, help.home live-wired via guarded no-op. Golden corpus → 526 (help.home_message_save minted + main's mining_workshop_craft_write, reconciled as a UNION at merge over the 524 merge-base — minted_goldens 64); check_parity_depth 49/49 ported (kernel ported); run_golden_parity 50/50 subsystems ported (help subsystem already flipped, this adds goldens only). Full golden-parity gate verifies in CI (session-window wall); per-case mint_golden ORACLE-VERIFY green locally. NEXT-TASKS gap #4 (settings-audit) found already-done on inspection — no work required. Corpus disk-count via parity/goldens/*/*.json = 526 (find -name overcounts to 527 via the top-level _sweep_skips.json metadata file). The autonomous apparatus (self-wake / pacemaker / message bus) stays retired — no standing wake trigger re-armed. Forward work: docs/NEXT-TASKS.md.
