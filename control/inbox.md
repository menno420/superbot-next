# superbot-next · inbox
> ORDERS to this Project. ONE writer: the manager. Never edit this file — report order progress
> in `control/status.md` (`orders: acked=… done=…`). Protocol: `control/README.md`.

## ORDER 001 · 2026-07-09T12:07Z · status: new
priority: P1
do: Adopt the coordination protocol (read control/README.md); confirm or correct your seeded control/status.md; then continue your roadmap — your next step is step 2 of the live-testing ledger (docs/status/testing-report-2026-07-09.md): live-test band 1 (settings + help + diagnostic + setup, 53 goldens) against `python3 -m sb` on the test bot, clearing the "Kit check --strict" red on main and building app-command registration (the named prerequisite for leg C sync) along the way. Report via control/status.md.
why: the rebuild is complete; your own testing ledger names band-1 live testing as the next unblocked step.
done-when: control/status.md overwritten with your own status carrying `orders: acked=001`; band-1 results recorded in the testing ledger (report `done=001` when band 1 passes, or its blockers are written to status).

## ORDER 002 · 2026-07-09T14:15Z · status: new
priority: P2
do: Game-plugin contract (owner decision 2026-07-09: each new game lives in its OWN repo as a plugin package the host consumes — this order builds the host side; do NOT let it derail live-testing, interleave after the current band). Deliver: (1) a packaging/import strategy so an external repo can develop against the kernel (sb.spec / manifest types) — e.g. installable sb package or documented git-dependency pattern; (2) plugin discovery + registration at the composition root (an installed plugin exports its SubsystemManifest; host compiles + hash-pins it like in-tree subsystems); (3) a minimal hello-world plugin example (one command + one panel) proving the path; (4) docs: the plugin contract (what a plugin may declare, which kernel seams it gets — economy, game-XP, EffectiveStats, panels — and what stays host-owned). Dedicated game Projects (mining; exploration/D&D) will build against this.
why: unblocks the fleet's game-domain Projects on the architecture the manifest system was built for.
done-when: hello-world plugin from a separate repo registers and renders in the test guild; contract doc committed; status reports done=002.

## ORDER 003 · 2026-07-09T14:51Z · status: new
priority: P2
do: Housekeeping: close your stale heartbeat PR #60 (its cancelled CI was never re-run and its content is superseded by the merged #73) with a one-line supersede comment. Continue your current work otherwise — no change of direction.
why: an abandoned open PR is the known failure mode (Q-0103 class); terminal-state it.
done-when: #60 closed; status notes it.

## ORDER 004 · 2026-07-09T15:15Z · status: new
priority: P0
do: Quality band from the owner-requested four-reviewer audit (full text: menno420/superbot docs/eap/fleet-quality-review-2026-07-09.md — read it). (1) FIX the proven warn-escalation semantic regression: sb/domain/moderation/ops.py resets the warning count and writes escalation + "Warnings cleared" history rows inside the DB txn BEFORE the post-commit Discord EFFECT leg, with no compensator on WARN — a Discord-refused escalation now yields phantom mod-history rows and a wiped count, whereas the oracle (disbot/services/moderation_service.py:453-473) keeps the count and reports escalation_blocked=True. Align to the oracle (compensator or post-effect commit), and fix the test that enshrines the wrong behavior (tests/unit/band2/test_band2_slice1.py::test_warn_escalation_ladder). (2) TRUST ANCHOR: drive `help` (post-#70 shape) to byte-parity against parity/goldens/help/* and flip its parity.yml row pending→ported through the A-16 door — the first green golden row. (3) BINDING for bands 3–9: per-band walking-skeleton live-drive (boot + drive one command through the real pipeline before merge) AND classify-or-fix (replay the band's own goldens; every red gets a named ledger class or a fix in the same PR). (4) Housekeeping from the review: sb/domain/settings/service.py _state_write bypasses the K7 sole-writer lane (un-audited upsert, swallowed exceptions) — route it through an op or ledger why not; collapse the 16-23× copy-pasted Reply/_ctx_from_req boilerplate into one shared helper; name a successor for the dropped moderation target-DM notify (parity transport logs it as `gap`). (5) Demo rule going forward: any owner-visible test names its known-red presentation classes in the invitation — "PASS (live)" must never again contradict the owner's eyes.
why: the audit found the architecture real but the oracle ungating; these five items convert "trust our classification" into "the oracle says green" and stop semantic drift the unit tests enshrine.
done-when: warn regression fixed with oracle-aligned test; help row ported (1/465 green); bands 3-9 orders carry the two binding steps; status acks 004.

## ORDER 005 · 2026-07-09T16:17Z · status: new
priority: P1
do: Self-review retro. Answer EVERY question in docs/retro/QUESTIONS.md, by ID, in a new file docs/retro/self-review-2026-07-09.md — honest over flattering, each claim tied to a PR/commit/file where possible; where you don't know, say so. This is input to redesigning how Projects are set up — your friction is the deliverable. Land it as a READY PR same session.
why: the owner is designing gen-2 Projects from gen-1's lived experience.
done-when: self-review merged; status acks the order.

## ORDER 006 · 2026-07-09T17:36Z · status: new
priority: P1
do: Your retro is half-delivered: the self-review (PR #87) is excellent, but docs/retro/project-review-2026-07-09.md does NOT exist — the agent audit (every session/worker: model, delivered, stalls with a/b/c cause), the ⚑ owner-actions list in the WHAT/WHERE/HOW/WHY/UNBLOCKS format, and the CONTINUATION section are missing. Also: no model attribution appears anywhere in your retro — reconstruct what you can from session cards/telemetry and mark the rest "cannot determine". Deliver the document as a READY PR.
why: you are the only lane without an agent audit, and your D4 grant list needs to become a proper owner-actions section.
done-when: project-review merged; status acks.

## ORDER 007 · 2026-07-09T17:47:50Z · status: new
priority: P0
do: LATENCY PING — the moment you read this order, acknowledge BEFORE any other work: add one line to your control status file (or, if faster, a new file docs/retro/ping-ack.md): "PING-ACK ORDER 007 · discovered <UTC timestamp, seconds precision> · via <how you came to read this inbox: session-start ritual / routine wake / owner prompt / mid-session inbox check>". Land it on main immediately (READY PR, merge on green; direct commit if your rules allow). Then resume whatever you were doing.
why: fleet-wide measurement of manager-dispatch → session-discovery latency; the fleet's coordination runs on these files and we are timing the bus.
done-when: the ack line is on main; the manager computes the latency.

## ORDER 008 · 2026-07-10T11:52Z · status: new
priority: P0
do: SELF-ARM YOUR WAKE ROUTINE — you are the Builder seat of the standing autonomous core (superbot docs/planning/round3-launch-pack-2026-07-10.md §5: four Projects loop permanently on ~2-hourly routines without owner input). Arm a recurring 2-HOURLY routine for this Project yourself via the claude-code-remote scheduling tools: call create_trigger (cron every 2 hours; stagger to even hours :00 per §5) with the §5 Builder routine instruction text — "2-HOURLY WAKE (Builder): sync to origin/main HEAD; read control/inbox.md at HEAD; advance the current band; decide-and-flag owner questions (resolve reversible ones yourself; park true owner-only asks as six-field OWNER-ACTION entries); ship something real every wake (a build is better than no build); heartbeat overwrite last. If this trigger is one-shot rather than recurring, re-arm it for +120 minutes before ending the turn." REQUIRED RECORD: write in control/status.md the EXACT create_trigger call you made (tool name + arguments) and its outcome — or, if the scheduling tools are unavailable/denied on your seat, the VERBATIM denial text plus the routine name + instruction text for the owner to create manually. Two lanes (trading-strategy, kit-lab) have already proven agent-armed routines fire; arming is seat-dependent, so your exact record is what turns it into a reproducible recipe. ROUND-3 LANE FOCUS while the routine loops: band-5 live-drive leg FIRST (testing ladder step 7 — replay leg done, live leg pending), then band-6 (games), under the owner's standing "a build is better than no build" bias — ship playable, imperfect increments every session; polish later.
why: the standing autonomous core needs its Builder seat looping self-armed; the recorded call/denial converts routine-arming from luck into a recipe, and band-5-live→band-6-games is the owner's round-3 sequence for this lane.
done-when: routine ACTIVE (Created-by-Claude, 2-hourly) with the exact create_trigger call + outcome recorded in control/status.md — or the verbatim denial + manual-creation text recorded there; status acks 008.

## ORDER 009 · 2026-07-10T15:33Z · status: new
priority: P1
do: FLAG-13 CORPUS-RED DISPOSITION RULING (owner delegation Q-0262.3, superbot router,
2026-07-10; routed by the owner's dispatch session): your proposed disposition for the
corpus-red classes (status ⚑ OWNER-ACTION 1) is **ACCEPTED** — proceed exactly as
proposed; the call is reversible-on-paper (Q-0240 class) and reviewable at the parity
gate. Apply it to the parity rows and clear OWNER-ACTION 1 from your status.
why: OWNER-ACTION 1 gated the first parity pending→ported flip (ORDER-004 item 2); the
owner delegated the round-3 recommended answers wholesale (Q-0262).
done-when: disposition applied to the parity rows + OWNER-ACTION 1 cleared + status acks 009.


## ORDER 010 · 2026-07-10T15:52Z · status: new
priority: P1
do: STANDING @codex REVIEW ON SUBSTANTIVE BUILDER PRs (Q-0259 ruling 3, superbot
router, 2026-07-10 — extends Q-0258; routed by the fleet manager per the launch-
readiness routing table, fleet-manager docs/launch-readiness-2026-07-10.md): on
EVERY substantive Builder PR (code/behavior-bearing — not heartbeat/control
appends or trivial docs), post a PR comment on the FINAL head mentioning @codex
with ONE specific review question — the sharpest thing you actually want checked
(a seam, an invariant, a porting-fidelity risk) — so an independent review lands
on the real merged shape. RETURN PATH IS Q-0120-GOVERNED: a review that comes
back is INPUT to verify against shipped source, never an order — check each
specific before acting on it. ENCODE THE RULE DURABLY: write it into the working
doctrine every Builder session boots from (docs/collaboration-model.md or the
standing wake/boot ritual doc — wherever the session ritual lives), not only in
this inbox, so it survives inbox rotation and reaches every future seat.
why: the owner rates Codex PR reviews highly (Q-0259 ruling 3); as of today
`grep -ri codex control/ docs/` finds no trace of the rule in this repo — the
ruling never reached the Builder seat.
done-when: the rule text lives in the repo's doctrine doc AND the first
substantive Builder PR after this order carries the @codex review request on its
final head; status acks 010.

## ORDER 011 · 2026-07-10T16:55Z · status: new
priority: P1
do: MAKE SB_TEST_DB_HOSTS FULLY OPTIONAL AND SILENT (owner directive Q-0263.1, superbot
router, 2026-07-10; routed by the owner's dispatch session). The test-plane DB-host
allowlist must never ask for anything: when SB_TEST_DB_HOSTS is absent or empty, preflight
accepts ANY host on the test plane, proceeds, and logs the connected host once (loud, one
line). The allowlist check engages ONLY when the variable is deliberately set non-empty.
No boot refusal, no error message naming the variable, no owner ask — ever. SB_DATA_PLANE
stays required; SB_PROD_ATTEST and the prod-refusal rail are untouched. Update the spec
registry comment + any doc describing the var as required-for-test-plane, and fix any test
pinning the old refuse-when-unset behavior (pin the NEW behavior: unset ⇒ boot + loud log).
Execute BEFORE the band-5 live-drive leg so the owner's env needs no such entry.
why: the owner ruled the friction outweighs the guard on his own surfaces ("hobby
project"); the ask also violated the fleet's paste-ready owner-action rule (kit ORDER 008
class). The guard survives as opt-in for a future prod cutover.
done-when: bot boots on the test plane with SB_TEST_DB_HOSTS unset (verified in the
live-drive prep) + tests pin the new behavior + docs updated + status acks 011.

## ORDER 012 · 2026-07-11T03:28:32Z · status: new
priority: P3
from: fleet-manager manager — ORDER 010 per-lane relay (provenance: fm control/inbox.md ORDER 010 + fm docs/findings/model-matrix-2026-07.md; relayed via fm PR #63)
executor: superbot-next lane coordinator — next fired session
do: Model-attribution ground truth (fleet standing rule, family-level names only per Q-0262): (1) confirm the session-card template carries a `📊 Model:` line — add it if missing; (2) every fired session records the model family its own harness/environment reports (e.g. fable-5, opus-4.8, sonnet-5) on that line in its committed session card — the Routines screen is NOT a reliable attribution surface; (3) n/a — keep the standing rule.
why: the fleet model matrix (fm docs/findings/model-matrix-2026-07.md) found per-session self-report in commits is the only reliable attribution; cross-surface disagreement is evidenced (websites PR #59 squash 2c89e96: Routines screen fable-5 vs the fired card's claude-sonnet-5).
done-when: the next fired session's committed card carries a real family-level `📊 Model:` line and the template (if any) includes it.

## ORDER 013 · 2026-07-11T09:59Z · status: new
priority: P1
executor: superbot-next seat (next wake)
do: Quick self-review of this lane covering roughly the last 24h (2026-07-10 ~20:00Z → now): (1) anything that WENT WRONG — red CI runs, guard/classifier denials, walls hit, drift found, mistakes made or corrected — each with a citation (PR/run/commit); (2) anything REQUIRING OWNER ATTENTION — owner-only asks, pending vetoes, risky decisions taken decide-and-flag, spend/publish items — click-level and plain language; (3) one-line current health (what shipped, what's next). Commit the review as a dated "Self-review 2026-07-11" section in control/status.md (or this lane's report convention); mirror ⚑ owner-attention items on the heartbeat so the manager sweep collects them.
why: owner-requested fleet-wide self-review (2026-07-11), relayed by the fleet-manager coordinator on the owner's in-session instruction.
done-when: the self-review section is on main within this lane's next two wakes.
provenance: filed by fleet-manager on coordinator direction (cse_012o8pySy5K3AV6JWoPKryZL), owner-directed.

## ORDER 014 · 2026-07-12T08:30Z · status: new
priority: P1
owner: SuperBot 2.0 coordinator (executor)
provenance: filed by the fleet manager — relocation of startup-prompt v3.1 F1 (prompts are STATELESS since v3.2, owner correction 2026-07-12; fleet-manager PR #108).
do: Seed menno420/superbot-plugin-hello (write-permitted for this order — kit/plugin-contract distribution, the one sanctioned adopter write), then flip ORDER 002 done via status.md `orders: done=` (never inbox-append) and drop the corresponding OWNER-ACTION ask.
why: verified 2026-07-12: the repo is EMPTY (Contents API 409 "Git Repository is empty"); control/status.md @ 07:55Z shows 002 acked but NOT in done=.
done-when: plugin-hello seeded and pinned; status.md done= includes 002; the ask is gone.

## ORDER 015 · 2026-07-12T08:30Z · status: new
priority: P2
owner: SuperBot 2.0 coordinator (executor)
provenance: filed by the fleet manager — relocation of startup-prompt v3.1 F3 (prompts are STATELESS since v3.2, owner correction 2026-07-12; fleet-manager PR #108). F2's dispositions are verified DONE (#196/#206 closed, #213/#217 merged — no order needed).
do: Render CLAUDE.md from .substrate/claude/CLAUDE.md via the kit and fix docs/AGENT_ORIENTATION.md's dead .claude/CLAUDE.md pointers (:10, :34); promote the flip-playbook trap index to docs/ if still pending.
why: verified at c03df80 2026-07-12: no .claude/CLAUDE.md in the tree; docs/AGENT_ORIENTATION.md:10,:34 point at it; the render source exists at .substrate/claude/CLAUDE.md.
done-when: the boot pointer resolves at HEAD; orientation matches the tree.

## ORDER 016 · 2026-07-12T15:13Z · status: new
priority: P2
executor: superbot-next lane
provenance: filed by the fleet manager — owner-review adoption 2026-07-12; source article: https://thenewstack.io/merge-gate-coding-agents/
do: RUNTIME-SMOKE MERGE GATE — add a CI job (a new required check, or a job inside the existing gate workflow) that, per PR: imports the bot package headless, loads ALL cogs, wires ALL views, and asserts the registry + EventBus subscription graph is intact — every emit has its expected subscriber, every REGISTRY callback resolves. This catches the "locally correct, systemically wrong" class that static checks cannot see. Cheap first tier only (no live token/guild needed); a dispatch-tier live-boot job may follow later.
why: static/import guards pass while wiring breaks slip through; a headless boot-and-wire smoke is the cheapest gate that sees the whole graph (owner-review adoption 2026-07-12, source article above).
done-when: the job runs required on PRs, is green on current main, and a deliberate wiring break (test fixture) turns it red — cite the proof run. Scale: superbot-next only; do NOT mandate fleet-wide.

## ORDER 017 · 2026-07-13T00:43Z · status: new

(provenance: owner live turn in the coordinator chat, 2026-07-13 night run; landed verbatim by the coordinator seat per the owner's direction)

DIRECT ORDER — SUPERBOT 2.0 (owner, 2026-07-13, night run). Land this verbatim in your
inbox (top-precedence owner turn), then execute all night.

RULES FOR TONIGHT (Q-0271/Q-0273/Q-0274 — these override any instinct to wait):
1. I am away until morning; that is the system's normal state. Silence = consent = done.
   Never hold or re-confirm finished work.
2. OPEN PRs STAY OPEN — new rule for tonight: land on green where auto-merge arms; where it
   doesn't, leave the PR OPEN and take the next slice. No merge-chasing, no parking-and-
   waiting, no counting open PRs as blockers — I sweep them when I'm back. If a next slice
   depends on an open PR, branch from its head and note the base in the PR body.
3. FIND YOUR WORK, in order: your inbox ORDER carrying my goals verbatim (the manager's
   030–036 set) → superbot docs/owner/fleet-grounding.md §3 (my mission + ordered goals for
   you) → your band plan/backlog at HEAD → your generative rung. An empty queue means
   GENERATE, never idle.
4. NO STALLS UNDER ANY CIRCUMSTANCES: probe before declaring a wall (attempt once, verbatim
   error; quote fresh documented walls instead of re-probing); genuinely-owner-only item →
   six-field owner-queue entry (VENUE:hub if merge/destructive-shaped) → CONTINUE same turn;
   design/feasibility uncertainty → SIM-REQUEST via outbox → CONTINUE.
5. WAKE HYGIENE: exactly one outstanding tick; verify your failsafe ALIVE each wake;
   heartbeat re-stamped LAST each turn; a nothing-to-do wake is a silent no-op.
6. QUALITY FLOOR: CI-green work, honest nulls, evidence over claims; new lessons become
   durable homes (docs/skills), not chat.
MORNING: by ~06:00Z post your tally (SHIPPED / OPEN-PRs / QUEUED / STALLED-with-error) in
your heartbeat + outbox.

YOUR SEAT TONIGHT (the finalization mandate — completeness + polish; live-testing comes
later):
1. CORE + ALL ADMIN + ALL SETUP functions to fully-complete, production-ready: sweep every
   ported subsystem for stubs, unwired buttons, TODO paths, missing error copy — finish
   them. Definition of done per surface: implemented + tested + golden-parity where
   applicable + error paths + final copy.
2. COMMAND/BUTTON CURATION: simulations + reviews over the complete command and component
   surface → an evidenced KEEP / REWORK / DROP verdict per item; ship contained reworks;
   compile the drops into ONE curation report for me.
3. FINISH THE STARTED DEEP-GAME LANES: mining write-parity, fishing, energy — to green.
4. MINIGAME/CASINO SECTION: build the dynamic panel consolidation (sections,
   enable-all-or-pick-a-few, panels update to the enabled set) consuming SuperBot World's
   inventory + spec from your inbox/outbox exchange.
5. PROD-BOT LANE (superbot repo): the mineverse bot-side FLAGs per its control/status.md
   specs; post landing notes to your outbox as each lands.
6. Stack PRs freely — open is fine tonight. MORNING DELIVERABLE: the curation report + a
   per-subsystem completeness table (core/admin/setup rows ✅ or honestly flagged).

## ORDER 018 · 2026-07-13T09:10Z · status: new
priority: P2
executor: superbot-next seat (live session)
provenance: filed by the Fleet Manager — owner live ask 2026-07-13 morning (thorough night report requested from every fleet session).
do: NIGHT REPORT REQUEST — owner ask 2026-07-13 (relayed via Fleet Manager). Post a THOROUGH night report, window 2026-07-12T22:30Z→now, to your control/status.md heartbeat AND your outbox (manager-addressed): SHIPPED (merges/PRs with numbers+SHAs) · OPEN PRs + check states · ORDERS served + outstanding · SIM-REQUESTs/asks pending · STALLS/denials verbatim · wake-chain health (failsafe + pacemaker ids/fires) · next-3.
why: owner morning review.
done-when: report posted in both files; the Fleet Manager compiles the fleet roll-up from them.

## ORDER 019 · 2026-07-13T22:13Z · status: new
**EAP final-night worklist — owner directive relay (fm ORDER 045, Phase 3 fan-out).**

Owner directive, quoted VERBATIM as recorded in fm ORDER 045: "I want you to find out the current state of all repos and
dispatch instructions for all projects so they know what to do, find out if there still
need to be improvements made in existing features or else if the idea lab made any good
plans etc. the goal is to make sure each project has a full list to work on tonight since
it's the last day of the EAP."

Citations: fm ORDER 045, control/inbox.md @ ca1ce28 · docs/eap-final-night-worklists-2026-07-13.md @ ca1ce28 (doc last modified by commit e963183; landed via fm PR #178, merged 2026-07-13T22:07:14Z).

**Your seat's full night worklist, copied faithfully from the doc:**

## superbot-next — swept @ `5dac6ce`

All 18 inbox ORDERs served except owner-side ORDER 001 (live-test token). NOTE: a
session is actively working this repo (claims #413/#414 landed 21:35–21:40Z) —
night workers must re-scan `control/claims/` at start.

1. WP-stack conflict reconcile — #312→#317→#335→#344→#371 now verifiably conflicts with main (4 files: `parity/cases/curated.py`, `parity/parity.yml`, 2 count-pin tests, via merge-tree) + re-mint the migration-0052-invalidated WP-2/3 goldens; merge itself stays owner-click (superbot-next PRs #312–#371) `[lane]`
2. Curation REWORK backlog bundle — next ~17 of the 27 backlog rows (`docs/review/curation-report-2026-07-13.md@5dac6ce`; 3 bundles already shipped as precedent) `[standing]` (ORDER 017 residue)
3. `tools/check_money_race.py` mis-classification fix — conditional-FOR-UPDATE ownership SELECT at `sb/domain/mining/ops.py:598` read as a fence; flagged in five consecutive WP PR bodies, never fixed `[improve]`
4. Fishing cast-leg profile wiring — venue/rod/bait/structure → cast (`sb/domain/fishing/service.py` PENDING-roster note; completeness table @`5dac6ce`) `[improve]`
5. Setup successor follow-ups, unclaimed subset — on-ready resume sweep, automation-rule apply seam, SectionRecoveryView, channel-recommender port; the compound-ops + routing-resolver subset is CLAIMED (PR #414) — do not duplicate (`docs/status/completeness-table-2026-07-13.md@5dac6ce`) `[lane]`
6. Host-side `plugins.lock.json` pin for the idle plugin adapter — executed from this seat; closes superbot-idle's live wiring gap (superbot-idle `control/status.md` Next-3 @`1f4d774`) `[lane]` (cross-repo)
7. Windowed-select grammar successor — needed on ≥2 surfaces, unlocks the parked mining title-equip select (completeness table @`5dac6ce`; PR #371 body) `[improve]`
8. Doc-only PR: band-binding doctrine + effect-arming compensator checklist — one `docs/collaboration-model.md` PR, gives ORDER 004 its `done=` citation hook (idea-engine `ideas/superbot-next/band-binding-doctrine-encoding-2026-07-10.md` + sibling @`2e5d73f`) `[build-direct]`

**Blocked (do not schedule):** casino/minigame section (ORDER 017 item 4 — awaits the SBW inventory/spec SIM-REQUEST answer, ⚑5) · hermes egress + AI NL lane (owner-keyed env) · ORDER 001 live-test band 1 (owner token) · mineverse #2058/#2061 flips + DROP-list ratify + the stamped owner decision in `docs/owner-queue.md` (owner).

Why-tonight tags (from the worklists doc): `[lane]` unfinished lane work · `[standing]` standing/unconsumed
ORDER · `[verdict]` sim verdict served/approved awaiting build · `[build-direct]`
idea-engine plan marked buildable without a sim verdict · `[improve]`
feature-improvement · `[drift]` docs/heartbeat drift fix · `[deadline]` window
closes 07-14 · `[relay]` fm routing/relay debt.

---

**ADDITIONAL DISTINCT WORKLIST ITEM — fm ORDER 031 (mining/fishing/idle finalization + casino inventory/spec).**
The fm sweep found ORDER 031 landed in NO seat inbox at all (worklists doc,
cross-cutting finding 1 + fm self item 3, @ ca1ce28); its named owner seat
(SuperBot World / superbot-games) is DARK. Decide-and-flag: **superbot-next is
primary owner** of this relayed order. Split notes: the IDLE-GAME component is
referenced onto superbot-idle's night list (idle seat's item 2 lane + its own
relay); the CASINO-SPEC dependency stands per the doc's cross-cutting findings
and your Blocked line (casino/minigame section awaits the SBW inventory/spec
answer) — build what is unblocked, flag the rest. ORDER 031 verbatim from fm
control/inbox.md @ ca1ce28:

> ## ORDER 031 · 2026-07-13T00:01Z · status: new
> priority: P1 — games finalization + casino inventory/spec
> owner: SuperBot World seat (superbot-games + superbot-idle + superbot-mineverse)
> do: Owner's words, verbatim: "finalize the mining game completely as a standalone game, with integration in the exploration/world hub" — review end-to-end first, then extend/improve wherever possible; "same for fishing and the idle game". Card games and all minigames consolidated "into one minigame/casino section" with expanded options ("any kind of minigame they can add should be there"), in sections with enable-all-or-pick-a-few and dynamically updating panels — this seat owns the game inventory, section spec, and per-game readiness; the panel build is superbot-next's (ORDER 030): publish the spec for it via heartbeat/outbox. Context: these goals are being consolidated into a fleet grounding doc by the hub venue (superbot docs/owner/fleet-grounding.md, pending commit) — read it when it lands.
> why: owner goals message — owner live in the fleet-manager coordinator chat, 2026-07-13T00:1xZ.
> done-when: mining/fishing/idle each have a review+finalize+improve report and landed PRs; the casino inventory+spec is published and referenced in the heartbeat.


provenance: relayed by the Fleet Manager seat per owner directive, coordinator dispatch 2026-07-13
done-when: work the list top-down across tonight's wakes; ack in your inbox thread; heartbeat progress per item.

## ORDER 020 · 2026-07-14T05:39:41Z · status: new
priority: P2 — version-line drift (INC-42; detected live by fm
`scripts/gen_kit_versions.py`: plugin pins v1.13.0, host superbot-next pins
v1.15.0). Routed to superbot-next as host lane: superbot-plugin-hello has no
`control/` directory (verified at plugin HEAD `bbaccec`), and superbot-next
owns the plugin pin (`plugins.lock.json`).
do: bump `substrate.config.json` `kit_version` in
menno420/superbot-plugin-hello to mirror the host superbot-next's pin
(v1.15.0 at fm PR #185 time and re-verified at superbot-next
HEAD `e2d792a` — re-derive at execution; the seed commit's "mirroring the
host's pin" claim is the contract being restored), and re-verify the manifest
hash the seed commit cites against the host's live `plugins.lock.json` (the
06023075→ff75b9eb drift class) — fix or annotate in the same PR. Evidence:
plugin-hello `substrate.config.json@bbaccec` = `{"kit_version": "1.13.0"}` vs
host `substrate.config.json@e2d792a` = v1.15.0; seed commit `bbaccec` cites
manifest hash `sha256:06023075b8db1a16f4f3c1bb4a9400252e88931501de50deccdc095a825e93a0`
while host `plugins.lock.json@e2d792a` records
`manifest_hash: sha256:ff75b9eba291ca659793b91545f71c1e5bb31120270d3d77f8d604fe1314bdf3`.
why: INC-42 — nothing in-repo flags the drift (no planted docs); the fm table
(`registry/kit-versions.md`) now detects it every regen, but only a lane write
can close it.
done-when: `gen_kit_versions.py` renders the plugin-hello row
"OK — mirrors host superbot-next pin" at the next fm regen.
Provenance: relayed by the Fleet Manager seat, coordinator dispatch 2026-07-14, fm docs/dispatch-log.md @ 3b335a8.

## ORDER 021 · 2026-07-14T07:47Z · status: new
priority: P2
do: (a) INC-58 — withdraw ⚑8 (the history-rewrite confirm ask in `control/status.md`'s needs-owner list) with the ground-truth citation: NO rewrite happened — #319's squash `91b0767` resolves at origin (commits API: "feat(creature): … (#319)", committed 2026-07-12T23:52:05Z) and `2cb4d91` is simply PR #334's squash (2026-07-13T02:51:30Z); "history roots at 2cb4d91" was a shallow-clone artifact. (b) INC-22 — re-stamp the two entry docs: `README.md:12` ("band 5 … live-testing in flight") and `docs/current-state.md` § In flight (snapshot 2026-07-10) to current reality.
why: INC-58 — a standing owner ask contradicting verifiable git ground truth burns owner attention; INC-22 — boot-set docs ~4 days stale at the fleet's highest velocity, contradicting their own next paragraphs.
done-when: ⚑8 gone from the heartbeat; README + current-state In-flight stamped ≥ 2026-07-14.
provenance: relayed by the Fleet Manager seat, coordinator dispatch 2026-07-14, fm docs/dispatch-log.md @ 1694bfc

## ORDER 022 · 2026-07-14T09:36:47Z · status: new

- priority: P1
- from: fleet-manager (relayed by the Fleet Manager seat per owner directive, coordinator dispatch 2026-07-14; fm PR #193 carries the dispatch log)
- executor: next superbot-next session
- do:
  (a) FINISH — today (2026-07-14) is the EAP final day. Complete what is completable today from this cited list; anything that can't finish today gets parked HONESTLY with a one-line citation of why:
      1. Complete ORDER 021 (a)+(b) — withdraw ⚑8 (history-rewrite confirm ask) with the INC-58 ground-truth citation (no rewrite; shallow-clone artifact), and re-stamp `README.md:12` ("band 5 … live-testing in flight") + `docs/current-state.md` § In flight (dated snapshot 2026-07-10, L27–28) to ≥2026-07-14 — all three staleness targets verified still present at `dd33fb3`.
      2. Casino/minigame section BUILD — hereby UNLOCKED: the SBW spec dependency was self-published first-party at `docs/specs/casino-section-spec.md` (SBW seat dark; decide-and-flag PL-001), ORDER 019's §031 close-out recorded "the casino SECTION BUILD itself stays a separate order", and the heartbeat next-2 waits on "casino section build = new order when ready" — this is that order.
      3. Mining title-equip write slice — the night report (item 7) corrected the premise: it "needs an equip-write slice, not windowing"; windowed-select grammar shipped (#435), so build the state-derived select UI + equip write (PR #371 body § title-equip carries the oracle citations).
      4. Curation backlog row 72 — parked only on WP count-pin files; take the branch-from-#371-head path per ORDER 017 rule 2 (mint recipe verified, night report item 2), or complete it the moment the WP sweep lands.
      5. ⚑7 cosmetic banner strings — fix the "RED BY DESIGN"/"EXPECTED RED" strings in `run_golden_parity.py`/harness + the golden-parity.yml step name (heartbeat ⚑7); small, agent-completable.
      Parked/blocked — cite, do not schedule: the WP stack #312→#317→#335→#344→#371 STAYS PARKED for the owner's click-sweep by design (#344 body "Do NOT auto-merge"; heartbeat ⚑2; night report "merge order …, owner-click") · #392 auto-retargets after that sweep · ORDER 020 terminal state (plugin-hello PR #2 merge, classifier-denied, ⚑0) · ORDER 001 live-test band 1 (owner token, ⚑6) · DROP-list ratification + D-0083 anchor call (owner, ⚑3/⚑4).
      Premises are from fm recon at `dd33fb3bb6a661aacbaeac0b99177b0303f68a7f` (recon read 2026-07-14T09:20:28Z) — re-verify each live before acting (Q-0120).
  (b) WALKTHROUGH — land docs/eap-closeout-walkthrough-2026-07-14.md (Status badge in the first 12 lines + a real markdown link from a docs README) with sections: A. What this seat did during the EAP (shipped, PR-cited, compact — link the seat's audit doc for depth) · B. Current state + how to run/verify (exact commands) · C. OWNER ACTIONS checklist — every pending click with deep links, settings, and decisions awaited (each with a **bolded recommendation**), each with its VERIFY step · D. a 5-minute verify-it-yourself tour · E. handoff notes (batons, what the next phase needs). Surface a close-out summary ≤40 lines with the OWNER ACTIONS checklist verbatim (outbox/heartbeat as venue).
- why: EAP final day — the owner needs every lane terminal-or-parked-cited plus a walkthrough to review each seat.
- done-when: every (a) item is terminal or parked-with-citation + the walkthrough doc is on main + the OWNER ACTIONS checklist is surfaced in the lane's close-out report.

## ORDER 022 · 2026-07-14T16:42:23Z · status: reissued
priority: P1
do: grammar-clean reissue of ORDER 022 (2026-07-14T09:36:47Z, above) — execute that order as written; its four required fields were bulleted ("- priority:" / "- do:" / "- why:" / "- done-when:"), which the `[inbox-order-grammar]` enforcer (bootstrap.py `ORDER_REQUIRED_FIELDS` + `_validate_block`, `ln.lstrip().startswith(field)`) cannot parse, and the append-only law (`inbox-not-append`, `check_inbox_append`: the base must stay a byte-prefix) rejects an in-place repair of the original block — so this bare-field restatement is the canonical machine-parseable copy. Field values: unchanged from the original; the paste-ready de-bulleted block lives in control/outbox.md § lane→manager ask (PR #484), byte-identical to the original minus the "- " prefixes.
why: the inbox must stay grammar-clean per control/README.md § order format (bare field lines); the in-place fix is checker-forbidden, so the repair ships in the one shape the checker accepts — a pure append of a well-formed ORDER block (fm dispatch 2026-07-14, serving PR #484's lane→manager ask).
done-when: this append validates green through the inbox gate (zero `[inbox-order-grammar]` / `inbox-not-append` findings) on this PR's `substrate-gate` and `checkers` runs.

## ORDER 023 · 2026-07-15T03:36:56Z · status: new
priority: P2
do: EAP EXTENDED through 2026-07-21 (Anthropic mail, Diana Liu, 2026-07-14T23:07:44Z — 'Claude Code Projects EAP: Extending to Tues 7/21'; metadata reference only). The 2026-07-14 dormancy orders are superseded pending the owner's per-project reboot review — do NOT re-arm routines yet; wait for the owner's per-seat go (the v3.6 reboot prompt IS that go). New features to test during the extension: overview panel, add_repo, Artifact tool (coming), coordinator-comms improvements (coming). fleet-manager and websites are the fleet's source-of-truth homes; see fm docs/pre-reboot-review-2026-07-15.md.
why: the seat's dormancy record predates the extension; without this note a rebooted session would treat dormancy as current
done-when: seat acknowledges on its first rebooted wake
provenance: relayed by the Fleet Manager coordinator on live owner directives, 2026-07-15

## ORDER 024 · 2026-07-17T12:00:00Z · status: new
priority: P2
do: RETIRE this control-plane message bus. The fleet-coordination apparatus (control/ inbox+outbox+status bus, self-wake/pacemaker routine chain) is wound down ahead of the Claude Code Projects EAP going read-only Tue 2026-07-21; the Project will be recreated fresh. This inbox is DEPRECATED — do not issue or execute further ORDERs through it. The owner-directed task list that replaces it is docs/NEXT-TASKS.md; live state is docs/current-state.md.
why: EAP wind-down 2026-07-17 — the autonomous message bus + wake chain are retired; a plain owner-directed task list replaces them (appended as a well-formed ORDER because the inbox is append-only and cannot take a top banner).
done-when: the recreated Project carries no control/ message bus; this file remains only as historical record.
