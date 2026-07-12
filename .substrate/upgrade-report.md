# substrate-kit upgrade report — v1.14.0 → v1.15.0

> Generated 2026-07-12 by `bootstrap.py upgrade`. Rollback: `python3 bootstrap.py upgrade --rollback`.

**Docs:** consumer-edited: 8 · diverged: 3 · template-improved: 3 · unchanged: 10

| planted doc | class | note |
|---|---|---|
| CONSTITUTION.md | template-improved | consumer-untouched + template improved — safe to apply with `upgrade --apply-docs` |
| docs/decisions.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/architecture.md | unchanged | template identical across versions |
| docs/ownership.md | unchanged | template identical across versions |
| docs/runtime_contracts.md | unchanged | template identical across versions |
| docs/repo-navigation-map.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/helper-policy.md | unchanged | template identical across versions |
| docs/collaboration-model.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/ai-project-workflow.md | unchanged | template identical across versions |
| docs/owner-profile.md | unchanged | template identical across versions |
| docs/AGENT_ORIENTATION.md | diverged | both the template and the doc moved — manual merge |
| docs/current-state.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/question-router.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/CAPABILITIES.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/SKILLS.md | template-improved | consumer-untouched + template improved — safe to apply with `upgrade --apply-docs` |
| docs/ROUTINES.md | unchanged | template identical across versions |
| docs/ideas/README.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| .session-journal.md | unchanged | template identical across versions |
| control/README.md | diverged | both the template and the doc moved — manual merge |
| control/inbox.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| control/status.md | diverged | both the template and the doc moved — manual merge |
| control/claims/README.md | unchanged | template identical across versions |
| scripts/env-setup.sh | unchanged | template identical across versions |
| .claude/CLAUDE.md | template-improved | consumer-untouched + template improved — safe to apply with `upgrade --apply-docs` |

## Carve-out scan

- carve-out scan: ran — no kit-owned live workflow installed, nothing to scan.

## Capability-ledger seed refresh

- capability-seed: docs/CAPABILITIES.md fence already current — nothing to refresh.

This upgrade ships the venue-scoped capability ledger (grounded-skills §4.2): entries carry a venue token (owner-live · autonomous-project · routine-fired · subagent · any) and the ledger's kit-owned seed block carries the posture decision rule. If this repo carries a local prose copy of the boot-triad/venue-posture rule (superbot Q-0270), that copy is now superseded by docs/CAPABILITIES.md's posture rule — collapse the local copy into a pointer.

## Seat-digest refresh

- seat-digest: docs/seat-digest.md already current — nothing to refresh.

## Applied (--apply-docs)

- applied: CONSTITUTION.md (template@new, hash re-recorded)
- applied: docs/SKILLS.md (template@new, hash re-recorded)
- applied: .claude/CLAUDE.md (template@new, hash re-recorded)

## Template deltas for diverged docs

### docs/AGENT_ORIENTATION.md

```diff
--- docs/AGENT_ORIENTATION.md (template@old, current slots)
+++ docs/AGENT_ORIENTATION.md (template@new, current slots)
@@ -6,6 +6,21 @@
 > docs a given task needs. **NOT SOURCE OF TRUTH** — the binding contracts win.
 
 ## Start every session
+
+**Preflight first — land on origin's HEAD before reading anything else:**
+
+```
+git fetch origin main && git reset --hard origin/main
+```
+
+(or `git checkout -B main origin/main`; substitute your default branch).
+Then verify: local HEAD (`git rev-parse HEAD`) must equal
+`git ls-remote origin main`. A warm container clone can lag origin by
+dozens of commits, and a stale clone reads stale orders and stale state —
+every orientation read below assumes this step already ran. The hard reset
+discards uncommitted local changes by design: at session START there should
+be none; if `git status` shows work you did not author, stop and report it
+instead of resetting over it.
 
 The boot set lives in the working agreement — `.claude/CLAUDE.md` — and its
 orientation guidance (one list, one home). This file is not boot reading —
@@ -27,13 +42,18 @@
 `docs/repo-navigation-map.md` · `docs/ai-project-workflow.md` ·
 `docs/owner-profile.md` · `docs/current-state.md` · `docs/decisions.md` ·
 `docs/question-router.md` · `docs/CAPABILITIES.md` · `docs/SKILLS.md` ·
-`docs/ideas/README.md` — plus the root
+`docs/ROUTINES.md` · `docs/ideas/README.md` — plus the root
 `CONSTITUTION.md` (the working agreement) and `.session-journal.md`.
 
 Recurring action? **`docs/SKILLS.md`** — the skill index — names every
 kit-shipped skill and when to reach for it; check it before improvising a
 procedure.
 
+Arming, deleting, or auditing a scheduled trigger/routine/wake chain?
+**`docs/ROUTINES.md`** — binding choice, delivery verification,
+probe-not-record, scheduler-health signatures, pacing — read it before
+touching the trigger registry.
+
 ## Verifying any change
 
 See the working agreement (`.claude/CLAUDE.md`) and its verify guidance
```

### control/README.md

```diff
--- control/README.md (template@old, current slots)
+++ control/README.md (template@new, current slots)
@@ -131,6 +131,27 @@
 the latest `check --strict` verdict on this tree; `engaged:` = the post-adopt engagement gate
 (`yes` once no UNRENDERED banner/slot remains, live CI runs the gate, and the session loop
 has engaged).
+
+**Exact grammar or invisible — keep the `kit:` token PLAIN.** The parser accepts a bold label
+*before* a plain token (`- **kit heartbeat:** kit: v1.2.3 · check: green · engaged: yes` is a
+live valid shape), but bolding the token itself does NOT parse — the fleet registry then reads
+the row as "no `kit:` line" and the lane's engaged signal silently vanishes (a live adopter
+incident, not a hypothetical). The taught negative example:
+
+```markdown
+- **kit:** v1.2.3 · check: green · engaged: yes
+```
+
+← does NOT parse (`KIT_LINE_RE`, kit `src/engine/grammar.py` — the optional bold group cannot
+contain the `kit:` token). If your heartbeat wants a bold label, put it *before* a plain
+`kit:` token.
+
+**Version truth defers to the generated registry, never to this line.** Heartbeat `kit:`
+lines are self-reports and chronically lag 1–3 releases behind the tree (the fleet's
+recurring self-report DRIFT class); the kit repo's generated `docs/adopters.md` —
+regenerated from each adopter's committed tree — is the fleet's version truth, and your own
+committed tree (the vendored dist) is yours. Never hand-assert a fleet version spread from
+heartbeat lines; keep this line in sync as a courtesy signal, not as proof.
 
 ## ⚑ needs-owner — the OWNER-ACTION item format (quality contract)
 
```

### control/status.md

```diff
--- control/status.md (template@old, current slots)
+++ control/status.md (template@new, current slots)
@@ -13,3 +13,8 @@
 The `kit:` line is your kit self-report (substrate-coordinator visibility): keep the version in
 sync with your vendored kit on every upgrade, `check:` = your last `check --strict` verdict,
 `engaged:` = the post-adopt engagement gate (yes once `check` reports ENGAGED/green live CI).
+Keep the `kit:` token PLAIN — the bold-label form `- **kit:** v1.2.3 · check: green · engaged: yes`
+does NOT parse and the fleet registry reads it as no `kit:` line at all (grammar + the valid
+bold-label-before-plain-token shape: `control/README.md` § "status.md format"). And this line is
+a self-report, not version truth — self-reports chronically lag; the kit repo's generated
+`docs/adopters.md` and your committed tree are the version truth to defer to.
```

