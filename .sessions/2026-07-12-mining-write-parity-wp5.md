# 2026-07-12 — deep-mining WRITE-PARITY lane — WP-5 skill-spend PORT + write golden

> **Status:** complete (WP-5 DELIVERED — the oracle `skill_service.allocate`
> ported verbatim onto the audited `mining.skill -> record_skill` seam,
> `skill_route` flipped, two skill-spend write goldens minted byte-identical,
> `player_skills` exemption retired (ratchet mining `{events:4, tables:15->16}`),
> a `lock_skill_slot` advisory fence + a two-txn over-allocation concurrency
> regression added (RED→GREEN observed); gate GREEN (477 ported goldens) + all
> checkers green. PR #335, stacked on #317.)

- **📊 Model:** opus-4.8 · high · parity/golden-minting (Q-0194)

## WP-5 scope (skills — PORT + MINT)

Stacked on WP-3 (#317, branch `mining-write-parity-wp3`). At HEAD the remaining
`depth.exemptions.mining` `guard-only-capture` rows are `player_skills` (mine)
and `mining_structures` (WP-6). WP-5 retires **`player_skills`**.

The `!skill <branch>` argful point-spend was an honest D-0043 pending terminal
(`skill_route` returned the BLOCKED successor copy; NO `record_skill` leg). This
slice PORTS the oracle `services/skill_service.py::allocate` faithfully:

- New `@workflow("mining.record_skill")` leg (`ops.py`) + `mining.skill`
  CompoundOpSpec (audit_verb `mining_skill_allocated`) — resolves + normalizes
  the branch, validates amount, checks the per-branch cap (10) and the shared
  available-points budget (`min(level, SOFT_TOTAL_CAP=20) − total_spent`, level
  from the game-XP curve), then `set_skill_points` upserts `player_skills` — all
  in ONE advisory-fenced txn. Constants/copy VERBATIM from oracle.
- `skill_route` flipped: the argful branch runs the audited op and prefixes the
  invoker mention on BOTH success and business-refusal (the oracle
  `ctx.send(f"{mention} {result.message}")` shape). Bare `!skill` guard byte
  unchanged (goldens/mining/sweep_skill).

## MONEY-RACE — skill-point over-allocation fence

The spend is a read-then-settle over the SHARED available-points budget: two
concurrent `!skill <a>` / `!skill <b>` into different branches both read
`total_spent=0`, both pass `n <= avail`, both commit → the pool is overspent
(the classic cross-branch budget race; `set_skill_points` writes an absolute
value so a same-branch race is a lost update). Fenced with a new
`lock_skill_slot` `pg_advisory_xact_lock` (the `lock_vault_upgrade_slot`
precedent) acquired BEFORE the alloc/level read, plus a two-transaction Postgres
regression proving it serializes (RED without lock, GREEN with).

## Goldens (capture_case, byte-stable)

- `mining.skill_write` — `!skill mining` (game-XP fixture seeds level so
  `avail >= 1`) → `player_skills` upsert (added row) → RETIRES `player_skills`.
- `mining.skill_bad_branch` — `!skill <nonsense>` → the bad-branch refusal
  (mention-prefixed), a pure read (no `db_delta` on player_skills) — the key
  error-branch pin.

## Parked honest-pending (with reasons)

- **respec** — no command form in the oracle (`skill_service.respec` is reached
  ONLY via the skills-panel button); its coin-sink ingress rides the deferred
  skills-panel port. `player_skills` is already retired by the allocate spend
  (the added row covers the table), so respec is not needed for the exemption.
- **title equip** — select-driven per scope PART C (session-minted select ids
  are not reconstructable). Stays honest D-0043 pending.

## 💡 Session idea

The PORT slices (WP-5/6) are where "constants/copy VERBATIM" earns its keep: the
whole value of a write golden is that it freezes the handler as the oracle's own
contract, so a single invented word in a refusal string silently forks the two
bots while every gate stays green (the golden would just pin the fork). The
durable discipline is **fetch the oracle function and diff every message byte
before trusting a ported leg** — here `skill_service.allocate`'s four faces
(bad-branch / non-positive / per-branch-cap / insufficient-points) plus the
`mining_cog.py` mention-prefix shape were confirmed byte-identical against the
oracle at `c65750e3` before the capture, and the two error faces the golden
can't reach (cap + budget) got a dedicated leg test asserting the exact copy —
so the contract is pinned end to end, not just on the one path a golden happens
to drive. A follow-up worth a checker: a "verbatim-copy audit" that flags a
ported leg whose user-facing strings have no matching oracle literal, so a port
that paraphrases is caught at review, not by a play-tester months later.

## ⟲ Previous-session review

WP-3 (#317) landed 5 depth/world/workshop write goldens green, retired
`mining_world` + `mining_gear_wear`, ratchet mining `{events:4, tables:13→15}`,
gate 470→475, plus two `lock_workshop_slot` concurrency regressions. Its landing
report (`scratchpad/wp3-landing-report.md`) is the mint ground-truth: goldens
minted via `sb/adapters/parity/runner.capture_case` (the NEW-bot path). This
session stacks WP-5 on that branch and follows the same procedure, adding the
real PORT work (leg + route flip) ahead of the capture.
