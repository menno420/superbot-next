# 2026-07-13 — mining energy slice 1: persistence + migration

> **Status:** `in-progress`

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

(filled at close-out)

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

(filled at close-out)
