# 2026-07-12 — Tournament cross-game reverse guard + open-flag atomicity re-ledger

> **Status:** `complete`

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

## Follow-up 3 (money-review round-2) — PAID-tournament conservation golden

#302's tournament goldens pinned only the FREE leg (fee=0 / pot=0). The
PAID-pot money path was unpinned. Minted
`parity/goldens/blackjack/blackjack_tournament_paid_flow.json` (D-0073
procedure, `sb/adapters/parity/runner.capture_case`): open a fee-25
single-round tournament → two pre-funded entrants Join → `!bjstart` debits
each 25 (`tournament:entry_fee`) → per-entrant round → champion paid the
pooled 50 pot (`blackjack:tournament_win`) + `clear_active`, self-cleaning.
The golden's `economy_audit_log` rows ARE the conservation assertion:

```
member         -25  tournament:entry_fee     new_balance 75
second_member  -25  tournament:entry_fee     new_balance 75
second_member  +50  blackjack:tournament_win new_balance 125
```

two 25 debits sum to the single 50 payout — no coins minted or stranded.
Entrants pre-funded via `fixture_sql` (outside `db_delta`); fee = the
sim-pinned test value (a user command arg, not an oracle constant), pot =
summed stakes, payout reason oracle-verbatim. Refund
(`blackjack:entry_refund`) is not deterministically reachable in a
self-settling flow (fires only on the abort/forfeit branch) — noted, not
pinned. Double-captured byte-identical post-disposition. Count pins
reconciled onto current `main` (post-rebase over the WP-1 mining
write-parity goldens): on-disk 481→482, `minted_goldens` 19→20
(`parity.yml` + the two count-pin tests).

## Evidence

- `python3 -m pytest tests/ -q` — 2055 passed, 5 skipped (real Postgres,
  throwaway local instance; post-rebase over `main`).
- `python3 -m pytest tests/unit/band6/test_band6_blackjack_tournament.py
  tests/unit/band6/test_band6_rps_tournament.py -q` — 30 passed.
- `python3 -m pytest tests/unit/parity_adapter tests/unit/parity_gate -q`
  — 93 passed (the reconciled count pins).
- `python3 tools/run_golden_parity.py --gate` — GREEN, all 467 golden(s)
  across 51 ported subsystems replay clean (+1 over baseline: the new
  paid-tournament golden replays in-trajectory).
- `python3 tools/check_parity_depth.py` — OK, 482 goldens, no ratchet
  movement (the golden touches already-covered tables economy_audit_log/xp).
- `python3 -m pytest tests/integration -q` — 11 passed.
- `python3 bootstrap.py check --strict` — all checks pass.
- The reverse guard test red-proofed: neutralizing the blackjack
  foreign-flag guard makes
  `test_bjtournament_refuses_when_a_foreign_tournament_is_active` fail;
  restored, it passes.

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
