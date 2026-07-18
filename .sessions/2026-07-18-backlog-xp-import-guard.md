# Session — backlog capture: xp _record_import dead negative-level guard 2026-07-18

> **Status:** `in-progress`
>
> Born-red first commit (this card only) — HOLDs `substrate-gate` until the
> docs line lands and this flips `complete` as the deliberate LAST commit
> (per `.sessions/README.md`).

- **📊 Model:** opus-4.8 · low · docs-only

## Goal
Capture ONE code-cleanup lead in the forward backlog so it stops living only in
a session card. The lead (code-confirmed, Q-0120): `sb/domain/xp/ops.py`
`_record_import`'s `if level < 0: raise ValidatorError` guard is DEAD via the
public path — `reduce_max_levels` (`sb/domain/xp/migrate.py`) uses a `-1`
sentinel (`level > best.get(user_id, -1)`) that drops any `level < 0` before the
guard can fire. Pinned by
`tests/unit/band4/test_band4_xp_depth.py::test_import_negative_level_guard`
(surfaced by PR #542). This is a CAPTURED LEAD, not a fix — the
remove-vs-make-reachable call is an owner/fuller-context decision.

## Scope
Docs-only. One bullet appended to `docs/NEXT-TASKS.md` (the forward task list —
a code-cleanup lead belongs there, not in the owner product-decisions doc). No
production code touched. Branch `claude/backlog-xp-import-guard` off
origin/main `fd6f71d` (#542 merged).

## Trail
- LEAD anchor: `.sessions/2026-07-18-test-depth-xp.md` § Q-0120 finding already
  carries the guard recipe; this session promotes it from a session card into
  the backlog ledger so a future cleanup session finds it without a grep pass.
- Code confirmed: `sb/domain/xp/ops.py::_record_import` (the `level < 0` arm) +
  `sb/domain/xp/migrate.py::reduce_max_levels` (the `-1` sentinel).
- Verify: `python3 -m pytest tests/unit -q` (docs-only → unaffected).

## 💡 Session idea
A "guard recipe" buried in a session card is invisible to the forward planner —
the backlog ledger, not the per-session log, is where a deferred cleanup earns a
future session's attention. Promoting the one-liner from card to `NEXT-TASKS.md`
costs one bullet and saves the next session a re-derivation grep.

## ⟲ previous-session review
🔎 Prev-session review (`.sessions/2026-07-18-test-depth-xp.md`, `complete`):
that card reframed Gap-10 and left an explicit "Guard recipe for a later
cleanup" naming the exact code anchors + test target. This session acts on that
recipe's intent — not by fixing the guard (that's an owner call) but by moving
the lead into the backlog so it is no longer card-only. Prior guidance worked as
intended; this closes the "noted only in a card" loop.
