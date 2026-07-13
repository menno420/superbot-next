# 2026-07-13 — mining `!minestats` Deepest fix (ORDER 031 phase 2, games lane improve slice)

> **Status:** `complete`

- **📊 Model:** `fable-5` · games-lane improve slice · mandate: ORDER 031
  phase 2 (claim `control/claims/order-031-games-casino.md`, PR #423),
  executing the top unblocked item from
  `docs/review/games-finalization-2026-07-13.md` (mining review G1)

## Scope

Planned as two S-sized read-side items; one dropped at claim re-scan:

- **A — `!minestats` "Deepest" bug fix (review G1):** `stats_view`
  (`sb/domain/mining/service.py`) rendered `describe_position(depth)` —
  the *current* band — where the oracle renders the max-depth record
  (`disbot/cogs/mining_cog.py` `stats`: `db.get_max_depth` →
  `world.describe_position(max_depth)`;
  `disbot/utils/db/games/mining_player_state.py:91` returns 0 for a
  no-row player). The port's `store.get_max_depth` already matches that
  fallback and the descend op already records the value
  (`ops.py _record_descend` → `store.record_depth`), so the fix is a
  read swap in the handler + retiring the stale docstring excuse.
  `sweep_minestats` is a fresh-player sweep (depth = max_depth = 0) —
  expected golden-neutral; verified via the parity harness.

- **B — how-to panel port: DROPPED.** The claim re-scan at session start
  found `control/claims/curation-rework-night-bundle.md` (merged #426,
  2026-07-13 22:44 — after the mining review's claim scan) claims row 60
  "retire `mining.how_to_pending`" on `claude/curation-night-1`. Claimed
  work is hands-off; reported back to the coordinator instead of racing.

## Close-out

Branched from `f263066`. Item A landed in `494bb26` (one hunk in
`sb/domain/mining/service.py stats_view`: `get_max_depth` read + Deepest
renders `describe_position(max_depth)`; stale docstring excuse replaced
with the live citation). Verified on the provisioned local ladder
(`docs/operations/local-verification.md`): `python3 -m pytest tests/ -q`
= **2904 passed, 2 skipped**; `python3 tools/run_golden_parity.py
--gate` = **gate: GREEN — all 494 golden(s) across 50 ported
subsystem(s) replay clean** (sweep_minestats byte-identical — the
predicted golden-neutrality held, no re-pin); `python3 bootstrap.py
check --strict` = exit 0 once this card flips (the only red was the
designed born-red hold; the claims-duplicate `tests/` warnings are
pre-existing and advisory). No golden files changed. Item B dropped
(claimed by #426 — see Scope).

## 💡 Session idea

The G1 bug survived because the fresh-player golden can't distinguish
current depth from max depth (both 0) and the docstring *asserted* the
divergence was unreachable after it had stopped being true (descend went
live and records max_depth). A tiny non-fresh parity fixture tier — one
golden family captured after a scripted descend/ascend — would make this
whole class of "fields that only diverge with state" regressions
harness-visible instead of review-dependent.

## ⟲ Previous-session review

The games-lane review session (`docs/review/games-finalization-2026-07-13.md`,
PR #432) left an unusually executable trail: gap G1 came with the exact
render line, the oracle counter-cites (mining_cog.py:157,181), the
already-landed write path (ops.py:428-433), and a golden-neutrality
prediction — this slice spent its time verifying rather than deriving,
which is the review format working as intended. One drift to note for
future reviews: its §5 claim scan was stale within hours (#426 claimed
the how-to item it ranked "UNBLOCKED, TOP PICK 2"), so ranked lists
need a claim re-scan at execution time, as this slice's orders required.
