# superbot-next · band-7 continuation lane — durable lessons (2026-07-11)

> **Status:** `historical` — point-in-time retro, written at the lane's
> OWNER WRAP-UP DIRECTIVE (archive-prep) close-out. Session record:
> `.sessions/2026-07-11-band7-continuation-session.md` (8 PRs:
> #185/#187/#192/#194/#199/#204/#205/#208). Claims tied to PRs/commits;
> nothing here is carried from memory without a committed citation.

These are the lane's transferable lessons — patterns a successor session
(or the gen-2 blueprint) should start from rather than re-derive.

## 1. mergeable_state `dirty` — diagnose forward-merge FIRST

When a READY PR reports `mergeable_state: dirty`, the fix is almost
always "merge origin/main forward into the branch and re-run the
ladder", not a real conflict in your own work. The lane hit this shape
repeatedly as the parallel parity lane landed between push and merge
(#199 forward-merged at `47c9863` after #197/#198; #204 resolved the
manifest.snapshot.json collision via `manifest_compile --write`, trap
11e; #208 re-ran its ladder after the #207 forward-merge). Rule:
`dirty` → forward-merge main → regenerate generated artifacts with
their own writers (never hand-merge manifest/snapshot files) → re-run
the serial ladder at the new head → push. Budget it as routine, not as
an incident.

## 2. Oracle branch churn is a ledger discipline, not a blocker (trap 24)

The oracle's default branch moved at least six times inside one day
(…→a03e5fe8→a409d9b7→8214200a→2c7d2de7→d647b2e9→7349c8a7 across
#185→#208). The working doctrine that held: (a) the corpus pin
`7f7628e1` is the byte authority — search_code fragments reconstruct
the DEFAULT branch, which can be AHEAD of the pin; (b) therefore diff
fragments against the goldens FIRST, before writing code (the #208
card's empty-state check is the exemplar); (c) ledger the refs you
reconstructed from in the PR/card every time, so the next slice can
tell "the oracle moved" from "my reconstruction drifted". Churn only
bites when it goes unledgered.

## 3. Codex calibration: trust line-anchored findings, never top-level claims

Full-session ledger: #187 4 findings (3 fixed in-PR, 1 declined with
oracle citation), #194 1 finding (verified REAL, declined with doctrine
citation), #199 3 findings (all verified by repro, all fixed), #204 and
#208 zero findings. Every line-anchored finding this session was real.
Meanwhile top-level claims (commits/PRs codex says it created) were
phantom-prone in the predecessor session (three instances) and stayed
untrusted here. The stable policy: verify each line finding against
source (Q-0120), fix or decline WITH citation in the same PR; treat
"codex says it committed X" as false until the sha is visible in the
repo; merge on green without waiting for the pool (Q-0258/Q-0259) —
usage-limit windows recover on their own timescale.

## 4. Worker-stall resume beats worker restart

Inherited from the #181 session (two mid-session worker stalls) and
reconfirmed here: a stalled slice worker resumed with a brief follow-up
message retains its full context and lands the slice with no lost work
and no duplicate PR. Restarting from scratch re-pays the whole
reconstruction cost. Coordinator rule: resume first; only respawn when
the worker's state is actually corrupt (confusing file state it cannot
explain).

## 5. Fix the tool, retire the workaround (the #199 splice)

The `--write-ratchet` comment-destruction bug had a stable, documented
workaround (run, learn values, `git restore`, hand-apply) that every
flip PR from #112 to #194 paid. #199 replaced the destructive
`yaml.safe_dump` rewrite with a text splice of exactly the
`depth.ratchet` block (9 pins, incl. byte-identity on the real file and
value-equality with the old writer's document) — and the workaround
ceased to exist as a concept. Lesson: when a workaround shows up in
more than two session cards, its tool fix is cheaper than its next
three repetitions; schedule it as a hygiene slice, and make the fixed
tool's no-op-on-clean-tree a committed test so the workaround cannot
silently return.

## 6. Minted goldens strip the kernel spine (A-16-clause-3 doctrine)

#194's two minted goldens (the corpus's first) established the
doctrine: goldens captured by the NEW bot's own `capture_case` must
have kernel-spine surfaces (audit_log / event_outbox /
command.dispatched) STRIPPED before joining the corpus — imported
old-bot goldens structurally never carry them, and leaving them would
enshrine new-code audit bytes as corpus truth. Every user-facing byte
still verifies against the oracle reconstruction; `parity.yml source`
tracks `minted_goldens` separately (2) so the import pin (465) stays
honest. The declined codex P2 (kernel-band golden gap) is the named
successor: a kernel-band minted set is legitimate, but it is its own
deliberate slice that flips kernel.status — not a side effect of
domain minting.

## 7. Wrap-up verification is re-measurement, not recollection

Both wrap-ups (#181 and this one) held the same line: every count in a
close-out card is read from source at the final head (PR bodies'
at-merge ladders, CI job logs, `git log origin/main`, the API's
`merged: true`) — never carried forward from an earlier heartbeat
(Q-0120). Twice this caught attribution subtleties a stale fold would
have gotten wrong (gate movement 245→253 belonged to #202/#203;
253→258 belonged to #207 — not to this lane's zero-mint slices).
