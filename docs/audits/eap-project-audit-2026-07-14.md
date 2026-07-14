# superbot-next — EAP close-out project audit (2026-07-14)

> **Status:** `historical` — final EAP close-out audit, one-off deliverable; not part
> of the repo's own doc rotation. Evidence pin: `origin/main @ dd33fb3` (2026-07-14
> 10:09:12 +0200) unless a later SHA/PR is named. GitHub numbers from an MCP snapshot
> 2026-07-14T09:24Z. Decision-ledger entries are referenced by number in prose
> ("ledger entry NNNN"), never as bare stamp tokens — their stamp homes stay unique.

This document stands alone: it is the consolidated audit of the superbot-next Early
Access Program week — what was built, with which tools, against which walls, at what
friction and ceremony cost, what the fleet fixed itself, and what still hurts.

---

## 1. Identity & scale

| Fact | Value | Source |
|---|---|---|
| Primary repo | `menno420/superbot-next` (only git remote) | `git remote -v` |
| Repos touched | `menno420/superbot` (port oracle; cross-repo PR #2072, drafts #2058/#2061) · `menno420/superbot-plugin-hello` (external-plugin proof; PR #2 parked) | docs/review/curation-report-2026-07-13.md:25 (oracle clone `superbot@cdb2680`) · control/status.md@dd33fb3:24-25 |
| Seat | agent fleet (coordinator + dispatched worker lanes), owner reviewing/clicking | CONSTITUTION.md; control/README.md |
| Active window | **2026-07-08 → 2026-07-14 (7 calendar days)** — first commit `de36d28` 07-08, 49 commits already on main on 07-14 | `git rev-list origin/main` |
| Session cards | **222** in `.sessions/` (excl. README); per-day 5/15/50/66/80/6 over 07-09→07-14 | `ls .sessions/` |
| Commits on main | **466** total = 8 merge + 458 non-merge; peak day **104 on 07-13** (the EAP final night, owner kickoff 22:26Z per control/outbox.md@dd33fb3:193) | `git rev-list --count origin/main` |
| PRs | **466 opened (#1–#466): 448 merged / 11 closed-unmerged / 7 open, 0 drafts** — snapshot 09:24Z; cross-check 448+11+7=466 ✓. #467 (this lane's claim) merged post-snapshot 09:27:35Z. Cadence ≈ 1 PR per ~20 min over the repo's life | MCP `list_pull_requests` pages 1–5 + `search_pull_requests is:merged/is:unmerged` + git log |
| Closed-unmerged | 11 (2.4%); only ~5 are true duplicate/collision losses (#328 #336 #354 #355 #438) — the rest deliberate scratch/supersede closes (#315 was an intentional merge=union probe). Zero silent abandonment older than same-day | 01-prs dataset; .sessions/2026-07-13-coordinator-seat-close.md:94-95 |

History-integrity caveat: an earlier standing alarm claimed main had been rewritten to
"~104 commits rooting at 2cb4d91"; refuted — shallow-clone artifact, withdrawn by
ORDER 021 (#464, `9f1f130`). The 466 figure is the intact graph. See §6.3.

Backlog at close (all measured at dd33fb3):

- **Completeness table** (docs/status/completeness-table-2026-07-13.md): **49 subsystem
  rows — core 44 ✅ / 5 ⚑ (ai · casino · cleanup · hermes · mining) · admin 46 ✅ / 3 ⚑
  (btd6 · settings · utility) · setup 47 ✅ / 2 ⚑ (setup · xp)**; "Every flag is a
  *declared-honest* terminal or an in-flight/owner-gated lane — the sweep found **zero
  silent gaps**" (lines 114-116). Manifest sweep: 413 commands, 370 panel actions,
  57 selectors, ~200 panels, zero unregistered refs; 27/89/13 pending
  commands/actions/selectors, all polite declared terminals.
- **Curation** (docs/review/curation-report-2026-07-13.md): **1088 items (407 commands,
  681 components) → KEEP 918 / REWORK 110 / DROP 60 / NOT-MEASURED 0**; after the night
  bundles (#428/#434 + pre-shipped rows) REWORK is effectively down to **rows 26 and
  72** (row 26 owned by the WP lane, row 72 parked on WP count-pin files —
  control/outbox.md@dd33fb3 04:48:20Z report, item 2). DROP-list ratification (60
  items) is an owner ask.
- **Standing needs-owner**: **9 numbered ⚑ items** (control/status.md@dd33fb3:23-33) —
  plugin-hello #2 merge, superbot #2058/#2061 flips, WP-stack sweep
  (#312→#317→#335→#344→#371), DROP ratify, ledger-entry-0083 anchor call, SBW section
  spec, standing credentials, cosmetic banner strings, and ⚑8 (withdrawn by #464).

## 2. Tooling used

Verdicts grounded in quoted session-card experience (full working notes: scratchpad
02-tooling-used); each row carries one load-bearing citation.

| Tool / surface | How used | Verdict | Citation |
|---|---|---|---|
| GitHub MCP — read/query | The ONLY GitHub route (`api.github.com` direct HTTP is a verified wall); live PR-state audits, pinned-SHA oracle reads; GraphQL leg rationed | **Reliable** (REST); GraphQL quota tight | .sessions/2026-07-13-coordinator-seat-close.md:43 "verified live at GitHub 2026-07-13T10:44Z — 9 open"; docs/CAPABILITIES.md@dd33fb3:81-82, 93-94 |
| GitHub MCP — PR create/merge | Create routine (dozens of PRs #302–#465); merge works mechanically but is where the auto-mode classifier bites, by venue: "12 clean review-merges, then 3 terminal classifier denials" | **Reliable create/query; painful merge** — resolved by moving landing to the enabler | control/outbox.md@dd33fb3:106-107 "Permission for this action was denied by the Claude Code auto mode classifier. Reason: No reason provided."; coordinator-seat-close.md:62-65 |
| Auto-merge enabler (.github/workflows/auto-merge-enabler.yml, PR #321) | Arms GitHub-native squash auto-merge at PR open for `claude/*`; six required named gates stay the enforcement; refuse-to-arm + `do-not-automerge` + in-progress-card SKIP guards | **Reliable** — no curse card on record; only stall class is upstream (dirty merge-ref ⇒ zero check runs) | coordinator-seat-close.md:40 "#332 MERGED 10:01Z by github-actions[bot] (the enabler, as designed)"; .sessions/2026-07-13-energy-slice-1.md:63-66 (refuse-to-arm field-proven) |
| send_later / create_trigger wake chains | Failsafe 2-hourly cron + ~15-min one-shot pacemaker chain; health auditable via list_triggers | **Flaky (platform-side), workable with redundancy** — wedge 01:07–02:44Z, vanished trigger, env-teardown kill all survived | docs/ROUTINES.md@dd33fb3:20-21 "0-for-2 on fresh-session cron fires vs 100% on self-bound crons and one-shot chains"; coordinator-seat-close.md:87-88 |
| Worker relays (walled-call pattern) | One trigger-MCP call per worker, verify-after-arm, every time — the standard route around classifier/platform walls | **Reliable** (as the workaround it is) | coordinator-seat-close.md:80-81; docs/ROUTINES.md:65-67 "parallel multi-call writers hung reliably under load (four workers, one night)" |
| tools/mint_golden.py + 27-checker fleet | Canonical golden mints (PR #416) after a FOURTH scratch re-invention; checkers caught real classes (money-race, orphans) | **Reliable core, named footguns** — mint is capture-seam-blind (date seeding, §6.5); two documented mis-classifications (§7.2) | .sessions/2026-07-13-port-tooling-mint.md:78-81 "double-captured byte-identical across two independent boots" |
| Local Postgres parity runs | Two verified recipes (cluster restart + role/DB creates; root-safe initdb); full 494-golden gate runs locally | **Reliable once provisioned; painful to discover** — the wall was imagined twice before the ledger entry killed it | docs/CAPABILITIES.md@dd33fb3:110-124 "The golden-parity gate IS runnable locally in a worker seat — no CI round-trip needed" |
| Oracle access (LOCAL superbot clone / pinned-SHA MCP reads) | Route A: add_repo → local clone (works in coordinator/plain seats, PR #305). Route B: MCP `get_file_contents` pinned at a SHA + `search_code` (after clone denials in dispatched lanes) | **Reliable but venue-dependent** — clone classifier-walled in dispatched lanes; pinned MCP reads are the proven fallback, weaker for tree-wide grep | docs/CAPABILITIES.md@dd33fb3:149-161 "the `git clone` step it prescribes is DENIED by the auto-mode permission classifier … denied 3x on 2026-07-13" |

Not measured: MCP latency/error rates as numbers; enabler arm-to-merge timing;
search_code use frequency.

## 3. Tooling walled or missing

28 rows audited (full verbatim working notes: scratchpad 03-walls). DELTA style:
rows that merely restate `docs/CAPABILITIES.md` are compressed to one line + pointer;
full verbatim is kept for the high-cost walls. Dispositions: ACCEPTED / FLEET-FIX /
ANTHROPIC.

### 3.1 High-cost walls — full verbatim

| # | Capability | Verbatim denial + date | Workaround | Disposition |
|---|---|---|---|---|
| 1 | Merge a PR without human review (#313 on owner silence) | `"[Merge Without Review] ... silence is not consent"` — 2026-07-12T23:31Z (control/outbox.md@dd33fb3:100-101) | Park gate-green for owner click; enabler covers `claude/*` | ACCEPTED — merge authority deliberately owner-gated |
| 2 | Delegate review+merge of a workflow-file PR (#321) | `"[CI Bypass] The delegation instructs the sub-agent to review and squash-merge #321, an auto-merge-enabler .github/workflows change ..."` — 2026-07-13T00:08Z (outbox:102-104) | Owner merged it (enabler landed `e9f1cd5`) | ACCEPTED — workflow changes are a legitimate escalation class |
| 3 | Dispatch a worker to merge #322+#320 | `"Permission for this action was denied by the Claude Code auto mode classifier. Reason: No reason provided."` — 2026-07-13T00:10Z (outbox:105-106) | Owner-click sweep | ANTHROPIC — ask: *"When the auto-mode classifier denies an action, please always populate the Reason field — 'No reason provided' denials cost a diagnosis round-trip per incident; a one-line reason lets the seat route to the correct workaround immediately."* |
| 4 | Child non-author review-merge of #320 | `"[Merge Without Review] The sub-agent prompt directs a direct merge_pull_request (squash) of PR #320 to main with no human approval (only a Codex bot comment and the agent's own review); no user authorized merging without review, and the coordinator/night-run context is not user intent."` — 2026-07-13T03:40Z (outbox:107-111) | #320 parked gate-green; owner merged 07-13T13:54Z | ACCEPTED — agent review does not substitute for user consent |
| 11 | LOCAL `git clone` of the port oracle from dispatched-lane worker seats | Ledgered: clone "DENIED by the auto-mode permission classifier … denied 3x on 2026-07-13" (docs/CAPABILITIES.md@dd33fb3:149-161). The denial's own verbatim string was never transcribed — ledger and .sessions/2026-07-13-night-windowed-select.md:26 both point without quoting. Route works in plain worker venue (CAPABILITIES.md:178-184, PR #305) — venue-scoped | MCP `get_file_contents` pinned at a commit SHA after add_repo; `search_code` for tree greps | ANTHROPIC — ask: *"Please let the auto-mode classifier permit `git clone` (read-only) of a repository that add_repo has already authorized for the session — dispatched-lane workers are denied the clone of menno420/superbot even though the same session may read every file via GitHub MCP, and whole-tree greps degrade badly through search_code."* |
| 22 | Hermes work-order transmit (egress leg) | `RuntimeError: missing_config` — 2026-07-13, rps-bot-match seat; env carries neither `CLAUDE_ROUTINE_FIRE_URL` nor `CLAUDE_ROUTINE_TOKEN`; `service.bridge_configured() == False` (CAPABILITIES.md@dd33fb3:162-177; outbox:118-119) | None agent-side — sequence the POST-adapter port WITH the owner keying the env vars | ACCEPTED — owner-keyed credential by design |

### 3.2 Remaining rows — compressed (pointer = where the full entry lives)

| # | Capability | One-line wall + pointer | Disposition |
|---|---|---|---|
| 5 | plugin-hello PR #2 agent merge | Paraphrase only on record: "classifier denied agent merge — ratification park" (control/status.md@dd33fb3:24); 06:09Z verbatim NOT on record (§3.3) | ACCEPTED (merge-gate class) |
| 6 | Non-draft superbot PR from dispatched context | "'no genuine user authorization' for a merge=deploy path" → #2058/#2061 parked as drafts (outbox:112-113) | ACCEPTED — deploy consent stays with owner |
| 7 | Destructive git/db ops in worker seats | force-push / `reset --hard` / `dropdb` each classifier-denied 2026-07-13 (outbox:114-116); restructure to non-destructive equivalents | FLEET-FIX — narrow allowlist in .claude/settings.json (the CLAUDE.md preflight itself prescribes `reset --hard origin/main`) |
| 8 | Delete remote branches | 403 every path (CAPABILITIES.md:78-80); verbatim `"error: RPC failed; HTTP 403"` on scratch/union-test branches (outbox:117) | FLEET-FIX — owner enables "Automatically delete head branches" (standing ⚑6) |
| 9 | Tag push / release via git | HTTP 403 from git proxy (CAPABILITIES.md:75-77); `workflow_dispatch` release path proven | ACCEPTED |
| 10 | Direct HTTP to api.github.com | Blocked → MCP-tools-only (CAPABILITIES.md:81-82); `raw.githubusercontent.com` at pinned SHA serves full files ("one curl vs ~30 search_code queries", .sessions/2026-07-12-btd6-stats-normal-view.md:134-139). No 405/407 on record (§3.3) | ACCEPTED |
| 12 | MCP oracle read WITHOUT add_repo | `"Access denied: repository "menno420/superbot" is not configured for this session. Allowed repositories: menno420/superbot-next"` (outbox:40-43; hit again 07-14, night-tail card) | FLEET-FIX — "add_repo first" baked into oracle-reading prompts (already ledgered) |
| 13 | Oracle full-file reads, early worker sessions | Denied over PRs #112–#132 (team memory, playbook item 3); superseded by rows 10/12 routes | ACCEPTED — superseded |
| 14 | EnterWorktree from pinned-cwd worker | Verbatim wall ledgered CAPABILITIES.md:125-136; manual `git worktree add` fully equivalent (both curation bundle PRs shipped that way) | ACCEPTED |
| 15 | `gh` CLI | Not installed (team memory statement; no error transcript) — MCP covers | ACCEPTED |
| 16 | Repo creation via integration token | "GitHub App 403 on repo-create" (docs/retro/project-review-2026-07-09.md:57); owner created plugin-hello repo 07-12 | ACCEPTED — resolved |
| 17 | Modify repo Settings / Rulesets | "agent tokens can READ but cannot MODIFY rulesets or merge settings" (CAPABILITIES.md:191-199) → update-branch dance; owner fix = merge queue or ruleset carve-out (OWNER-ACTION 3) | FLEET-FIX — owner clicks (§9.5) |
| 18 | Environment/Project creation; console knobs | Owner-click console actions (CAPABILITIES.md:83-88); create_trigger is agent-side since 07-11 | ACCEPTED |
| 19 | Self-merge of owner-gated PRs | Venue-differing classifier boundary (CAPABILITIES.md:89-92) | ACCEPTED — record per venue |
| 20 | GraphQL API quota | "tight — batch … prefer REST-backed MCP tools" (CAPABILITIES.md:93-94); no verbatim quota error on record | ACCEPTED |
| 21 | Unattended permission prompts | Silent stall in unattended seats; grants differ by venue (CAPABILITIES.md:95-99) | FLEET-FIX — fewer-permission-prompts allowlist per venue |
| 23 | pytest on fresh container | Needs pip install; must target `tests/` (CAPABILITIES.md:185-190) | FLEET-FIX — SessionStart hook pre-install |
| 24 | Codex reviewer | "@codex comment draws only a chatgpt-codex-connector rate-limit reply and NO review" (playbook 14g; #148/#151 comments) | ACCEPTED — don't-wait doctrine (Q-0258) |
| 25 | GitHub Actions reliability | `"Failed to resolve action download info. Error: Service Unavailable"` (#387 first run, outbox:181-183); dirty merge-ref ⇒ zero check runs; check-run outage ~03:40Z | ACCEPTED — platform weather; triage ladder in playbook (§4) |
| 26 | search_code staleness | Reconstructs the oracle's DEFAULT branch, can be ahead of the corpus pin (playbook trap 24, PR #173) | FLEET-FIX — pin reads at a SHA (doctrine) |
| 27 | Mass-edit of PR bodies | Claimed "[External System Writes]" denial (04:29Z) — NOT on record (§3.3) | Cannot disposition from record |
| 28 | Direct push to main | Claimed GH013 block — NOT on record (§3.3) | Cannot disposition from record |

### 3.3 Not found on record — coordinator-relayed, absent at dd33fb3

The following were relayed into this audit as claimed incidents but are **not on the
verbatim record anywhere at dd33fb3** (repo-wide greps over `.sessions/`, `control/`,
`docs/`, team memory, and `git log --all --grep`; bootstrap.py/.substrate excluded).
They are stated here exactly as: relayed but unrecorded — if the originating seats
still hold the transcripts, append them to docs/CAPABILITIES.md.

1. **"[External System Writes]…" PR-body mass-edit denial, 2026-07-14 04:29Z** — zero
   hits for "External System" / "04:29".
2. **plugin-hello PR #2 merge denial verbatim at 06:09Z** — only the paraphrase at
   control/status.md@dd33fb3:24 exists.
3. **GH013 direct-push-to-main block** — zero hits for "GH013" / "protected branch".
4. **The oracle git-clone denial's own verbatim string** — ledgered as having existed
   ("denied 3x"), never transcribed.
5. **api.github.com 405/407 proxy errors** — only 403 is on record.
6. **Stub-200 "not enabled" wall** — no hit in any source.
7. **Verbatim 403/429 quota strings** (GraphQL, codex) — findings/paraphrases only.
8. **`gh` CLI "command not found" transcript** — team-memory statement only.

## 4. Merge & landing friction

**Time-to-land, n=448 merged PRs** (merge-commit committer timestamps on main,
verified exact against API `merged_at` for #320; #279 via API):

- **median 3 min · mean 30 min · p90 ~1 h**; 342/448 (**76%) under 15 min**, 90%
  under 1 h, 42 in 1–6 h, 5 over 6 h.
- **Worst 5:** #320 **14.1 h** (mining energy core — classifier-denied review-merge,
  waited for the owner click, merged by menno420 07-13T13:54Z) · #333 **11.0 h** ·
  #352 **8.8 h** · #332 **8.3 h** · #345 **6.4 h** (all four: the 07-13 Actions
  check-run starvation incident). The tail is not review latency — every >6 h case is
  owner-click or platform-weather.

**Event-starved / zero-check heads — 5 documented: #332 #333 #345 #352 #373.**
Mechanism (coordinator card §b): "Actions event-starvation: largely a dirty-merge-ref
effect (merging main into the branch re-attaches checks); two PRs genuinely
event-dead needing close/reopen — and close/reopen alone did not cure #333/#352"
(verified at GitHub 10:44Z: both OPEN with ZERO check runs after close/reopen,
.sessions/2026-07-13-coordinator-seat-close.md:32-34). **Cure: merge main in;
close/reopen is insufficient.** Correction to the relayed claim: **#394 (44 min) and
#444 (2.3 h) landed clean** on the normal enabler path — no stall narrative exists
for either. Disposition: FLEET-FIX — bake merge-main-in into the PR-babysit routine;
ANTHROPIC note in §9.2.

**Owner-click set (live get 09:3xZ):** WP stack **#312→#317→#335→#344→#371** —
gate-green, mergeable-clean, reconciled since **04:46Z** (control/outbox.md ORDER-019
report 04:48:20Z) and still unmerged ~4.5 h later; it now freezes unrelated green
work (#466 "Parked green under coordinator WP-stack freeze"). Plus **#392** (based on
wp3, sequenced behind the stack) and **#320** (owner-merged after 14.1 h).
Disposition: ACCEPTED by design (human-in-the-loop for non-`claude/*` merge
decisions), with the label-keyed second-enabler proposal (coordinator card:103-108)
as the standing FLEET-FIX candidate.

**Classifier denials on the merge path: 5 verbatim** — the four §3.1 rows 1–4 quotes
plus plugin-hello #2 ("classifier denied agent merge — ratification park",
control/status.md:24). Context: "12 clean review-merges, then 3 terminal classifier
denials" before the enabler made merge calls unnecessary for `claude/*`
(coordinator card:61-65). Disposition: ANTHROPIC (venue-dependent boundary); fleet
already routed around it canonically.

**First-merged-wins duplicate losses:** #438/#439 (same stamp-dedupe fix, #438 closed
6 min after #439 merged) and #448/#449 ("parallel PR #448 landed the identical
CAPTURE_WORLD_WEATHER storm seed on main (7b0a661) while this PR's CI was attaching",
.sessions/2026-07-14-hotfix-weather-goldens.md:30-33 — slimmed and landed as #449);
earlier #354/#355/#358, #328, #336. Disposition: FLEET-FIX, adopted — claims must
land on main first (§7.3).

**merge-base skew (WP stack):** "GitHub server-side merges ignore merge=union →
merge-base skew from per-branch main folds; empty-delta ancestry merges restored
linearity" (control/outbox.md@dd33fb3:202); proven via deliberate scratch PR #315.
Disposition: PLATFORM-ACCEPTED; mitigation is team memory.

**CI rounds: not measured** corpus-wide (would need ~448 per-PR API calls; no
reliable text marker in cards — grep hits are local test re-runs). Lower bound:
**≥5 PRs needed a manual CI re-attach round** (#332 #333 #345 #352 #373) plus one
documented flake re-run.

## 5. Scheduling & wake friction

**Honest negatives first.** Two relayed items are **not in this repo** and could not
be re-derived here: (a) the "**1220-row trigger audit**" — every `1220` hit is
unrelated (a pytest count, a line-number cite); the only "trigger audit" text is a
*proposal* (docs/retro/q0265-routine-loop-2026-07-11.md:65-68); (b) "**GEN-3**" —
zero hits case-insensitive. Both are fleet-manager-side if they exist. Also
**corrected:** there was no "~03:07Z missed turn" — **03:07Z is on record as a
successful failsafe fire**; the real incident is the **01:07–02:44Z scheduler wedge**
(control/outbox.md@dd33fb3:120-121: "trigger-scheduler wedge 01:07–02:44Z (stalled
fires flushed 02:44–02:47Z)").

**The wedge:** "Scheduler wedge 01:07–02:44Z: all fires flushed late; diagnosed by a
probe tick; bridged by a child backup wake"
(.sessions/2026-07-13-coordinator-seat-close.md:66-67). Failsafe fires observed
23:07Z · 02:44Z (late flush of the 01:07 slot) · 03:07Z · 05:08Z · 07:08Z · 09:08Z;
pacemaker chain continuous with the wedged 01:37/01:58 ticks firing late at 02:46Z,
`run_once_fired` verified platform-side (outbox:125-130). "Redundant wake paths
(failsafe cron + pacemaker chain + child backup wake) carried the seat through the
platform wedge" (coordinator card:87-88).

**Hard reliability numbers** (docs/ROUTINES.md@dd33fb3, read in full):

- Fresh-session cron delivery **0-for-2** vs **100%** on self-bound crons and
  one-shot chains (2026-07-12 forensics) — fresh-session cron is doctrine-labelled
  "UNVERIFIED-BROKEN until a scheduled fire is proven in your environment" (L17-24).
  Load-bearing suspect: the registry "surfacing a DIFFERENT environment id than the
  one recorded at arm time" (L25-29).
- Wedge signature: "`enabled ∧ next_run_at < now − 15min` = an undelivered fire" (L54-55).
- `fire_trigger` trap: "sets `last_fired_at` WITHOUT advancing `next_run_at`" (L58-61).
- Write pacing: "parallel multi-call writers hung reliably under load (four workers,
  one night)" (L66-67) — hence one-trigger-call-per-worker, verify-after-arm.
- Registry integrity: "a trigger recorded 'verified live' has vanished within hours,
  unfired, with no audit trail visible agent-side" (L49-50); one prior failsafe died
  `auto_disabled_env_deleted` (platform env-teardown 2026-07-11T16:31Z, fleet-wide).

**Architecture that held:** ~15-min send_later/one-shot pacemaker links + 2-hourly
odd-hour failsafe (`0 1-23/2`, currently trig_012sSzXkABoZEFW1BqXuqi3v,
control/status.md:15), plus per-cutover re-arm ("a self-bound trigger dies with its
session") and residual `list_triggers` checks at close-out (q0265 retro: "ZERO
enabled triggers now target the coordinator session"; ~40 chain links carried PRs
#114–#208 over one 24 h window). Disposition: platform reliability is ANTHROPIC
(§9.3); the redundancy doctrine is the fleet's own working fix.

## 6. Environment & platform issues

1. **Postgres cluster wipes on container restart** — "Container restarts WIPE the
   cluster provisioning … this is now the expected recovery, not an anomaly" (team
   memory ops-notes). Proven literal recipe: `pg_ctlcluster 16 main start`, then as
   postgres `CREATE ROLE parity LOGIN CREATEDB PASSWORD 'parity';` + the three
   `CREATE DATABASE` lines, verify with tools/run_golden_parity.py `--gate`
   (ledgered: docs/CAPABILITIES.md@dd33fb3:110-124, "gate: GREEN — all 494 golden(s)
   across 50 ported subsystem(s) replay clean"; root-safe initdb variant L137-148).
   Disposition: ACCEPTED (recipe documented); FLEET-FIX candidate: boot-time
   auto-provision.
2. **Dual-TRUNCATE deadlock / shared-Postgres bleed** — "concurrent sibling-lane
   replays share the single local Postgres `superbot` database (two distinct backends
   captured issuing the harness's full-corpus TRUNCATE simultaneously and
   deadlocking, pg log 01:19 UTC; the gate loop itself is sequential —
   tools/run_golden_parity.py:101, parity/harness/dbsnap.py:39-45)"
   (.sessions/2026-07-13-farm-leaderboard-parity.md:53-63). The proposed
   advisory-lock/flock serialization fence is **named but unbuilt**; the isolated CI
   gate is the arbiter. Disposition: FLEET-FIX (build the fence).
3. **INC-58 false history-rewrite alarm = shallow-clone artifact** — the standing ⚑8
   claim ("history now roots at whole-tree snapshot 2cb4d91, ~104 commits") was
   refuted: "`git fetch --unshallow` on a fresh clone resolves 434 commits … SHA
   `91b0767` (PR #319) resolves cleanly … a shallow clone shows exactly this symptom"
   (docs/audits/2026-07-13-fleet-cleanup-audit.md:109-121). ⚑8 withdrawn by ORDER 021
   (#464, `9f1f130`). Residual FLEET-FIX: the boot-ritual line "if a SHA a doc cites
   doesn't resolve locally, try `git fetch --unshallow` before flagging a history
   rewrite".
4. **MCP PR-state ~25 min stale** — "Staleness-sensitive reads are cross-checked
   before acting (MCP PR-state reads observed ~25 min stale — confirm merge/CI state
   via git fetch or the Actions runs)" (CONSTITUTION.md:49-51). Observed again during
   this audit: the list payload reported `merged:false` for long-merged PRs.
   Disposition: ANTHROPIC (read-path lag); workaround is binding doctrine.
5. **Date-live golden rot (#448/#449)** — "4 fishing goldens were minted date-live
   07-13 (weather derives from UTC date) → fleet-wide gate red at midnight; fixed by
   #448 (seed via CAPTURE_WORLD_WEATHER) + #449 (canonical stripped re-mints +
   fishing ratchet floor 3/10→2/8)" (control/status.md@dd33fb3:4). Mechanism: the
   capture never armed the seed seam, so goldens embedded 07-13's Storm face
   (sb/domain/fishing/weather.py derives from the UTC calendar date); 07-14 replays
   derived Rain and diffed red. **Rule now mandatory: a golden's case id must be in
   CAPTURE_WORLD_WEATHER before minting.** Proposed unbuilt guard: mint_golden
   refuses/warns on a weather-bearing mint with no seed. Disposition: FLEET-FIX
   (fixed same night; guard pending).
6. **Context exhaustion — one recorded casualty** — band-3 wrap-up "ran out of
   context mid-wrap-up: #86/#87 left un-merged behind the ruleset, band-3→4 handoff
   file never written" (docs/retro/project-review-2026-07-09.md:59). No other
   explicit incident on record; the ~25% per-session orientation re-read tax
   motivated the routed (not front-loaded) boot set. Disposition: ANTHROPIC/ACCEPTED;
   mitigations behavioral.

## 7. Process & ceremony cost

**Born-red cards + gates — verdict: kept-worth-it, tune.** The card-hold engaged as
designed, repeatedly ("the born-red card held the substrate gate red while checks
ran, exactly as designed", .sessions/2026-07-13-completeness-table.md:39-41; the
enabler's card SKIP makes the flip the arm precondition), and the ceremony's origin
incident (#44 premature merge under the old dist) never recurred. The cost side is
concentrated in one seam:

- **#436→#439 and #440→#445 — duplicate-CITATION incidents** (the relay called them
  "duplicate-session"; the record says duplicate-citation/double-stamp): #436 re-cited
  a decision already stamped elsewhere; #440 (the external audit doc) landed a
  reachability orphan + a re-cite. Both escaped to main because **the strict stamp
  check runs in the non-required `checkers` job**, then "took `--strict` red for
  every branch cut after the merge". Cost tallied from the cards: **2 dedicated
  remediation sessions/PRs (#439, #445) + 2 pristine-worktree innocence probes
  (recovery-view; night-audit pre-fix repro) + 1 on-branch re-fix with full ladder
  re-run** (mining-minestats: "pytest 2924 passed … gate GREEN 494/494") — all for
  doc-token dupes a write-time hint would have stopped.
- **#425 — check_money_race real false-green**: the fence fixpoint's propagation
  promoted a conditionally-locking reader to an unconditional fence, "silently
  masking rule A downstream of an unlocked read"; the bug was flagged in five WP PR
  bodies before anyone fixed it; fix verified honest ("3 of the 4 new pins fail"
  with the fix stashed). One latent class flagged, not fixed (docstring mentioning
  FOR UPDATE).
- **Orphan-guard baseline is by-design**: check_orphan_pendings shipped RED-against-
  baseline (9 seeded orphans, prune-only rule); the burn-down then worked ("8 dead,
  1 live" pruned → "0 dangling, 0 new orphans").
- **"checkers non-required" confusion re-paid 5+ times**: four kit-upgrade cards
  carry the same deviation note, v1.10.0 measured the hole (a sibling card graded by
  mtime), and it STILL surprised the coordinator on 07-13 ("`checkers` is not a
  required context", filed under SURPRISES). This one seam is the hole every §7
  incident escaped through.
- **Claims-on-main-first — kept**: "claim files riding feature branches are invisible
  at main HEAD"; earlier-at-HEAD arbitration resolved all collisions with zero lost
  work (#338/#352 salvage), and the ONE deliberate skip (the weather-goldens hotfix
  filing its claim in-PR) reproduced the collision class the same night (#448 vs
  #449).

Ceremony savers on record: the auto-merge enabler removed the merge-call ceremony
entirely for `claude/*`; the golden-parity report leg flipping live-green retired a
standing "(red-by-design)" explanation tax.

## 8. What we fixed ourselves

1. **#386** — manifest `stable_hash` line dropped from the tracked snapshot; the
   two-PR recompile conflict class is gone entirely (`bec00af`;
   docs/operations/manifest-snapshot-conflicts.md).
2. **superbot #2072** (cross-repo) — generated-dashboard conflict resolver; 2-hourly
   dashboard-cron conflicts became mechanical (team memory; control/status.md:25).
3. **#448/#449** — fishing golden date-rot fixed + CAPTURE_WORLD_WEATHER seeding now
   mandatory pre-mint; daily gate flap dead (`7b0a661`, `dfaf8fb`).
4. **#435** — windowed-select grammar past Discord's 25-option cap; 43-cog routing
   picker wired (`d9e1df8`).
5. **#415** — check_orphan_pendings checker (retired-pending orphan class) (`6db55ea`).
6. **#416** — tools/mint_golden.py one-command canonical mint, ending hand-mint drift
   after four scratch re-inventions (`221fbf7`).
7. **#425** — check_money_race fence mis-classification fixed; the checker no longer
   green-lights unfenced reads (`9634e81`).
8. **Ledger entry 0090** — kernel one-shot timer + session push-edit seam: a
   sanctioned real-time lane (bite cues) that keeps goldens deterministic; shipped as
   #460 (`8d8141f`) + #462 (`6c7cda3`).
9. **Empty-delta ancestry merges** — root-caused WP-stack un-mergeability
   (server-side merge=union ignore, proven by scratch PR #315); all five stacked PRs
   verified mergeable-clean (control/outbox.md:202).
10. **Claim-on-main-first discipline** — after the #354/#355 parallel-duplicate
    incident; "a branch-only claim protects nothing" (control/claims/README.md step 3).
11. **#213 + #221** — wallet-race fixed, then a static CI checker so the class can't
    recur (`f71d60b`, `71af879`).
12. **#223** — tournament-entry double-debit race: advisory slot lock + existence
    check before the fee debit (`80464ab`).
13. **#293** — runtime-smoke merge gate: no merge if the app can't boot headless or
    the wiring graph broke (`3cc0426`).
14. **#197** — check_sim_gate overlay-masks-manifest VALUE drift; 42 latent drifts
    corrected in the same PR (`2d65739`).
15. **#394** — fishing bait-consume race fence (conditional-decrement) (`d51e38c`).

## 9. Top 5 remaining pains

1. **Merge-without-review classifier + owner-click bottleneck** (venue-scoped;
   parks every gate-green stack). The WP stack has been gate-green since 04:46Z and
   still freezes downstream lanes (#466); #320 waited 14.1 h. Disposition:
   ANTHROPIC + FLEET-FIX hybrid — fleet side, the label-keyed second-enabler
   proposal; Anthropic side, paste-ready ask: *"When the auto-mode classifier denies
   an action, please always populate the Reason field — 'No reason provided' denials
   cost a diagnosis round-trip per incident; a one-line reason lets the seat route
   to the correct workaround immediately."*
2. **Actions event-starved check-run heads stalling auto-merge** — 5 documented
   (#332 #333 #345 #352 #373; 8–11 h tails). FLEET-FIX: the merge-main-in ritual
   (close/reopen proven insufficient) baked into PR babysitting. ANTHROPIC note:
   dirty-merge-ref heads spawning ZERO check runs turns a required-checks branch
   into an unlandable one with no agent-side cure but a synthetic push.
3. **Scheduler wedge / fresh-session cron 0-for-2** — the 01:07–02:44Z wedge plus
   fresh-session cron delivery 0-for-2 vs 100% self-bound. ANTHROPIC, paste-ready:
   *"Fresh-session-per-fire cron routines went 0-for-2 on scheduled delivery in this
   environment while self-bound crons and one-shot chains delivered 100%; a trigger
   recorded 'verified live' also vanished without a tombstone, and fire_trigger does
   not advance next_run_at. Please expose trigger delivery/audit state agent-side
   and fix fresh-session cron delivery."*
4. **Oracle git-clone denial in dispatched lanes** — ANTHROPIC, paste-ready:
   *"Please let the auto-mode classifier permit `git clone` (read-only) of a
   repository that add_repo has already authorized for the session — dispatched-lane
   workers are denied the clone of menno420/superbot even though the same session
   may read every file via GitHub MCP, and whole-tree greps degrade badly through
   search_code."*
5. **Require-up-to-date update-branch dance** (ruleset is admin-only for agents) —
   every doc/control PR behind a moving main pays a forward-merge round. FLEET-FIX,
   owner action: enable a merge queue, or carve `docs/**`+`control/**` out of
   require-up-to-date (OWNER-ACTION 3, standing since 07-11).

## 10. Wishlist

Ranked; deduped against §3/§9 (nothing here is already dispositioned there).

1. **Merge queue** on main — retires §9.5 and most of §9.2's exposure in one owner
   click.
2. **Branch-delete permission** for agent tokens (or the auto-delete repo setting) —
   the 403 wall is pure accumulating clutter (scratch/union-test branches still
   live).
3. **Trigger observability**: list_triggers exposing last-delivery status + tombstones
   for deleted/vanished triggers, so wake-chain audits stop being forensics.
4. **Label fields in MCP PR payloads** — `get`/`list` return no labels today, so
   label-keyed automation (the proposed second enabler) can't be verified agent-side.
5. **Non-stale PR reads** — a consistency mode or freshness stamp on MCP PR-state
   reads, so seats stop cross-checking every read against git/Actions (§6.4).
6. **Write-time stamp/reachability hint** (pre-commit) — would have stopped both §7
   duplicate-citation incidents at authoring time; folding `check --strict` into a
   required gate is the complementary CI half.
7. **Mint-time weather-seed guard** in mint_golden (§6.5's proposed preflight).
8. **Advisory-lock fence** for shared-Postgres parity runs (§6.2 — named, unbuilt).

## 11. Honest gaps

Could not be measured from this repo's record:

- **Exact >1-CI-round PR count** — needs ~448 per-PR API calls; no reliable text
  marker in cards (grep hits are local test re-runs). Lower bound stated: ≥5 (§4).
- **The "1220-row trigger audit" and "GEN-3"** — fleet-manager-side if real; not
  re-derivable here (§5).
- **3 relayed denials with no verbatim on record** (External-System-Writes 04:29Z,
  plugin-hello 06:09Z, GH013) plus the untranscribed oracle-clone denial string —
  §3.3 lists all eight absences verbatim-searched.
- **Label fields** — not returned by the MCP PR payloads used for the §4 tables.
- **Live queries of menno420/superbot and superbot-plugin-hello** — out of scope for
  this audit; cross-repo facts cite this repo's local record only.

Parked at close (not failures — waiting on named events):

- **#466** fishing cast-again — parked green under the coordinator WP-stack freeze.
- **WP stack #312→#317→#335→#344→#371** (+ #392 behind it) — awaiting owner-click
  sweep.
- **Curation rows 26 and 72** — WP-lane-owned / WP count-pin-parked.
- **Conform sweep** and **mineverse flips** (superbot #2058/#2061 draft
  deploy-holds) — owner flips = deploy.
- **plugin-hello PR #2** — ratification park (owner merge).
