# 2026-07-15 — band-5 partial-honesty tail (speaking compensators + proof after-keys)

> **Status:** `complete`

- **📊 Model:** `fable-5` · resumed band-5 testing seat (the 2026-07-09
  session that shipped #94/#95) · mandate: land the remainder of its
  mid-flight fixes that current main still lacks, then close the band-5
  loop (report cross-check, handoff, heartbeat).

## Scope

The band-5 live-drive ledger (testing-report band-5 row) recorded 3
live-leg bugs; PR #111 fixed them. Two adjacent defects remained on
main at `ad75bbc`, verified live before building:

1. **Compensated PARTIAL renders the withdrawn success copy** — since
   D-0062 the proof record legs speak; the engine keeps
   `result.user_message` when an EFFECT leg fails and its compensator
   withdraws the row, so `grant_access` PARTIAL echoed
   "<@w> has access … auto-unlocks at …" (observed verbatim in the
   band-5 session's own live drive, scratchpad `live-band5.log`,
   `!timedprize` with the then-unarmed port). Fix: a compensator that
   returns `LegOutcome.user_message` OWNS the op's copy (engine
   replaces the success lines); silent compensators change nothing —
   the D-0058 warn partial ack survives by construction.
2. **Proof success acks read a `"record"` after-key that never
   existed** — `_rollup` keys by `StepResult.target_name`
   (`record_lock`/`record_unlock`), so armed-port grants rendered
   "granted access to <#0>!" / "auto-unlocks at ?" — the #111 ack-copy
   class, left behind in proof_channel/handlers.py (replay-invisible:
   no success-grant golden).

## ⟲ Previous-session review

This seat's own #95 (D-0062) introduced the leg acks that made defect 1
expressible — the band-4 handoff's silent-success audit was right to
arm the copy, wrong to leave the PARTIAL path unexamined; the live
drive caught it the same session, but the session ended before the fix
landed, and the 2026-07-10 live-drive session's ledger row (correctly)
recorded only what it re-observed. Lesson carried: when a leg gains a
voice, audit every outcome path that echoes `result.user_message`, not
just SUCCESS — and land the fix in the same PR as the voice.

## 💡 Session idea

The `"record"` after-key class has now bitten twice (#111 role, this
proof tail) because `(result.after or {}).get("<leg name>")` is
stringly and unchecked. A cheap checker advisory — flag any
`result.after.get("X")` whose X matches no `StepResult(_, "X", …)`
target_name in the same domain — would make the class unwritable, the
compensator-invariant way.

## Close-out

Landed as PR #491 (squash) — commits: session card + claim born first,
then the fix slice (engine seam + speaking compensators for
`proof_channel.compensate_lock`/`compensate_unlock`/
`role.compensate_grant_temp` + the three proof after-key reads +
D-0091 + `tests/unit/band5/test_band5_partial_honesty.py`, 5 tests).
Verified: full suite 3119 passed / 16 skipped; golden gate GREEN
locally (502 goldens / 50 ported subsystems — compensator paths fire
only on EFFECT refusal, which no golden captures); 19-checker fleet +
`bootstrap.py check --strict` green; guard-fires telemetry delta
committed. Band-5 close-out (report cross-check, band5-handoff.md,
heartbeat) continued in this session after the PR.

Guard recipe (deferred): the session-idea checker above — anchor
`_rollup` (`sb/kernel/workflow/engine.py`) vs `result.after.get(`
call sites in `sb/domain/*/handlers.py`; test target
`tests/unit/band5/test_band5_partial_honesty.py::test_proof_success_acks_read_the_leg_after`.
