# 2026-07-18 — Reconcile the required-check count (6 → 7): pip-audit added to branch protection

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD. First
> commit was this card alone (held the gate red); the reconciling edits landed
> in the second commit; this flip is the last.

- **📊 Model:** opus-4.8 · low · docs-only

## Goal

Tonight the owner added `pip-audit` (a separate job in
`.github/workflows/ci.yml`) to `main`'s required status checks, so the live
required set went from **6 → 7**: `code-quality, manifest-validate,
architecture, sim-gate, golden-parity, check_compat_frozen, pip-audit`
(confirmed via the auto-merge-enabler's live ruleset query at 22:26Z). Prose
that describes the merge bar / what-blocks-a-merge as "six" is now stale.

Reconcile ONLY the genuinely-stale required-SET references, verifying each hit
before touching it. Statements that `named-gates.yml` **defines six named
gates** stay ACCURATE (that file still defines six) — the seventh required
check (`pip-audit`) is a separate `ci.yml` job that branch protection now also
requires.

## Scope

- Grep `*.md` / `*.yml` / `*.yaml` for `six/6 (required|named)` +
  `required.*(gate|check)`; classify each hit STALE-vs-ACCURATE.
- Fix genuinely-stale required-SET prose only. Surgical.

## Deliver — classification + edits

**STALE (required-SET / merge-bar said six) → fixed to seven, naming pip-audit:**

- `.github/workflows/auto-merge-enabler.yml` — header comment, the ruleset-note
  comment, the refuse-to-arm `::warning::`, and the "auto-merge enabled" echo.
  The echo now references the job's own dynamic required-context count
  (`steps.rules.outputs.required`) so it can never drift again. The dynamic API
  context-count query stays source-of-truth; **the arming logic is untouched.**
- `docs/current-state.md` (Review rhythm) — "must be green on the six required
  named checks … before they can land" → the seven required checks (six named
  gates + `pip-audit` from ci.yml).
- `docs/NEXT-TASKS.md` (item 6) — "Keep the six named CI gates … as the merge
  bar" → names `pip-audit` (ci.yml) as the additional required check.

**ACCURATE (about named-gates.yml, not the required set) → LEFT untouched:**

- `.github/workflows/named-gates.yml` header — correctly says it carries the
  six §6 named gates.
- `docs/current-state.md` (~line 22) — a status line ("the six named gates …
  are green on main"), not a merge-bar definition; still accurate.
- Every `.sessions/*` historical card that says "six" — immutable trail, each
  accurate at its write time; rewriting history would be wrong.

**Follow-up (generated / interview-rendered — NOT hand-edited, would clobber):**

- `.claude/CLAUDE.md` (~line 61) and `docs/owner-profile.md` (~line 15) both
  say the merge bar is six named checks. Both are substrate-kit renders from the
  staged interview; a hand-edit is clobbered on the next `bootstrap render`.
  **Guard recipe:** reconcile these at the kit interview/template source, not
  the generated artifact — re-render then flows the fix into both files.

## Verification

- `python3 -m pytest -q --ignore=examples` → **3531 passed, 2 skipped, 1
  warning in 114.03s** (docs/workflow-comment change only; no runtime surface).
- `python3 bootstrap.py check` → **exit 0**; the session-card gate selects and
  validates this card. Pre-existing advisories (never exit-affecting) are
  unrelated (control/ claims format, seat-digest drift, other cards' model-line
  classes).
- `.github/workflows/auto-merge-enabler.yml` re-parsed with `yaml.safe_load` →
  **YAML OK**.

## 💡 Session idea

The enabler's "six named gates" prose drifted the moment branch protection
changed because the count was **hardcoded in four places** while the job already
computes the live count (`steps.rules.outputs.required`). This slice pointed the
merge echo at that dynamic value, but the header/comment/warning strings still
restate the list by hand. **Guard recipe:** have the enabler emit the required
contexts it actually read (`echo "required contexts ($count): $contexts"` already
exists at `.github/workflows/auto-merge-enabler.yml` step `rules`) as the single
source in all operator-facing prose, and drop the hand-maintained name list from
comments — then a future ruleset change (8th check, renamed gate) never leaves
stale enabler prose behind.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-d1-pillow-12-security-bump.md` (the pip-audit
remediation card). Its `💡` idea proposed *exactly* tonight's owner action —
"add a `pip-audit` job to `.github/workflows/named-gates.yml` … so a vulnerable
lock is a *required* red" — because #560 auto-merged a known-vulnerable Pillow
pin while pip-audit was only a non-required `ci.yml` job. Tonight that idea
landed as a branch-protection change (pip-audit now required), which is precisely
what turned the fleet-wide "six required checks" prose stale. That card's lesson
carries directly into this one: when a required-check set changes, the operator
prose describing "what blocks a merge" has to move with it — and the durable fix
is to stop hardcoding the count (this session's own idea, above).

## Close-out

- **PR #577** — https://github.com/menno420/superbot-next/pull/577 (branch
  `claude/reconcile-required-gates-count`, base `main`).
- Commits: born-red card `140cda4`, reconciling edits (next), this flip (last).
- Files: `.github/workflows/auto-merge-enabler.yml` (prose/echo only — arming
  logic unchanged), `docs/current-state.md`, `docs/NEXT-TASKS.md`, this card,
  and the `.substrate/guard-fires.jsonl` telemetry delta.
- No `sb/` source change. pytest green; bootstrap check exit 0; YAML valid.
- Merge on green (the seven required checks — the six named gates + pip-audit).
