# Flag-13 corpus-red disposition (ORDER 009 / Q-0262.3) — 2026-07-10

> **Status:** `binding` (owner delegation Q-0262.3 → ORDER 009: the proposed
> disposition is ACCEPTED "exactly as proposed"; reversible-on-paper, Q-0240
> class, reviewable at the parity gate.)

## The three ruled classes and their encodings

The proposal (docs/retro/project-review-2026-07-09.md §2 item 1,
docs/status/testing-report-2026-07-09.md item 13, control/status.md
OWNER-ACTION 1) offered per class: exemption rows / normalizer scope /
accepted-forever red. The least-destructive encoding was chosen per class:

1. **Kernel event+audit shapes** (audit_log / event_outbox / idempotency
   rows + `command.dispatched` / `audit.action_recorded` event shapes on
   every mutation golden) — **normalizer scope.** Kernel-owned tables and
   events (exactly the `kernel:` coverage-home lists in `parity/parity.yml`)
   are dropped from BOTH the golden and the fresh capture before diffing.
   Their coverage obligation stays real: it lives in the parity.yml `kernel`
   section (A-16 clause 3), not in every band's goldens.
2. **The old `xp.coins` alias column** (coins split to `economy_balances`
   at the ledgered coins boundary) — **normalizer scope.** The `coins` key
   is dropped from `xp`-table rows in both docs. The economy_balances rows
   themselves still diff (they are real domain surfaces).
3. **The shipped invoking-message deletion** (the old bot deleted the
   invoking message after every command — a reason-less trailing
   `delete_message` wire call on virtually every golden; v1 deliberately
   does not delete user messages) — **documented exemption.** Reason-LESS
   `delete_message` calls are exempt from the replay diff in both docs;
   reasoned deletes (real moderation/cleanup behavior) still diff.

## Mechanism

- Rows: `parity/parity.yml` → `dispositions:` section (data, reviewable).
- Mechanism: `sb/adapters/parity/dispositions.py`, applied in
  `sb/adapters/parity/runner.py::replay_case` to BOTH documents,
  symmetrically — every non-disposed byte still diffs, and a later behavior
  change on either side of a disposed surface cannot smuggle through
  (both docs get the same treatment).
- The goldens are NEVER rewritten (parity/README.md integrity rule) and the
  imported harness (`parity/harness/`) stays verbatim.
- Pinned by tests/unit/parity_adapter/test_dispositions.py.

## Why symmetric-drop, not expected-side-only

An expected-side-only strip would flag a future v1 invoking-message
deletion as "unexpected (new behavior)" — useful, but it would also make
the disposition an asymmetric special case in an otherwise symmetric diff.
The ruled classes are "accepted differences", not "old-side noise": the
symmetric drop encodes exactly that and keeps the mechanism one honest
sentence long.

## Provenance

ORDER 009 (control/inbox.md 2026-07-10T15:33Z), owner delegation Q-0262.3;
flag 13 first named by the band-2 testing pass and inherited by every later
band (docs/status/testing-report-2026-07-09.md item 13); OWNER-ACTION 1
cleared from control/status.md by the follow-up heartbeat PR of the
2026-07-10 band-5 compensator-fixes session.
