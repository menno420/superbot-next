# `telemetry/model-usage.jsonl` merge conflicts — what's covered, what isn't

> **Status:** `binding` (runbook)

## The friction

`telemetry/model-usage.jsonl` is the PL-004 model-usage feed (KL-3):
`bootstrap.py session-close` appends **one JSON line per session at EOF**.
Every PR carries a session card, so every PR appends a row — and any two
concurrent PRs therefore textually conflict on that file (observed on
#310/#311/#313, each needing a manual union merge). The conflict is never
real: the only reader (`bootstrap.py _model_usage_sessions`) parses
line-by-line into a **set** keyed by session slug — order-insensitive and
duplicate-tolerant — so the correct resolution is always "keep BOTH lines".

## The mechanism: `merge=union` (and its verified limits)

`.gitattributes` carries:

```
/telemetry/model-usage.jsonl merge=union
```

**What this covers (verified locally):** `git merge`, `git rebase`, and
`git cherry-pick` auto-resolve concurrent appends by keeping both sides'
lines — no conflict markers, no manual edit. Reproduced: two branches each
appending a different line conflict without the attribute; with it, both
merge ("Merge made by the 'ort' strategy") and rebase resolve cleanly with
all lines present.

**What this does NOT cover (verified live, 2026-07-12):** GitHub's
server-side merge — PR mergeability, the merge button, and the
"Update branch" button — ignores repository `.gitattributes` merge drivers.
Live test on this repo: scratch branches `scratch/union-test-a`/`-b` each
appended a different row; PR #315 (head b, base a) reported
`mergeable_state: "dirty"`, and after committing the union attribute to the
base branch the recompute went `unknown` → **still `"dirty"`**. This matches
GitHub's own position: "GitHub doesn't consider user-defined .gitattributes
files (normally, we use our own .gitattrbutes file which you can't change)"
— <https://github.com/orgs/community/discussions/9288> (open feature request,
unimplemented as of 2026).

So: **the PR will still SHOW as conflicted** when another telemetry-appending
PR merges first. What changes is the fix — hand-editing conflict markers
becomes one mechanical rebase.

## Runbook — resolving a conflicted PR

From the PR's branch checkout:

```
git fetch origin main
git rebase origin/main   # union driver auto-keeps both telemetry rows
git push --force-with-lease
```

No manual edit of the file. If anything OTHER than
`telemetry/model-usage.jsonl` conflicts, that part is a real conflict —
resolve it on its own merits (see `docs/parity/flip-playbook-traps.md`
trap 10(e) for the known rebase-race pair, e.g. `manifest.snapshot.json`
via `manifest_compile.py --write`).

## Invariants that make union-merge safe here (re-check if they change)

- One compact JSON object per line (`_append_jsonl`), no multi-line records.
- Dedupe is by `session` slug at read time; duplicate lines are harmless.
- Row order carries no meaning; no consumer reads "the last line".
- Only `bootstrap.py` session-close writes the file; nothing in `sb/`,
  `tools/`, or CI reads it.

If a future consumer sorts the file, rewrites it in place, or gives order
meaning, revisit this attribute — `merge=union` can interleave lines in
either order and must never be pointed at a file where that matters.
