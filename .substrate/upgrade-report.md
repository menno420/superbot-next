# substrate-kit upgrade report — v1.13.0 → v1.14.0

> Generated 2026-07-12 by `bootstrap.py upgrade`. Rollback: `python3 bootstrap.py upgrade --rollback`.

**Docs:** consumer-edited: 6 · diverged: 4 · template-improved: 2 · unchanged: 10

| planted doc | class | note |
|---|---|---|
| CONSTITUTION.md | template-improved | consumer-untouched + template improved — safe to apply with `upgrade --apply-docs` |
| docs/decisions.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/architecture.md | unchanged | template identical across versions |
| docs/ownership.md | unchanged | template identical across versions |
| docs/runtime_contracts.md | unchanged | template identical across versions |
| docs/repo-navigation-map.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/helper-policy.md | unchanged | template identical across versions |
| docs/collaboration-model.md | diverged | both the template and the doc moved — manual merge |
| docs/ai-project-workflow.md | unchanged | template identical across versions |
| docs/owner-profile.md | unchanged | template identical across versions |
| docs/AGENT_ORIENTATION.md | unchanged | template identical across versions |
| docs/current-state.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| docs/question-router.md | diverged | both the template and the doc moved — manual merge |
| docs/CAPABILITIES.md | diverged | both the template and the doc moved — manual merge |
| docs/SKILLS.md | template-improved | consumer-untouched + template improved — safe to apply with `upgrade --apply-docs` |
| docs/ideas/README.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| .session-journal.md | unchanged | template identical across versions |
| control/README.md | diverged | both the template and the doc moved — manual merge |
| control/inbox.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| control/status.md | consumer-edited | template unchanged — consumer-owned, nothing to apply |
| control/claims/README.md | unchanged | template identical across versions |
| scripts/env-setup.sh | unchanged | template identical across versions |

## Carve-out scan

- carve-out scan: ran — no kit-owned live workflow installed, nothing to scan.

## Capability-ledger seed refresh

- capability-seed: docs/CAPABILITIES.md fence already current — nothing to refresh.

This upgrade ships the venue-scoped capability ledger (grounded-skills §4.2): entries carry a venue token (owner-live · autonomous-project · routine-fired · subagent · any) and the ledger's kit-owned seed block carries the posture decision rule. If this repo carries a local prose copy of the boot-triad/venue-posture rule (superbot Q-0270), that copy is now superseded by docs/CAPABILITIES.md's posture rule — collapse the local copy into a pointer.

## Applied (--apply-docs)

- applied: CONSTITUTION.md (template@new, hash re-recorded)
- applied: docs/SKILLS.md (template@new, hash re-recorded)

## Template deltas for diverged docs

### docs/collaboration-model.md

```diff
--- docs/collaboration-model.md (template@old, current slots)
+++ docs/collaboration-model.md (template@new, current slots)
@@ -35,6 +35,18 @@
 directly: one plain sentence, an exact click path, paste-ready text.
 Withdraw asks that have gone stale; fewer, clearer asks beat complete lists.
 
+Every owner-facing OUTPUT — not just asks — follows the owner-assist output
+standard (canonical: `control/README.md` § "Owner-assist output standard"):
+values arrive finished and paste-ready, with the exact link to where each
+one goes (a full file in one copyable block — never a recipe the owner must
+derive); every manual step carries a risk class (✅ safe / ↩️ reversible /
+⚠️ irreversible); a decision put to the owner is a structured choice —
+options A/B(/C) with a **bolded recommendation** and a one-line rationale,
+answerable with one letter — never an ask that requires the owner to
+parse, derive, or transform anything; a large output ships as a control-plane
+rendered link plus a 3-line digest in chat, with full text in one copyable
+block in chat as the fallback where the plane cannot render the repo yet.
+
 ## Friction → guard
 
 Anything that interrupts a session's workflow — a stale file, a checker that
```

### docs/question-router.md

```diff
--- docs/question-router.md (template@old, current slots)
+++ docs/question-router.md (template@new, current slots)
@@ -21,6 +21,11 @@
 - **Routing result:** (which doc / slot the answer landed in)
 ```
 
+Options are structured choices — A/B(/C) with a **bolded recommendation**
+and a one-line rationale, answerable with one letter; never a question that
+requires the owner to parse, derive, or transform anything (the owner-assist
+output standard, `control/README.md`).
+
 ## Open questions
 
 (Unanswered Q-blocks live here until the maintainer decides; a blocking one gates
```

### docs/CAPABILITIES.md

```diff
--- docs/CAPABILITIES.md (template@old, current slots)
+++ docs/CAPABILITIES.md (template@new, current slots)
@@ -16,53 +16,97 @@
 hand reminders. This ledger makes capability knowledge durable across
 sessions: one session's discovery is every later session's starting fact.
 
+<!-- substrate-kit:capability-seed BEGIN — kit-owned, refreshed at upgrade. Append your findings BELOW the fence (## Append log), never inside it. -->
+
+## Posture decision rule — establish your venue first
+
+- **Owner-live session:** assume NO special limitations apply — act and merge
+  directly (superbot Q-0269).
+- **Autonomous / routine-fired seat:** pre-route around every known stall
+  class recorded below; park only on a REAL denial, never preemptively
+  (superbot Q-0270 boot triad: model · venue · ability envelope).
+
+Venue tokens (every entry names where it was verified): `owner-live` ·
+`autonomous-project` · `routine-fired` · `subagent` · `any`. Capabilities are
+**venue-scoped, not global** — the same operation can work owner-live, be
+org-refused on a cross-session binding, and prompt-stall in a plain-started
+seat while never prompting in a Routine-spawned one (fleet night review,
+2026-07-12). A flat CAN/CANNOT ledger is wrong somewhere by construction.
+
 ## THE DISCOVERY RULE
 
 Before declaring anything impossible, and before assuming a tool or
 credential is missing:
 
-1. **Check this file** — the capability or wall may already be recorded.
+1. **Check this file** — the capability or wall may already be recorded for
+   your venue.
 2. **Check the environment** — `printenv` / list the available tools BEFORE
    assuming no credentials exist (provisioned env tokens are routinely
    forgotten, not absent).
 3. **Attempt once** — try the operation and capture the **exact** error text;
    a guessed wall and a verified wall are different facts.
 4. **Append the finding same session** — capability or wall, dated, with the
-   evidence (exact error, or proof it worked) and the workaround if one was
-   found. An unrecorded discovery is re-paid by every future session.
+   venue token, the evidence (exact error, or proof it worked) and the
+   workaround if one was found. An unrecorded discovery is re-paid by every
+   future session.
+5. **Staleness — re-verify what you build on**: an entry older than the
+   staleness window (config `cadence.staleness_days`, default 14) that your
+   work depends on is a **claim, not a fact** — re-verify it with one cheap
+   attempt and append the result. Re-verifications APPEND, never edit: a
+   refuted wall can self-resolve platform-side, and a ledger with no
+   freshness data is confidently stale — worse than ignorant.
 
 ## Capabilities — verified working
 
-- **Media is readable**: a video is never "unviewable" — extract frames
-  (`ffmpeg -i in.mp4 -vf fps=1 frame_%04d.png`) and read the images; same
-  idea for audio (transcribe) and PDFs (render pages). Try the recipe before
-  reporting a format wall.
-- **Provisioned credentials**: the environment often carries tokens/keys as
-  env vars — `printenv` first; a missing-looking credential is usually a
-  missing *look*.
-- **Release cutting despite the tag wall**: `workflow_dispatch` on the
-  release workflow (with a version input) creates the tag in-Actions —
+- `any` · **Media is readable**: a video is never "unviewable" — extract
+  frames (`ffmpeg -i in.mp4 -vf fps=1 frame_%04d.png`) and read the images;
+  same idea for audio (transcribe) and PDFs (render pages). Try the recipe
+  before reporting a format wall. — LAST-VERIFIED: 2026-07-10
+- `any` · **Provisioned credentials**: the environment often carries
+  tokens/keys as env vars — `printenv` first; a missing-looking credential is
+  usually a missing *look*. — LAST-VERIFIED: 2026-07-10
+- `any` · **Release cutting despite the tag wall**: `workflow_dispatch` on
+  the release workflow (with a version input) creates the tag in-Actions —
   proven repeatedly fleet-wide after direct tag pushes 403'd.
+  — LAST-VERIFIED: 2026-07-12
 
 ## Walls — verified blocked (use the workaround; don't rediscover)
 
-- **Tag push / release create via git**: HTTP 403 from the environment's git
-  proxy → use the workflow_dispatch release path.
-- **Branch deletion**: 403 on every path (git push `:branch` and API) →
-  owner deletes by hand / enables "Automatically delete head branches".
-- **`api.github.com` direct HTTP**: blocked → GitHub access is MCP-tools-only.
-- **Environment / routine / Project creation**: owner-click actions in the
-  console — queue them under `⚑ needs-owner`, never wait silently.
-- **Self-merge classifier**: sessions can be refused merging owner-gated PRs
-  while their other capabilities work — and the boundary differs by session
-  kind (a child session was refused where a coordinator was not). Record
-  which kind of session hit which boundary.
-- **GraphQL API quota**: tight — batch queries and prefer the REST-backed
-  MCP tools for bulk reads.
+- `any` · **Tag push / release create via git**: HTTP 403 from the
+  environment's git proxy → use the workflow_dispatch release path.
+  — LAST-VERIFIED: 2026-07-12
+- `any` · **Branch deletion**: 403 on every path (git push `:branch` and
+  API) → owner deletes by hand / enables "Automatically delete head
+  branches". — LAST-VERIFIED: 2026-07-10
+- `any` · **`api.github.com` direct HTTP**: blocked → GitHub access is
+  MCP-tools-only. — LAST-VERIFIED: 2026-07-10
+- `any` · **Environment / Project creation**: owner-click actions in the
+  console — queue them as structured owner asks, never wait silently.
+  Routine/schedule creation is NO LONGER a blanket wall: `create_trigger`
+  arms routines agent-side (proven 2026-07-11); the console-only knobs
+  (model class, branch-push, auto-fix PRs) remain owner-only.
+  — LAST-VERIFIED: 2026-07-11
+- `subagent` · **Self-merge classifier**: sessions can be refused merging
+  owner-gated PRs while their other capabilities work — and the boundary
+  differs by venue (a child session was refused where a coordinator was
+  not). Record which venue hit which boundary. — LAST-VERIFIED: 2026-07-10
+- `any` · **GraphQL API quota**: tight — batch queries and prefer the
+  REST-backed MCP tools for bulk reads. — LAST-VERIFIED: 2026-07-10
+- `routine-fired` · **Silent prompt-stalls**: a permission prompt in an
+  unattended seat is a silent stall, and grant boundaries differ by venue —
+  the same tool call can be pre-granted in a Routine-spawned seat and prompt
+  in a plain-started one. Pre-route around recorded stall classes; verify
+  grants per venue, never globally. — LAST-VERIFIED: 2026-07-12
+
+<!-- substrate-kit:capability-seed END -->
 
 ## Append log — newest first
 
-Format: `- YYYY-MM-DD · capability|wall · finding · evidence · workaround`.
+Format: `- YYYY-MM-DD · capability|wall · <venue> · finding · evidence · workaround`
+(venue ∈ `owner-live` · `autonomous-project` · `routine-fired` · `subagent` ·
+`any`; older five-field lines without a venue token stay valid — read them
+as venue `any`.)
 
-(Hand-filled by sessions, per the discovery rule. Seed walls/capabilities
-above came from the fleet's lived 2026-07 findings; local ones go here.)
+(Hand-filled by sessions, per the discovery rule. Seed rows above are
+kit-owned — they refresh at upgrade between the fence markers; local
+findings go here, below the fence.)
```

### control/README.md

```diff
--- control/README.md (template@old, current slots)
+++ control/README.md (template@new, current slots)
@@ -148,6 +148,7 @@
 WHAT: <one plain sentence, zero jargon — the thing the owner does>
 WHERE: <exact click path or URL>
 HOW: <paste-ready text/values where applicable, or "click only">
+RISK: <one class per manual step — ✅ safe / read-only · ↩️ reversible (say how to undo) · ⚠️ irreversible / destructive>
 WHY-IT-MATTERS: <one sentence, in product terms>
 UNBLOCKS: <what starts moving the moment it's done>
 VERIFIED-NEEDED: <the attempt you made + the exact error/wall proving only the owner can do
@@ -159,6 +160,69 @@
 never exit-affecting — when a non-`none` ⚑ needs-owner list lacks these fields.
 
 Grammar source of truth: the tokens, field lists, and regexes of this format are kit-owned constants in the kit's `src/engine/grammar.py` (EAP §6.8) — the SAME module the `check` enforcers consume, so writer and enforcer cannot drift; agreement is pinned by the kit's `tests/test_grammar.py`.
+
+## Owner-assist output standard — every owner-facing output, not just asks
+
+The OWNER-ACTION block above covers the *needs-owner ask*; this standard
+covers ALL output routed to the owner — reports, questions, values to paste,
+links. The contract in one line: **the owner never derives anything** — an
+output that requires the owner to parse, derive, or transform anything is a
+drafting defect, not an owner task.
+
+1. **Paste-ready, finished values.** Every value the owner must enter is
+   computed and printed final — `NAME=value`, the full command, the full
+   file body — never a recipe for deriving it. When the owner must paste
+   something, give the exact link to where it goes; a full file goes in ONE
+   copyable fenced block, directly in chat.
+2. **Exact destination, always.** Every action names its exact destination:
+   a deep URL, a console path to the exact field (surface → section →
+   field, e.g. `Railway → project → service → Variables`), or a repo path +
+   line. Never a bare "go to settings" — `check` nags that class (advisory).
+3. **Risk class on every manual step:** ✅ safe / read-only · ↩️ reversible
+   (say how to undo) · ⚠️ irreversible / destructive. One class per step,
+   stated on the step (the `RISK:` line in an OWNER-ACTION block).
+4. **Structured choices, recommendation first.** A decision put to the
+   owner is options A/B(/C) with a **bolded recommendation** and a one-line
+   rationale, answerable with one letter — never an ask that requires the
+   owner to parse, derive, or transform anything.
+5. **Large outputs: digest + rendered link, never a wall of text.** Default
+   delivery is a control-plane rendered link plus a 3-line digest in chat;
+   the fallback — full text in one copyable block directly in chat — applies
+   where the control plane cannot render the repo yet. Link rules: deep-link
+   the exact file, never the repo root; the rendered view for things the
+   owner should *read*, the GitHub blob URL for things the owner should
+   *edit*; post-merge, link `ref=main`; the control-plane render cache is
+   180 s — append `&refresh=1` when the owner must see a just-pushed change.
+
+Worked example — digest + rendered deep link + a six-field ask carrying its
+risk class (every rule above in one output):
+
+```
+📄 Adopter-outcomes report — shipped (PR #247, merged b862e9a)
+
+Digest: before/after adoption is unmeasurable (9/10 adopters born <20h
+before their kit-install PR); false-claim audit near-clean (1 confirmed,
+self-corrected in 6 min); post-adoption time-to-ship baselines recorded.
+
+Full report (rendered, phone-readable):
+https://control-plane-production-abb0.up.railway.app/journal/substrate-kit/file?path=docs/reports/2026-07-11-adopter-outcomes-measurement.md
+
+⚑ OWNER-ACTION — set GITHUB_TOKEN on the control-plane service
+WHAT: paste one variable into Railway so private-repo pages stop degrading.
+WHERE: railway.app → project `websites` → service `control-plane` →
+       Variables → New Variable.
+HOW (paste-ready): name `GITHUB_TOKEN`, value = the fine-grained PAT you
+       created for the fleet's repos (contents: read). One paste, Save.
+RISK: ↩️ reversible — delete the variable to undo.
+WHY-IT-MATTERS: private-repo renders show "not-configured" banners until
+       this is set.
+UNBLOCKS: rendered file links + queue items for private repos.
+VERIFIED-NEEDED: attempted 2026-07-11 — raw fetch of a private path
+       returns 404 without a token (token-on-raw also verified NOT to
+       work, so the API fallback is the only private path).
+```
+
+Grammar source of truth: the risk-class tokens, the structured-choice phrases, and the vague-destination scan of this standard are kit-owned constants in the kit's `src/engine/grammar.py` — the SAME module the `check` enforcers AND the `/intake` skill pins consume, so writer, skill, and enforcer cannot drift; agreement is pinned by the kit's `tests/test_owner_assist.py`.
 
 ## `inbox.md` order format (manager-written, append-only)
 
```

