# Session — tournament open-flag TOCTOU posture-pin 2026-07-18

> **Status:** in-progress

- **📊 Model:** Opus 4 family · high · hardening

## Goal
Harden the shared tournament `active_tournament` open-flag guard WITHOUT
changing its behaviour: pin the DELIBERATELY non-atomic (accepted-posture)
open guard with a characterization test and a tripwire comment, so an
accidental future "fix" into a strict compare-and-set trips CI and routes
the change back to the owner-decision ledger
(`docs/ideas/tournament-open-flag-toctou-2026-07-12.md`, `outcome:
accepted-posture`) instead of shipping a silent divergence from the
superbot oracle.

## Scope
Non-behavioral hardening slice. Branch `claude/tournament-open-toctou` off
origin/main `1c14d43`. Born red (`in-progress`) as the first commit; holds
the PR red until the deliberate Status flip lands.

The diff is exactly:
1. **Characterization test** — `tests/unit/band6/test_band6_tournament_open_toctou.py`:
   pins the REAL `tournament_flag.set_active` as a plain unconditional
   UPSERT (no `WHERE` compare-and-set guard, no `RETURNING` win/lose
   read-back, returns `None`) — the accepted non-atomic posture.
2. **One tripwire comment** — a single line above `set_active` in
   `sb/domain/games/tournament_flag.py` citing the idea doc +
   `accepted-posture (strict fence = owner-decision)`.
3. **This card.**

NO product logic change. The originally-scoped strict-atomic fix was NOT
landed: a sibling review confirmed the loose guard is intentional and
oracle-faithful, and a strict fence is an OWNER-DECISION — not shipped
autonomously.

## Trail
- Idea doc `docs/ideas/tournament-open-flag-toctou-2026-07-12.md`
  (`outcome: accepted-posture`) marks the non-atomic open guard as the
  parity-faithful port of the oracle's own unfenced `get_active`/refuse;
  worst case (stranded pot) is boot-sweep-recovered. Decision: MATCH the
  oracle, do NOT add a fence.
- The SETTLE path (row-DELETE count settle-once token) and the ENTRY path
  (#223 advisory lock) are already atomic — only the OPEN guard is the
  deliberate non-atomic window, and it now has a characterization tripwire.
- Verify: `pytest tests/unit/band6/test_band6_tournament_open_toctou.py`
  → 2 passed; existing `test_band6_rps_tournament.py` +
  `test_band6_blackjack_tournament.py` → 30 passed (zero behaviour drift).

## 💡 Session idea

Characterization/posture-pin tests deserve a naming + discovery convention
so the fleet can tell "pins current accepted behaviour, do not delete to
make a change pass" apart from "regression test for a real fix". A shared
`_accepted_posture` / `_posture_pin` suffix (like this file's test names)
plus a one-line index in `docs/ideas/` back-references would let a future
agent that WANTS to change the pinned behaviour find the owning ledger row
directly from the failing test name, instead of rediscovering the
oracle-parity rationale from scratch.

## ⟲ Previous-session review

The 2026-07-18 prod-readiness-backlog session (docs-only, `1c14d43`) left
the tree marker-clean and prioritized the pending slices; this hardening
slice picks the tournament open-flag row from that backlog but, unlike a
port slice, correctly resolves it as a posture-pin rather than a behaviour
change once the accepted-posture ledger was read — carrying the
"read the idea doc before hardening" discipline the backlog assumes.
