# Review findings — parity, money-like domains, AI surface, lifecycle

Date: 2026-07-11
Reviewer focus: PR-volume regression review after the recent parallel-lane merge burst.

This document records the concrete findings from the focused review of:

1. parity harness semantics,
2. money-like economy / blackjack / games payout paths,
3. AI operator surface inertness and prompt/provider paths,
4. lifecycle and plugin pin / boot verification.

It intentionally avoids style/refactor notes and only records correctness-relevant findings.

## Prioritized findings

### F-001 — Major — Blackjack solo terminal actions can double-settle under concurrent component submits

**Files:**

- `sb/domain/blackjack/ops.py`
- `sb/domain/games/store.py`

**What happens:**

Blackjack solo terminal actions load the active game through `_load_solo`, which calls `games_store.fetch_user_checkpoint`. That store read is a plain `SELECT` with no row lock. Terminal settlement then applies the coin delta before deleting the checkpoint row.

Because the row is not locked before settlement, two in-flight terminal actions can both observe the same active game and both apply the same payout/debit. The later checkpoint delete does not protect the money movement that already happened.

**Concrete failure scenario:**

1. A user has an active solo blackjack hand with a non-zero bet.
2. The user double-clicks `Stand`, or Discord retries a component interaction while the first transaction is still in flight.
3. Transaction A and transaction B both call `_load_solo` and read the same `game_state` row.
4. Both run dealer resolution and call `_settle_solo`.
5. If the user wins, both transactions credit the win. If the user loses, both transactions debit/floor-debit the loss.
6. Both then attempt to delete the checkpoint row; by then the duplicate balance mutation has already occurred.

**Impact:**

Direct wallet correctness issue. The bug can mint extra coins on wins or burn extra coins on losses.

**Severity:** Major.

### F-002 — Major — PvP accept flows can double-escrow because pending challenge rows are read without locking

**Files:**

- `sb/domain/blackjack/ops.py`
- `sb/domain/rps/ops.py`
- `sb/domain/games/store.py`
- `sb/domain/games/wager.py`

**What happens:**

Blackjack and RPS PvP accept flows load the pending challenge with `games_store.fetch_checkpoint`. That store read is a plain `SELECT` with no `FOR UPDATE`. The accept flows then call `wager.escrow_pvp_in_txn`, which debits both participants and upserts one escrow checkpoint per participant.

If two accepts run concurrently, both transactions can see the same pending row and both can debit both wallets. The escrow rows are upserted by the same natural key, so the second accept overwrites the same stored escrow state instead of preserving two separate stake records. Later settlement/refund only sees the current escrow rows and can therefore pay/refund one pot while both players were debited twice.

**Concrete failure scenario:**

1. Player A challenges Player B for 500 coins.
2. Player B double-clicks `Accept`, or Discord retries the accept interaction.
3. Transaction A and transaction B both read the pending challenge before either marks/deletes it.
4. Both transactions debit A and B by 500 in `escrow_pvp_in_txn`.
5. Both transactions upsert the same two escrow checkpoint rows.
6. Settlement/refund later locks the stored rows and pays/refunds one recorded stake per player, leaving the second debit unrecovered.

**Impact:**

Direct wagered-game wallet-loss bug. It can permanently strand or destroy a duplicate escrow debit.

**Severity:** Major.

### F-003 — Major — Golden parity gate can false-green if a ported golden is not reconstructable

**Files:**

- `sb/adapters/parity/cases.py`
- `tools/run_golden_parity.py`

**What happens:**

The replay-case loader reconstructs cases from golden documents. For click inputs with normalized session custom IDs, `_step_from_input` returns `None`; `reconstruct_case` then returns `None` for the entire golden. `load_replay_cases` only includes successfully reconstructed cases plus typed curated cases.

The gate iterates the returned replay cases but does not compare the replayed count against the golden count for each ported subsystem. `_replay_corpus` even documents a missing-count return shape, but the implementation returns only `results`. Therefore a future ported golden that cannot be reconstructed, and is not represented by a typed curated case, can be silently omitted while the gate reports green for the remaining cases.

**Current-corpus note:**

A local corpus check found one unreconstructable golden, `parity/goldens/blackjack/blackjack_solo_round_hit.json`. That exact case is currently covered by `parity.cases.CURATED_CASES`, so this review did not find a presently omitted green in the current corpus. The bug is the gate invariant: it does not fail closed if reconstruction silently drops a ported golden.

**Concrete failure scenario:**

1. A new ported subsystem gains a golden containing a normalized click custom ID such as `<cid:1>`.
2. The case is not duplicated in `CURATED_CASES`.
3. `_step_from_input` returns `None`, so `reconstruct_case` drops the case.
4. `run_gate` replays the remaining cases and reports green because it only counts failures in replayed cases.

**Impact:**

Harness false-green risk. A weak parity gate invalidates the evidentiary value of green parity claims for affected goldens.

**Severity:** Major.

## Areas reviewed that looked clean

### AI provider inertness with `AI_ENABLED=false`

The normal AI gateway path appears to fail closed for provider calls when `AI_ENABLED=false`:

- `AI_ENABLED` defaults false when config is unset/uninstalled.
- `flags.task_enabled()` returns false when global AI is disabled.
- `AIGateway.execute()` checks task enablement before redaction and before provider lookup/call, returning a degraded response instead of invoking a provider.

This does not mean the whole AI surface is inert: routing, auditing, and memory behavior can still run before the gateway degrades. The specific reviewed claim was provider inertness; that path looked clean.

### Plugin pin and boot verification

Installed plugins that are not pinned, or installed plugins whose manifest hash differs from the committed pin, are reported as violations. Pinned-but-not-installed plugins are treated as warnings/skips, not startup failures. That matches the current plugin-host contract that the lock file is an allowlist ceiling rather than a required-install list.

No correctness bug was found in this area unless the intended production policy changes to “every pinned plugin must be installed.”

## Commands used during review

```bash
find .. -name AGENTS.md -print
rg --files docs control
rg -n "golden|parity|expected|actual|assert|AI_ENABLED|ai_operator|blackjack|balance|payout|plugin_pin|plugins.lock|FAILED_STARTUP|RUNNING|shutdown|startup" sb tests tools pyproject.toml plugins.lock.json
sed -n '1,260p' sb/adapters/parity/runner.py
sed -n '1,240p' sb/adapters/parity/cases.py
sed -n '80,150p' tools/run_golden_parity.py
python - <<'PY'
from pathlib import Path
import json
from sb.adapters.parity.cases import reconstruct_case
root = Path('parity/goldens')
unreconstructable = []
for path in sorted(root.glob('*/*.json')):
    doc = json.loads(path.read_text())
    if reconstruct_case(doc) is None:
        unreconstructable.append((path, doc.get('case_id'), doc.get('subsystem')))
print(len(list(root.glob('*/*.json'))), len(unreconstructable))
print(unreconstructable)
PY
python - <<'PY'
from parity.cases import CURATED_CASES
print([c.id for c in CURATED_CASES if 'blackjack' in c.id])
PY
sed -n '1,340p' sb/domain/blackjack/ops.py
sed -n '1,260p' sb/domain/games/wager.py
sed -n '1,260p' sb/domain/rps/ops.py
sed -n '160,420p' sb/kernel/ai/nl_engine.py
sed -n '160,360p' sb/kernel/ai/gateway.py
sed -n '1,180p' sb/kernel/ai/flags.py
sed -n '240,560p' sb/app/main.py
sed -n '1,280p' sb/app/plugin_host.py
git status --short
```
