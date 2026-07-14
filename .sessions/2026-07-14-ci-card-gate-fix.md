# 2026-07-14 — ci: enforce the born-red session-card hold with the kit's substrate-gate

> **Status:** `in-progress`

- **📊 Model:** `Fable 5` · CI enforcement lane · claim
  `control/claims/ci-card-gate-fix.md` (claim PR #478).

## Scope

**Goal:** make the born-red session-card hold a CI-enforced fact
instead of a convention. Today a PR whose own card says `in-progress`
can show all-green checks.

**The bug (two halves):**

1. None of the six required contexts (code-quality, manifest-validate,
   architecture, sim-gate, golden-parity, check_compat_frozen — all in
   `named-gates.yml`) ever runs `bootstrap.py check`, so no required
   check grades any session card at all.
2. ci.yml's non-required `checkers` job (ci.yml:65-66) runs bare
   `python3 bootstrap.py check --strict`; with no `--session-log` the
   card selection falls back to `latest_session_log` = max mtime
   (bootstrap.py:1939-1946, wiring :16379-16383). Fresh CI checkouts
   flatten mtimes, so it grades an arbitrary card — PRs #477 (run
   29326284700) and #466 went green with in-progress cards in their
   own diffs.

**Fix plan:**

- Install the kit's staged gate byte-for-byte:
  `.substrate/ci/substrate-gate.yml` →
  `.github/workflows/substrate-gate.yml` (the `adopt
  --wire-enforcement` install path, LIVE_CI_RELPATH). It grades
  exactly the card(s) in the PR diff: added in-progress/drafted card
  ⇒ born-red HOLD exit 1 (`check_added_card`), modified card graded
  with `--require-session-log`, control/**-only diffs fast-lane,
  deleted card red.
- Pin ci.yml's `checkers` line to `--session-log
  .sessions/__no-card-in-diff__.md` so its card grading is a
  deterministic advisory skip instead of an mtime guess; card
  enforcement moves wholly to substrate-gate.
- Regression test `tests/test_session_card_gate.py` pinning the hold
  seam through the same CLI invocation CI uses.
- Live proof on this PR: substrate-gate must hold THIS card red while
  `in-progress`, then flip green when this card flips `complete`.

Owner action remains: add `substrate-gate` to the required status
checks in the main ruleset (agent tokens cannot edit rulesets). The
auto-merge enabler's diff-derived refusal (belt) stays untouched;
this adds the required-check suspenders.
