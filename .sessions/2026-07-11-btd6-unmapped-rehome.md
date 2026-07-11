# 2026-07-11 — btd6 `_unmapped` re-home wave (62 goldens → the ported btd6 row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · parity re-home

## Scope

The band-7 successor slice named by the wave-5 successor map
(`control/status.md` REMAINING `_unmapped` FAMILY HISTOGRAM): the
btd6-family 62 — the largest single `_unmapped` block — re-homed onto the
PORTED `btd6` row, the #193/#200/#202/#203/#207/#211 re-home pattern.

## What shipped

62 goldens moved `parity/goldens/_unmapped/` → `parity/goldens/btd6/`
(one-line `subsystem` flip each, bytes otherwise verbatim):

- **32 prefix sweeps** (`sweep_btd6ref*` 8, `sweep_btd6strat*` 9,
  `sweep_btd6events*` 9, `sweep_btd6ops*` 6) — the oracle's legacy
  standalone command trees. Byte-diff against the ported unified-tree
  siblings proved 31/32 IDENTICAL up to case_id/input-content/last_xp/
  subsystem (e.g. `sweep.btd6ops_readiness` ≡ `sweep.btd6_ops_readiness`);
  the one exception, bare `!btd6ref`, pins the shipped `send_help`
  SILENCE (`delete_message` only — the `grp_bare` shape), NOT the hub
  panel bare `!btd6` opens.
- **30 slash sweeps** (`sweep_slash_btd6_*`) — ALL structurally EMPTY
  (zero calls, zero db_delta): the capture guild never registered the
  grouped `/btd6 …` app commands, so discord.py dropped the interactions
  lib-side. They replay green by the #151 harness drop rule (an
  unregistered slash name never reaches dispatch) — and they are a
  standing trap-17-style constraint: DECLARING any `/btd6 …` slash
  surface later must reproduce that silence for these exact inputs or 30
  cases regress at once.

The port gap the prefix sweeps forced (the #193 oracle-wins law): the
legacy alias trees in `sb/manifest/btd6.py` routed to band-5 INVENTED
handlers — usage-cards (`ref_usage_view`, `strat_usage_view`,
`events_usage_view`, `ops_usage_view`), a parallel `ref_*_view`/
`strat_*_view` implementation with its own copy, and
`events_pending`/`ops_pending` ingestion terminals — none of them the
oracle bytes. Every alias CommandSpec now dispatches the SAME oracle
handler as its unified sibling (`btd6.cmd_*` in
`sb/domain/btd6/oracle_surface.py`); the four bare group commands route
`btd6.grp_bare`; legacy `btd6ops` gained its missing `announcechannel`
row (golden `sweep_btd6ops_announcechannel` drives it). The invented
handlers in `sb/domain/btd6/service.py` stay registered (panel actions
`btd6:*` and `tests/unit/band7/test_band7_btd6.py::test_reference_views`
still reference `ref_tower_view`/`events_usage_view`/`ops_usage_view`)
but no command routes them.

Bookkeeping: compat pin +1 command row (`btd6ops`-group
`announcechannel`; names/groups/aliases only — route changes are
pin-free), `manifest/layout/btd6.lock.json` amended ADDITIVELY with the
one new legacy-seed Exempt row + `check_sim_gate --write-baseline`,
`manifest_compile --write`. `--write-ratchet` ran byte-stable — btd6
stays `{events: 1, tables: 4, settings: 1}` (the incoming goldens carry
only already-counted surfaces). ZERO new depth exemptions, ZERO new
reason/disposition classes, compensator allowlist EMPTY.

## Evidence

- btd6 corpus 41/41 green pre-change (post-teardown baseline), then
  **103/103 green** after the re-route (`_replay_corpus({"btd6"})`,
  local real Postgres, serial).
- Full gate at the branch head: `gate: GREEN — all 328 golden(s) across
  39 ported subsystem(s) replay clean`; `check_parity_depth: OK — 50
  subsystems (39 ported), 467 goldens`; report leg 334/467 green,
  467/467 replayable, `_unmapped` 176→114.
- `tests/integration` 5/5; named gates all clean (namespace, escape
  hatches, schema growth, amendments, shadowing, no-skip, config usage,
  metric cardinality, egress, sim gate, compat).
- Unit suite: 1462 passed / 11 failed / 2 skipped canonical-order local —
  the SAME 11 failures reproduce at clean main `977bb27` (verified by
  running `pytest tests/ -q` at main before and after; identical FAILED
  list) and all 11 pass in file-isolation. PRE-EXISTING canonical-order
  pollution in the #213–#215 window, invisible to CI (the tests job
  installs only pytest+pyyaml, so the dep-guarded suites skip there).
  Follow-up ledgered below, NOT fixed here (scope).

## Guard recipe (the pre-existing flake follow-up)

Canonical `pytest tests/` with full deps fails 11 at main `977bb27`:
`tests/unit/ai/test_k10_nl_engine_evals.py::TestNLEngine::test_denied_unconfigured_audits_one_row`,
`tests/unit/ai/test_k10_nl_frontend.py::TestPolicyResolver::test_no_reader_denies_unconfigured`,
4× `tests/unit/band2/test_channel_state_rehome.py`,
`tests/unit/band3/test_band3_treasury_inventory.py::test_treasury_hub_renders_the_golden_bytes`,
4× `tests/unit/band6/` (blackjack_pvp end-to-end, deathmatch_casino
manifests, message_games manifests, ux_lab_home footer). All green in
isolation — the #141/#156 test-order-flake family (some earlier-listed
suite pollutes a registry/ref table). Bisect recipe: `pytest tests/ -q
--deselect` halves until the polluter pair surfaces; prior fixes armed
idempotent `ensure_*_refs()` re-registration or both-direction registry
isolation in the affected conftest.

## 💡 Session idea

The 30 empty `sweep_slash_btd6_*` goldens now sit in `goldens/btd6/` as
pure drop-rule pins. A tiny invariant test — "for every golden whose
steps carry a `slash` input and ZERO calls, assert the name is NOT in
the compiled slash registry" — would turn the trap-17 silence constraint
from tribal knowledge into a one-line CI red the moment anyone declares
`/btd6 …` (or `/setup depth`, same class) without reproducing the
capture's drop behavior.

## ⟲ Previous-session review

The #208 btd6 resolver maps/modes slice (merge `0e7cacd0`) closed the
first #144 parked domain item and measured the wrap-up counts this slice
booted from. What it did well: carrying the shipped `_match_terms`
common-word quirk unimproved — that discipline is exactly why 31/32
alias sweeps replayed green here the moment routing was fixed, with zero
copy drift to chase. What it could have done better: its wrap-up map
listed the btd6-family 62 as one opaque block; the 32-prefix/30-slash
split (and the fact the slash half is EMPTY drop-rule pins) was cheap to
measure and would have let the successor price the slice before opening
a single golden — successor maps should carry the one-line shape probe,
not just the count.
