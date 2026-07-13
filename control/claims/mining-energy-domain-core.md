# Mining energy — domain-core port claim — `mining/energy-domain-core`

> **CLAIM** — the "separate lane" the deep-mining WRITE-PARITY lane explicitly
> ceded (`control/claims/mining-write-parity-lane.md` lines 23-26: cook/use "depend
> on the un-ported mining energy/consumable system (a **separate lane**)"). This
> claim opens that lane with its FIRST, zero-blast-radius slice only: the PURE
> ENERGY DOMAIN CORE + unit tests. No persistence, no migration, no command wiring.

Scope + deferred-owner-decision record: `docs/scoping/energy-system-scope.md`.

- `mining/energy-domain-core` · **mining energy pure domain core (slice 0)** — port `disbot/utils/mining/energy.py` from the oracle verbatim to `sb/domain/mining/energy.py` (mirrors `sb/domain/fishing/energy.py`); pure headless regen/consumption math (`EnergyState`, `settle`/`can_dig`/`spend`/`restore`/`seconds_until`/`restore_value`/`bar`), oracle-verbatim constants (`MAX_ENERGY=60`, `DIG_COST=1`, `REGEN_SECONDS=10`, `RESTORE_VALUES`), full unit coverage · area: `sb/domain/mining/energy.py`, `tests/unit/mining/`, `docs/scoping/` · 2026-07-12

**DEFERRED (NOT this slice) — later, gated slices.** Persistence (ALTER
`mining_player_state` + `get_energy`/`set_energy`) and command wiring (`!cook`/
`!use` argful terminals) are separate later slices. **Dig-gating `!fastmine`
awaits an OWNER DECISION and must sequence strictly AFTER WP-3 (#317)** —
`mining_player_state` is the same table WP-3 is mid-flight re-freezing. This
slice touches NO golden, NO `parity/parity.yml`, NO `mining_player_state`.
