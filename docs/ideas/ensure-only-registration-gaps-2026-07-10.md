---
state: captured
origin: lab
shipped_pr: null
shipped_repo: menno420/superbot-next
merged_date: null
outcome: open
---

# Ensure-only registration gaps: 99 refs invisible to the live root (2026-07-10)

> **Status:** `ideas`
>
> **State:** captured (found by the composition-parity sweep while killing
> BUG A's class for band-6 — `tests/unit/invariants/test_composition_parity.py`).
> **Origin:** this repo's own band-5 live-drive ledger, bug 1 (#109 → fixed
> for role in #111), generalized.

**One line:** 99 refs across 8 subsystems are registered ONLY inside their
manifest's `ENSURE_REFS` hook — the live root (`sb.app.main.load_live_manifests`)
never runs those hooks, so each one is a `RefUnresolved` BUG envelope waiting
for its first live dispatch, while the polite unit suites stay green.

## The class (BUG A, band-5 ledger bug 1)

`ENSURE_REFS` is the compiler/plugin-host RE-ARM seam (restore refs after
`clear_ref_table`), not a boot step. The live root imports `sb.manifest.*`
and dispatches. Registration must therefore happen at MODULE IMPORT
(declaring IS reserving) — the `sb/domain/role/handlers.py`
`_register_pending()` pattern from #111. Blackjack (2 refs) and rps (4 refs)
were fixed in the same PR that landed the invariant; the remainder below is
gated by the test's `_KNOWN_ENSURE_ONLY` burn-down list (may only shrink).

## The burn-down (99 refs, by registering module)

| module | refs | shape |
|---|---|---|
| `sb.domain.ai.service` | 20 handler views/routes | real handlers registered only in the ensure path |
| `sb.domain.btd6.service` | 23 handler views/routes/pendings | same |
| `sb.domain.projmoon.service` | 10 handler views | same |
| `sb.domain.mining.service` | 28 pending terminals | `pending_handler` calls only in ensure |
| `sb.domain.fishing.service` | 15 pending terminals | same |
| `sb.domain.creature.service` | 1 pending terminal (`creature.battle_pending`) | same |
| `sb.domain.proof_channel.handlers` | `panel:proof_channel.hub` | hub panel factory only in ensure |
| `sb.domain.role.panels` | `panel:role.hub` | same (the #111 fix covered handlers, not the panel) |

Exact ref names: the `_KNOWN_ENSURE_ONLY` set in
`tests/unit/invariants/test_composition_parity.py` (kept there so prune-on-fix
is enforced by `test_burn_down_entries_are_still_real`).

## Fix shape (mechanical, per module)

Extract the ensure-only registrations into a `_register_*()` function, call
it at module import AND from the ensure hook (idempotent — `pending_handler`
and the `is_registered` guards already tolerate re-arm), then prune the
module's rows from `_KNOWN_ENSURE_ONLY`. One PR per subsystem family is a
natural quick-win slice; band-6 game work should take mining/fishing first
(player-facing pending terminals).

## Risk if left

Every listed handler ref is routed by a `CommandSpec` or panel action — the
first live `!mine`, `!fish`, `!btd6`, `!pm`, or ai-panel click after CUT-1
dies in a BUG envelope exactly like `!roleinfo` did in the band-5 live drive.
