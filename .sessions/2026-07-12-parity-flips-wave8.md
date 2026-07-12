# 2026-07-12 — parity flips wave 8 (setup + quicksetup: the last two walls fall — THE PARITY PROGRAM IS COMPLETE AT 50/50)

> **Status:** `complete`

- **📊 Model:** Fable · high · feature build (Q-0194)

## Scope

The parity-flips lane's wave 8: the two OWNER-SHAPED walls that survived
every prior wave — setup (PARKED at the trap-17 create-channel wall
since wave 6) and quicksetup (BLOCKED D-0030 since wave 2) — each
flipped pending→ported in its own squash-merged-on-green PR on the
6-check ruleset (`report` red-by-design, non-required). Both flips ride
the #242 channel-ops ENABLER (D-0077) that the band-7 successor lane
landed for exactly this purpose. **With these two merges the parity
program is COMPLETE: all 49 real subsystem rows + the kernel coverage
home = 50/50 program rows ported.** No pending subsystem row remains in
parity/parity.yml — the only pending directory is `_unmapped`, the
re-home pool (106 goldens, 101 not yet green), which is attribution
work over ALREADY-PORTED rows, not port work. Every count below is
re-verified at HEAD `7334083` (#246's merge, main HEAD at wrap-up) per
Q-0120, not replayed from mid-wave memory. This wrap-up card + its
telemetry row + the status fold ride the wrap-up PR (control fast lane,
docs-only — trap 25: no Postgres ladder in the wrap-up seat; counts
are CI-LOG-VERIFIED instead).

## The two PRs (each merge sha verified against `git log origin/main` at `7334083`)

1. **#245** `32544d9` — setup pending→ported, **9/9 goldens** (the 8
   setup-dir goldens + `_unmapped/sweep_setup` re-homed onto the row as
   its create-carrying golden — setup dir hand-counted 9 files at
   HEAD, report job shows `setup 9/9 green [ported]`). THE TRAP-17
   WALL RESOLVED WITHIN EXISTING VOCABULARY: the slash goldens'
   zero-channel-call shape replays via find-branch over runner-seeded
   `CAPTURE_WORLD_CHANNELS` (sb/adapters/parity/runner.py:137 — the
   sweep_xpimport/#203/#207 leaked-state precedent generalized to
   gateway-cache channel state; `reset_case_state()` clears +
   re-seeds per case), and the create branch is exercised by the
   re-homed sweep_setup golden — trap 17's "no ruled twin" claim was
   STALE, retired by #242's `ParityChannelStateActions` twin + this
   seam. `setup.open_workspace` takes the D-0065 create-BEFORE-DB
   shape — the oracle sequences create before any DB write and never
   rollback-deletes — so NO compensator is declared and the
   compensator allowlist stays EMPTY
   (tests/unit/workflow/test_compensator_invariant.py:23
   `_ALLOWLIST: dict[str, str] = {}` at HEAD); the D-0077-ruled
   `setup.compensate_create_channel` handler stays reserved for the
   DB-first shape only (sb/domain/setup/ops.py). ZERO depth
   exemptions (no setup rows in parity.yml depth.exemptions at HEAD);
   migration `0037_setup_session.sql`; ratchet setup
   {events: 2, tables: 3, settings: 0}. tools/check_egress.py gained
   `actions` as a sanctioned port receiver (line 52 — the
   `actions = active_actions()` domain binding convention; the S11
   fence still bans `create_text_channel` by name outside adapters).
   Depth notes: `/setup-depth` deliberately green-by-absence;
   `/setup-delegate` + `/setup-undelegate` capture-skipped in
   `_sweep_skips.json` ("unsupported required option type user").
   Gate at its merge: run 29186558036 gate job 86633632162 — "gate:
   GREEN — all 364 golden(s) across 49 ported subsystem(s) replay
   clean" + "golden-parity gate: 49 ported / 2 pending" (pending
   _unmapped [106] / quicksetup [1]) + "check_parity_depth: OK — 50
   subsystems (48 ported), kernel ported, 471 goldens"; integration
   11 passed same job.
2. **#246** `7334083` (main HEAD) — quicksetup pending→ported, **1/1
   goldens** (sweep_slash_setup), THE PROGRAM'S 50TH AND FINAL ROW.
   One CAPTURE_WORLD_CHANNELS seed (`"sweep.slash_setup"` reusing
   #245's leaked-workspace machinery — the same channel id the
   `-advanced`/`-status` cases pin) is the flip's only code change;
   zero exemptions; ratchet quicksetup {events: 0, tables: 0,
   settings: 0} — the all-zero row (parity/parity.yml:880). Codex
   reviewed FOR REAL this time (comment 4950625506 on the actual
   final head `015569d712`: "Didn't find any major issues"; the
   cross-case-ordering question posted as comment 4950621154 — no
   phantom artifacts claimed, Q-0120-consistent).

## End counts (wave-8 END state = PROGRAM END state, CI-LOG-VERIFIED at main `7334083`, #246's merge)

- parity **50/50 PROGRAM ROWS PORTED** — 49 subsystem rows + the
  kernel coverage home; parity.yml at HEAD hand-verified: 50
  subsystems entries with 49 `ported` and only `_unmapped: pending`,
  kernel `status: ported`. THE PORT PROGRAM IS COMPLETE — no
  subsystem row is pending, no wall remains.
- gate **GREEN 365/365 across 50 ported** — main-push golden-parity
  run 29186950621 gate job 86634702696: "gate: GREEN — all 365
  golden(s) across 50 ported subsystem(s) replay clean" +
  "golden-parity gate: 50 ported / 1 pending" with the pending table
  reduced to a single line, _unmapped [106 goldens] +
  "check_parity_depth: OK — 50 subsystems (49 ported), kernel ported,
  471 goldens" (same job); integration 11 passed same job (the
  F-001/F-002 real-Postgres concurrency regressions INCLUDED).
- report **370/471 green, 471/471 replayable** — report job
  86634702704 same run: "green: 370/471 replayed cases match their
  golden" + "replayable: 471/471" + "ported: 50/51 subsystems" with
  setup 9/9 · quicksetup 1/1 green [ported] and EVERY ported row
  green in the per-subsystem table; `_unmapped 5/106 green [pending]`
  is the ONLY non-green line; "report: RED — 101 golden(s) not yet at
  parity (EXPECTED until the last subsystem flips ported)" —
  red-by-design, non-required; the 101 are all `_unmapped`.
- units **1722 passed / 8 skipped in CI** (ci run 29186950619 tests
  job 86634702742 — deps-free CI shape; local canonical ladders with
  deps differ by the standing guarded-import skip delta).
- corpus **471 = 465 imported + 6 minted** (unchanged — both flips
  rode imported/re-homed goldens, zero mints); `_unmapped` **107→106**
  at HEAD (wave movement: sweep_setup → setup at #245; hand-counted
  106 files in parity/goldens/_unmapped at HEAD).
- REMAINING parity work is ONE POOL: the `_unmapped` re-homes — 106
  files, 101 not yet green (5 already alias green through ported
  rows), mostly btd6-family sweeps over the PORTED btd6 row +
  deep-system mining strays + fishing gear surfaces + mixed
  singletons. All of it is attribution/re-home work toward a
  fully-green report job; none of it is porting.

## Traps confirmed / new intel

- **Re-evaluate old park claims against the current tree before
  honoring them**: trap 17's "no ruled twin for create_channel" was
  recorded true in wave 6 and FALSE by wave 8 — #242 had landed the
  twin + D-0077 in between. A parked wall's justification has a shelf
  life; the wave-8 planner re-derived the wall from source and found
  it already half-demolished.
- **The create-carrying golden lives in `_unmapped`**: when a row's
  slash goldens record zero channel calls (trap-17 shape), look for
  the create vocabulary in the `_unmapped` sweeps and re-home the
  carrier onto the row WITH the flip (#245 sweep_setup — the
  D-0077 §4 depth finding executed).
- **CAPTURE_WORLD_CHANNELS**: leaked gateway-cache channel state is
  seeded per case id off the runner map and cleared by
  `reset_case_state()` — the CAPTURE_WORLD_* family's third member
  (guild directory #125, weather #236, channels #245); never
  hand-patch harness state in domain code.
- **D-0065 create-BEFORE-DB needs no compensator** — declared shape
  confirmed in the merged tree; the allowlist stays EMPTY and the
  D-0077 handler stays reserved for the DB-first shape.
- **First domain caller of the channel-ops port** needs the
  `actions = active_actions()` receiver form — check_egress
  sanctions `actions` as a port receiver (tools/check_egress.py:52,
  #245); the S11 fence still bans `create_text_channel` by name
  outside adapters.
- Trap 25 honored: wrap-up seat ran no Postgres ladder; every count
  above is CI-log-verified at the merge sha.

## Verification

Merge shas verified against `git log origin/main` at `7334083` (setup
`32544d97eda69f29637170f7e81ff143fa7bc840`, quicksetup
`73340834a77b0098352a20e5e9fa489070e3f14f`); end counts
CI-LOG-VERIFIED at those shas (run/job ids per claim above);
parity.yml statuses re-read at HEAD (49 ported subsystem rows +
`_unmapped: pending` machine-counted; kernel: ported); `_unmapped`
106 / setup 9 / quicksetup 1 hand-counted on disk at HEAD; source
anchors re-verified at HEAD (CAPTURE_WORLD_CHANNELS at
sb/adapters/parity/runner.py:137 with the per-case reseed at :267,
`actions` in tools/check_egress.py:52, migration
0037_setup_session.sql on disk, `_ALLOWLIST = {}` at
tests/unit/workflow/test_compensator_invariant.py:23, the D-0065
contrast clause + `setup.compensate_create_channel` in
sb/domain/setup/ops.py, zero setup/quicksetup depth.exemptions rows,
quicksetup's all-zero ratchet row, the setup-delegate/undelegate
skips in parity/goldens/_sweep_skips.json); `python3 bootstrap.py
check --strict` green at the wrap-up head.

## 💡 Session idea

The parity program's ONE remaining lane is now unambiguous: the
`_unmapped` re-home sweep (106 goldens, 101 not yet green). The wave-7
histogram minus sweep_setup says the bulk is btd6-family sweeps over
the PORTED btd6 row (flip-sized re-homes per the #193 law — the btd6
row already replays 103/103 green, so most re-homes should be pure
`git mv` + parity.yml citation moves), plus deep-system mining strays
(the skill/stash/vault/workshop `_pending` handler families visible in
the report log), fishing gear surfaces (rodrecipes/sail/tidepool), and
mixed singletons. A dedicated re-home wave — or two, split
btd6-family vs games-family — is the shortest path to a fully-green
report job, which would retire the LAST standing red in CI and turn
`report` into a required check. Sequencing note stands from wave 7:
land btd6 re-homes only when the band-7 successor lane's btd6 slices
are idle, since both touch parity/goldens/btd6/.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-parity-flips-wave7.md`, this lane's
direct predecessor.) Its end-state map was exactly right: "NOTHING
ELSE IS PENDING — every real subsystem row is ported; both remaining
walls are owner-shaped" — and its 💡 idea correctly identified the
`_unmapped` pool as the program's last agent-shaped lane. What it
called wrong, instructively: it filed setup and quicksetup as
"owner-shaped" walls that would stay parked "short of owner action."
Wave 8 falsified that within 24 hours — not because the wave-7 writer
misread the tree, but because the tree MOVED: the #242 enabler landed
from a different lane the same day, and the wall's two blockers
(no capture twin, no ruled compensator class) dissolved without any
owner action. The correction is now trap 37: park claims cite the
tree at park time and must be re-derived at pick-up time, never
honored on faith. Its trap doctrine otherwise held perfectly: the
CAPTURE_WORLD_* seeding lane it documented for weather (#236) was the
exact mechanism that resolved trap 17 (channels, #245); its
"price by golden count TIMES substrate distance" advice priced wave 8
correctly (setup carried the substrate — migration 0037, ops/plan/
service/store — while quicksetup was a one-seed afternoon).
