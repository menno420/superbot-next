# substrate-kit upgrade report — v1.0.0 → v1.2.0

> Generated 2026-07-09 by `bootstrap.py upgrade`. Rollback: `python3 bootstrap.py upgrade --rollback`.

**Docs:** consumer-edited: 12 · diverged: 6

| planted doc | class | note |
|---|---|---|
| CONSTITUTION.md | diverged | both the template and the doc moved — manual merge |
| docs/decisions.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/architecture.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/ownership.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/runtime_contracts.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/repo-navigation-map.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/helper-policy.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/collaboration-model.md | diverged | both the template and the doc moved — manual merge |
| docs/ai-project-workflow.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/owner-profile.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/AGENT_ORIENTATION.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/current-state.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/question-router.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/ideas/README.md | diverged | both the template and the doc moved — manual merge |
| .session-journal.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| control/README.md | diverged | no recorded hash or old templates unavailable (pre-1.0 install) — manual review |
| control/inbox.md | diverged | no recorded hash or old templates unavailable (pre-1.0 install) — manual review |
| control/status.md | diverged | no recorded hash or old templates unavailable (pre-1.0 install) — manual review |

## Template deltas for diverged docs

### CONSTITUTION.md

```diff
--- CONSTITUTION.md (template@old, current slots)
+++ CONSTITUTION.md (template@new, current slots)
@@ -49,6 +49,20 @@
 - Every rule change ships with its provenance id. This file carries **no
   history** — the ledger does; superseded rules are looked up there.
 
+## Program law
+
+Rulings that bind **every** repo in this program live canonically in the
+substrate-kit repo at `docs/program/rulings.md` — the [PL-NNN] register
+(https://github.com/menno420/substrate-kit/blob/main/docs/program/rulings.md):
+PL-001 decide-and-flag · PL-002 never-wait rebuild autonomy · PL-003
+rail-before-scale · PL-004 empirical model allocation · PL-005 observe-first
+budgets · PL-006 source-wins / false-green · PL-007 enforce-don't-exhort ·
+PL-008 adopt-freely with a kill-switch · PL-009 the kit-lab's rails.
+**Cite PL-IDs — never copy ruling bodies into this repo.** The register is
+the one home; a local copy is drift by construction. Repo-local rulings stay
+in `docs/decisions.md` / `docs/question-router.md`; a local ruling promoted
+program-wide becomes a PL-block there and a pointer here.
+
 ## Rails specific to superbot-next
 
 (Hand-filled: the project's own hard rules, one bullet each, each citing its
```

### docs/collaboration-model.md

```diff
--- docs/collaboration-model.md (template@old, current slots)
+++ docs/collaboration-model.md (template@new, current slots)
@@ -46,6 +46,16 @@
 earns a dedicated research pass or its own session before being answered
 from memory alone.
 
+## Program law
+
+This model's program-wide form, and the rulings that bind every repo in the
+program, live canonically in the substrate-kit repo at
+`docs/program/rulings.md` (the [PL-NNN] register — e.g. PL-001
+decide-and-flag, PL-002 never-wait, PL-007 enforce-don't-exhort) and
+`docs/program/collaboration-model.md`
+(https://github.com/menno420/substrate-kit/tree/main/docs/program).
+**Cite PL-IDs — never copy ruling bodies into this repo.**
+
 ## Drift & staleness
 
 - When a doc and a source file disagree: ${drift_resolution}
```

### docs/ideas/README.md

```diff
--- docs/ideas/README.md (template@old, current slots)
+++ docs/ideas/README.md (template@new, current slots)
@@ -16,6 +16,30 @@
 (5) OUTCOME  implemented | on a roadmap | in discussion | rejected
 ```
 
+## Frontmatter — the idea-outcome record
+
+Every idea file in this directory (README excepted) opens with a flat
+YAML-subset frontmatter block — the machine-readable outcome record
+("ideas that ship and survive"), so a sweep can score the backlog without
+parsing prose:
+
+```
+---
+state: captured | routed | promoted | historical
+origin: lab | owner | consumer:<owner>/<repo>
+shipped_pr: null | <PR number in shipped_repo>
+shipped_repo: null | <owner>/<repo>
+merged_date: null | YYYY-MM-DD
+outcome: open | shipped | survived | reverted | rejected
+---
+```
+
+Conventions: `shipped`/`survived`/`reverted` require all three ship fields;
+`open`/`rejected` keep them null; `survived` means the merge is ≥ 30 days old
+with no revert; name files `<slug>-YYYY-MM-DD.md` (the generation-date cohort
+key) and link every file from this README. The prose keeps the story, the
+frontmatter keeps the score.
+
 ## Backlog
 
 (Captured ideas, each with a state and a next destination — none left at `raw`.)
```

