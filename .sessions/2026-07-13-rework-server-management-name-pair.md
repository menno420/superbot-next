# 2026-07-13 — curation rework: regularize the server-management prefix/slash pair (row 73)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · curation rework lane · mandate: curation report
  row 73 (`docs/review/curation-report-2026-07-13.md` L1210 + §Rework
  backlog "server-management"), claim
  `control/claims/server-management-name-pair.md` (PR #376), token
  `claude/rework-server-management-name-pair`.

## Scope

The `server-management` surface ships as TWO CommandSpecs at
`sb/manifest/server_management.py:27-39` — prefix `servermanagement` and
slash `server-management`, both routing to `panel:server_management.hub` —
and its goldens are split across TWO directories
(`parity/goldens/server_management/sweep_servermanagement.json` for the
prefix, `parity/goldens/servermanagement/sweep_slash_server-management.json`
for the slash). Decide the minimal honest regularization: (A) ledger the
pair as deliberate (setup-depth precedent, `sb/manifest/setup.py`) +
unify the golden directories if the parity mapping machinery sanctions a
byte-preserving move, or (B) grammar growth (slash-twin field on
CommandSpec) only if A is dishonest or the twins pattern is widespread.
Parity gate must stay green WITHOUT re-cutting golden bytes.

## What shipped

_(in progress)_

## 💡 Session idea

_(pending close-out)_

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-rework-settings-access.md`.) _(review
pending close-out — to be written against what this session actually
hits.)_
