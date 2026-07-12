# 2026-07-12 — slice 3 port: vault / stash / unstash / vaultupgrade / mineinv (safe stash + capacity sink)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The faithful port of mining slice 3 — the per-player **safe stash** (vault) and
its coin-sink capacity upgrade. Four shipped commands move from honest D-0043
pending terminals to real handlers, one already-live alias leaves the PENDING
roster, stacked on slice 2 (PR #289, itself on slice 1 PR #286):
`!vault` · `!stash` · `!unstash` · `!vaultupgrade` · (`!mineinv` de-PENDING).

Planned delivery:

- **Domain** (`sb/domain/mining/capacity.py`): the shipped capacity math ported
  VERBATIM from the oracle (`disbot/utils/mining/capacity.py`) — `CapStatus`,
  `distinct_types`, `vault_capacity`, `vault_upgrade_cost`, `vault_status`,
  `vault_warning`, `BASE_VAULT_CAP`/`VAULT_SLOTS_PER_LEVEL`/`MAX_VAULT_LEVEL`
  and the `_VAULT_UPGRADE_BASE_COST=2000` / `_VAULT_UPGRADE_COST_STEP=1500`
  ladder.
- **Stores + migrations**: `mining_vault` (item-state, `user_id` TEXT to match
  `mining_inventory`; symmetric deposit/withdraw deltas) as a registered
  store, plus a `mining_player_state.vault_level` column for the capacity tier.
  Migrations `0044_mining_vault.sql` (CREATE) + `0045_mining_vault_capacity.sql`
  (ALTER) (+ checksums).
- **Audited write ops** (`ops.py`): stash / unstash (symmetric item moves,
  one-leg one-txn) + stash-all-resources + the vault upgrade (economy debit +
  vault_level bump, the `mining:vault_upgrade` reason) — all faithful to
  `services/mining_workflow.py`.
- **Vault panel** (`panels.py`): the shipped `views/mining/vault_panel.py`
  `MiningVaultView` + `build_vault_embed` as a session (ephemeral) `mining.vault`
  PanelSpec — 📥 Deposit · 📤 Withdraw · 📦 Stash All Ore · ⬆️ Upgrade · ↩ Mining
  Hub + the standard nav row, its live 🏦 Mining Vault embed built by a
  renderer override (goldens/mining/sweep_vault pins every byte).
- **Handlers** (`service.py` `_register()`): the stash / unstash usage guards,
  the vaultupgrade insufficient-funds refusal (a pure read — no write, no audit
  row), stash-all; the 5 keys removed from `PENDING`.
- **A-16 depth floor**: a `depth.exemptions.mining` `guard-only-capture` row for
  the new `table:mining_vault`.
- **Golden re-home** (#193 law): the 4 `_unmapped` sweeps
  (sweep_vault/stash/unstash/vaultupgrade) re-homed into the gated `mining` row
  (gate 435 → 439) by `git mv` + the one sanctioned `subsystem` flip. `mineinv`
  was already re-homed (#250) onto the mining-core row (`mining.inventory_view`),
  so it contributes NO gate bump — this slice only removes its stale PENDING key.

## Verification (local, real Postgres, pristine DB)

- **golden-parity GATE GREEN — all 439 golden(s) across 51 ported
  subsystem(s) replay clean** (was 435; the +4 re-home takes it to 439,
  mining 20 → 24, `_unmapped` 33 → 29), incl. sweep_vault / sweep_stash /
  sweep_unstash / sweep_vaultupgrade. Each verified byte-identical against
  the REAL handlers by a targeted `replay_case` pass BEFORE the `git mv`
  (all four GREEN), then again in the full gate after. (A first full-gate
  run reported 154 `db_delta.settings` regressions — that run overlapped
  the serial pytest run on the SAME `parity_replay` DB, the documented
  concurrent-DB pollution false-red; re-run ALONE on a clean DB it is
  GREEN.)
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  468 goldens** (the new `table:mining_vault` declared surface held by a
  `guard-only-capture` exemption; `vault_level` rides the already-held
  `mining_player_state` exemption; R3 ratchet unchanged).
- **check_migrations: clean (45)** — 0044_mining_vault.sql +
  0045_mining_vault_capacity.sql appended to `checksums.json`.
  **manifest_compile: green** (snapshot recompiled, P9 parity).
- **check_money_race: OK — 0 violations** (the audited `!vaultupgrade`
  read-then-settle fenced with `lock_vault_upgrade_slot`'s
  `pg_advisory_xact_lock`, the #213/#217 precedent). **check_sim_gate: OK**
  (the new 5-action `mining.vault` panel's layout [A] fields pinned via
  three legacy-seed Exempt overlays + a regenerated baseline).
  check_compat_frozen / check_namespace / check_escape_hatches /
  check_schema_growth all clean.
- **pytest tests/unit: 1748 passed, 5 skipped** on a pristine DB, run
  SERIALLY (`-p no:randomly`). `tests/unit/invariants/test_composition_
  parity.py`: 3 passed (the 5 now-removed `*_pending` refs —
  vault/stash/unstash/vaultupgrade/mineinv — pruned from the burn-down);
  test_check_money_race 11 passed; sim_runner/test_run_and_gate 27 passed.
- `bootstrap.py check --strict`: the only red was the by-design born-red
  HOLD while this card declared `in-progress` — flipped `complete` in this
  final commit; nothing else.

### 4 re-homed goldens (git mv `_unmapped → mining`, subsystem flip only)
sweep_vault, sweep_stash, sweep_unstash, sweep_vaultupgrade — rename
similarity R98/R99 (only the `"subsystem"` line changed; asserted
calls/events/db_delta bytes untouched — #193 law). mineinv was already
re-homed (#250) onto the mining-core row (`mining.inventory_view`), so it
contributed NO gate bump — this slice only removed its stale PENDING key.

## 💡 Session idea

The vault opens a fourth held write lane onto the shared "argful mining
capture" follow-up the slice-2 card scoped: `mining_vault` is
corpus-expressible (`!stash <owned item> [n]` writes a row) but every imported
sweep drove only the bare `!stash` usage guard, so the deposit row lands in no
golden. It joins the growing `guard-only-capture` ledger (equip / loadout / wear
/ skill / geared-descend / world-reseed) — one capture run after the ladder
completes should seed a persona with a pack of ore + coins, drive one deposit,
one withdraw, and one funded `!vaultupgrade`, mint the row-bearing goldens, and
DELETE every held exemption at once (the D-0069 class exit). The vaultupgrade
success path is the sink's only coin-moving write; its insufficient-funds
refusal (the ONLY path any golden pins) is a pure read, so the coin ledger stays
untouched by the corpus.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-slice2-descend-ascend-mineworld-port.md`, the
slice-2 descend/ascend/mineworld port.) Its headline — PUSHED + PR GREEN,
stacked on #286 — landed the depth-band + world-seed stack clean, and its
durability discipline (push the born-red card first, re-push per commit) is the
rule this slice adopted from minute one. Its substrate map was again exactly
right: the `mining_player_state` exemption it refreshed already anticipated the
`vault_level` column would ride the same already-declared table (no new
exemption for the ALTER — only the brand-new `mining_vault` table needs one),
and its correction to the slice-1 idea — treat the `guard-only-capture`
exemptions as ONE growing ledger the whole ladder drains once at the end, not
per-rung — is precisely how this slice framed its own vault hold. One thing to
carry forward: slice 2's vault was the first slice whose pinned golden is a FULL
component-bearing card (the 🏦 Mining Vault embed + five buttons + nav row),
not a plain guard string or an attachment-filename collapse — so the render-model
fidelity (minted `<cid:N>` session ids, the exact field/footer bytes) is a
larger parity surface than the earlier rungs, and the session PanelSpec +
renderer-override recipe proven here is the template slices 4–6's hub cards reuse.
