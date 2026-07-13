# 2026-07-13 — farm leaderboard parity trim + `top_farmers` filter (ORDER 031 phase 2)

> **Status:** `in-progress`

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

_(pending)_
