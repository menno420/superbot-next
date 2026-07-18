# 2026-07-18 — test-depth coverage for sb/domain/role (handler refusal ladders + DB-truth views)

> **Status:** `in-progress`

- **📊 Model:** [[fill: family · effort · test-depth]]

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

- `python3 -m pytest tests/unit -q` → [[fill: verbatim tail]]
- `python3 tools/check_namespace.py` → clean
- `python3 tools/check_no_skip.py` → clean

## Deviation ledger

[[fill: skipped gaps + why]]

## 💡 Session idea

[[fill: one idea]]

## ⟲ Previous-session review

[[fill: review of the most recent OTHER .sessions card]]

## Close-out

[[fill: PR # + test count]]
