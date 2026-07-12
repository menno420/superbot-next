# Claim

- `claude/telemetry-merge-friction` · **Reduce `telemetry/model-usage.jsonl` merge conflicts** — every PR's session-close appends one row at EOF, so any two concurrent PRs merge-conflict there (#310/#311/#313 each needed a manual union merge); ship the smallest VERIFIED mechanism that shrinks that friction (`.gitattributes merge=union` for local merge/rebase + an honest runbook for the server-side gap) · `.gitattributes` + `docs/operations/telemetry-merge-conflicts.md` + `docs/parity/flip-playbook-traps.md` + `.sessions/2026-07-12-telemetry-merge-friction.md` · 2026-07-12
