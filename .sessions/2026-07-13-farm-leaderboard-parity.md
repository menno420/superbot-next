# 2026-07-13 — farm leaderboard parity trim + `top_farmers` filter (ORDER 031 phase 2)

> **Status:** `complete`

- **📊 Model:** `fable-5` · games lane, farm slice · mandate:
  control/claims/order-031-games-casino.md (PR #423); executes ranked items
  1 + 2 of docs/review/games-finalization-2026-07-13.md (farm section).

## Scope

One small parity PR, two S items from the farm end-to-end review — both
reported as UNPINNED byte drifts (no golden or test pins the old bytes;
re-verified this session by grep over parity/goldens/ + tests/):

1. **Farm leaderboard provider parity trim** — align
   sb/domain/games/providers.py farm registration with the oracle
   `FarmProvider` (disbot/services/rank_providers.py:331-337):
   `display_title="🐔 Chicken Farm Leaderboard"`,
   `empty_hint="No farms yet. Use \`!farm\` to start your coop."`,
   `card_theme="harvest"` (RankProvider supports it,
   sb/domain/community/rank_providers.py:51; deathmatch precedent).
2. **`top_farmers` `chickens > 0` filter** — restore the oracle WHERE
   clause (disbot/utils/db/games/farm.py:89-91) in
   sb/domain/farm/store.py `top_farmers`.

Definition of done: `python3 -m pytest tests/ -q` green, golden gate
GREEN, `python3 bootstrap.py check --strict` exit 0 (minus this card's
own born-red hold), PR opened READY on menno420/superbot-next.

## ⟲ previous-session review

- Built on docs/review/games-finalization-2026-07-13.md (review-idle seat,
  same order): its farm §6 ranked list named items 1+2 "TOP UNBLOCKED,
  same-file-family, one small parity PR" — this session is exactly that
  slice, nothing more. Collision re-scan: control/claims/
  curation-night-night-3 mints farm K7-lane goldens (collect/buy/upgrade)
  — different surface (no leaderboard/top_farmers bytes), no overlap.

## 💡 Session idea

The review's farm item 3 (inline level-up note on collect) is the next
smallest farm parity step, but it touches the shared games result-card
lane — a claim check before starting is mandatory, not optional.

## Close-out

Both items landed oracle-verbatim in `f2183bf` (providers.py farm
registration + store.py `top_farmers` WHERE clause; SQL string
byte-identical to the oracle after concatenation), then origin/main merged
in at `519a070` (brings the weather-golden seed fix 7b0a661 / PR #448).
Verification: `python3 -m pytest tests/ -q` → 2990 passed, 2 skipped;
`python3 bootstrap.py check --strict` → "all checks passed", exit 0.
Local full-gate runs were RED with **randomized cross-case db_delta
bleed** — proven environmental, not this branch: concurrent sibling-lane
replays share the single local Postgres `superbot` database (two distinct
backends captured issuing the harness's full-corpus TRUNCATE
simultaneously and deadlocking, pg log 01:19 UTC; the gate loop itself is
sequential — tools/run_golden_parity.py:101, parity/harness/dbsnap.py:39-45
— so a second truncater can only be a second process). This branch's own
rendered surfaces (`sweep.leaderboard`, `sweep.farm`) replayed GREEN in
every run and no diff in any run contains a farm/leaderboard byte.
Coordinator decision (decide-and-flag): push and let the isolated CI gate
arbitrate.

**Guard recipe (deferred):** local gate runs need an exclusive-DB fence —
e.g. `pg_advisory_lock` taken by `sb.adapters.parity.boot.Harness.start()`
(or a flock in tools/run_golden_parity.py) so two lane workers serialize
instead of corrupting each other's db_delta; test target: two concurrent
`run_replay` invocations, second blocks until first closes.
