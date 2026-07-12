# 2026-07-12 — rps tournament "already registered" copy → oracle verbatim

> **Status:** `complete`

- **📊 Model:** Claude Opus 4.8 · high · parity copy-drift fix, red-then-green

## Scope

One bounded slice: fix the punctuation drift PR #223 ledgered out of scope —
`sb/domain/rps/tournament.py::register_player`'s in-memory duplicate-entry
guard refused with `"You're already registered."` (period) where the oracle
ends with `!`. Golden-uncovered refusal path (no `parity/goldens/rps_tournament/`
golden pins it), so the drift was invisible to the gate.

## Oracle (verbatim)

`menno420/superbot@main` (HEAD `b7d017d`) —
`disbot/views/rps/registration.py:49`, the Join-button ephemeral reply:
`"You're already registered!"` (exclamation). Cross-checked against
`disbot/cogs/rps_tournament_cog.py::try_register_player` (guards the roster
ahead of the fee block, returns `False`) and the games-layer twin already at
the oracle byte-form (`sb/domain/games/wager.py::AlreadyEnteredError` default =
`"You're already registered!"`). The drift lived only at the rps in-memory
guard.

## Delivered

- `sb/domain/rps/tournament.py` — the duplicate guard now returns the oracle
  byte-form `"You're already registered!"` (with a comment citing the oracle
  view + the wager.py twin). Smallest faithful change: inline, matching the
  file's existing inline-copy pattern (`"Registration is not active."`, the
  fee-gate copy) — rps has no copy/constants module.
- `tests/unit/band6/test_band6_rps_tournament.py` — new
  `test_duplicate_registration_refusal_is_oracle_verbatim` drives
  `register_player` into the duplicate branch and asserts the exact bytes;
  the walking-skeleton wire assertion tightened from a `"already registered"`
  substring to the full `"You're already registered!"` so the wire path is
  pinned too.

## Evidence

- `python3 -m pytest tests/` — 1728 passed / 8 skipped (includes the new test).
- `python3 tools/run_golden_parity.py --gate` — GREEN, all 412 goldens across
  51 ported subsystems replay clean (zero golden movement — no golden covers
  this refusal).
- `python3 bootstrap.py check --strict` — all checks passed.

## 💡 Session idea

The #223 close-out's suggested sweep (grep new-tree user-copy literals against
oracle `search_code` fragments for punctuation-level drift in golden-uncovered
refusal paths) paid off here on the first pull. Worth a standing lint: for
every domain refusal string not pinned by a golden, require a unit test that
asserts the exact bytes — golden coverage is the only thing that made the OTHER
rps copy drift-proof, so uncovered copy needs a cheap byte-pin substitute.

## ⟲ Previous-session review

PR #223 (`2026-07-12-tournament-entry-race-fix`) ledgered this exact drift as a
one-line out-of-scope note ("the new tree's in-memory guard copy at
`sb/domain/rps/tournament.py:153` uses a period, oracle uses `!`") AND named
the fix shape in its Session idea. That was a complete work order: exact
file/line, the oracle byte, and the enforcement gap (golden-uncovered). This
slice needed zero discovery beyond re-confirming the oracle bytes at HEAD.
The one under-spec: it didn't say whether to route both sites through a shared
constant — resolved here as "no", since the games-layer twin already matches
the oracle and rps uses inline copy throughout (a shared constant would be a
larger, non-faithful refactor).
