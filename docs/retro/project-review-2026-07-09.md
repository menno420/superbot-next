# Project review — superbot-next gen-1 (2026-07-09)

> **Status:** `historical` — ORDER 006 deliverable (agent audit + owner-actions + continuation, point-in-time).
> Companion to `docs/retro/self-review-2026-07-09.md` (ORDER 005, PR #87) — that
> file answers the QUESTIONS.md IDs; THIS file is the agent audit, the ⚑
> owner-actions list, and the continuation section the retro was missing.
>
> **Method + honesty note on attribution.** This Project's sessions did not
> record model identity anywhere durable. The only in-repo evidence is the
> squash-commit `Co-authored-by:` trailer, which is `Claude
> <noreply@anthropic.com>` (model unspecified) for 30 of 38 main commits.
> Exactly three sessions left a model-bearing trailer: the orchestration
> retrospective (PRs #51/#53) and the band-4 testing session (PRs #88/#90) —
> both `Claude Fable 5`. Everything else below is marked **cannot determine**.
> Session cards/telemetry live on the coordinator/owner side, not in this
> repo; if they exist, they can overwrite the "cannot determine" cells.

## 1. Agent audit — every session/worker

Stall causes are classified per the B1 taxonomy: **(a)** preventable by the
agent, **(b)** preventable by better setup/seed, **(c)** genuinely external.

### 1.1 Build phase (2026-07-08 16:17Z → ~14h, PRs #1–#50)

One coordinator session + one long-lived builder session spawning **18
sequential workers** (full narrative:
`docs/status/rebuild-orchestration-retrospective-2026-07-09.md`). Model for
every build worker: **cannot determine** (trailers say only "Claude").

| # | Worker | Delivered | Stalls (cause) |
|---|---|---|---|
| 1–2 | repo-population ×2 | repo seed, structure, migrations skeleton | none recorded |
| 3 | kit-CI | checker fleet + CI wiring (green from PR #1) | none recorded |
| 4–8 | kernel S0–S15 ×5 | the kernel bands (workflow engine, K-lanes, settings, panels, outbox) | required-checks misconfig froze PR #35 at "Expected" until the ruleset was fixed **(b)** |
| 9 | layer-V | versioning/StoreSpec layer | none recorded |
| 10 | K10 | invariants/sweep machinery | none recorded |
| 11–15 | Sequence-C port bands ×5 | domain ports (bands 1–7 corpus) | band-3 build worker **externally killed mid-task** **(c)**; transient real CI failures on PR #40 fixed before merge **(c→a resolved)** |
| 16 | scout | verified repo/branch state after the kill | none — dispatched BECAUSE of a stall |
| 17 | continuation | resumed band 3 cleanly from the scout's map | none recorded |
| 18 | resumed worker | finish + consolidation | none recorded |
| — | coordinator + builder sessions | plan, owner interface, PR #50 completion report | one child session died at provisioning **(c)**; child briefs capped ~4KB forced relay-worker hops for mid-task corrections **(b)** |

### 1.2 Testing/hardening phase (2026-07-09, PRs #51–#90)

Sequential single-worker sessions (same Claude-Session id on every commit),
each handing off via scratchpad files + `control/status.md`.

| Session | Model | Delivered (main) | Stalls (cause) |
|---|---|---|---|
| Orchestration retrospective | **Claude Fable 5** (trailer) | #51/#53 retrospective doc; #52 old-vs-new diff overview (sibling) | `check --strict` findings needed a follow-up commit (#53) **(a)** |
| Kernel-boot smoke (CUT-1) | cannot determine | #54 composition root (`python3 -m sb` → RUNNING; found+fixed the draft.py timestamptz PREPARE bug live); #55 report row | PR #54 went "behind" twice under the up-to-date ruleset while doc PRs raced it **(b)** |
| Band-1 (settings/help/diag/setup) | cannot determine | #56 panel registration fix, #58-class dispatch fix (f04fd4f), band-1 report row (855f94a); replay 0/53 ledgered-red | none recorded beyond the shared merge dance **(b)** |
| CUT-1 successors | cannot determine | #61 app-command registration + live prefix feed (ledgered); #62-class report row | left heartbeat PR #60 open with cancelled CI — the Q-0103 abandoned-PR class, later closed by ORDER 003 **(a)** |
| Band-2 slice-1 (moderation/logging) | cannot determine | #63-class moderation ack/target/duration fixes (4d9b382); report row (73cd4cb) | none recorded |
| Owner-feedback triage | cannot determine | #65-class component-feed arming (b8cbd05), #66-class confirm re-entry fix (a6d48d1), triage report row (a627153) | the owner's live session was contaminated by the OLD bot answering `!` in the same guild (flag 15) **(b/c)**; "PASS (live)" had contradicted the owner's eyes → ORDER-004 item 5 rule **(a)** |
| Presentation rework | cannot determine | #69-class S9b confirm view (a9aeb08), kit v1.2.0 upgrade (4755f8b), category help (1492d18), render rule (59755e3), report+heartbeat | scope boundary (settings-EDIT vs presentation) needed an owner ruling — parked as flag 14/17a rather than guessed **(deliberate stop, not a stall)** |
| ORDER-002 plugin host | cannot determine | #75 plugin contract v1 (entry-point host, hash pins, hello example), report row #76-class, heartbeat | GitHub App 403 on repo-create — integration tokens cannot create `menno420/superbot-plugin-hello` **(c)** → flag 18a, still open |
| Band-2 slice-2 (operator spine) | cannot determine | #79 responder chunking + word-op acks, #80 warn-escalation compensator (= ORDER-004 item 1); both ledgered, #81 report, #82 heartbeat; replay 0/14 classified | none beyond the merge dance **(b)** |
| Band-3 (economy family) | cannot determine | #83 ORDER-004 item 4 (platform latch lane, handler kit, DM successor), #85 four seam/ack/copy fixes; both ledgered, #86 report, #87 ORDER-005 self-review; replay 0/9 classified | **ran out of context mid-wrap-up**: #86/#87 left un-merged behind the ruleset, band-3→4 handoff file never written **(a/b — context budget)** |
| Band-4 (xp/karma/community — THIS session) | **Claude Fable 5** (trailer) | inherited wrap-up (merged #86/#87 via API branch-update); #88 four fixes (chat-award feed armed live+harness, RNG seam 2nd victim, karma two-clocks cooldown bug, refusal copy 4th victim; ledgered — the band-4 decisions entry); #90 report row; replay 0/15 classified, live ladder driven; this document (ORDER 006) | GitHub GraphQL rate limit blocked `enable_pr_auto_merge` ~25 min (REST still worked — merged via REST once checks completed) **(c)**; one REST merge attempt returned 405 while required checks were still "Expected" **(a — retried too early)** |
| Manager (inbox writer) | cannot determine | ORDERs 001–006 (#57, #68, #74, #78, #84, #89) | n/a — one-writer protocol held; zero inbox conflicts |

### 1.3 Audit observations

1. **Zero unresolved stalls.** Every stall above either resolved in-session,
   was resolved by a successor (scout/continuation, band-4 wrap-up), or is a
   ledgered owner-action (flag 18a). No abandoned work exists on main;
   the one abandoned PR (#60) was terminal-stated by ORDER 003.
2. **The dominant (b)-class stall is the merge dance**: the ruleset's
   require-up-to-date + concurrent PRs cost every session manual
   branch-update passes (PR #54 twice; #86/#87 stranded a whole session's
   tail; #88/#90 each needed one). A merge queue or a doc-path exemption
   removes the entire class (also flag 4 in the testing report).
3. **The dominant (a)-class lesson is budget-for-wrap-up**: the band-3
   session spent its context on excellent fixes and left its own PRs
   un-shepherded. Gen-2 shape: wrap-up (merge + handoff + heartbeat) is the
   FIRST claim on budget, not the last.
4. **Model attribution is a one-line fix**: the commit trailer already
   carries a co-author name; sessions should write the model id there (as
   the two Fable 5 sessions did) and in the status heartbeat. Recommend a
   seed rule: `Co-Authored-By: Claude <model-id> <noreply@anthropic.com>`.

## 2. ⚑ Owner-actions (WHAT / WHERE / HOW / WHY / UNBLOCKS)

Consolidates every standing ⚑ from `control/status.md`, the testing report's
"Flagged for owner", and the self-review's D4 grant list. Ordered by leverage.

1. **WHAT:** Rule on the corpus-red disposition (flag 13, kernel-surface
   drift). **WHERE:** one paragraph appended as an inbox ORDER (or a doc in
   `docs/` the ORDER points at). **HOW:** choose per class: exemption rows /
   normalizer scope / accepted-forever red — for kernel event+audit shapes,
   the old `xp.coins` alias column, and the invoking-message deletion.
   **WHY:** bands 1–4 are 0/91 with every red already classified; the
   classification is done, only the POLICY is missing. **UNBLOCKS:**
   ORDER-004 item 2 (help byte-parity, the first A-16 `pending→ported`
   flip), every later band's flips, and the `report` CI leg going green.
2. **WHAT:** Create the repo `menno420/superbot-plugin-hello` (flag 18a).
   **WHERE:** GitHub, owner account. **HOW:** create empty repo, move
   `examples/superbot-plugin-hello/` verbatim (pin hashes the manifest, not
   the repo — no re-pin needed). **WHY:** integration tokens get 403 on
   repo-create; this is the ONLY remaining ORDER-002 done-when item.
   **UNBLOCKS:** ORDER 002 → done; the mining/exploration game Projects'
   reference pattern.
3. **WHAT:** Kill the branch-update merge dance. **WHERE:** repo ruleset /
   merge settings. **HOW:** enable the merge queue, or drop
   require-up-to-date for `docs/**`+`control/**` paths. **WHY:** every
   session lost time to it and one session's tail was stranded on it (§1.3
   item 2). **UNBLOCKS:** unattended session wrap-ups; less API traffic
   (the same dance triggered today's rate-limit stall).
4. **WHAT:** Invite a sacrificial test member and share its id (flag 9).
   **WHERE:** MineSnakeBotTest guild. **HOW:** throwaway Discord account,
   post the id in an inbox ORDER. **WHY:** kick/ban full-effect proof needs
   a kickable body; ban fires WITHOUT confirm once the guild-action adapter
   arms. **UNBLOCKS:** band-2 moderation `verified_live` evidence with real
   effects + unban undo.
5. **WHAT:** Remove the OLD SuperBot from the test guild or change one
   prefix (flag 15). **WHERE:** MineSnakeBotTest. **HOW:** kick
   1403818430758654132 or reconfigure its prefix. **WHY:** two bots answer
   `!`, which contaminated the owner's hands-on session once already.
   **UNBLOCKS:** clean owner hand-passes; unambiguous prefix_twin_live
   evidence. (NOTE: with the band-4 chat award armed, the old bot's
   messages are correctly ignored as bot-authored — but human testers still
   see doubled replies.)
6. **WHAT:** Boundary ruling — settings-EDIT hub + setup-wizard FLOW
   (flags 14/17a). **WHERE:** inbox ORDER. **HOW:** name them functionality
   successors (schedule a band) or presentation successors (stay parked).
   **WHY:** they are the largest unported band-1 surfaces and block those
   golden rows forever otherwise. **UNBLOCKS:** band-1 corpus health;
   scoping for a settings-EDIT worker.
7. **WHAT:** Ratify the hub topology (flag 21). **WHERE:** inbox ORDER
   referencing the sim-pass-1 categories. **HOW:** yes/no on the harvested
   category seed + `parent_hub` growth + Home-nav wiring. **WHY:** the v1
   declaration-first hubs deviate from the shipped 5-feature grids
   (band-4's community hub red class); one ruling covers every hub.
   **UNBLOCKS:** hub render parity classes; the BrowserView successor scope.
8. **WHAT:** Test-plane AI envelope for band 7. **WHERE:** environment
   (secret store). **HOW:** `ANTHROPIC_API_KEY` with a spend cap +
   `AI_ENABLED` flag flip, per completion report §5 step 9. **WHY:** AI is
   deliberately dormant; band 7 cannot start without keys. **UNBLOCKS:**
   the last testing band (NL shell, review loop, presets, routing).
9. **WHAT:** Hands-on pass of the presentation surfaces. **WHERE:** test
   guild (bot is RUNNING from latest main). **HOW:** the click list from
   the coordinator; NEW this session — type any message in a test channel
   and check `!rank`: a real keyboard message should earn 15–25 XP on a
   60s cooldown (the one evidence line agents cannot synthesize). **WHY:**
   ORDER-004 item 5 — owner eyes are the presentation oracle. **UNBLOCKS:**
   human-lane `verified_live` rows; flag 16's remaining click evidence.
10. **WHAT:** Standing-grant set for gen-2 (self-review D4, as policy).
    **WHERE:** gen-2 Project seed. **HOW:** repo-create + merge-queue
    bypass on the namespace; sacrificial account + intents pre-approved;
    capped API key; the flag-13-class disposition rule written at seed;
    bot-restart pre-approval. **WHY:** these five grants were every stop
    this generation hit. **UNBLOCKS:** zero-human end-to-end for gen-2.

## 3. CONTINUATION — what the next session picks up

- **Ladder position:** completion report §5 — steps 1–6 DONE (kernel boot,
  band 1, band 2 ×2 slices, band 3, band 4; plus OF/PR/O2 side rows). NEXT
  = **step 7 / band 5: governance + roles + platform** (visibility chain,
  capability overrides, role feasibility/automation, temp grants + expiry
  sweep, command-access policy, proof_channel locks, teardown hooks;
  goldens: role 1, proof_channel 3, general/utility sweeps). Then step 8
  games (wager→checkpoint→message), step 9 AI (needs owner action #8).
- **Band-5 handoff:** session scratchpad `band4-handoff.md` — includes the
  fresh-DB replay recipe, the driver composition (subscribe roster armed,
  `Resp.ack` trap), the settings/binding bracket patterns, synthetic-actor
  block discipline (use 06xx), and the band-5 audit target: **grep the
  band-5 stores for `NOW()` before live-driving** (karma's two-clocks
  cooldown bug — the band-4 ledger entry — is exactly the shape temp-grant expiry sweeps
  would repeat).
- **Standing rules that bind every next band:** ORDER-004 item 3
  (walking-skeleton live-drive from the branch BEFORE merge +
  classify-or-fix every replay red in the same PR) and item 5 (owner-visible
  demos name their known-red presentation classes).
- **Open order state:** 001 done · 002 acked (owner-blocked on action #2) ·
  003 done · 004 items 1/3/4 done, item 2 gated on action #1 · 005 done
  (PR #87) · 006 done (this document).
- **Environment as left:** test bot RUNNING from latest main (HEALTH 8080,
  `/ready` 200, 13 guild commands, plugin admitted, message feed armed WITH
  the passive XP chat award); Postgres 16 up (superbot_test + disposable
  parity_band1..4 DBs); DB rows left by testing are documented per band in
  the testing report; boot recipe in the scratchpad `boot-handoff.md`.
- **Where the truth lives:** testing ledger
  `docs/status/testing-report-2026-07-09.md` (rows + flags), the full decisions ledger
  `docs/decisions.md`, protocol `control/README.md`,
  self-review `docs/retro/self-review-2026-07-09.md`, build narrative
  `docs/status/rebuild-orchestration-retrospective-2026-07-09.md` +
  `rebuild-completion-report-2026-07-09.md`.
