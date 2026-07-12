# 2026-07-12 — deep-mining WRITE-PARITY lane — WP-2 vault write goldens

> **Status:** HOLD (born-red — WP-2 in flight: stash / unstash / stash-all /
> vaultupgrade write goldens + mining_vault / mining_player_state exemption
> retire. First commit plants the flag; flips complete on the last commit.)

- **📊 Model:** opus-4.8 · high · parity/golden-minting (Q-0194)

## WP-2 scope (vault — pure capture, write legs already live)

Stacked on WP-1 (#306, branch `mining-write-parity-lane`). The vault write legs
are already ported + wired live (`sb/domain/mining/ops.py`
`record_stash/unstash/stash_all/vault_upgrade`, routed argful in `service.py`);
every imported sweep pinned only the bare/guard byte, so `mining_vault` and the
`vault_level` face of `mining_player_state` carry `guard-only-capture`
exemptions. This slice mints row-bearing write goldens that DRIVE those
mutations, making the live handlers their own frozen contract, and RETIRES both
exemptions.

Terminals (4):
- `mining.stash_write` — `!stash diamond 5` (inventory-seeded) → −mining_inventory
  / +mining_vault; `<@u> Deposited **5× diamond** into your vault — safe and out
  of your pack.`
- `mining.unstash_write` — `!unstash diamond 5` (vault-seeded) → −mining_vault /
  +mining_inventory; `<@u> Withdrew **5× diamond** from your vault back into your
  pack.`
- `mining.stash_all_write` — `!vault` → 📦 Stash All Ore click (inventory-seeded)
  → move sellable resources pack→vault; `<@u> Stashed …`
- `mining.vault_upgrade_write` — `!vaultupgrade` (funded balance) → coin debit +
  `mining_player_state.vault_level` bump; `<@u> Vault upgraded to capacity **45**
  item types for **2000** 🪙. Balance: **500** 🪙.`

Reply copy is byte-identical to the oracle (`services/mining_workflow.py`
vault_deposit/withdraw/deposit_all/upgrade). Retire `depth.exemptions.mining`
`table:mining_vault` + `table:mining_player_state` (vault_level rides
mining_player_state — the vaultupgrade capture covers it), then
`check_parity_depth.py --write-ratchet`.

## Concurrency fold-in (money-reviewer follow-up)

vault_upgrade is advisory-fenced (`lock_vault_upgrade_slot`), so this slice adds
a dedicated TWO-TRANSACTION Postgres concurrency regression test racing two
concurrent first-upgrades of a fresh player — asserting the lock serializes them
(both pay the escalating `vault_upgrade_cost` schedule, level lands at 2, no
double-charge / lost tier). Mirrors
`tests/integration/test_farm_mining_money_race.py`.

## 💡 Session idea

vault_upgrade is the one WP-2 terminal that writes `mining_player_state`
(vault_level rides it), so a single funded-upgrade capture retires a table WP-3
was slated to cover — the exemption granularity is per-table, and the first
row-bearing delta on it wins. The capture harness thus quietly pulls a WP-3
retire forward, and WP-3 is left covering only the depth column + mining_world +
gear-wear.

## ⟲ Previous-session review

WP-1 (#306) landed 5 equip/loadout write goldens green and left the ported gate
at 466, mining ratchet `{events: 3, tables: 9}`. Its landing report
(`scratchpad/wp1-landing-report.md`) is the mint ground-truth: goldens are minted
via `sb/adapters/parity/runner.capture_case` (the NEW-bot path), never
`parity/run.py` (which boots the un-ported oracle bot). This session stacks WP-2
on that branch and follows the same procedure verbatim.
