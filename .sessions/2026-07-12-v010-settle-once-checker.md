# 2026-07-12 — V010 settle-once checker: the D-0078 parked successor lands

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · checker build (Q-0194)

## Scope

Build the settle-once architecture guard sim-lab VERDICT 010 approved and
D-0078 parked with a named successor (audit §8's exact terms: contract c,
warn-first per Q-0105, the #133 `tournament_flag.clear_active()` fence as
reference, EVERY money-moving root enumerated — the cogs/-drift lesson).
One merged-on-green PR: `tools/check_settle_once.py` + hermetic
red-then-green tests + the ci.yml checkers-loop word + this paperwork
(D-0079, the audit §8 PARKED→BUILT flip, telemetry row, status heartbeat).

## What shipped

- `tools/check_settle_once.py` — stdlib-only, DB-free, never imports sb;
  REUSES tools/check_money_race.py's machinery by import (parse/resolve/
  fence fixpoint/branch-aware walk) with a WIDENED money seed
  (credit_coins/try_debit_coins/credit_treasury/try_debit_treasury/
  credit_karma + the wager aliases). Root enumeration is DERIVED: a root
  = money-fixpoint function carrying a literal `@workflow("…")`
  decorator; money functions reachable from no leg WARN as "undeclared
  money path".
- Classification per root: CW (self-detecting conditional writes), CAS
  (money dominated by the first branch after an atomic consume — the
  #133 / gc_sweep shape), RC (FOR-UPDATE/advisory-fenced load + gating
  state consumed in the same txn); else WARN unless ledgered.
- Measured at HEAD `291caec`: **29 roots — RC:13 CAS:11 CW:3
  allowlisted:1 known-risk:1 warn:0**, undeclared:0. Every ledger row
  verified against source before being added. The one KNOWN RISK is
  karma `_record_give` (unlocked cooldown/cap reads + unconditioned
  `credit_karma` upsert, sb/domain/karma/ops.py:138-229) — loud on
  every run, exit 0, stale-row-RED when fixed.
- Four ledgers, all stale-row-is-RED: SETTLE_SITES (11 guard anchors,
  re-validated per run), REARM_SITES (5 multi-stage re-arms: rps+bj
  tournament_open→set_active, farm collect→set_farm, economy
  daily/work→cooldown anchors), ALLOWLIST (rps `_record_solo_play`),
  KNOWN_RISKS (karma).
- `tests/unit/invariants/test_check_settle_once.py` — 18 hermetic pins:
  RED on the pre-#133 free-branch credit, the ungated gc refund, the
  unfenced load-then-settle; GREEN on the shipped shapes verbatim;
  stale-ledger RED for all four tables; re-arm green/stale; the
  telemetry-line format; real-tree baseline (warn-set == ledgers,
  undeclared == []).
- `.github/workflows/ci.yml` — `check_settle_once` in the checkers loop
  (alphabetical, after check_schema_growth).

## Honest boundaries (in the checker's Q-0105 header)

CAS dominance is approximated as "the first branch after an atomic
consume guards its surviving paths" — no dataflow, so a rowcount bound
ignored across an unrelated branch can fool it (the @codex question on
the PR head). Fences propagate from helpers even when conditional
inside them. The lint pins the PROVEN shapes; it is not a general
concurrency analyzer.

## Verification

Serial local ladder at the branch head: `python3
tools/check_settle_once.py` green (1 known-risk line, exit 0); the FULL
committed checker fleet green incl. check_money_race and
check_runtime_smoke; `python3 -m pytest` full suite green (counts in
the PR body); `bootstrap.py check --strict` via the fleet run.

## 💡 Session idea

The warn→red graduation for this checker has a natural trigger already
in the tree: the telemetry line's `warn:` field. A one-line follow-up
(same class as check_doc_cites rule-b's playbook) could ratchet
`warn:0` — once the karma known-risk is fixed and its row deleted, flip
the WARN class to RED so no NEW unguarded money leg can land silently.
The graduation is a two-line diff (exit 1 when warn_roots) plus a
decisions entry; the evidence trail to justify it is being printed on
every CI run starting now.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-live-adapter-landing.md`, the most recent
completed card at branch time.) Its merge claims verified: #263
`248d068`, #278 `b7a0513`, #283 `291caec` are exactly origin/main's top
three commits at this branch's base. Its "no live effect has been driven
yet" NEXT-STEP stands and is re-recorded in this slice's status
heartbeat: the ORDER-004 live-drive proof for the merged adapter stack
is PARKED — this cloud session's permission layer denies booting the bot
with the Discord token, so the acceptance run needs an owner-side or
broader-permission session. Its correction note (the '11 known-red
integration tests' being local provisioning state) held here too: the
freshly provisioned local Postgres ran the full suite green.

## Close-out

One READY PR, squash-merged on 6/6 required green (`report`
red-by-design). Classification counts, ledger contents and the fleet/
pytest evidence in the PR body; @codex question posted on the final head
without waiting (Q-0258).
