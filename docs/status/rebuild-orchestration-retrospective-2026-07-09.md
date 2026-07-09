# SuperBot Rebuild — Orchestration Retrospective (2026-07-09)

> **Status:** `reference` — coordinator-level retrospective on HOW the rebuild
> was orchestrated. The build content itself is covered by the completion
> report (`docs/status/rebuild-completion-report-2026-07-09.md`); this doc
> records the process, the incidents, and the coordinator's assessment of the
> orchestration model. Source + merged PRs win over this doc.

## 1. How the build ran

The rebuild was run as a Projects-style multi-session effort: one coordinator
session held the overall plan and talked to the owner, and one long-lived
builder session drove the work by spawning workers. Eighteen sequential
workers did the building itself: two repo-population workers and one kit-CI
worker at the start, five kernel workers (S0–S15 across the kernel bands), one
layer-V worker, one K10 worker, five band workers for the Sequence C port
bands, one continuation worker, one scout, and one worker that was resumed
mid-task on S12. On the coordinator side there was additionally one overnight
watchdog routine (five hourly cycles, zero stalls detected) plus four small
lookup/relay workers.

Every unit of work followed the same loop: read the frozen spec, cut a branch,
open a PR, let the gates run, squash-merge, write a progress-log handoff, and
add a decision-ledger entry. The result was 49 merged rebuild PRs (#1–#49,
every number exists; the completion report itself landed as PR #50) in roughly
14 hours end to end — PR #1 merged 2026-07-08 16:17 UTC, PR #50 merged
2026-07-09 05:56 UTC — with zero rework: no PR had to be reverted or redone.

## 2. Incidents and recoveries

Several things went wrong during the run. None of them lost work.

- **Band-3 worker externally killed.** The worker building band 3 was killed
  from outside mid-task. A scout worker was dispatched to verify the actual
  repo and branch state, and a continuation worker then resumed cleanly from
  the progress log. The band completed normally.
- **Required-checks misconfiguration froze PR #35.** A branch-protection
  ruleset named a check that would never report, so PR #35 sat at "Expected"
  and could not merge. The owner fixed the ruleset, after which #35 and #36
  auto-merged within minutes of each other (01:15 and 01:18 UTC). Auto-merge
  fired end-to-end for the rest of the run.
- **D-0025: parity flips deferred rather than faked.** Band 1 found that
  parity rows could not honestly be flipped without a replay adapter, so
  D-0025 recorded the deferral instead of flipping rows on weak evidence. The
  adapter was then actually built (PR #27, ledgered as D-0028: a fake-HTTP
  transport over the real pipeline), keeping flips at zero honestly.
- **Transient CI failures on PR #40** (band 6 slice 1) were caught by the
  checker fleet and fixed before merge, not after.
- **A misleading credential name.** A repo variable named
  `DISCORD_BOT_TOKEN_PRODUCTION` initially read as the production token; it
  was clarified with the owner to be a separate test-bot token, avoiding a
  wrong assumption in the credential registry.
- **Mid-run upstream upgrade absorbed.** substrate-kit v1.0.0 shipped from a
  sibling session while the port bands were still running; the pin and
  vendored-dist upgrades landed as PRs #42/#44/#46 (with #46 completing a
  prematurely merged #44) without disturbing the band pipeline.
- **One child session died at provisioning.** A child session failed during
  environment provisioning (setup-script failure) before doing any work, and
  was simply respawned.

## 3. Discipline evidence

The process guarantees held up under checking, not just on trust. The 465
parity goldens were imported byte-identical and are checksummed. The adopted
`bootstrap.py` is byte-exact against its source, with the adoption provenance
pinned to an exact commit and blob SHA in the ledger (D-0002). Owner answers
gathered in PR #30 were applied and ledgered in PR #34 rather than being acted
on informally. Spec conformance is enforced by checkers in CI (22 `check_*`
tools at the end of the run), so conformance does not depend on any one
agent's diligence. The progress-log handoffs survived a live crash — the
band-3 kill in section 2 was recovered entirely from durable state. Every band
boundary was reported back to the coordinator before the next band started.
And the run closed with a merged completion report (PR #50) rather than an
unwritten understanding.

## 4. Substrate-kit assessment

This rebuild was also the kit's first serious downstream exercise, and it
performed well. The cold adoption worked on the first try — `check --strict`
was green from PR #1 onward. The checker fleet caught real regressions before
merge (the PR #40 CI failures in section 2 were real, not flaky-red noise).
And an upstream upgrade (kit v1.0.0) flowed into a live downstream build
mid-run without breakage. Verdict: the kit does what it was built to do here.

## 5. Multi-repo coordination

Three repos played fixed roles. The old `superbot` repo was a strictly
read-only truth source — goldens, oracle pins, and reverse-engineering
reference, never written to. `substrate-kit` is the upstream home of the
workflow tooling, with its own CI and release process. `superbot-next` is the
consumer, with its adoption provenance pinned (D-0002) and its kit version
pinned (PR #42).

The frictions were real but manageable: repo access is scoped per session, so
each new session had to have the right repos added before it could work;
PR webhooks produced roughly 60 no-op coordinator wakes over the run (events
that woke the coordinator but required no action); and owner-facing items
accumulated across many progress-log entries until they were consolidated —
fixed by compiling the single deduplicated owner-flag list (31 items at the
time of consolidation) that now lives in the completion report.

## 6. Coordinator's opinion on the Projects model

The following assessment is the coordinator's own view, recorded so future
sessions do not have to rediscover it.

**Strengths.** The project gives a stable front door: the owner always talks
to the same coordinator, regardless of which worker is active. Children own a
unit of work end-to-end and are individually inspectable afterwards — when the
band-3 worker died, its transcript and its branch told the whole story.
Band-boundary wakes are cheap, so supervision cost stays low. PR webhooks are
a free progress signal: the coordinator could watch merges happen without
polling. Most importantly, keeping all real state durable — repos, the
decision ledger, team memory — makes any individual agent replaceable, and the
run proved it. Recoverability beat raw efficiency, and for a 14-hour build
that is the right trade.

**Weaknesses.** Event noise per useful wake is high (section 5's ~60 no-op
wakes). There is no native coordinator timer — `send_later` binds to the
session that arms it, so watchdog timers had to be routed via the coordinator
session. Child briefs are capped around 4KB, which forces the real
instructions into repo files. The coordinator cannot message a child directly,
so mid-task course corrections needed a relay-worker hop. Session containers
are isolated from each other, so any file exchange must go through repos or
team memory rather than a shared filesystem. And one child died at environment
provisioning (section 2), which is a failure mode the model itself introduces.

**Net.** The overhead is real but linear — it does not compound as the build
grows, whereas a single long session degrades. Correctness and auditability
scale better under this model than under one long session. Recommended for
multi-repo builds of this size; overkill for small tasks.

## 7. Pointers for future sessions

- Completion report (totals, repo map, owner-flag list, testing order):
  `docs/status/rebuild-completion-report-2026-07-09.md` (PR #50).
- Old-vs-new diff overview:
  `docs/status/old-vs-new-diff-overview-2026-07-09.md` (landing separately,
  same date).
- Testing report: `docs/status/testing-report-2026-07-09.md` (in progress at
  the time of writing).
- Decision ledger: `docs/decisions.md`, D-0001…D-0048.
- Team memory: `/tmp/claude/memory/team/` (session-infrastructure side).
- Testing is owner-driven, subsystem by subsystem — the suggested order is
  §5 of the completion report.
