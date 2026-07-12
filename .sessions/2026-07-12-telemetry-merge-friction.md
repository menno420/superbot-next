# 2026-07-12 — telemetry merge friction: verified union-merge posture for model-usage.jsonl

> **Status:** `in-progress`

- **📊 Model:** [[fill: model]] · [[fill: effort]] · [[fill: task-class]]

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

## 💡 Session idea

[[fill: idea]]

## ⟲ Previous-session review

[[fill: review]]
