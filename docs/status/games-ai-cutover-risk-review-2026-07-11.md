# Games + AI cutover risk review (2026-07-11)

**Reviewed HEAD:** `ab1e9162596f897000a43d085f2b6aa3f78090ad`.

This note documents the July 11, 2026 verification pass over the rebuilt games money domains, the golden-parity gate, and the band-7 AI operator surface. It confirms three previously reported issues are still live and records additional same-class risks found while widening the review.

## Cutover blockers

### P0: Blackjack solo terminal settle can double-apply

**Files:** `sb/domain/blackjack/ops.py`, `sb/domain/games/store.py`, `sb/kernel/workflow/engine.py`.

`_record_solo_stand()` and `_record_solo_double()` load the active solo hand through `_load_solo()`, which calls `games_store.fetch_user_checkpoint()`. That store helper performs a plain `SELECT` without `FOR UPDATE`. The terminal path then credits/debits the wallet and deletes the checkpoint. Blackjack ops are declared as `IdempotencyPosture.NATURAL_KEY` with `dedup_key=None`; the workflow engine only creates a durable `once()` key for `DURABLE_ONCE` and only applies an in-process mutex for `SINGLE_FLIGHT`.

**Failure scenario:** two concurrent Stand/Double interactions both read the same active hand, both compute the same terminal result, both credit or debit the wallet, and both delete the row. The row delete does not prevent the second money leg because the second transaction already loaded the row.

**Minimal fix:** add and use a `FOR UPDATE` checkpoint load for solo mutating/terminal actions, or move the terminal operations to a correctly scoped `SINGLE_FLIGHT`/`DURABLE_ONCE` posture. Prefer the DB lock for multi-worker correctness.

### P0: Blackjack PvP accept can double-escrow

**Files:** `sb/domain/blackjack/ops.py`, `sb/domain/games/store.py`, `sb/domain/games/wager.py`.

`_record_pvp_accept()` loads the pending challenge through `_load_pending()`, which calls `games_store.fetch_checkpoint()` with a plain `SELECT`. It then calls `wager.escrow_pvp_in_txn()`, which debits both players and upserts the escrow rows by natural key. Racing accepts can therefore debit both wallets twice while leaving only the final escrow checkpoint state.

**Failure scenario:** an opponent double-clicks Accept, or two accept interactions race. Both transactions load the pending challenge before either deletes it. Both debit both wallets. The escrow row upserts collapse to one logical escrow state, stranding the extra stake in the ledger.

**Minimal fix:** lock the pending challenge row before escrow (`SELECT ... FOR UPDATE`) and consume/delete it under that lock. A session-scoped `SINGLE_FLIGHT` can reduce local duplicate work but is not a substitute for a DB lock across workers.

### P0: Golden parity gate can false-green on unreplayable ported goldens

**Files:** `tools/run_golden_parity.py`, `sb/adapters/parity/cases.py`.

`run_gate()` computes the golden count per subsystem but never checks that the number of replayed cases equals the number of golden files for each `ported` subsystem. `load_replay_cases()` silently drops any golden that cannot be reconstructed and is not already in `CURATED_CASES`.

**Failure scenario:** a subsystem is marked `ported`, but one of its golden JSON files cannot be reconstructed into a replay case. The case loader drops it, the gate replays only the reconstructable subset, and the gate reports green if that subset has no diffs.

**Minimal fix:** make the case loader return missing/unreconstructable golden IDs, and make `run_gate()` fail closed when `replayed_count_by_subsystem != golden_count_by_subsystem` for any `ported` subsystem.

## Additional same-class findings

### P0: Farm collect can double-credit accrued eggs

**Files:** `sb/domain/farm/ops.py`, `sb/domain/farm/store.py`.

`farm.record_collect` reads the farm aggregate via `store.get_farm()`, which is a plain `SELECT`, computes settled eggs, credits coins, then writes eggs back to zero. Farm ops also use `NATURAL_KEY` with no dedup key.

**Failure scenario:** two concurrent collect requests read the same eggs/timestamp, compute the same payout, both credit coins, and both write eggs to zero.

**Minimal fix:** lock the farm aggregate row for mutating paths, including creation of a default row for new farmers, or use a compare-and-swap/conditional update that consumes the settled eggs exactly once.

### P1: Farm buy/upgrade can lose updates while charging twice

**Files:** `sb/domain/farm/ops.py`, `sb/domain/farm/store.py`.

`buy_chicken` and `upgrade_coop` read farm state without a lock, debit coins based on the stale price, then overwrite the aggregate with `chickens + 1` or `coop_level + 1`.

**Failure scenario:** two buy/upgrade requests race. Both charge the user, but both write the same next aggregate state, so the user can pay twice for one chicken or one coop level.

**Minimal fix:** lock the farm row around read/settle/price/debit/write, or use atomic conditional updates keyed on the observed state.

### P0: Mining sell/sell_all can over-credit inventory

**Files:** `sb/domain/mining/ops.py`, `sb/domain/mining/store.py`.

`record_sell` and `record_sell_all` read inventory with a plain `SELECT`. `_sell_rows()` later decrements quantities using `update_mining_item()`, whose update floors at zero, then credits the already-computed sale total.

**Failure scenario:** two sell requests read the same ore quantity. The first decrements to zero and credits coins. The second decrement floors at zero but still credits coins for the stale quantity.

**Minimal fix:** for single-item sell, use a conditional decrement (`WHERE quantity >= qty RETURNING ...`) before crediting. For sell-all, lock the user's positive inventory rows, recompute under lock, then decrement and credit.

## Documentation / posture issue

### P1: `wager.py` docstring overclaims K7 `once()` protection

**File:** `sb/domain/games/wager.py`.

The wager primitive docstring says idempotency is double-guarded by the K7 `once()` fence plus `FOR UPDATE` row consumption. Current blackjack/farm/mining money ops are generally `NATURAL_KEY` with no dedup key, and the engine only applies `once()` to `DURABLE_ONCE` specs. The docstring should either be narrowed to the settlement helpers that actually consume locked rows, or the relevant ops should be moved to a posture that actually provides the claimed fence.

## AI operator surface verification

### Prompt injection containment: verified clean in reviewed paths

**Files:** `sb/kernel/ai/nl_engine.py`, `sb/kernel/ai/instructions.py`, `sb/kernel/ai/safety.py`.

The current user message, recent channel turns, retrieved facts, bot knowledge blocks, and operator-authored instruction profile bodies are wrapped with `wrap_untrusted_text()` before they are included in the prompt stack. The wrapper disarms literal untrusted-data delimiters and strips unsafe control characters.

### `AI_ENABLED=false`: provider calls are gated, but the surface is not fully inert

**Files:** `sb/kernel/ai/flags.py`, `sb/kernel/ai/gateway.py`, `sb/kernel/ai/nl_engine.py`.

The gateway checks `flags.task_enabled()`, which returns false when `AI_ENABLED=false`, before dispatching to providers. However, `nl_engine.handle_message()` can return a vetted preset reply before it reaches the gateway. If operational policy is that `AI_ENABLED=false` means no AI subsystem responses at all, add an early global gate in `handle_message()`. If preset replies are intentionally allowed with providers disabled, document that distinction in operator-facing status/readiness copy.

## Areas verified clean or lower risk

- **Treasury:** contribution/disbursement use conditional or atomic economy/treasury writes instead of stale read/overwrite money flows.
- **Casino:** current port exposes the hub and pending poker terminal only; no active casino money/table engine was found in the reviewed slice.
- **Blackjack tournament settlement:** payout/abort use the existing `lock_rows_for_settlement()` row-consumption helper with `FOR UPDATE`.

## Recommended remediation order

1. Fix blackjack solo terminal locking and PvP pending accept locking before games go live.
2. Make the golden parity gate fail closed on ported subsystem denominator mismatches before any cutover claim relies on it.
3. Fix farm collect and mining sell/sell_all before exposing those domains with real coin value.
4. Reconcile `wager.py` idempotency documentation with actual K7 posture.
5. Clarify and/or enforce `AI_ENABLED=false` semantics for preset replies.
