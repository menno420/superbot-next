# 2026-07-18 — test-depth coverage for sb/domain/role (handler refusal ladders + DB-truth views)

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`) — releases the born-red `substrate-gate` HOLD so
> the server-side lander can merge on green. First commit was the born-red
> card + claim alone (held the gate red); the new test file landed in the
> second commit; this flip is the last. Full `tests/unit` was green (3366
> passed, 2 skipped) and both stdlib-`ast` guards clean at flip time. No
> `sb/` product code, no golden touched — additive test file only.

- **📊 Model:** Opus 4 family · high · test-depth

## Scope

The role handler layer (`sb/domain/role/handlers.py`) carries the refusal
ladders and DB-truth read views that neither `tests/unit/band5/
test_band5_role.py` (feasibility/planners/K7 legs) nor
`tests/unit/band6/test_operator_hub_edits_a.py` (the Create modal slice)
reach. This slice is purely additive — ONE new test file, NO product or
golden change, DB-free — pinning:

- **`role.deleterole`** — the full feasibility gate ladder: usage guard →
  `guild is None` honest-wait → `role is None` → the ABOVE_BOT feasibility
  refusal (`❌ Could not delete **{name}**: {reason}`) → the unarmed
  provisioning RuntimeError refusal → the success path's shared-mutation_id
  audit + lifecycle pair.
- **`role.reactroles_bind`** — usage guard, the `fetch_message`
  `LookupError`→"Message not found" and `RuntimeError`→"⚠️ {exc}" forks,
  and the reaction-add warn branch that keeps the saved row.
- **`role.temprole`** — usage / missing-token / invalid-duration refusals,
  plus a direct `_parse_duration` boundary table (bare=minutes, >1yr, 0,
  non-digit, empty).
- **`feasibility.evaluate_role`** — the ABOVE_ACTOR actor-hierarchy verdict.
- the six DB-truth text views (time/xp/reaction/exemptions/manage/
  diagnostics) — populated render + empty-state copy each, both diagnostics
  forks.
- the `assignroles`/`debugroles`/`refreshmembers` unarmed-adapter BLOCKED
  copy, the authority-ref floors, and the hub audience-tier floor.

## Deliver

- `tests/unit/band5/test_band5_role_depth.py` — 26 DB-free cases
  (`asyncio.run`, `SimpleNamespace` ducks, monkeypatched `store` readers,
  the `reset_role_ports_for_tests` autouse fixture; the band5 dir
  convention).

## Verification

- `python3 -m pytest tests/unit -q` → `3366 passed, 2 skipped, 1 warning
  in 63.86s (0:01:03)` (the new file: 26 passed in 0.25s)
- `python3 tools/check_namespace.py` → `check_namespace: clean`
- `python3 tools/check_no_skip.py` → `check_no_skip: clean (every surface
  funnels through resolve())`

## Deviation ledger

- **No gaps skipped.** All eight gaps in the assignment brief were
  feasible DB-free and are covered: P1 deleterole ladder (6 branches),
  reactroles_bind (4 branches), temprole + `_parse_duration` table,
  ABOVE_ACTOR; P2 the six views (both diagnostics forks), the three
  unarmed-adapter refusals, the authority-ref floors, the hub
  audience-tier floor. No padding — each case asserts the specific
  branch/copy/value that matters.
- Verdict copy is pinned to `feasibility._REASONS` verbatim (e.g. the
  ABOVE_BOT byte `above my highest role — I can't manage it`); the
  provisioning-refusal case asserts the `❌ Could not delete **{name}**:`
  prefix rather than the long unarmed-port RuntimeError tail, so it stays
  robust to that message's wording.

## 💡 Session idea

The **success** paths of the mutating handlers still lean on the
`_create_role_lane`/`deleterole` twins for their shared-mutation_id
audit+lifecycle pair — but `reactroles_bind`'s post-write ack (the
role-name resolution via `service.find_role` over the live guild view)
and `temprole`'s happy-path expiry ack are only exercised through the
seam tests, not the handler. A follow-up one-file slice could pin those
two acks end-to-end with an armed guild view + a monkeypatched
`engine.run`, closing the last uncovered handler branches (the ack copy,
not just the refusals).

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-owner-decisions-agenda.md` (the current
`origin/main` HEAD, #539) — a docs-only slice that consolidated every
scattered owner-open-question across the 2026-07-18 design docs into one
prioritized `docs/design/OWNER-DECISIONS-2026-07-18.md` agenda, indexed
from `docs/design/README.md`. Same born-red-first / flip-last discipline
this card follows, and it models the decision-block shape (Decision ·
Options · Recommendation · Unblocks · Source) the owner rips through. Its
posture is the mirror of this slice: it gathers *product-intent*
questions for the owner, whereas this slice closes a *verification* gap
no owner decision was blocking — the two together keep the split between
"needs a human call" and "just needs coverage" clean. No overlap; nothing
to reconcile.

## Close-out

- **PR #541** — https://github.com/menno420/superbot-next/pull/541
- `tests/unit/band5/test_band5_role_depth.py`, **26 DB-free cases**,
  full `tests/unit` green (3366 passed / 2 skipped), both guards clean.
- Server-side lander merges on green (the six required named gates) —
  not merged agent-side.
