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
