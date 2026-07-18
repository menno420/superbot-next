# Claim — blackjack-remaining-surface

- `claude/blackjack-hub-solo-table` · **item 5 of
  `docs/ideas/blackjack-remaining-surface-2026-07-10.md` — the hub-button solo
  flow: `blackjack.hub`'s Solo Free Play / Solo Bet actions route the bare
  `blackjack.solo_start` op (RESULT_CARD text / modal) instead of OPENING THE
  INTERACTIVE TABLE VIEW (the shipped `!blackjack` path). Unify both onto a new
  `blackjack.hub_solo` handler that deals through `solo_start` and opens
  `blackjack.table` on the interaction surface (the `casino.poker_open`
  command+button precedent).** · files: `sb/domain/blackjack/handlers.py`,
  `sb/domain/blackjack/panels.py`, tests under `tests/unit/band6/` · 2026-07-18
