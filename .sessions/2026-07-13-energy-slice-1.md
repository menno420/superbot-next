# 2026-07-13 — mining energy slice 1: persistence + migration

> **Status:** `complete`

- **📊 Model:** `fable-5` · energy-lane slice 1 (persistence) · stacked on
  #320 `mining/energy-domain-core` per ORDER 017 rule 2 (branch from an
  open PR's head, note the base in the PR body)

## Scope

Slice 1 of the energy lane per `docs/scoping/energy-system-scope.md`
(slice plan, "Slice 1 — persistence + migration"):

1. `migrations/0052_mining_energy.sql` — ALTER `mining_player_state`
   ADD `energy INTEGER NOT NULL DEFAULT 0`,
   `energy_updated_at BIGINT NOT NULL DEFAULT 0` (the faithful
   missing-row `(0,0)` posture: every existing depth-player settles to a
   full bar on first read; oracle migration 086 shape) + the
   `checksums.json` entry.
2. `sb/domain/mining/store.py` — `get_energy` / `set_energy`, a PLAIN
   upsert on the existing `mining_player_state` store (NON-audited /
   non-money — the `sb/domain/fishing/store.py`
   `get_fishing_energy`/`set_fishing_energy` precedent; NO new store
   row — energy rides `MINING_PLAYER_STATE_STORE`, so the existing
   `mining.erase_subject_state` erasure already covers the columns).
3. Unit round-trip tests (the `_RecordingConn` DB-free SQL-shape pin,
   `tests/unit/band6/test_band6_games_substrate.py` pattern).

Oracle semantics source: `disbot/utils/db/games/mining_player_state.py`
@ `87bbe1dbf0c504d1ef1fc9db466224303f16afba` — `get_energy` missing-row
→ `(0, 0)`; `set_energy` upsert `ON CONFLICT (user_id, guild_id) DO
UPDATE SET energy=$3, energy_updated_at=$4`.

NOT this slice: no command wiring (`!cook`/`!use` stay BLOCKED pending
terminals — slice 2), no `!fastmine` dig gating (slice 3, owner-gated,
sequenced after WP-3 #317), no golden touched, no `parity/parity.yml`
change.

## What shipped

All three scope items, PR #384 (base `mining/energy-domain-core`, stacked
on #320; contains the main catch-up merge @ e3d3768 — slice-1 delta =
the card, the claim, and ca740ca):

- `migrations/0052_mining_energy.sql` + `checksums.json` entry — the
  ALTER lands both columns `IF NOT EXISTS`, NOT NULL DEFAULT 0/0.
- `sb/domain/mining/store.py` `get_energy`/`set_energy` — oracle
  signatures/semantics verbatim (`disbot/utils/db/games/
  mining_player_state.py` @ `87bbe1d`), minus the oracle's
  `updated_at=now()` touch (the target's `updated_at` is a BIGINT epoch
  — the `set_depth` precedent). Exported in `__all__`; no new StoreSpec.
- `tests/unit/mining/test_mining_energy_store.py` — 9 DB-free tests:
  missing-row `(0,0)`, int coercion, plain unlocked TEXT-id read, upsert
  SQL shape, the no-`now()` pin, a spend→set→get round-trip, the 0052
  DDL pin, and the no-new-store-row pin.
- Verify: `pytest tests/ -q` → 2478 passed, 13 skipped; all local gate
  mirrors OK (shadowing / namespace / no-skip / config-usage /
  migrations / money-race / parity-depth / runtime-smoke /
  compat-frozen). CI @ ca740ca: all six named gates green (required
  `gate` leg green; the non-required `report` leg also green).

Decide-and-flag: PR base = `mining/energy-domain-core` directly, no
frozen copy — the auto-merge enabler refuses to arm on a base with zero
required status-check contexts, so arming can never merge into the
parked #320 branch (evidence: e0adeb6 reached that branch by plain
push). The PR stays OPEN per ORDER 017 rule 2.

## 💡 Session idea

The stacked-PR catch-up merge needs an unshallow first: this container's
clone is SHALLOW, so `git merge origin/main` into a branch cut from
another PR's head fails with "refusing to merge unrelated histories"
until `git fetch --unshallow origin`. Worth a one-liner in
`docs/AGENT_ORIENTATION.md` § "Start every session" next to the
preflight reset — the error message sends you toward
`--allow-unrelated-histories` (WRONG — that would duplicate history)
when the real fix is deepening the clone.

## ⟲ Previous-session review

Previous card (`2026-07-13-curation-rework-cleanup-words.md`, PR #327):
exemplary evidence discipline — the per-item "verified still-pending at
HEAD" sweep and the explicit deliberate-leave-behinds section made its
boundary with the word-mutation slice unambiguous; its 💡
(worktree-first for parallel lanes) is exactly the collision class a
stacked lane like this one risks and is still unplanted in orientation.
