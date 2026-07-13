# 2026-07-13 — install auto-merge enabler (PR-landing workflow, fm ORDER 029)

> **Status:** `complete`

- **📊 Model:** `fable-5` · fleet-manager coordinator's hands · owner directive 2026-07-12 (uniform landing workflows across the fleet)

## Scope

Install `.github/workflows/auto-merge-enabler.yml` — adapted from
idea-engine `.github/workflows/auto-merge-enabler.yml@819a8d5` — so
agent PRs arm GitHub-native auto-merge (squash) at open and land the
moment the six required named checks go green. This makes the practice
`docs/current-state.md` already documents ("auto-merge (squash) the
moment the six required named checks are green") actually true: before
this PR no workflow implemented it and every merge was manual.

## What shipped

- `.github/workflows/auto-merge-enabler.yml` (PR #321), all reference
  guards kept: same-repo + non-draft + head-prefix allowlist job gate;
  rules-count refuse-to-arm (zero required contexts = no arm);
  `do-not-automerge` label carve-out with 15s fresh API re-read;
  in-progress/drafted session-card SKIP (argv/env-only parsing, no shell
  interpolation of PR-controlled content); head-ref provenance line in
  the squash commit body.
- Prefix allowlist from evidence (PR heads #309–#320): `claude/`,
  `port/`, `mining/`, `test/`, `docs/`, `fix/`. `scratch/` deliberately
  excluded (#315 was an explicit do-not-merge scratch branch);
  unprefixed heads stay manual-land.

## Provenance (doctrine change, deliberate)

Owner, fleet-manager coordinator chat 2026-07-12T23:00Z: "yes you have
my explicit standing permission to merge all PRs ... your job
specifically is to ... help them overcome merge problems, that's why
you have write access to every repo" + "can you make sure the same
workflows exist here?". Recorded as fleet-manager inbox ORDER 029.
Opt-out: `do-not-automerge` label per PR, or revert the workflow.

## Watch items (guard recipe)

- The enabler proves itself on the next real agent PR: check the
  `auto-merge-enabler` run on that PR's Checks tab. If the repo setting
  "Allow auto-merge" (Settings → General → Pull Requests) is OFF, the
  arm step (`gh pr merge --auto --squash`, last step of
  `.github/workflows/auto-merge-enabler.yml`) fails with a visible
  `::warning::` naming that fix — flip the toggle, then any push
  (`synchronize`) re-arms. Nothing merges silently either way.
- If `bootstrap.py adopt/upgrade` ever regenerates this file from the
  kit, re-apply the host customizations (prefix allowlist, `drafted`
  card status, six-named-gates messaging) — header comment marks them.

## 💡 Session idea

Add a branch-prefix drift tripwire (idea-engine has one:
`preflight --branch-prefix-drift`): the enabler's allowlist is
evidence-pinned to today's prefixes, and a new agent lane adopting a
new prefix (e.g. `feat/`, `parity/`) would silently not arm. A tiny
tool that surveys recent PR head refs (or `Head-ref:` squash-body
lines) and warns when an unlisted prefix appears keeps the allowlist
honest instead of quietly stale.

## ⟲ Previous-session review

Previous session (2026-07-12 coordinator close-out) left a clean HEAD
and an accurate current-state doc — but that doc *described*
auto-merge-on-green as live practice while no workflow implemented it
(every merge was manual). Docs-ahead-of-reality drift is worse than
docs-behind: an agent reading it would assume its PR lands itself and
walk away from an unmerged PR. System improvement: when a convention
doc states an *automated* behavior, name the file that implements it
(as this card does) so the claim is checkable in one `ls`.
