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
