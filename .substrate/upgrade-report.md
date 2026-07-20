# substrate-kit upgrade report — v1.17.0 → v1.20.1

> Generated 2026-07-20 by `bootstrap.py upgrade`. Rollback: `python3 bootstrap.py upgrade --rollback`.

**Docs:** consumer-edited: 9 · diverged: 5 · template-improved: 1 · unchanged: 10

| planted doc | class | note |
|---|---|---|
| CONSTITUTION.md | diverged | both the template and the doc moved — manual merge |
| docs/decisions.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/architecture.md | unchanged | template identical across versions |
| docs/ownership.md | unchanged | template identical across versions |
| docs/runtime_contracts.md | unchanged | template identical across versions |
| docs/repo-navigation-map.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/helper-policy.md | unchanged | template identical across versions |
| docs/collaboration-model.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/ai-project-workflow.md | unchanged | template identical across versions |
| docs/owner-profile.md | unchanged | template identical across versions |
| docs/AGENT_ORIENTATION.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/current-state.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/question-router.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/CAPABILITIES.md | diverged | both the template and the doc moved — manual merge |
| docs/SKILLS.md | template-improved | consumer-untouched + template improved — safe to apply with `upgrade --apply-docs` |
| docs/ROUTINES.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/reading-path.md | unchanged | template identical across versions |
| docs/ideas/README.md | diverged | both the template and the doc moved — manual merge |
| .session-journal.md | unchanged | template identical across versions |
| control/README.md | diverged | both the template and the doc moved — manual merge |
| control/inbox.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| control/status.md | diverged | both the template and the doc moved — manual merge |
| control/claims/README.md | unchanged | template identical across versions |
| scripts/env-setup.sh | unchanged | template identical across versions |
| .claude/CLAUDE.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |

## ⚠️ Gate carve-outs (host additions the kit-owned regen could not keep)

- carve-out: .github/workflows/auto-merge-enabler.yml — host-added step 'Skip arming while the PR's own in-diff session card is in-progress' in job 'enable-auto-merge'
- carve-out: full pre-regen enabler banked at .substrate/backup/auto-merge-enabler.pre-regen-5efc734a.yml — host additions were NOT carried into the regenerated kit-owned enabler; move them into a separate workflow file (e.g. .github/workflows/host-ci.yml) and commit that before shipping this upgrade/adopt PR.

## Carve-out scan

- carve-out scan: .github/workflows/substrate-gate.yml — ran, 0 found (live matched the previous kit template byte-for-byte; the delta is kit-side template evolution)
- carve-out scan: 2 carve-out line(s) reported above (see the ⚠️ section).

## Capability-ledger seed refresh

- capability-seed: NOT refreshed — the fenced seed block in docs/CAPABILITIES.md differs from the kit-form fence (edited inside the fence, or the old templates are unavailable). The fence is kit-owned: move your own findings BELOW the fence into the append log, restore the block between the BEGIN/END markers to kit form (copy it from the new template render), and the next upgrade refreshes it automatically.

This upgrade ships the venue-scoped capability ledger (grounded-skills §4.2): entries carry a venue token (owner-live · autonomous-project · routine-fired · subagent · any) and the ledger's kit-owned seed block carries the posture decision rule. If this repo carries a local prose copy of the boot-triad/venue-posture rule (superbot Q-0270), that copy is now superseded by docs/CAPABILITIES.md's posture rule — collapse the local copy into a pointer.

## Seat-digest refresh

- seat-digest: NOT regenerated — docs/seat-digest.md differs from the last kit-written render (hand-edited, or no hash recorded). It is a derived render, never a copy of record: move any real finding into the capability ledger / skill index, then regenerate with `python3 bootstrap.py seat-digest` (overwrites this file only; the sources are untouched).

## Applied (--apply-docs)

- applied: docs/SKILLS.md (template@new, hash re-recorded)

## Template deltas for diverged docs

### CONSTITUTION.md

```diff
--- CONSTITUTION.md (template@old, current slots)
+++ CONSTITUTION.md (template@new, current slots)
@@ -58,6 +58,15 @@
   check that contradicts visible evidence is **a bug in the CHECK, not a
   clearance** (PL-006). Every load-bearing claim cites a commit / PR / tag /
   run.
+- **Cross-repo feeds carry a pinned contract.** When this repo commits a
+  generated artifact another repo consumes over a raw URL, the seam carries a
+  committed, versioned shape contract: the producer stamps the version into the
+  artifact and enforces fail-closed parity in CI; the consumer pins the version
+  it built against and verifies at render time, surfacing drift as an honest
+  banner — never faked data. It kills the cross-repo feed-desync bug class
+  before it can silently blank a consumer page. Full pattern + skeleton: the kit
+  recipe
+  (https://github.com/menno420/substrate-kit/blob/main/docs/recipes/pinned-feed-contract.md).
 - When a doc and a source file disagree: the source file wins — read the code, fix the doc in the same change; a checker that reports green against visible drift is itself the bug (PL-006 source-wins / false-green)
 
 ## Autonomy rails — act vs. ask
@@ -75,11 +84,19 @@
   hallucinated gate unless it names an owner-only class below — proceed.
   Ship on green CI; unremarked work is accepted — owner control is
   reaction after visibility, never pre-approval (PL-012).
-- **An open PR is never a reason to stop.** Open READY (never draft) →
-  arm auto-merge while checks pend → it lands itself; blocked branch →
-  update it (merge, never force) and re-arm; a real, verbatim
-  arming/merge denial → park the PR ready, queue ONE owner item for the
-  systemic cause, take the next slice the same turn (PL-012).
+- **An open PR is never a reason to stop.** Open READY (never draft) and
+  **land your own work** — flip to ready, arm auto-merge, or merge it
+  yourself (MCP/REST, or let a merge-on-green workflow land it) the moment
+  CI is green. Landing a green PR, your own or a sibling's, is a **normal
+  agent action, not an owner action** — there is **no standing
+  "classifier-denied" merge wall; do not invent one, and never route a
+  mergeable green PR to the owner.** If the branch falls behind, update it
+  (merge, never force). Only if a *specific* merge/arm call returns a
+  real, verbatim permission refusal *this session* do you park that one
+  call (attempt-once rule), queue ONE owner item for the systemic cause,
+  and take the next slice the same turn — one refusal is specific to that
+  call and venue, never a permanent prohibition and never a reason to
+  write a new wall into the docs (PL-012).
 - **Ask first only for the owner-only classes:** repo settings / rulesets
   / required checks · secrets / env vars / host provisioning · external
   publish + spending money · destructive prod-data ops · account/portal
```

### docs/CAPABILITIES.md

```diff
--- docs/CAPABILITIES.md (template@old, current slots)
+++ docs/CAPABILITIES.md (template@new, current slots)
@@ -84,12 +84,16 @@
   console — queue them as structured owner asks, never wait silently.
   Routine/schedule creation is NO LONGER a blanket wall: `create_trigger`
   arms routines agent-side (proven 2026-07-11); the console-only knobs
-  (model class, branch-push, auto-fix PRs) remain owner-only.
-  — LAST-VERIFIED: 2026-07-11
-- `subagent` · **Self-merge classifier**: sessions can be refused merging
-  owner-gated PRs while their other capabilities work — and the boundary
-  differs by venue (a child session was refused where a coordinator was
-  not). Record which venue hit which boundary. — LAST-VERIFIED: 2026-07-10
+  (model class, plan/seat settings) remain owner-only. **Branch creation
+  and commit-pushes work agent-side** — only ref *deletion* is walled (see
+  Branch deletion above). — LAST-VERIFIED: 2026-07-18
+- **Merging works agent-side — NOT a wall.** Agents flip drafts to ready,
+  arm auto-merge, and merge their own or a sibling's PR (MCP/REST) once CI
+  is green — verified 2026-07-18 by a direct MCP merge. There is **no
+  standing self-merge/owner-gated-merge wall**; do not record one. If a
+  *specific* merge/arm call is refused, that refusal is specific to that
+  call, venue, and the session's permission mode — note it as a dated,
+  verbatim one-off, never generalize it into doctrine. — LAST-VERIFIED: 2026-07-18
 - `any` · **GraphQL API quota**: tight — batch queries and prefer the
   REST-backed MCP tools for bulk reads. — LAST-VERIFIED: 2026-07-10
 - `routine-fired` · **Silent prompt-stalls**: a permission prompt in an
```

### docs/ideas/README.md

```diff
--- docs/ideas/README.md (template@old, current slots)
+++ docs/ideas/README.md (template@new, current slots)
@@ -43,3 +43,13 @@
 ## Backlog
 
 (Captured ideas, each with a state and a next destination — none left at `raw`.)
+
+## Shipped (survive window open)
+
+(Promoted ideas whose PR merged; the revert-scan flips them `survived`
+after the 30-day window, `reverted` otherwise.)
+
+## Historical / pointer stubs
+
+(Link-resolution stubs for travelled docs — canonical copies live in the
+origin repo; frontmatter still tracks their outcome.)
```

### control/README.md

```diff
--- control/README.md (template@old, current slots)
+++ control/README.md (template@new, current slots)
@@ -41,6 +41,42 @@
   `bootstrap adopt --lane <name>`: it plants `control/status-<name>.md` (skip-if-exists),
   declares it in `heartbeat_files`, and leaves `inbox.md`/`README.md` single — a second lane
   never re-plants the first Project's files (the double-adoption fix).
+
+## Delegated tally — coordinator-written heartbeats (multi-repo seats)
+
+A coordinator seat that spans several repos may legitimately write the authoritative
+tally in ITS status file, leaving the member repos' own heartbeats stale **by design**
+(live precedent: the 2026-07-12→13 night run — the mineverse coordinator wrote the whole
+SuperBot World tally while the member seats' heartbeats sat hours stale, and a
+staleness-only sweep would have misclassified shipping seats as stalled). Two conventions
+keep the delegation legible instead of looking like a dead lane:
+
+1. **The delegated write is MARKED.** A coordinator overwriting a member repo's status
+   (or carrying its tally) states so on the heartbeat it writes, first line after
+   `updated:`:
+
+   ```markdown
+   COORDINATOR-DELEGATED heartbeat write — the coordinator seat authorized this status
+   overwrite; authoritative tally for this repo lives here.
+   ```
+
+   One-writer-per-file is preserved as *one writer at a time*: the delegation line names
+   the current writer, so a sweep never sees two silent writers.
+
+2. **The member repo POINTS to its live tally.** A seat whose tally is delegated keeps
+   its own `status.md` from going silently stale by carrying a standing pointer in
+   `notes:` (or directly under `updated:`):
+
+   ```markdown
+   notes: tally DELEGATED to the coordinator seat — live status lives in
+   <coordinator-repo> control/status.md; this heartbeat updates only on this seat's own
+   sessions.
+   ```
+
+**Sweep rule (for managers and roll-up readers):** classify a seat by its **PR record +
+the coordinator's status file**, never by seat-heartbeat staleness alone. A stale member
+heartbeat carrying the delegation pointer is a healthy delegated lane; a stale heartbeat
+with no pointer and no PR activity is the actual dark-lane signal.
 
 ## Per-session ritual (every session, and every routine wake)
 
```

### control/status.md

```diff
--- control/status.md (template@old, current slots)
+++ control/status.md (template@new, current slots)
@@ -17,4 +17,6 @@
 does NOT parse and the fleet registry reads it as no `kit:` line at all (grammar + the valid
 bold-label-before-plain-token shape: `control/README.md` § "status.md format"). And this line is
 a self-report, not version truth — self-reports chronically lag; the kit repo's generated
-`docs/adopters.md` and your committed tree are the version truth to defer to.
+`docs/adopters.md` and your committed tree are the version truth to defer to. If this seat's
+tally is written by a coordinator seat elsewhere (multi-repo lanes), mark it — the delegated-write
+convention and the sweep rule live in `control/README.md` § "Delegated tally".
```

