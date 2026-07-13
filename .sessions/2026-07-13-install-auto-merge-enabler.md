# 2026-07-13 — install auto-merge enabler (PR-landing workflow, fm ORDER 029)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable 5 · fleet-manager coordinator's hands · owner directive 2026-07-12 (uniform landing workflows across the fleet)

## Scope

Install `.github/workflows/auto-merge-enabler.yml` — adapted from
idea-engine `.github/workflows/auto-merge-enabler.yml@819a8d5` — so
agent PRs arm GitHub-native auto-merge (squash) at open and land the
moment the six required named checks go green. This makes the practice
`docs/current-state.md` already documents ("auto-merge (squash) the
moment the six required named checks are green") actually true: today
no workflow implements it and every merge is manual.
