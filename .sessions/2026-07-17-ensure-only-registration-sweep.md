# 2026-07-17 — ensure-only registration sweep: retire the last burn-down entry (`panel:role.hub`)

> **Status:** `in-progress`

- **📊 Model:** Opus 4.8 · worker session · composition-parity burn-down

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

- `python3 -m pytest tests/ -q` → see close-out.
- `python3 tools/check_parity_depth.py`, guard scripts
  (check_symbol_shadowing / check_namespace / check_no_skip /
  check_config_usage), and the composition-probe re-run → see close-out.

## 💡 Session idea

With `_KNOWN_ENSURE_ONLY` now empty, `test_no_new_ensure_only_refs` and
`test_burn_down_entries_are_still_real` become a pure floor: any newly
added ensure-only ref reds immediately with no burn-down cushion. Worth a
one-line note in the test docstring that the burn-down is fully retired,
so a future author does not re-add an "exemption" row —
tests/unit/invariants/test_composition_parity.py, target
`test_burn_down_entries_are_still_real`.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-16-conform-sweep-457.md` (#457 conform
sweep). Its discipline of deriving the target list by a structural marker
scan AT HEAD rather than trusting an inherited count is exactly what this
session needed: the 2026-07-10 ledger claimed 99 refs, but the live probe
found one. Adopted that "re-derive from the tree, never from the doc"
rule as STEP 1 here.
