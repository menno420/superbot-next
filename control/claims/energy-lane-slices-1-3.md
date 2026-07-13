# Mining energy lane — slices 1–3 claim — `claude/energy-slice-1` ff.

> **CLAIM** — continues the energy lane the slice-0 claim
> (`control/claims/mining-energy-domain-core.md`, PR #320) opened: the
> "separate lane" the deep-mining WRITE-PARITY lane explicitly ceded
> (`control/claims/mining-write-parity-lane.md` — cook/use "depend on the
> un-ported mining energy/consumable system (a **separate lane**)").

Scope + slice plan: `docs/scoping/energy-system-scope.md` (branch
`mining/energy-domain-core`, PR #320). Branches: `claude/energy-slice-1`
and successors (`claude/energy-slice-2`, `claude/energy-slice-3`), each
stacked on the previous open head per ORDER 017 rule 2.

- `claude/energy-slice-1` · **slice 1 — persistence + migration** —
  `migrations/0052_mining_energy.sql` (ALTER `mining_player_state` ADD
  `energy`/`energy_updated_at`, DEFAULT 0/0) + `get_energy`/`set_energy`
  in `sb/domain/mining/store.py` (plain upsert, non-audited/non-money,
  fishing precedent; NO new store row) + unit round-trip tests · area:
  `migrations/`, `sb/domain/mining/store.py`, `tests/unit/` · 2026-07-13
- `claude/energy-slice-2` · **slice 2 — cook/use wiring + argful
  goldens** — `use_route`/`cook_route` BLOCKED→LIVE, one-txn ops,
  oracle-verbatim copy, canonical-harness goldens · area:
  `sb/domain/mining/{service,ops}.py`, `sb/manifest/mining.py`,
  `manifest.snapshot.json`, `parity/cases/curated.py`,
  `parity/goldens/mining/`, `parity/parity.yml` · 2026-07-13
  (ACTIVE — branch pushed, stacked on `claude/energy-slice-1` @ #384)
- `claude/energy-slice-3` · **slice 3 — fastmine dig gating** — energy
  spend + out-of-energy refusal in `record_mine`/`fastmine_route`;
  re-mints `sweep_fastmine`; OWNER-gated (Option A) and sequenced
  strictly AFTER WP-3 (#317) · 2026-07-13 (queued)

**Shared-table note.** Slices 1–2 touch `mining_player_state` columns the
WP lane does not (energy/energy_updated_at); slice 3 is the only leg that
collides with WP-3's re-frozen contract and stays parked behind it.
