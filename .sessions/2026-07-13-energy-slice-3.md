# 2026-07-13 — mining energy slice 3: dig energy-spend into !fastmine

> **Status:** `complete`

- **📊 Model:** `fable-5` · energy-lane slice 3 (fastmine dig gating,
  Option A) · stacked on #317 `mining-write-parity-wp3` (itself on #312
  `mining-write-parity-wp2`) per ORDER 017 rule 2 (branch from the
  highest unmerged head the work depends on, note the base in the PR
  body), with `origin/main` merged in (slices 1–2 + the energy core are
  main-only).

## Scope

Slice 3 of the energy lane per `docs/scoping/energy-system-scope.md`
(slice plan, "Slice 3 — wire dig energy-spend into `!fastmine` (ONLY
under Option A; sequence AFTER #317)"):

1. `sb/domain/mining/ops.py` — `record_mine` gains the dig energy
   spend inside the existing txn: `get_energy` → settle → `can_dig`
   gate → spend `DIG_COST=1` → `set_energy`, over the #320 pure energy
   core (`MAX_ENERGY=60`, `REGEN_SECONDS=10`) + the slice-1
   `get_energy`/`set_energy` store pair.
2. `sb/domain/mining/service.py` — `fastmine_route` out-of-energy
   refusal as a ROUTE-LEVEL PRE-TXN pure read (the slice-2
   ValidatorError-envelope trap), carrying the `~{wait}s` hint from
   `seconds_until_next_dig`. Refusal copy oracle-verbatim @ 87bbe1d.
3. Goldens (canonical D-0073 `capture_case`, double-captured):
   RE-MINT `sweep_fastmine.json` (its db_delta now carries the
   `mining_player_state` energy 60→59 write) + mint the NEW
   out-of-energy refusal golden.
4. Ratchet / count-pin reconcile against the post-WP-3
   `mining_player_state` contract (in-merge union: corpus 500 /
   minted 38 before this slice's mint).

Oracle copy source: `disbot/services/mining_workflow.py` `mine()` @
`87bbe1dbf0c504d1ef1fc9db466224303f16afba` (local clone, never MCP).

NOT this slice: no chop/explore energy gating (the scoping doc digs
only the mine leg), no migration, no new store functions.

## What shipped

All four scope items, PR #392 (base `mining-write-parity-wp3` — #317
and #312 were both still OPEN, so the slice stacked on the highest
unmerged head per ORDER 017 rule 2, with `origin/main` @ 4f52643 merged
in; merge commit 85c1812 reconciled the count-pin/parity conflicts to
the union corpus 500 / minted 38, mining ratchet {events: 4,
tables: 15}):

- `sb/domain/mining/ops.py` `_record_mine` — in-txn
  get_energy → settle → can_dig → spend(1) → set_energy at the leg head
  (oracle `dig()` bracket @ 87bbe1d grafted onto fastmine; the in-leg
  ValidatorError is the race fence only).
- `sb/domain/mining/service.py` `fastmine_route` — route-level PRE-TXN
  pure-read refusal, oracle hint verbatim, `~{wait}s` via
  `energy.seconds_until` (`_time.time()` rides the harness's pinned
  wall-clock seam).
- Goldens (D-0073 capture_case, double-captured byte-identical
  post-disposition): NEW `mining_fastmine_out_of_energy_refusal`
  (probe-derived fixture stamp lands the hint at ~5s); RE-MINTED
  `sweep_fastmine` (energy 60→59 joins its db_delta) + the four
  WP-2/WP-3 mining_player_state goldens (pre-0052 rows gain the energy
  column defaults on the merged schema — the post-WP-3 contract
  reconcile, replies unchanged, columns-only diff).
- Pins: corpus 500→501, minted 38→39; ratchet unchanged
  (`--write-ratchet` no-op). Band6 FakeMiningStore gains
  get_energy/set_energy fakes + 2 new leg tests.
- Verify @ cb3a90f: pytest 2521 passed / 2 skipped; gate GREEN 501/501;
  all 12 local check mirrors + manifest_compile green; CI named-gates +
  golden-parity (gate AND report legs) + ci all SUCCESS.

Decide-and-flag: (1) Option A adopted via the coordinator baton (the
scoping doc's "C first, then A after WP-3" recommendation — C shipped
as slices 1–2); (2) the refusal replies PLAIN on the command lane (the
oracle renders the hint in the grid-view embed, a D-0043 surface this
port lacks; slice-2 refusal posture is the command-lane home);
(3) chop/explore stay ungated — the oracle brake sits on `dig()` alone.

## 💡 Session idea

A schema migration silently invalidates every OLDER golden that pins a
full row of the migrated table: the WP-2/WP-3 mining_player_state
goldens were minted before 0052 added the energy columns, so the first
merged tree that carried both went gate-RED with "unexpected (new
behavior)" column diffs — nothing in check_migrations or the ratchet
connects `ALTER TABLE … ADD COLUMN` to "re-mint the row-pinning goldens
of that table". A one-line rule in the flip playbook (grep
parity/goldens for rows of any table a migration widens; budget the
re-mints into the same PR) turns this from a surprise red into a
checklist item.

## ⟲ Previous-session review

## ⟲ Previous-session review

Previous card (`2026-07-13-energy-slice-2.md`, PR #385): its 💡 —
pinning the ValidatorError-envelope trap with the explicit instruction
that slice 3's out-of-energy refusal must be a route-level pure read —
is exactly the failure this session would otherwise have re-derived
from a red capture; writing the successor's trap into the predecessor's
card is the cheapest cross-slice insurance this lane has found.
