# 2026-07-12 — Tournament cross-game reverse guard + open-flag atomicity re-ledger

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · money-path review follow-up (regression pin + parity-decision doc)

## Scope

Two follow-ups from the independent money-path review of the now-merged
#277 (the cross-game `active_tournament` foreign-flag guard):

1. **Reverse-direction regression test.** #277 pinned only the bj→rps
   refusal (`test_rpsregister_refuses_when_a_foreign_tournament_is_active`).
   The symmetric rps→bj direction — a live RPS tournament makes
   `!bjtournament` refuse — had a guard but NO test. Add the mirror.
2. **Open-flag atomicity.** Evaluate the shared `active_tournament`
   OPEN check-and-set's non-atomicity (a narrow TOCTOU) and decide,
   parity-first, whether to fence it or document the accepted posture.

## Follow-up 2 — outcome: guard already present, test is a green pin

The blackjack opener's foreign-flag guard exists and is correct
(`sb/domain/blackjack/handlers.py::tournament_open_route`:
`if existing and existing != "blackjack": … return`, oracle copy
verbatim). Added
`test_bjtournament_refuses_when_a_foreign_tournament_is_active` to
`tests/unit/band6/test_band6_blackjack_tournament.py` (seeds the shared
flag `"rps"`, sends `!bjtournament`, asserts the oracle refusal
`"A **rps** tournament is already active in this server."`, the RPS flag
untouched, no blackjack state, no money moved). It PASSES with the guard;
red-proof: neutralizing the guard makes it fail (blackjack opens on top of
the RPS flag). So this is a regression pin, NOT a bug fix — no missing
reverse guard was found.

## Follow-up 1 — decision: MATCH the oracle, document the accepted posture

The OPEN guard (`get_active` read → refuse) is a genuine non-atomic
check-and-set. Exact window:
`sb/domain/rps/handlers.py::register_route` and
`sb/domain/blackjack/handlers.py::tournament_open_route` each read
`get_active(gid)` on a SEPARATE autocommit connection (no lock;
`sb/domain/games/tournament_flag.py::get_active`, `conn=None`), then later
`set_active` in the workflow txn — two DIFFERENT-game opens interleaving
across that read→write await gap can both pass and clobber the shared
value. The ENTRY race is fenced (`wager.py` advisory lock, #223) and the
SETTLE race is atomic (`clear_active` DELETE-count check-and-set), but the
OPEN path has NO equivalent fence.

Parity check (menno420/superbot@97d281e5): the oracle's open guard is the
SAME unfenced `get_active`/refuse (`disbot/cogs/rps_tournament_cog.py`,
`disbot/cogs/blackjack/actions.py`), and its recovery is a boot sweep
(`disbot/cogs/rps_tournament/_helpers.py::clear_stale_tournament_flag`,
spawned at `cog_load`). The oracle ALSO uses non-atomic get/refuse + boot
recovery. Per the parity rule, the faithful posture is to MATCH it, not to
invent atomicity the oracle lacks. Worst case (a stranded pot) is
recovered by the boot escrow + flag sweep — low severity, self-healing.

Re-ledgered in `docs/ideas/tournament-open-flag-toctou-2026-07-12.md`
(window, low-severity rationale, boot-sweep recovery, oracle citation) and
a note in `sb/domain/games/tournament_flag.py`'s module docstring. A
strict-serialization fence (advisory lock keyed on `(guild,
"tournament-open")`) is flagged as an OWNER-DECISION — it would diverge
from the oracle — not taken unilaterally.

## Delivered

- `tests/unit/band6/test_band6_blackjack_tournament.py` — the rps→bj
  reverse refusal regression test (green; red-proofed).
- `docs/ideas/tournament-open-flag-toctou-2026-07-12.md` — the
  accepted-posture re-ledger.
- `sb/domain/games/tournament_flag.py` — module-docstring concurrency-
  posture note (no behavior change).

## Evidence

<!-- filled at close-out -->

## 💡 Session idea

The three races on ONE shared flag (entry / open / settle) have THREE
different concurrency postures — advisory-locked, non-atomic-by-parity,
atomic-by-construction — and only two were ever pinned. A checker that,
for any state used as a per-owner CAS token, enumerated every read/write
site and asserted each is either fenced or explicitly ledgered as
accepted-non-atomic would have surfaced the open path's bare posture
without a human review pass. The #277 card already gestured at the
owner-cardinality half of this; the missing half is per-SITE fence
accounting.

## ⟲ Previous-session review

This follow-up grades #277's own close-out. #277 correctly restored the
dropped rps→bj... (bj→rps) guard and pinned ONE direction, and its card
even named the settle-once token's owner-cardinality invariant — but it
left two threads for a reviewer to pull: the reverse direction went
untested (the guard existed, so nothing was red, so nothing forced the
test), and the OPEN guard's non-atomicity was implied by the "clobbers the
flag" framing but never named as a distinct, accepted TOCTOU with the
oracle parity that justifies leaving it. The lesson carried forward: when
a fix restores a guard whose whole point is a check-and-set, the close-out
should state that guard's atomicity class outright (fenced / accepted-
non-atomic / atomic-by-construction) rather than leave it as an inference,
and should pin BOTH directions of a symmetric guard even when one is
already green.
