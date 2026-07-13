# superbot-next — fleet cleanup audit (2026-07-13, EAP final night)

> **Status:** `historical` — one-off external audit, not part of the repo's own doc rotation.
> Author: a read-only fleet-cleanup audit pass, run in parallel with a live coordinator
> session and the owner's ORDER 045 fleet dispatch. **No PR in this repo was merged, closed,
> or edited by this audit** — see "Why nothing was touched" below.

## What this repo is

`superbot-next` is the ground-up rebuild of `superbot`, a production Discord bot. Per
`README.md` and `CONSTITUTION.md`, it is built fresh on a portable workflow substrate
(`substrate-kit`) rather than forked from the old bot; the live `superbot` repo is used only
as the behavioural (golden-parity) reference, not the code base. At audit time the repo
reports all seven port bands built — 41+ subsystems, 400+ commands, a hash-pinned
`manifest.snapshot.json` — booting to `RUNNING` against real PostgreSQL, with a 22-checker
CI fleet plus a golden-parity replay harness (`parity/`) that diffs live behaviour against
byte-captured goldens from the old bot.

The repo also hosts the plugin-host side of a game-plugin contract
(`docs/game-plugin-contract.md`, `pyproject.toml`) so external game repos (e.g.
`superbot-idle-plugin`, `superbot-plugin-hello`, both present under `examples/`) can be
pip-installed against the `sb` kernel/spec package.

## Structure

- `sb/` — the kernel + domain code (610 `.py` files): `sb/kernel` (config, db, events,
  workflow, authority, panels, scheduler — never imports domain), `sb/domain/<subsystem>`
  (port-band subsystems behind an audited workflow seam), `sb/adapters` (discord/http),
  `sb/app` (composition root), `sb/manifest` (declarations + handler registration),
  `sb/spec`/`sb/namespace` (stdlib-only grammar leaves).
- `parity/` — the golden-parity harness: `parity/cases/curated.py` (typed `GoldenCase`
  definitions), `parity/goldens/<subsystem>/*.json` (byte-captured expected output),
  `parity/harness/runner.py`, `parity/parity.yml` (per-subsystem ported/pending ledger).
- `tools/` — 27 `check_*.py` committed checkers (money-race, schema-growth, namespace,
  symbol-shadowing, egress, orphan-pendings, runtime-smoke, …) plus `bootstrap.py` (the
  substrate-kit CLI, `check --strict`).
- `control/` — the fleet coordination bus: `inbox.md` (manager-written orders, 19 entries),
  `status.md` (this Project's own heartbeat, one writer), `outbox.md` (manager-addressed
  reports), `control/claims/` (one-file-per-claim work-claim ledger, 12 files at HEAD).
  `.claude/CLAUDE.md` is the rendered working agreement (source: `.substrate/claude/CLAUDE.md`).
- `docs/` — architecture/ownership/runtime-contracts (binding), `docs/status/` (completeness
  tables, testing ledgers), `docs/review/` (curation + program reviews), `docs/retro/`
  (self-reviews), `docs/ideas/`, `docs/planning/`, `docs/scoping/`, `docs/parity/`,
  `docs/requests/`. `docs/decisions.md` is a 659-line append-only decision ledger (62+
  entries referenced from CI's own `check_amendments`/stamp checker).
- `.sessions/` — 197 dated per-session logs (the born-red/flip-green session-card
  convention), newest ones from tonight's night lane (e.g.
  `.sessions/2026-07-13-starboard-threshold-modal.md`).
- `tests/unit/` (band-numbered) + `tests/integration/` (real-Postgres concurrency
  regressions) — 226 test files.

## CI setup and health

Three workflows carry the required gates (`.github/workflows/named-gates.yml`,
`ci.yml`, `golden-parity.yml`), all triggered on both `push: branches: [main]` and
`pull_request`:

- **named-gates.yml** — the 6 named required checks: `code-quality` (pytest, no runtime
  deps — guarded-import discipline under test), `manifest-validate` (compile + namespace +
  escape-hatches + schema-growth + `check_runtime_smoke`), `architecture` (symbol-shadowing,
  no-skip, config-seam, metric-cardinality, egress, money-race lint), `sim-gate`,
  `golden-parity`'s `gate` job (ported subsystems replay clean vs a real Postgres service
  container), `check_compat_frozen`.
- **ci.yml** — a broader, **non-required** fleet: `tests`, `checkers` (the 20+
  `tools/check_*.py` scripts + `bootstrap.py check --strict`), `lockfile-fresh`.
- **golden-parity.yml** — `gate` (required) + `report` (non-required, full-corpus honesty
  dashboard; per `README.md`/`docs/current-state.md` it went "live green" on
  2026-07-13, 484/484 goldens, run `29238825392`).

**Verified live, PR #428 (`btd6: guided CT-team set flow`, merged as `7fdd682`, checked
23:07–23:10Z 2026-07-13):** all 6 required named-gates checks green
(`code-quality`/`manifest-validate`/`architecture`/`sim-gate`/`golden-parity`/
`check_compat_frozen`), `golden-parity`'s `report` job green, but **`ci.yml`'s `checkers`
job is currently RED** (job `86957651283`, run `29292077172`) — non-blocking since it isn't
in the required set. Root cause (see "Inconsistencies" below): a `bootstrap.py check
--strict` `[stamp]` finding — the btd6 parked decision (stamped in
`docs/status/rebuild-completion-report-2026-07-09.md`) cited from two docs.

**Push-trigger gap.** `list_workflow_runs` for `ci.yml` / `named-gates.yml` /
`golden-parity.yml` filtered to `event: push, branch: main` shows **no runs newer than
2026-07-13T13:55:09Z** (run `29255726426`, triggered by the merge of PR #384), even though
dozens of PRs merged to `main` after that point (verified: `origin/main` HEAD moved from
`d085a67` → `7fdd682` — 8 new merges — in the ~15 minutes this audit was running). By
contrast, `pull_request`-triggered runs for the same workflows fire continuously and
normally (verified up to a `queued` run at `23:12:32Z`). Practical impact is limited — every
required gate also runs on `pull_request` before merge, so merge-time safety is unaffected —
but any automation that specifically depends on the `push`-to-`main` trigger (e.g. a
post-merge-only dashboard refresh, if one exists) has been silently idle for roughly 9 hours.
Not investigated further per the read-only mandate; worth a coordinator/owner look (Actions
concurrency/usage limits are one plausible cause, given the repo's very high merge velocity —
see PR range below).

## Doc quality

Overall high and unusually well cross-referenced for a repo built in ~5 days (first commit
`de36d28` "Intent commit: what superbot-next is"; 434 commits on `main` as of audit time).
Specific observations:

- `docs/current-state.md` correctly labels itself a dated snapshot ("2026-07-10") and defers
  to `control/status.md` as live truth — this is a deliberate one-source-of-truth design, not
  drift.
- `docs/AGENT_ORIENTATION.md`'s `.claude/CLAUDE.md` pointers (lines 10, 44) are **live** —
  `.claude/CLAUDE.md` exists (3,664 bytes, rendered from `.substrate/claude/CLAUDE.md`),
  confirming inbox ORDER 015 (2026-07-12) was actually completed, not just marked done.
- `control/status.md` (updated `2026-07-13T18:03:41Z` at audit time, ~5h stale relative to
  the ~40+ merges that landed after it) carries a self-flagged ⚑ item 8 questioning whether
  `main`'s git history was rewritten ("history now roots at whole-tree snapshot 2cb4d91, ~104
  commits; old per-PR squash SHAs like #319's no longer resolve locally though GitHub confirms
  the merges"). **Checked and refuted by this audit:** `origin/main` history is intact end to
  end — `git fetch --unshallow` on a fresh clone resolves 434 commits from `de36d28` (the
  initial "Intent commit") through the S1–S8 kernel-build commits (`5fc555a` … `664b611`)
  to the current tip; SHA `91b0767` (PR #319) resolves cleanly. The commit `2cb4d91`
  cited in the status file is a real, in-history commit (PR #334), not a rewritten root. The
  most likely explanation is that the flagging session was working from a **shallow clone**
  (`git clone --depth=1`, the default for many CI/session bootstraps) — a shallow clone shows
  exactly this symptom (only the most recent commit resolves locally, "GitHub confirms the
  merge" but the local repo can't see it) and is indistinguishable from a real rewrite unless
  you think to run `git fetch --unshallow`. Recommend closing ⚑ item 8 as a false alarm and,
  as a process fix, adding a one-line note to the session-start boot ritual: "if a SHA a doc
  cites doesn't resolve locally, try `git fetch --unshallow` before flagging a history
  rewrite."
- `control/claims/` has a live, real defect: the `bootstrap.py check --strict` "claims"
  advisory currently reports a **4-way `claims-duplicate` false positive** on the literal
  token `tests/` (see "Inconsistencies" below) — a checker parsing bug, not an actual
  4-way work collision.

## Open PRs — findings and disposition

**10 open PRs** at audit time (not the 7 named in this task's briefing — 3 more opened
during the ~20 minutes between the briefing snapshot and this audit, itself confirming the
"actively being worked right now" framing). Per this task's explicit repo-specific
instruction, **no open PR in this repo was merged, closed, edited, or commented on.** All
findings below are read-only observations for the record.

| # | Title (short) | Draft | Created (UTC) | `mergeable_state` | Note |
|---|---|---|---|---|---|
| 435 | windowed-select grammar + mining title-equip wire | no | 23:05:27Z | not checked (created during audit) | night lane, born-red card |
| 434 | curation rework night bundle 1 | no | 23:02:30Z | not checked | night lane |
| 432 | ORDER 031 phase 1 — games/casino inventory review | **yes** | 22:59:03Z | draft | explicitly a review/inventory doc PR |
| 423 | claim ORDER 031 games/casino lane | **yes** | 22:33:27Z | draft | claim-only PR |
| 392 | mining energy slice 3 — fastmine energy spend | no | 15:06:03Z | `clean` | base is stacked on WP-3 (#317, open); PR body states it is sequenced strictly after the WP stack and "OWNER-gated (Option A)" |
| 371 | WP-7 — respec + craft write goldens (title-equip dropped honest-pending) | no | 09:53:42Z | `unstable` | base branch is `mining-write-parity-wp6` (#344, open) — stack tail |
| 344 | WP-6 — structure-build write golden | no | 03:04:37Z | not re-checked | WP stack |
| 335 | WP-5 — skill-spend write golden | no | 02:05:10Z | not re-checked | WP stack |
| 317 | WP-3 — depth/world/wear write goldens | no | 2026-07-12T23:20:28Z | not re-checked | WP stack |
| 312 | WP-2 — vault write goldens | no | 2026-07-12T22:29:53Z | **`blocked`** | base `main`; PR body says the owner sweeps this stack "in the morning"; every WP-stack PR's own body names the merge order `#312 → #317 → #335 → #344 → …` as an **explicit owner-click decision**, not a mechanical one |

All 10 fall under the repo-specific "do not touch" instruction: the two drafts (#423, #432)
and the two newest ready PRs (#434, #435) were all created **within the last ~25 minutes** of
this audit running; the six-PR write-parity (WP) stack (#312→#317→#335→#344→#371, plus the
energy-slice-3 PR #392 stacked on top) is the exact "stacked chain verifiably conflicted with
main, explicitly reserved for an owner-click merge decision" the briefing named — confirmed
directly from each PR's own body text ("the owner sweeps the stack in the morning", "this
branch does not rebase/chase main", "OWNER-gated (Option A)") and from live `mergeable_state`
(`blocked` on #312, `unstable` on #371). **Correctly left untouched, not because verification
was skipped, but because verification confirmed the "leave it" call.**

No PR was merged. No PR was closed as superseded. No PR was flagged as needing an urgent fix
beyond what the repo's own coordinator has already surfaced in `control/status.md` /
`control/outbox.md` (the ⚑ needs-owner list there already covers the WP-stack sweep, the
DROP-list ratification, and the mineverse flag flips in the sibling `superbot` repo).

## Concrete inconsistencies found

1. **`ci.yml`'s `checkers` job is red on current `main`** (non-blocking, since it isn't a
   required named-gate). Cause: `bootstrap.py check --strict`'s `[stamp]` rule fires because
   the btd6 parked decision (stamp home
   `docs/status/rebuild-completion-report-2026-07-09.md`) is now cited from **two** docs —
   `docs/status/completeness-table-2026-07-13.md:62` (added by PR #428, merged `7fdd682`,
   23:10Z) and `docs/status/rebuild-completion-report-2026-07-09.md:222` (pre-existing). The
   tool's own rule ("stamp each decision at one home") is violated by the newest merge. Small,
   mechanical, one-line fix (drop the citation from one of the two docs or repoint it to the
   canonical `docs/decisions.md` entry) — left for the repo's own session per the "do not
   touch" instruction, but flagged here since it is currently reddening a CI job on `main`.
2. **`check_claims` 4-way false-positive duplicate.** Four unrelated claim files —
   `control/claims/completeness-remainders.md`, `night-fishing-verify-idle-pin.md`,
   `night-money-race-and-doctrine-doc.md`, `parity-hygiene-flavor-orphans.md` — each list
   `tests/` as one entry in their comma-separated "area/files" field. The checker's
   claims-duplicate rule appears to parse that trailing area list rather than only the
   backticked branch/scope token the `control/claims/README.md` grammar defines, so it
   reports all four as claiming the same work (`tests/`). They are not — each targets a
   distinct branch and scope (completeness-table rows, fishing verify, money-race checker fix,
   parity hygiene). Advisory-only (never exit-affecting per the checker's own design), but it
   is currently producing 3 lines of false-alarm noise on every `checkers` CI run and would
   mask a real duplicate-claim signal if one occurred alongside it. Tooling fix candidate:
   the claims-duplicate parser should only match the first backticked token per bullet, not
   any backticked substring in the line.
3. **`control/claims/mining-write-parity-lane.md` fails its own claim-bullet grammar
   (`claims-format` advisory).** Its six slice bullets end with full ISO-8601 timestamps
   (e.g. `· 2026-07-12T21:33:48Z`) rather than the bare `YYYY-MM-DD` the
   `control/claims/README.md` grammar specifies. Cosmetic — the file is otherwise a clear,
   well-structured claim ledger — but it means this specific claim is technically invisible
   to the checker's own duplicate scan (the grammar mismatch the README warns about: "an
   unparseable claim is invisible to the duplicate scan").
4. **`control/status.md` ⚑ item 8 (history-rewrite concern) is very likely a false alarm** —
   see "Doc quality" above for the full verification. Recommend the next `control/status.md`
   overwrite drop this item (or replace it with the shallow-clone explanation) rather than
   carry it forward as an open owner-action.
5. **Push-triggered CI silence since 13:55Z** (see "CI setup and health" above) — reported as
   an observation, not confirmed as a bug; flagged for the coordinator to check GitHub Actions
   usage/billing or workflow-run history for silent failures, since it is not visible from
   inside a session that only watches its own PR's checks.

## Suggestions (fleet-wide and repo-local)

1. **Centralize the claims-duplicate parser fix across the fleet.** The `control/claims/`
   convention (`control/claims/README.md` here) is explicitly described as a kit-owned,
   cross-repo pattern ("EAP program review 2026-07-10 §6.4 — the fleet's forked claim
   mechanisms unified on the measured winner"). The parsing bug in finding #2 above is a
   defect in the shared grammar/checker, not something local to this repo — if the checker is
   shared (or copy-pasted) across the ~20-repo fleet, every repo using the one-file-per-claim
   convention likely has the same false-positive risk whenever a claim's area list happens to
   include a short, common path fragment like `tests/`. Worth a single fix in whatever repo
   owns the canonical checker source, propagated fleet-wide, rather than 20 local patches.
2. **A lightweight "is my SHA local?" reminder would have prevented finding #4.** The
   shallow-clone-looks-like-a-rewrite trap (doc quality section) is generic to any git-based
   coordination bus this fleet uses — any session that clones fresh each wake and then diffs
   against a SHA cited in a doc is exposed to it. A one-line addition to the shared boot
   ritual / `docs/collaboration-model.md` template ("un-shallow before trusting a 'SHA doesn't
   resolve' signal") would be cheap insurance across every repo in the fleet, not just this
   one.
3. **The `report` job's "live green since 2026-07-13" framing in `README.md` /
   `docs/current-state.md` is currently accurate but is being kept fresh only by
   `pull_request`-triggered runs**, given the push-trigger gap in finding #5. If the
   push-trigger silence turns out to be a real Actions-side issue (not just this audit's
   window), the dashboard's claim of continuous full-corpus greenness would quietly stop being
   re-verified on `main` itself (only on PR heads, which is still meaningful, but is a subtly
   different guarantee than "every push to main is confirmed green"). Worth a coordinator
   session checking `Settings → Actions` usage/limits, since this repo runs an unusually large
   number of jobs per PR (14 check-runs per PR observed on #428) at very high merge velocity
   (PR numbers alone moved from the 380s to 436+ over the course of one night).
4. **Doc-citation dedup ("stamp each decision at one home") should probably be enforced
   *before* merge, not just observed after.** Finding #1 shows the rule catching a real
   violation, but only in the non-required `ci.yml` `checkers` job — a PR can still merge
   (via the required named-gates set) while introducing a new stamp violation. If `bootstrap.py
   check --strict`'s exit code matters to the project (and its presence suggests it does),
   folding it into `named-gates.yml`'s `manifest-validate` job (which already runs several of
   `bootstrap.py`'s sibling checks) would close that gap without adding a new required check
   name.

## Why nothing was touched

Per this audit's repo-specific instructions: this repo has a live coordinator session
actively landing work (confirmed directly — `origin/main` advanced by 8 commits during the
~15 minutes this audit ran, and 4 of the 10 open PRs were created in the same window), a
stacked write-parity PR chain explicitly reserved in its own PR bodies for an owner-click
merge decision, and 2 draft PRs from an in-flight ORDER-031 relay. This audit made **zero**
writes to git state (no merge, no close, no comment, no label change) on any of the 10 open
PRs. The only change this audit makes is this report itself, on a new branch, as a
non-draft, unmerged PR — left open per instruction for the repo's own auto-merge/sweep
convention or a human to land.
