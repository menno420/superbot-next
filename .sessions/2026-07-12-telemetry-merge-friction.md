# 2026-07-12 — telemetry merge friction: verified union-merge posture for model-usage.jsonl

> **Status:** `complete`

- **📊 Model:** Claude 5 family · high · tooling/infra

⚑ Self-initiated: recurring-friction class — `telemetry/model-usage.jsonl` is
append-only and every PR's session-close appends one row at EOF, so any two
concurrent PRs merge-conflict on it. Observed live on #310/#311/#313, each of
which needed a manual union merge to land. This slice evaluates the candidate
mechanisms with evidence and ships the smallest one that provably reduces the
friction.

## Scope

One bounded slice: (1) map every consumer of `telemetry/model-usage.jsonl`,
(2) VERIFY — not assume — what `.gitattributes merge=union` does and does not
cover (local merge/rebase vs GitHub's server-side PR mergeability), via web
evidence plus a live scratch-PR test on this repo, (3) ship the honest
smallest change: the attribute line + a runbook that states the server-side
gap out loud.

## Consumers mapped (nothing else reads or writes the file)

- Writers: `bootstrap.py` `harvest_model_usage` (session-close, single-latest)
  and `reconcile_model_usage` (whole-tree sweep) — both append one compact
  JSON line per session via `_append_jsonl`, deduped by session slug.
- Reader: `bootstrap.py` `_model_usage_sessions` — parses line-by-line,
  skips invalid lines, returns a SET of session slugs. Order-insensitive,
  duplicate-tolerant → line-union of two appends is semantically safe.
- No tools/ checker, no CI workflow, no sb/ code touches the file
  (`rg 'model-usage'` over the tree; only two doc/claim mentions).

## Evidence (verified, not assumed)

- LOCAL merge/rebase honor `merge=union`: reproduced in a scratch clone —
  two branches each appending a different line conflict WITHOUT the
  attribute; WITH `/telemetry/model-usage.jsonl merge=union` both `git merge`
  ("Merge made by the 'ort' strategy") and `git rebase` auto-resolve keeping
  both lines.
- GitHub SERVER-SIDE does NOT honor it: live test on this repo — scratch
  branches `scratch/union-test-a`/`-b` each appended a different row; PR #315
  (b → a) reported `mergeable_state: "dirty"` without the attribute, and
  STILL `"dirty"` after committing the attribute to the base branch
  (recompute observed: `unknown` → `dirty`). Matches GitHub's own statement
  ("GitHub doesn't consider user-defined .gitattributes files",
  community discussion #9288). PR #315 closed after the test.

## Delivered

- `.gitattributes` — `/telemetry/model-usage.jsonl merge=union`: local
  merges/rebases/cherry-picks of concurrent telemetry appends auto-resolve.
- `docs/operations/telemetry-merge-conflicts.md` — the runbook: what the
  attribute covers, the verbatim evidence for what it does not (GitHub's
  merge button / mergeability / update-branch stay conflicted), and the
  two-command resolution for a conflicted PR (`git fetch` + `git rebase
  origin/main` → union auto-resolves → force-push).
- `docs/parity/flip-playbook-traps.md` — trap 26(e) rebase-race note now
  points at the attribute + runbook instead of prescribing a hand union.

## Verification tails

- `python3 -m pytest tests/ -q` → `2050 passed, 13 skipped, 1 warning in 40.77s`
- `python3 bootstrap.py check --strict` → `check: session log
  .sessions/2026-07-12-telemetry-merge-friction.md complete.` /
  `check: all checks passed.` (exit 0; one pre-existing never-exit-affecting
  claims-format advisory on `mining-write-parity-lane.md`)
- `git check-attr merge telemetry/model-usage.jsonl` →
  `telemetry/model-usage.jsonl: merge: union`

## 💡 Session idea

The claims README already measured shared-append files at ~98% conflict under
concurrency and fixed it structurally (one file per claim, 0%). The telemetry
feed has the exact same access pattern but its writer is kit-generated
`bootstrap.py`, so the structural fix (per-session shard files under
`telemetry/model-usage/`, reader globs) can't be applied host-side. Worth
filing upstream to substrate-kit: shard the KL-3 feed per session slug the way
the claim ledger shards per claim — that would make the PR-page conflict
banner disappear entirely, which no `.gitattributes` mechanism can (verified:
GitHub's server-side merge ignores `merge=union`, scratch PR #315).

## ⟲ Previous-session review

The aip-07-08 card is a clean model of the shape this card mirrors: it named
its two audit items with file-level precision and pre-declared the sibling
pattern it would copy, which made review trivial; its plan step 4's
"verified by rg over tests/" is the same verify-don't-assume posture this
session applied to the merge=union question — the one place it could have
gone further is pasting the rg evidence itself, which this card does for its
live-test outputs.
