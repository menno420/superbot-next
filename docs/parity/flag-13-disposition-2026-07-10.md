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
   is dropped from `xp`-table rows in both docs. ~~The economy_balances
   rows themselves still diff (they are real domain surfaces).~~ *Superseded
   by the encoding completion below: the new home is dropped from both docs
   too; balance behavior stays pinned through the ledger bytes.*
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

## Ref renumbering (the drops' id-noise completion — help flip PR)

The capture Normalizer numbers run-minted ids by FIRST APPEARANCE
(`<msg:1>`, `<msg:2>`, …), so a ruled drop that consumed a ref shifts every
later number: the reason-less invoking delete minted `<msg:1>` on virtually
every shipped command golden, and the kernel `ai_decision_audit` row
consumed one more — leaving every surviving ref (e.g. the `panel_anchors`
row's `message_id`) permanently off-by-N against a fresh capture that never
allocates those refs. `apply_dispositions` therefore finishes with a
symmetric canonical renumbering of `<msg:N>` refs (first appearance in the
DISPOSED document, deterministic sorted-key traversal, per-document
bijection). This accepts NO new byte differences beyond the three ruled
classes — it stops the ruled drops from leaking id-noise, exactly the
Normalizer's own "one extra embed must not cascade id-noise" rule. Pinned
by `test_minted_refs_renumber_after_drops`.

## Encoding completion (2026-07-10, blackjack flip PR) — ⚑ owner-reviewable

The first MONEY-mutating gating golden (`goldens/blackjack/
blackjack_solo_round_hit.json`, whose `!daily` step funds the bet) exposed
two places where the first encoding under-implemented the accepted classes.
Both completions were made under the same Q-0262.3 delegation the original
encodings were chosen under ("the least-destructive encoding was chosen per
class" — session-chosen, owner-delegated), are data-only (`parity/
parity.yml`), reversible on paper (Q-0240), and pinned by new tests:

1. **Class 1, column form** — the kernel idempotency stamp
   (`economy_audit_log.mutation_id`) leaks the kernel spine INTO a domain
   ledger row. The accepted classifications (band-3/4 testing-report red
   decompositions, which the ruled proposal points at as "already
   classified") explicitly list "`mutation_id` rows" under kernel-surface
   drift; the table-list encoding missed the column form. New
   `kernel-surface-drift.columns` entry drops the ONE column from both
   docs; every domain byte of the ledger row (delta / new_balance /
   reason / actor_id) still diffs.
2. **Class 2, the boundary's NEW home** — goldens are old-bot captures, so
   no golden can ever contain an `economy_balances` row; keeping the new
   home in the diff made the accepted class self-defeating for every
   money-mutating golden (the old home dropped, the new home permanently
   red — no money subsystem could ever flip). New
   `xp-coins-alias.new_home_table` entry drops `economy_balances` rows
   from both docs. Balance BEHAVIOR stays fully pinned: every wallet
   mutation still diffs through `economy_audit_log`'s `delta`/`new_balance`
   bytes (a per-mutation pin, strictly stronger than the aggregate row),
   and INV-F reconciles the aggregate against the ledger continuously.

If the owner rejects either completion, revert the two `parity.yml` entries
and their mechanism lines in `sb/adapters/parity/dispositions.py`; the
blackjack subsystem row must then flip back `ported -> pending` (its gating
golden re-reds on exactly these two lines).

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
