# 2026-07-13 — session-card completeness fix (defuse the mtime-lottery gate trips)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · contained docs slice

## Scope

Two `complete`-status session cards on main lack the required Session
idea (`💡`) and Previous-session review sections:
`.sessions/2026-07-13-btd6-paragon-calculator.md` (PR #339) and
`.sessions/2026-07-13-ticket-setup-panel.md` (PR #347). Because the
`checkers` job validates the newest-by-mtime card, either one can trip
the gate for a FUTURE unrelated PR (verbatim error: "session log … is
missing: Session idea (expected `💡`), Previous-session review
(expected `previous-session review`)"). This slice adds GENUINE
sections to both — the idea and review derived from each slice's
actually-landed work (D-0086 / D-0084 ledgers) — changing nothing else
in the cards; the family-level `📊 Model:` lines stay intact. A scan of
all other 2026-07-13 cards found no other card missing either section
(21 cards checked; only the two named were incomplete).

## 💡 Session idea

The completeness markers are byte-checkable, so they shouldn't wait for
the mtime lottery: teach the checker (or a pre-push guard) to validate
EVERY card whose status reads `complete` in the diff, not just the
newest-by-mtime card — a card that flips to `complete` while missing
`💡`/review sections would then fail its OWN PR instead of a future
innocent one, which is where both of these regressions slipped through.

## Close-out

PR #361. Verification: `python3 -m pytest tests/` — 2328 passed,
2 skipped (full local suite); `python3 bootstrap.py check --strict` —
green except this card's own designed born-red hold (flipped by this
commit) and the pre-existing peer advisory on
`control/claims/mining-write-parity-lane.md` (claims-format,
untouched). All 14 PR checks green on the first run, including
`checkers` and `gate`.

## ⟲ Previous-session review

The morning true-up session (PR #360) recounted the completeness-table
headline and flagged WP-5/WP-6 honestly — its table edits were the
navigation aid this cleanup used to identify which fix slices (#339,
#347) owned the broken cards. In its wake one gap class it did not
sweep: card-marker completeness (it trued up table rows, not session
cards), which is exactly the residue this slice retires.
