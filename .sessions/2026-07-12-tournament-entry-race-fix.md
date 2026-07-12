# 2026-07-12 — tournament-entry double-debit race fix (the #221 KNOWN_RISKS row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · money-race bug fix, red-then-green (Q-0194)

## Scope

One bounded slice (PR #223): fix the money race the #221 lint ledgered as
its single KNOWN_RISKS row — `sb/domain/games/wager.py::
enter_tournament_in_txn` debited the entry fee and upserted the
natural-key entry row with NO advisory slot lock and NO existence check
(the #217 buy_chicken first-insert shape). Reachable via rps
`register_player` (Join button + ✅ reaction): its duplicate guard is
in-memory and yields at awaits, so two concurrent same-user entries both
debited while their upserts collapsed into ONE `uq_game_state` row — one
fee vanished (not in the pot, never refunded).

## Oracle semantics (Step 1)

Reconstructed via `mcp__github__search_code` over `menno420/superbot`
(direct file reads + list_commits DENIED for this seat; oracle head not
pinnable — all fragments returned at indexed ref `1ecc21138fe0a1eb6…`):
the oracle REJECTS a duplicate entry BEFORE any fee is taken —
`disbot/cogs/rps_tournament_cog.py try_register_player` guards
`paid_players`/`players` ahead of the fee block; the Join button
(`disbot/views/rps/registration.py`) replies **"You're already
registered!"** ephemeral; `disbot/utils/tournaments.py` returns the same
copy before its balance check. Pinned: reject-with-message, no debit, no
refund needed. (Noted drift, out of scope: the new tree's in-memory guard
copy at `sb/domain/rps/tournament.py:153` uses a period, oracle uses
`!`.)

## Delivered

- `sb/domain/games/wager.py` — `enter_tournament_in_txn` now takes
  `store.lock_new_checkpoint_slot` (pg_advisory_xact_lock on the
  (guild, user, subsystem) triple — the #213 solo_start precedent,
  identical lock ordering: advisory → game_state read → economy write)
  + a `fetch_user_checkpoint` existence check under the lock, BEFORE the
  debit; a committed entry row raises the new `AlreadyEnteredError`
  (D-0060 domain refusal, oracle copy verbatim) — the duplicate path
  never touches the wallet. Blackjack's launch loop treats the refusal
  as the shipped broke-player skip.
- `tests/integration/test_tournament_entry_race.py` — real-Postgres
  concurrency repro (the #213 test pattern): two concurrent
  `register_player` calls; asserts one fee debited, one ledger row, one
  entry row, one roster entry, loser refused with the oracle copy.
  RED at HEAD `71af879` (verbatim: "expected exactly one entry fee
  (-25); got a net change of -50 — one fee vanished (outcomes:
  (True, '') / (True, ''))"), GREEN with the fix (integration 10/10).
- `tools/check_money_race.py` — the KNOWN_RISKS row DELETED (stale-row
  guard); ledger now EMPTY; checker green with ZERO new
  ALLOWLIST/KNOWN_RISKS entries (the fix is structural: advisory fence
  before the money mutation). `test_main_exit_zero_on_head` re-pinned
  to the empty-ledger truth.

## Evidence

- units 1487 passed / 2 skipped local (real Postgres, canonical order);
  integration 10 passed; manifest_compile / check_sim_gate /
  check_compat_frozen / check_parity_depth green;
  golden-parity gate local: GREEN — 329/329 across 40 ported (zero
  golden movement from this fix).
- `check_money_race: OK — 0 violations under sb/domain (2 allowlisted
  site(s), 0 ledgered known-risk site(s))`.

## 💡 Session idea

The KNOWN_RISKS→fix coupling worked exactly as designed (the stale-row
guard forced this PR to delete the ledger row) — worth repeating for
other checkers: any "suspected real bug" a checker finds should land as
a loud ledger row whose deletion is mechanically tied to the fixing PR.
Also: the oracle copy drift found here ("You're already registered." vs
oracle "!") suggests a cheap sweep — grep the new tree's user-copy
literals against oracle search_code fragments for punctuation-level
drift in golden-uncovered refusal paths.

## ⟲ Previous-session review

The #221 card's KNOWN_RISKS row was a complete work order: exact
file/function/rule key, the reachable surface, the interleaving, the
fix shape (lock_new_checkpoint_slot + existence check), and the
enforcement hook (stale-row guard). This slice needed zero discovery
beyond oracle-copy confirmation. What it under-specified: the duplicate
outcome semantics ("shipped intent: refuse" was stated but not
oracle-evidenced) — the search_code reconstruction confirmed refuse-
with-copy and pinned the exact byte-form. Future ledger rows should
carry the oracle citation for the intended semantics up front.
