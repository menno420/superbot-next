# 2026-07-13 — night stamp dedupe: completeness table double-cites D-0043/D-0046

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · night lane worker · mandate: remediation slice — `bootstrap.py check --strict` red on main after #436 ([stamp] D-0043 + D-0046 each cited from both `docs/status/completeness-table-2026-07-13.md` and their stamp home `docs/status/rebuild-completion-report-2026-07-09.md`)

## Scope

PR #436 (fishing cast-leg true-up) added a `D-0043` citation to the
completeness table's fishing row and Top-gaps item 1, and the earlier btd6
row carries a `D-0046` token — but both decisions are already stamped in
`docs/status/rebuild-completion-report-2026-07-09.md`. The stamp checker
(`check_stamp_discipline`, bootstrap.py) counts ANY bare `\bD-\d{3,}\b`
token in a doc under `docs/` as a citation, so the only permitted form is
to drop the tokens from the table entirely. Reword the three sites to
refer to the parked work descriptively (service PENDING-roster note,
`sb/domain/fishing/service.py:1032`; "stamped in that module" pointer for
btd6) without the decision-id tokens. Do NOT touch the stamp home. Keep
the #373/#387/#410 facts intact.
