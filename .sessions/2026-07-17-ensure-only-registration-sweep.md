# 2026-07-17 — ensure-only registration sweep: retire the last burn-down entry (`panel:role.hub`)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · mechanical refactor

## Scope

NEXT-TASKS item 3, the tail of the ensure-only-registration-gaps class
(docs/ideas/ensure-only-registration-gaps-2026-07-10.md). That ledger
captured 99 refs across 8 subsystems registered ONLY inside their
manifest `ENSURE_REFS` hook — invisible to the live root
(`sb.app.main.load_live_manifests`), which imports + dispatches but never
runs those hooks when zero plugins are admitted, so each was a
`RefUnresolved` BUG envelope waiting on first live dispatch.

Ground-truth re-check at HEAD (bde8f68) via the composition probe — NOT
inherited from the 2026-07-10 doc: 97 of the 99 were already retired by
the intervening ai/btd6/projmoon/mining/fishing/creature slice ports.
The probe's `ensure_only` diff at HEAD is a single ref:

- **`panel:role.hub`** — `sb.domain.role.panels`. The #111 role fix
  covered the hub HANDLERS (`role.render_hub` / `role.render_info_card`)
  and the info-card panel factory (both already register at module
  import), but the `@panel("role.hub")` factory itself lived only inside
  `ensure_panel_refs()`.

This is the last member of `_KNOWN_ENSURE_ONLY` — retiring it empties
the burn-down list.

## Fix

Mechanical, faithful to the #111 / `_register_info_card_factory()`
pattern already in the same file:

- `sb/domain/role/panels.py`: extract the `panel:role.hub` factory
  registration out of `ensure_panel_refs()` into a new module-level
  `_register_hub_factory()` (idempotent `is_registered` guard, mirroring
  the sibling `_register_info_card_factory()`), call it at MODULE IMPORT
  alongside `_register_hub_render` / `_ensure_hub_provider` /
  `_register_info_card_factory`, and call it from `ensure_panel_refs()`
  in place of the inline block (ENSURE_REFS re-arm stays idempotent).
- `tests/unit/invariants/test_composition_parity.py`: prune
  `"panel:role.hub"` from `_KNOWN_ENSURE_ONLY` (prune-on-fix, enforced by
  `test_burn_down_entries_are_still_real`). The set is now empty.

No behavior change beyond making the ref resolve at import time.

## Verification

- `python3 -m pytest tests/ -q` → 3160 passed, 29 skipped.
- `python3 -m pytest tests/unit/invariants/test_composition_parity.py -q`
  → 3 passed (`test_no_new_ensure_only_refs` /
  `test_burn_down_entries_are_still_real` green with `_KNOWN_ENSURE_ONLY`
  now empty).
- `python3 tools/check_parity_depth.py` → OK, 49 subsystems (49 ported),
  523 goldens; guard scripts (check_symbol_shadowing / check_namespace /
  check_no_skip / check_config_usage) → all clean.
- `python3 bootstrap.py check --strict` → all checks passed (only
  pre-existing advisories; this card carries no model-line advisory).

## 💡 Session idea

With `_KNOWN_ENSURE_ONLY` now empty, `test_no_new_ensure_only_refs` and
`test_burn_down_entries_are_still_real` become a pure floor: any newly
added ensure-only ref reds immediately with no burn-down cushion. Worth a
one-line note in the test docstring that the burn-down is fully retired,
so a future author does not re-add an "exemption" row —
tests/unit/invariants/test_composition_parity.py, target
`test_burn_down_entries_are_still_real`.

## ⟲ Previous-session review

Reviewed the predecessor #506 coordinator close-out
(`.sessions/2026-07-17-coordinator-closeout.md`), which cleared the
fleet-wide PR backlog to 0 open (#499 / #500 / #503 / #505 landed on main
at `0df7ac8`), and its follow-on fresh-start cleanup #507
(`.sessions/2026-07-17-fresh-start-cleanup.md`), which retired the
`control/` message bus (inbox / outbox / status wound down) and stood up
`docs/NEXT-TASKS.md` as the forward ledger. The message-bus retirement
reads clean: `control/` scaffolding is deprecation-bannered (not silently
deleted), the append-only inbox gate is honored, and `docs/NEXT-TASKS.md`
is the correct source of "what to build next" — this session's task
(NEXT-TASKS build-backlog item 3, the ensure-only-registration-gaps
class) was picked straight from that ledger, confirming the handoff works
as intended.
