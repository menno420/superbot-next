# Requests to the sim-lab project — simulation work superbot-next wants (2026-07-12)

> **Status:** `plan`
>
> Cross-project request doc, addressed to the sibling **sim-lab** project on
> the owner's directive of 2026-07-12. Routing is via the owner / fleet
> manager (this repo has no direct write path to sibling projects — see
> [`README.md`](README.md)). Every claim below was re-verified against this
> repo at main `764a393` (#260); where a previously reported number moved,
> the counted-at-HEAD number is used and the counting method named.

Format per request: **what to simulate → why (with citation) → what a
passing result unlocks.**

---

## SIM-REQ-1 — Sim-back the pinned layout families (the sim gate currently verifies nothing)

**What to simulate.** Layout optimization runs for the highest-value pinned
layout families, using the oracles this repo already ships
(`sim/oracles/navigation.py`, `sim/oracles/dense_panel.py`,
`sim/oracles/settings_grouping.py`, driven by `sim/run.py --space <sim_id>`),
producing committed run records under `sim/records/` (winner, per-term
breakdown, top-5 alternatives, input hashes, seed — the record contract is
in `sim/records/README.md`).

**Why.** The sim gate (`tools/check_sim_gate.py`, a required CI job) pins
layout assignments against `sim/sim-gate-baseline.json` — counted at HEAD:
**802 assignments, 802 of 802 carrying `exempt` provenance, zero carrying a
simulation reference**, and `sim/records/` is empty (README only). (The
program review, `docs/review/program-review-2026-07-12.md` § "What the sim
lab and backlog say", reported 788 at its audited HEAD `c792079`; the
baseline has since grown to 802 — count method: `len(assignments)` and a
provenance-key histogram over the baseline JSON.) As provenance that layouts
were *optimized by simulation*, the gate currently verifies nothing — its
own honest state.

**Highest-value families by pin count** (counted from the baseline):
btd6 (76), ai (70), logging (59), diagnostic (54), moderation (49),
automod (46), mining (40), welcome (33), security (30).

**A passing result unlocks.** Baseline provenance flips exempt→sim-backed
family by family; the required sim-gate job starts guarding *ratified*
arrangements instead of legacy seeds; future layout changes need a sim
record, not a hand-wave.

## SIM-REQ-2 — Scale simulation of concurrent settles/entries (the money-race defect class)

**What to simulate.** Hundreds-to-thousands of concurrent actors driving the
money-bearing lanes against real Postgres: wallet credits/debits, game
settles, tournament entries, farm/mining reward claims — random
interleavings, crash/retry injection, with the invariants *money is
conserved*, *no double-debit/double-credit*, *no settle applied twice*.

**Why.** This defect class is proven real in this repo, three times over:
PR #213 (merge `f71d60b`) fixed wallet-race findings F-001/F-002 plus a
parity-gate false-green (F-003); PR #217 (merge `ed8eed34`) fixed the same
class in farm/mining credit-bearing legs (locking reads added); PR #223
(merge `80464ab`) fixed a same-user concurrent tournament-entry
double-debit (advisory slot lock + existence check before the fee debit) —
found by the static checker `tools/check_money_race.py` (PR #221) as a
KNOWN-RISK, then reproduced red-then-green in
`tests/integration/test_tournament_entry_race.py`. Today's defenses are the
static lint plus ~11 targeted integration race tests inside the required
gate job — targeted regressions, not exploration.

**A passing result unlocks.** Confidence the class is closed *everywhere*,
not only on the four fixed lanes; a machine-generated candidate list of
credit-bearing legs still missing locking reads; evidence for the
production-readiness story (`docs/review/program-review-2026-07-12.md` Q4).

## SIM-REQ-3 — Panel interaction flows (button/modal sequences are nearly un-goldened)

**What to simulate.** Multi-step component interactions as state-machine
walks over the declared panel surface: chooser pagination, settings
edit/reset widgets, game buttons (blackjack hit/stand, PvP accept), modal
open→submit→reject sequences — emitting deterministic interaction traces.

**Why.** Counted at HEAD over `parity/goldens/` (468 case files): steps
histogram `{1: 461, 2: 4, 3: 3}`; input kinds `{command: 408, slash: 66,
modal: 3, click: 1}` — the whole corpus contains exactly **1 button click
and 3 modal submits**. Panels count as "captured" when their component tree
is rendered, never when clicked (`parity/COVERAGE.md:22`). Component-interaction behavior is
essentially un-goldened while the live product is increasingly
component-driven (the band-7 chooser/widget/modal surface).

**A passing result unlocks.** Traces the existing minting procedure
(`parity/parity.yml:45-61` — the minted-goldens lane, capture_case with the
kernel-spine strip) can turn into real interaction goldens, closing the
review's named interaction blind spot (program review Q3 / Top-10 item 8).

## SIM-REQ-4 — Rehearse live-ladder rows 8 (games) and 9 (AI) before they are ever live-driven

**What to simulate.** A full simulated live-drive of the games band —
multi-player blackjack and RPS tournaments end-to-end with simulated
players, reaction ingress, timeouts and abandonment — and of the AI band
against the deterministic provider (`sb/kernel/ai/providers/deterministic.py`),
scripted so the same drive can later replay against the real test guild.

**Why.** The live-testing ledger (`docs/status/testing-report-2026-07-09.md`,
rows at lines 37-38) shows row **8. Games (band 6) — pending** and row
**9. Knowledge + AI (band 7 — needs keys) — pending**: the ladder's last two
rungs have never been live-driven. Every previous band's live pass found
bugs replay could not — silent acks in three bands, dead handlers,
clock/RNG leaks (program review, § "What the sim lab and backlog say").

**A passing result unlocks.** A found-defect list *before* the real live
pass; ready-made drive scripts for rows 8-9; for row 9 it de-risks the
owner-key-gated live-NL leg so the paid-key session spends time on
evidence, not on discovering harness bugs.

## SIM-REQ-5 — Economy balance and inflation over long horizons

**What to simulate.** An agent population playing the economy for weeks of
simulated time — earning lanes, game wagers and settles, tournament fees
and prizes, daily faucets vs sinks — tracking total money supply, Gini-style
concentration, and sink/source ratios under different activity mixes.

**Why.** The economy row is ported and gate-green (economy 6/6 goldens via
#152; treasury via #214 `827b134`) and games settle real coins (band-6,
#114–#138), but no document in this repo models long-run balance — searched
`docs/` and found no inflation/faucet-sink analysis of any kind. Parity
pins byte-behavior per command, not emergent system behavior.

**A passing result unlocks.** Tuning data (payout tables, fees, faucet
caps) with provenance; candidate `sim/records/` entries feeding SIM-REQ-1's
lane; a defensible economy story before any production cutover.

## SIM-REQ-6 — Coverage-exploration sims for never-observed events, tables, and settings

**What to simulate.** Guided command-sequence exploration that deliberately
drives the never-observed surface: bus events, DB tables, and settings keys
that no golden has ever touched — emitting minimal reproducible scripts per
newly-reached surface.

**Why.** The import-time coverage report (`parity/COVERAGE.md`): only
**21% of bus events** (37 of 47 never observed), **25% of DB tables**
(79 of 105 never touched), and **2% of settings keys** (117 of 120 never
mutated) are covered, versus 96%/88% of prefix/slash commands — the corpus
is heavily command-skewed (program review Q3). Many sweeps drove commands
bare as admin; mining's `!mine` golden literally pins an old-bot error
string, not gameplay.

**A passing result unlocks.** Capture scripts for new goldens on the
state/event surface; a corpus whose depth matches its breadth; early
warning on tables/events that are dead code versus merely untested.

---

*Anything above that sim-lab finds cheaper to prove or disprove a different
way — say so in the reply; these are requests, not specs.*
