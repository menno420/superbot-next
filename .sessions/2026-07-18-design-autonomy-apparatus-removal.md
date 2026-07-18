# 2026-07-18 — D6 autonomy-apparatus removal design doc (safe removal sequence)

> **Status:** `complete`

- **📊 Model:** Opus 4 family · high · kernel/architecture design · D6 autonomy-apparatus-removal design doc (born-red, holds substrate-gate)

## Goal

Produce backlog item **D6** as a PLAN doc proposing the safe, ordered removal
sequence for the retired autonomy apparatus — the `auto-merge-enabler.yml`
workflow + the `control/` message bus + the `docs/ROUTINES.md` wake-chain
doctrine (`docs/NEXT-TASKS.md` item #6). PLAN only: no removal is executed here
(owner-sequenced, deferred to the recreated Project post-2026-07-21).

## Scope

The completeness-reconciliation snapshot (`docs/status/completeness-table-2026-07-18.md`,
#525) recommended shifting the loop to **PLANNING mode** — turning the D1–D6
forward lanes into fuller design docs. This slice is the **D6** entry of that
series: the autonomy-apparatus removal plan, plus its row in the shared
planning-mode design index (`docs/design/README.md`).

Docs-only — no `sb/` or test code. Every claim is grounded evidence-first in the
apparatus files read this session (`.github/workflows/auto-merge-enabler.yml`,
`.github/workflows/substrate-gate.yml`, `.github/workflows/named-gates.yml`,
`control/{README,inbox,outbox,status}.md` + `control/claims/`,
`docs/ROUTINES.md`, `substrate.config.json`, `CONSTITUTION.md`,
`docs/current-state.md`, `docs/NEXT-TASKS.md`) with `file:line` citations at HEAD
`92710e2`.

## Deliver

- `docs/design/D6-autonomy-apparatus-removal.md` — the fuller plan doc:
  Problem/context (grounded, file:line for each apparatus item), Goals/non-goals
  (non-goal: executing the removal now), Removal inventory (exhaustive
  files/dirs + every dependent reference so nothing dangles), Proposed removal
  sequence (ordered, independently revertible, config-migration-before-deletion
  so no required gate reds mid-flight), Sequencing/preconditions (why
  post-2026-07-21 recreated Project), Affected surfaces, Rough size (M + S1–S6
  sub-slices), Open questions for the owner. `> **Status:** \`plan\`` badge (a
  valid docs-gate token).
- `docs/design/README.md` — the existing placeholder D6 row converted to a
  linked "this PR" row (append-only intent: only the D6 row touched, no sibling
  row modified — avoids the README merge conflict). `> **Status:** \`reference\``
  badge unchanged.

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (valid `plan`
  badge + the new doc reachable from the design index — no orphan); the only red
  in CI is this card's own designed born-red hold on the substrate-gate until it
  flips complete.
- `python3 -m pytest tests/test_session_card_gate.py` green; `check_compat_frozen`
  untouched (no `sb/` code touched — docs-only).

## 💡 Session idea

The load-bearing finding of the grounding pass is that the apparatus is
**half-retired in an unsafe way**: the `control/` docs carry retirement banners,
but (1) `auto-merge-enabler.yml` has **no** banner and still fires live
`on: pull_request` triggers (`:38-40`), and (2) `control/status.md` is still the
kit heartbeat gated by `substrate-gate.yml:52` (`check --strict --status-only`)
with `substrate.config.json` `claims_dir` pointed at `control/claims`. So the
naive removal — delete the files — would either leave a live auto-merge arming
path or **red a required gate**. The plan's core is therefore *ordering*: confirm
the replacement merge path (there is NO in-repo lander workflow), migrate the
kit-owned config off `control/` BEFORE deleting the file it gates, and repoint
the doctrine docs (CONSTITUTION's OWNER-ACTION-format citation to
`control/README.md`) before their targets vanish. Same D1–D6 theme as the rest
of the series: the retirement is declared ahead of where the wiring actually is.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-d4-observability.md` (the first
planning-mode design-doc card, #534-class) as the passing template for this
series — its structure (docs-only born-red card holding the substrate-gate, a
`plan`-badged doc grounded in real `file:line` citations, a single reachable
index row), model line, and verification shape are mirrored here. That card's
method — read the real surfaces in source, cite `file:line`, verdict only on
verified ground — is carried forward: every apparatus item and every dependent
reference in the D6 doc is grounded in a citation from the actual workflow /
`control/` / config files, and the doc is explicit about what is still LIVE
(the enabler) vs load-bearing (the heartbeat) vs safe-to-drop, rather than
trusting the "retired" banners at face value.

## Trail

- HEAD at start: `92710e2` (origin/main).
- Branch `claude/design-autonomy-apparatus-removal`.
- Commit 1 (this card, born-red) → commit 2 (D6 doc + design-index row) → push →
  non-draft PR → self-checks → flip this card to `complete` LAST.
