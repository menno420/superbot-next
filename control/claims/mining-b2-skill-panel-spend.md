# Claim — mining-b2-skill-panel-spend

- `claude/mining-b2-skill-panel-spend` · **scope: B2 mining skill-panel
  spend port** — re-point the four `sk_*` skill-panel buttons
  (`sb/domain/mining/panels.py`) from the pending terminal
  `mining.skill_spend_pending` to the real audited skill-spend write op
  (the same op `!skill` already drives, golden `mining_skill_write`), and
  mint a skills-embed golden for the panel path. Per
  `docs/status/completeness-table-2026-07-18.md` B2 (OPEN · MINTABLE).
  Files: `sb/domain/mining/panels.py`, mining skill tests,
  `parity/goldens/mining/…` skills-embed golden. · 2026-07-18 · session:
  this one
