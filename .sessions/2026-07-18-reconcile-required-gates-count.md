# 2026-07-18 — Reconcile the required-check count (6 → 7): pip-audit added to branch protection

> **Status:** `in-progress`
>
> Born-red first commit — this card alone, holding the `substrate-gate` red so
> parallel sessions see the in-flight slice. The reconciling edits land next;
> this badge flips to `complete` as the deliberate LAST commit.

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

## Plan / classification (to be finalized in the flip commit)

- `.github/workflows/auto-merge-enabler.yml` — STALE echo/comment prose ("six
  required named gates"); the dynamic API context-count query in the same job
  stays source-of-truth. Fix the prose only; do NOT touch the arming logic.
- `docs/current-state.md` (Review rhythm) — STALE: defines the landing bar as
  "the six required named checks."
- `docs/NEXT-TASKS.md` (item 6) — STALE clause: "the six named CI gates … as
  the merge bar."
- Left ACCURATE: `named-gates.yml` header + `current-state.md` line ~22 (both
  correctly say named-gates.yml carries six named gates).
- Generated / interview-rendered docs NOT hand-edited (noted as follow-up):
  `.claude/CLAUDE.md`, `docs/owner-profile.md`.
- `.sessions/*` historical cards LEFT (immutable trail; accurate at write time).

## Verification (pending — recorded at flip)

- `python3 -m pytest -q --ignore=examples`
- `python3 bootstrap.py check` (docs-gate + this card)
- workflow YAML sanity
