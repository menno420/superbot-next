# 2026-07-18 — D3 access-control + audit-log data-model design doc

> **Status:** `complete`

- **📊 Model:** Opus 4 family · high · kernel/architecture design — D3 access/audit data-model design doc (born-red, holds substrate-gate)

## Goal

Produce the **D3** planning-mode design doc: the durable access-control +
audit-log data model the settings admin-audit surface (B6) implies. A
docs-only, born-red planning artifact — no `sb/` code — grounded evidence-first
in the ACTUAL access/audit surfaces read this session, with `file:line`
citations at HEAD `fd6f71d`.

## Scope

- `docs/design/D3-access-audit-model.md` — the fuller design doc: Problem
  (grounded, honest that B6 is already DONE and the scout survey was stale),
  Goals/non-goals, Proposed design (the DATA MODEL — persist the per-channel
  role-set constraint the resolver already reads, the `delete_blocked_commands`
  under-port, the consolidated `audit_log` spine, audit-view scope, optional
  health chips — plus the PANEL TAXONOMY mapping matrix editor / audit view /
  health chips onto the model), Affected surfaces, Rough size (M + slicing),
  Open questions for the owner. `> **Status:** \`plan\`` badge (a valid
  docs-gate token; the taxonomy has no `proposal` token).
- `docs/design/README.md` — the D3 row in the planning-mode series table flipped
  from `planned` to point at this PR + doc (append-only single-line edit — the
  sibling-conflict-avoidance posture; D1 row left untouched).

## Deliver

The design doc + the index row, docs-only. No `sb/` or test code touched.

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badge valid
  + the doc reachable from the design index); the only red in CI is this card's
  own designed born-red hold on the substrate-gate until the card flips complete.
- Substrate-gate added-card lane exit 0 on the COMPLETE card;
  `pytest tests/test_session_card_gate.py`; `check_compat_frozen` untouched.

## 💡 Session idea

The load-bearing finding of the grounding pass is that superbot-next's
access-control + audit model is **further along than the backlog label
assumed** — the completeness snapshot itself marks B6 **DONE**
(`docs/status/completeness-table-2026-07-18.md:42`) and flags the "9 actions +
2 selectors pending" survey as stale. The rebuild already ships a per-guild
command-access store (`sb/domain/platform/command_access.py`), the K6 resolver
that consumes it (`sb/kernel/authority/channel_access.py`), and a single
consolidated append-only `audit_log` spine (`sb/kernel/workflow/audit.py`) that
replaced the oracle's five-plus per-subsystem audit tables. So the honest
design value is **not** "build the model" but "name the model of record and
close the four genuinely-thin spots": the `channel_role_sets` constraint the
resolver reads but nothing persists (dead capacity), the `delete_blocked_commands`
under-port, the audit view that filters to `subsystem='settings'` and so misses
the command-access changes sitting right beside it, and health chips that exist
nowhere. The recurring D-series theme holds: the grammar/spec leaves are richer
than the live wiring, so the planning docs are mostly about ARMING/persisting
what already resolves, not inventing subsystems.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (the D4 doc that
opened this planning-mode design-doc series) and `docs/design/README.md`'s
series section. This card is the **D3** entry in that same series and mirrors
the D4 card's shape exactly: read BOTH sides in source (the armed panels AND
the stores/resolver behind them, plus the oracle migrations at
`/workspace/superbot`), cite `file:line`, and verdict only on verified ground.
D4's method — "the declared surface runs ahead of the wired one, so plan the
ARMING not the inventing" — carried directly into D3's finding that
`channel_role_sets` resolves but never persists. The previous-session review
marker needle is present.
