# Session card: day-1 cutover prep

> **Status:** `complete`
>
> Born-red: this card was the sole FIRST commit (it held the substrate-gate
> red); the docs/control edits landed in following commits; the `in-progress` →
> `complete` flip is the deliberate LAST commit.

- **📊 Model:** opus-4.8 · high · docs-only
- date: Mon Jul 20 07:30:12 UTC 2026
- goal: make `main` a clean durable artifact for the recreated Project — add a
  successor day-1 runbook, correct stale factual pointers that describe
  already-completed 2026-07-18 owner work as live blockers, retire terminal
  merged-work claims, and refresh drifted test/golden counts.

## Plan
- [ ] Claim + born-red card committed and pushed first.
- [ ] Add docs/RECREATED-PROJECT-DAY1.md (binding day-1 runbook).
- [ ] Fix factual pointers: control/status.md, docs/design/D6-*, docs/current-state.md, docs/NEXT-TASKS.md.
- [ ] Retire 10 terminal merged-work claims under control/claims/.
- [ ] Verify (pytest or collect-only note).
- [ ] Flip card complete LAST; push; open READY PR.

## Outcome

Landed the day-1 cutover prep on `claude/day1-cutover-prep`: added
docs/RECREATED-PROJECT-DAY1.md, corrected control/status.md + docs/design/D6-*
to reflect the 2026-07-18 completions, refreshed counts to 3660/54 and 526/526,
and retired 10 terminal claims. pytest not installed locally (docs-only diff, no
Python touched — CI is the real check). — Mon Jul 20 07:30:12 UTC 2026

## 💡 Session idea

The predecessor's stamp-gate lesson landed for real here: a day-1 runbook that
wants to cite `D-0096` / `D-0101` collides head-on with `check_stamp_discipline`,
which reds a required gate the moment a decision id appears in a second
non-ledger doc under `docs/`. The honest fix is the one that card already wrote
down — a decision id has a *canonical* job (the ledger entry) and a
*navigational* job (pointing a reader at it); do the navigating in **prose +
date + `docs/decisions.md` pointer**, never the literal token. Two corollaries
proved cheap and reusable: (1) session cards live OUTSIDE `docs_root`, so a card
may cite `D-NNNN` freely — the discipline only binds files under `docs/`; (2) a
new binding doc must be *reachable* — link it from a read-path root
(`AGENT_ORIENTATION.md` / `current-state.md`) or `check_reachable` orphans it.
Run `bootstrap.py check --strict` before the substantive commit and the gate
names the exact over-citations and orphans in seconds — but this container has
no `pytest`/kit venv, so the first green signal was CI itself; the reconciliation
was a find-and-prose pass on the second push, not a re-derivation.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-20-decision-audit.md` (`complete`, `opus-4.8 ·
high · decision-audit`) — the D2-DEFER + owner-agenda-audit pass landed as #601
(the cutover SHA this runbook records). Its conventions carried here
byte-for-byte: born-red card as the sole first commit holding the substrate-gate,
substantive edits in following commits, the `in-progress → complete` flip as the
deliberate last commit; docs/control-only scope with zero `sb/` source touched.
Its 💡 — "navigate decisions by prose + date, not the literal token, or the
stamp gate reds" — was the exact wall this slice hit, and applying its rule
verbatim was the fix. Where this slice diverges: the audit pass *recorded* the
decisions (it could own the tokens in the owner-agenda doc), whereas this
runbook only *points at* them, so every reference here is prose + pointer by
construction.
