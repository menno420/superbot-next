# 2026-07-12 — CAPABILITIES ledger: verified worker-session port-oracle path (+ pytest env facts)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · docs-only ledger append, no product code

## Scope

`docs/CAPABILITIES.md` (the verified can/cannot ledger) did not record the
worker-session route to the port oracle, so every porting session re-derived
it — exactly the re-paid discovery the ledger exists to stop. This slice
appends the verified findings per the ledger's own discovery rule (step 4:
append the finding same session, dated, with venue token, evidence, and
workaround):

1. **Capability** — worker-session port-oracle path VERIFIED WORKING:
   claude-code-remote `list_repos` → `add_repo menno420/superbot` → local
   shallow clone, read as a read-only oracle (never MCP file reads as the
   oracle). Evidence: session `.sessions/2026-07-12-karma-view-target-id.md`
   / PR #305 — oracle clone head `97d281e` read successfully, 2026-07-12.
2. **Wall** — fresh container interpreter lacks `pytest` + `pytest-asyncio`
   (pip install required); pytest must target `tests/` — repo-root pytest
   breaks on `examples/`.

Docs-only diff: `docs/CAPABILITIES.md` append log, this card, and the
`control/claims/` claim lifecycle. No product code, no tests touched.

## Delivered

- `docs/CAPABILITIES.md` — two append-log entries (newest first) in the
  file's own entry format.
- Claim `control/claims/capabilities-oracle-path.md` (created first commit,
  deleted in the landing commit).

## Evidence

- kit gate: `python3 bootstrap.py check --strict` → only the designed
  born-red hold on this card's in-progress badge (flipped in the landing
  commit); docs-only diff, no pytest demanded by the gate.

## 💡 Session idea

The discovery rule's step 4 ("append the finding same session") failed
silently in the karma-view session — nothing gates a session that USES an
unrecorded capability without appending it. A cheap kit check could flag a
session card that cites an oracle/tool route absent from
`docs/CAPABILITIES.md`, turning the append rule from doctrine into a gate.

## ⟲ Previous-session review

The `2026-07-12-karma-view-target-id.md` card recorded the oracle-clone
evidence (head `97d281e`) precisely enough that this ledger entry could cite
it without re-verification — that is the ledger loop working. What it could
have done better: it used the oracle path without appending it to
`docs/CAPABILITIES.md` itself, which is why this slice exists.
