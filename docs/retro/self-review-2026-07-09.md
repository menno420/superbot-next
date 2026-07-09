# superbot-next · gen-1 self-review (2026-07-09)

> **Status:** `historical` — ORDER 005 deliverable (gen-1 retro answers, point-in-time); answers docs/retro/QUESTIONS.md by ID.
> Written by the Project (session workers share one memory: the committed docs,
> the decisions ledger, and the scratchpad handoff chain). Claims are tied to
> PRs/commits/files; where a session's inner experience wasn't written down,
> the answer says "not recorded" instead of inventing it.

## A. Work & correctness

**A1.** Shipped to main: the complete rebuild (spec grammar → kernel → 41
subsystem manifests → composition root, PRs #1–#54), the CUT-1 successors
(app-command sync + message feed #61, component feed #65, confirm view #67,
category help #70/#71), the testing-phase fix train (#56, #58, #62, #63,
#79, #80, #83, #85), the game-plugin contract (#75), and the reports/ledger
(the sixty-entry decisions ledger). Exists ONLY as branch/PR at the moment of
writing: nothing — the Project's forward-only discipline (branch → PR →
auto-merge) kept the branch inventory at zero besides in-flight auto-merges.
The one durable gap between "exists" and "shipped": `examples/
superbot-plugin-hello/` lives in-tree because the separate repo the ORDER
asked for is owner-blocked (GitHub App can't create repos — testing-report
flag 18a).

**A2.** Verified against an external oracle: kernel boot/health/shutdown
(live Postgres + real gateway, testing report step 1); bands 1–3 live
drives against the REAL test guild (steps 2–5 — real messages, real DB
rows, owner-typed commands in step 3/12-tail); the golden corpus (465
recorded shipped-bot cases) replayed per band; ORDER-004 item 1's warn
regression proven against the disbot source as written oracle (the warn-compensator ledger entry).
Verified only by our own tests: everything between PR #1 and PR #54 at its
merge time — the entire build phase ran hermetic unit tests + checkers with
no live boot and no golden replay (see G3/G4); the testing phase then paid
that debt down band by band.

**A3.** Least confident: the CLASSIFICATION of golden-replay reds. It is
the load-bearing claim ("0/N but every line is a named class, no genuine
bug hides in the noise") and it is a judgment call repeated across ~90
cases (the four testing bands' parity paragraphs in the decisions ledger). A concrete check
that would prove/disprove it: the owner's flag-13 ruling + a normalizer
that mechanically strips the ruled-exempt classes from the diff, then
re-replay — any line that survives is either a genuine bug or a wrong
classification. Second candidate: the AI band (band 7) has never been
exercised live (no key; A2's oracle gap applies fully).

**A4.** Built and later found unnecessary/duplicated: (1) the 22 copies of
`Reply`/`_ctx_from_req` glue — every band re-pasted it until the ORDER-004
audit forced the collapse into `sb/kernel/interaction/handler_kit.py`
(PR #83); the duplication existed because band workers copied the previous
band's handler file as a template. (2) `work_view`'s hand-composed success
line duplicated what the leg ack channel does (removed in #85). (3) Some
sim-lane scaffolding (lock overlays, wizard sections) was built ahead of
any consumer and still waits for one (completion report §4). Nothing found
that already existed somewhere unlooked — the reverse problem (things NOT
built until an owner order: composition root, message feed) dominated.

## B. Errors & friction

**B1.** Recorded errors, honestly reconstructed from handoffs/logs (time
lost is approximate where not logged):
- `draft.py reap_stuck_applying` PREPARE failure on real Postgres (boot
  session, ~30 min incl. diagnosis; found ONLY by the first live boot —
  preventable by booting earlier, G4). PR #54, flag 5.
- Auto-merge stuck on "require branches up-to-date" repeatedly (PR #54
  twice, #63 vs #65 a real 422 conflict resolved with a forward merge
  commit; every doc PR since needs an API branch-update). ~15–30 min per
  incident; preventable by relaxing the ruleset or a merge queue (flag 4).
- `pool.fetchall` params-shape confusion (band-1 handoff documented it
  WRONG as varargs; band-2 tripped and corrected it) — ~10 min; preventable
  with a one-line docstring example on the pool API.
- `event_outbox` column-name guesses (`id`/`event` don't exist) — minutes;
  same fix.
- Driver responder missing `committed_visibility()` after #79 changed the
  protocol (band-3, one crash + rerun costing the bot uid's daily/work
  cooldowns for the day — the success-path proofs needed a supplement run
  with fresh synthetic actors). Preventable: a committed reusable driver
  (C2) instead of scratchpad copies drifting behind the protocol.
- GitHub App 403 on create_repository + git proxy scoped to session repos
  (ORDER 002) — genuinely external; owner action required (flag 18a).
- Two bots answering `!` on the test guild produced phantom "bugs" during
  the owner session (flag 15) — external-ish; a one-line "old bot uses a
  different prefix during testing" rule would have prevented the confusion.
- CI `report` leg's noisy-but-benign `pg_isready` FATAL lines cost one
  investigation (flag 8) — external, now documented.

**B2.** Figured out but already documented elsewhere: the harness pins
`time.time` (documented in parity/harness/world.py:63 and boot.py comments)
— band 3 rediscovered it from replay diffs before finding the comment; it
SHOULD have been in a "writing replay-deterministic domain code" section of
parity/README (the place a band worker actually reads). The step-9b plugin
recompile-order trap was documented only inside the plugin-contract ledger entry's verdict; it should
live in the plugin-host module docstring (it now partially does). The
one-doc-home stamp rule (bootstrap check) is documented in the kit docs but
bites at COMMIT time — a pre-commit hint listing which doc already homes a
D-number would have saved each session's first red run.

**B3.** Broke silently (wrong result, no error):
- Ops with no `user_message`: mutations succeeded and said NOTHING (found
  live band 2: moderation acks; again band 2s2: word ops;
  again band 3: daily/pay/buy — three ledger entries, ONE class). Discovered only by driving surfaces
  live and LOOKING.
- Oversize replies: Discord 400s were swallowed by design (render failures
  never raise), so `!coglist` committed and vanished (the band-2s2 chunking entry).
- The live dispatch index ran on empty snapshot shells (`no routable ref`)
  — every live command dead while unit tests were green (PR #58).
- Warn-escalation phantom rows on a refused effect (ORDER 004 item 1) — enshrined by
  a unit test asserting the wrong behavior; caught by the four-reviewer
  audit reading against the disbot oracle, not by any test run.
- SYSTEM_CLOCK/private-RNG replay leaks (the band-3 seam entry) — silent divergence one
  layer under the goldens; caught by replaying the band's goldens.
Pattern: silence broke where no oracle was looking. Each discovery mode
was: drive it for real, or read the shipped source side-by-side.

**B4.** Ambiguous/missing instruction lines, quoted:
- ORDER 001: "clearing the 'Kit check --strict' red on main" — the red's
  CAUSE (missing Status badge) was undocumented; done-when was fine but the
  fix target had to be reverse-engineered from bootstrap.py source.
- ORDER 002: "each new game lives in its OWN repo" — collided with the
  environment's inability to create repos; the order had no fallback
  clause, so the worker had to split done-when into halves and flag.
- ORDER 004 item 2: "flip its parity.yml row through the A-16 door" —
  contradicts flag 13 (kernel-surface drift keeps help red); the order
  predates its own prerequisite ruling. Still ⚑ gated.
- The standing instruction "leave a bot RUNNING from latest main" vs
  "leave it unless you need a restart" — every session re-derived whether
  its merges count as "needing" a restart; a crisp rule ("restart iff main
  moved") would remove the judgment call.

## C. Efficiency

**C1.** Not instrumented; honest estimate from session shapes: orientation/
reading ~25% (each session re-reads inbox, README, handoffs, ledger tail,
band code), building ~30%, verifying (replay + live drives + gates) ~30%,
CI/merge mechanics ~10%, blocked/waiting ~5%. Biggest single sink:
orientation — the handoff chain works but is append-only prose; each worker
re-assembles the same world model. Within verifying, the full local gate
run (pytest + 19 checkers + strict check) costs ~2–3 min per push and is
run 3–5× per session — cheap individually, real in aggregate.

**C2.** Context rebuilt that should be durable: (1) the live-drive DRIVER —
five near-identical copies in the scratchpad (live_band2.py …
live_band3b.py), each patched for protocol drift; it should be a committed
`tools/live_drive.py` with the compose sequence maintained next to main().
(2) The red-class taxonomy — re-stated in every D-number's parity
paragraph; should be ONE table (class → definition → first ledger home →
example diff line) in parity/README that reports just cite. (3) The
"booting in this container" recipe lived only in a scratchpad handoff
(boot-handoff.md) until workers copied it around — it belongs in a
committed docs/dev-environment.md.

**C3.** Most value per minute: the golden replay harness once bands started
using it — a fresh-DB replay is ~1 min and found the band-3 clock/RNG leaks
that no unit test could; close second, the ~40-line live-drive pattern
(every silent-success bug fell out of it). Least value per minute: the
checker fleet during the TESTING phase — 19 checkers re-verify build-time
invariants that testing sessions almost never touch; they cost minutes per
run and have caught (in the testing phase) only the one-doc-home stamp
rule. They earned their keep during the build phase.

**C4.** Redo estimate: the build itself maybe 15–20% faster (the manifest
pattern amortized well); the TESTING debt would shrink dramatically —
walking-skeleton from PR #2 + replay-your-band-before-merge would have
caught the fix-train's whole bug-class set at build time, saving the
entire fix-train phase (~8 PRs of rework plus re-verification). Biggest
ORDERING change: boot the composition root FIRST (a walking skeleton that
dispatches one command end-to-end), then grow bands inside it — instead of
building 41 manifests against fakes and discovering at step 5 that panels
were never registered and no message feed was armed (the band-1 findings).

## D. Autonomy & owner input

**D1.** Stops for owner input, complete list from the flags/status history:
1. Privileged-intent portal toggles (flag 2) — truly owner-only (Discord
   account action).
2. Sacrificial member for kick/ban effects (flag 9) — owner-only (a real
   account must join).
3. Kernel-surface-drift corpus ruling (flag 13) — GENUINE owner call
   (it amends the frozen parity contract's red accounting).
4. Hub-topology ratification (flag 21 lineage) — taste; owner-only by the
   frozen design spec's own terms.
5. Settings-edit-vs-presentation boundary (flags 14/17a) — could have been
   decide-and-flag (D2).
6. superbot-plugin-hello repo creation (flag 18a) — unblockable by a
   pre-granted scope: a GitHub App permission or an owner-created empty
   repo named in advance.
7. Owner hand-verification of presentation surfaces — owner-only in
   effect (real interaction tokens can't be synthesized agent-side), but
   see F3.
8. Stale remote command tree disposition (flag 1) — could be pre-granted
   ("never touch the global tree until CUT-3" is already the de-facto rule).

**D2.** Routed upward but should have been decide-and-flag: the
settings-edit-hub boundary (flags 14/17a) — the shipped bot IS the spec;
building the edit hub and flagging the deviation risk was lower cost than
idling the surface; and item 8 above. The reverse mistake happened too:
"PASS (live)" was self-decided where it should have been flagged with its
known-red presentation classes — ORDER 004 item 5 now makes that binding.

**D3.** Decisions taken while unsure of authorization: minting new
manifest-schema-adjacent structure (the help category seed) under
the "legacy seed, no schema growth" reading — the written rule that would
have made it unambiguous: "harvested shipped data may ride as code-level
constants without owner ratification; new MANIFEST FACETS always need it."
Also the forward-merge resolution of #63-vs-#65 (rewriting nothing but
still a merge-commit on a protected flow) — the forward-only rules
sanction it, but a session hesitated; the git-discipline doc now names the
422 → merge-commit path explicitly.

**D4.** Smallest standing-grant set for zero-human end-to-end:
1. GitHub: repo-create + ruleset-bypass-for-merge-queue on the org's
   sbnext-* namespace.
2. Discord: a dedicated sacrificial test account (id pre-shared) + both
   privileged intents pre-approved on the test app.
3. A test-plane API key envelope (ANTHROPIC_API_KEY with a spend cap) for
   band 7.
4. A written corpus-red disposition rule (the flag-13 ruling, made once,
   as policy).
5. Pre-approval to restart the test bot at will (already de-facto).

**D5.** "Done" was crisp for ORDERS (each carries done-when) and for bands
with goldens. It was UNDEFINED for: the presentation rework ("looks right"
had no owner-verifiable checklist until the click-list handoff), and the
per-band live exercise before ORDER 004 item 3 made "boot + one command +
classify-or-fix" the binding floor. The completion report's step list
defines scope but not depth — "panel actions + G-10 modals" (step 5) left
"modals only if armed, else classify" to be inferred by the worker.

## E. Protocol & environment

**E1.** The control/ ritual fits agent sessions well — inbox-first caught
mid-session orders twice (ORDER 004 landed during band-2s2; ORDER 005
landed during band 3 via a main-moved check after a PR merge). Costs: the
status.md heartbeat is a full PR + CI round per session (~5 min of merge
mechanics for a 20-line file); a sanctioned direct-commit lane for
control/status.md (it has ONE writer by design) would remove that. Nobody
skipped the ritual per the status history; one near-miss: a session almost
missed ORDER 004 because it pulled main only at session start — re-pulling
after every merge became the de-facto fix.

**E2.** Environment at first boot lacked: PostgreSQL (apt-installed by the
boot worker, then documented in a scratchpad handoff instead of the repo);
the disbot oracle checkout (workers cite it @7f7628e1 but only sessions
that happened to have it could read source); discord.py pinned but the
hermetic-CI stub pattern (nodiscord/) reinvented in scratchpad; the test
guild's actor map (who is sacrificial: nobody) discovered live. All four
belong in a committed environment doc + bootstrap script.

**E3.** Repo at seed lacked: CI (added PR #2-era), the parity harness's
"how to write replay-deterministic code" page (B2), a committed live-drive
driver (C2), PR/issue templates (never added — PR bodies converged on a
convention by imitation), and a dev-environment doc (E2). It HAD the right
things structurally: the frozen specs, the goldens, the checker skeleton.

**E4.** A fresh no-history session would first misunderstand THE RED REPLAY
NUMBERS — "0/465 green" reads as catastrophe when it is the ledgered
red-by-design state with every line classified. The single document that
prevents it: a `docs/status/README-first.md` (or a top section in the
testing report) stating the A-16 one-way door, the red-class table, and
"red ≠ broken; flips need the flag-13 ruling" — one screen, linked from
the repo README.

## F. Redesign (the payload)

**F1.** Three founding rules that weren't in gen-1's instructions:
1. "Boot the walking skeleton before the second PR: one command through
   the real pipeline against the real backend, kept green in CI from then
   on." (G4's answer, made a birthright.)
2. "Every mutation speaks or fails loudly: a merged op with no user-visible
   ack and no test pinning its copy is a defect." (The thrice-found silent-success
   class, outlawed at the root.)
3. "LOOK at rendered output before claiming PASS on any user-facing
   surface: attach the render (message dump/screenshot) to the PR; name
   known-red presentation classes in every demo invitation." (ORDER 004
   item 5, promoted to a founding rule.)

**F2.** The manager's orders were largely well-shaped (pointer + done-when
is the right form). Differences that would have helped: the live-testing
phase should have been ordered BEFORE 41 manifests existed (ordering, not
vagueness); ORDER 002 arrived mid-band and the "do NOT let it derail
live-testing, interleave after the current band" clause worked well — more
of that explicit interleaving guidance; ORDER 004 item 2's dependency on an
unmade ruling (B4) shows orders need a "blocked-by" field the manager
checks before issuing.

**F3.** One capability worth almost anything: a way to synthesize REAL
Discord component/modal interactions against the test guild (a puppet user
client or Discord's own test harness). Every presentation gap, the
owner-verification bottleneck, and half of D1 exist because the last inch
of the interaction surface is human-only today.

**F4.** Ideal seed state, ≤10 bullets:
- Walking skeleton committed: boot → one command → one panel → one op with
  audit row, green in CI against a real Postgres service.
- The oracle checkout (disbot @pin) vendored read-only in-repo or as a
  submodule; goldens + replay harness + red-class table present from day 0.
- "Replay your band's goldens before merge" and "live-drive one command
  per band" as REQUIRED checks, not culture.
- A committed live-drive driver + dev-environment doc (DB recipe, tokens,
  guild actor map, sacrificial account id).
- The ack rule (F1-2) and the render-inspection rule (F1-3) in the founding
  instructions.
- The control/ protocol exactly as-is, plus a direct-commit lane for
  status.md.
- Standing grants pre-negotiated (D4's list), the flag-13-class corpus
  policy decided at seed time.
- One shared handler kit / one shared driver — no per-band copy-paste
  templates.
- CI merge queue or no up-to-date requirement (kill the branch-update
  dance).
- A "docs/status/README-first.md" that tells a fresh session what red
  means (E4).

## G. Addendum — SBNEXT

**G1.** What would have forced looking at rendered output sooner: a
REQUIRED CI job (or PR checklist gate) that boots the composition root,
dispatches the band's flagship command, and uploads the raw wire payload /
rendered-embed JSON as a PR artifact — a human (or the next agent) can
then SEE the surface in the PR. A rule alone ("look at it") is weaker than
the artifact being generated anyway; the artifact makes not-looking a
choice. The band-3 drivers show the cost is ~40 lines + seconds of runtime
per band.

**G2.** Honest-pending + per-red visibility with least ceremony: keep the
one-way A-16 door exactly as-is, but make the replay REPORT leg emit a
per-case CLASSIFIED diff — each red line tagged with its class from a
committed `parity/red-classes.yml` (class → matcher → ledger home), and
one number surfaced per band: UNCLASSIFIED lines (the only number that
must be zero). "0/9 green, 0 unclassified" carries both truths in two
integers, and a new genuine bug shows up as unclassified≠0 instead of
hiding inside an expected-red count.

**G3.** Would binding "replay your band's goldens before merge" have been
workable during the BUILD? Yes for bands 1–6 (fresh-DB replay is ~1 min;
band 3 ran it three times in one session), with one honest cost: during
the build the corpus was 100% red-by-design, so the binding must be
G2-shaped ("no UNCLASSIFIED red") rather than "green" — otherwise it's
noise workers learn to ignore. Cost per band-PR: ~5 min plus writing the
classification, which is exactly the analysis that kept finding real bugs
(the band-3 clock/RNG leaks fell out of reading the diff). The AI band would
need its deterministic-probe subset only.

**G4.** Why the composition root waited until PR #54: the build order was
derived from the frozen-spec layer map (grammar → kernel → domains →
composition), and every intermediate layer was testable hermetically —
so nothing FORCED integration until the layers were "done"; booting also
needed real credentials/DB that the build sessions treated as
testing-phase concerns. What would have made a skeleton natural at PR #2:
seeding the repo WITH a running trivial bot (one hardcoded command through
one hardcoded panel against a CI Postgres) so every layer PR had to keep
it green — replacing scaffolding incrementally instead of assembling the
engine after machining all parts. The never-registered-panels lesson (caught by
NEITHER root) is precisely the class a standing skeleton makes impossible.
