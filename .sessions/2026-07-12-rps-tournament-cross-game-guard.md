# 2026-07-12 — RPS tournament cross-game guard (dropped-in-port parity regression)

> **Status:** `in-progress`

- **📊 Model:** Claude Opus 4.8 · high · parity-regression bug fix, red-then-green (tournament edge-case audit)

## Scope

One bounded slice: restore the shipped cross-game tournament guard that
the RPS port dropped. `sb/domain/rps/handlers.py::register_route` writes
the SHARED `active_tournament` `guild_settings` flag row but — unlike the
blackjack port (`sb/domain/blackjack/handlers.py::tournament_open_route`,
which carries the `get_active` guard "verbatim") — never consulted that
flag. `!rpsregister` therefore opened on top of a live *blackjack*
tournament and clobbered its `active_tournament` value `blackjack → rps`.

## The bug (audit finding)

The champion payout leg keys its settle-once check-and-set on the
flag-row DELETE (`sb/domain/rps/ops.py::_record_tournament_payout` /
blackjack twin: `cleared = clear_active(...); if not cleared: return
paid=False` BEFORE `payout_tournament_in_txn`). Because both games share
ONE flag row per guild, two concurrent cross-game tournaments race on it:
whichever settles SECOND finds `clear_active()==0`, returns `paid=False`,
and never runs the paid settle — its champion is NOT paid and its escrow
rows are left stranded (recovered/refunded only at the next boot escrow
sweep). Reachable through the real command path: blackjack refuses to
open when another game's flag is set, but RPS did not, so
`!bjtournament` → `!rpsregister` → both live → the loser-to-settle is
stranded.

## Oracle semantics (Step 1)

Reconstructed via `mcp__github__search_code` over `menno420/superbot`
(direct file reads DENIED for this seat; fragments at indexed ref
`d5e815c2ce5ab5…`): `disbot/cogs/rps_tournament_cog.py` registration
open guards the shared flag BEFORE opening —

```python
existing = await tournament_state_service.get_active(ctx.guild.id)
if existing:
    await ctx.send(
        f"A **{existing}** tournament is already active in this server.",
    )
    return
```

and `disbot/services/tournament_state_service.py` documents the exact
invariant the port violated: *"Callers should compare against the kind
they intend to start (e.g. `if existing == "rps": …`) so a foreign kind
doesn't get clobbered by accident."* The blackjack cog carries the same
guard; both use the copy verbatim. The superbot-next blackjack port
already ships this as `if existing and existing != "blackjack":`
(reclaims a stale own flag — the boot flag-sweep posture). Pinned:
refuse-with-copy on a FOREIGN flag, reclaim a stale OWN flag.

## Delivered

- `sb/domain/rps/handlers.py` — `register_route` now reads
  `tournament_flag.get_active(gid)` after its in-memory guards and, when a
  FOREIGN game's flag is set, refuses with the oracle copy verbatim
  (`f"A **{existing}** tournament is already active in this server."`); a
  stale OWN `"rps"` flag stays reclaimable (`!= "rps"`), mirroring the
  blackjack port's guard shape exactly.
- `tests/unit/band6/test_band6_rps_tournament.py` —
  `test_rpsregister_refuses_when_a_foreign_tournament_is_active` (RED at
  HEAD `d3f3cb4`: `!rpsregister` clobbered the `"blackjack"` flag and
  opened; GREEN with the fix — refused, foreign flag untouched, no rps
  state, no money moved) + `test_rpsregister_reclaims_a_stale_own_flag`
  (pins the `!= "rps"` reclaim branch — a stale own flag still opens).

## Evidence

- `python3 -m pytest tests/` — 1744 passed / 5 skipped (real Postgres,
  throwaway local instance on :5433).
- `python3 tools/run_golden_parity.py --gate` — GREEN, 425/425 goldens
  across 51 ported subsystems replay clean (ZERO golden movement — the
  guard only fires on a pre-existing foreign flag, never in the golden
  replays).
- `python3 bootstrap.py check --strict` — all checks passed.

## 💡 Session idea

The settle-once check-and-set was built on a flag row that is SHARED
across games, but the port only defended one of the two write paths — a
guard that's correct only if BOTH openers respect it. Worth a checker:
any state used as a per-owner CAS token whose key is coarser than the
owner (here guild-scoped, but two owners = two games) should assert every
writer of that key gates on it. The blackjack/rps asymmetry would have
been a one-line lint.
