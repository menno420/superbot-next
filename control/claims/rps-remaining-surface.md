# Claim — rps-remaining-surface

- `claude/rps-solo-edit-in-place` · **item 2 of
  `docs/ideas/rps-tournament-remaining-surface-2026-07-10.md` — the solo
  result view edit-in-place: the shipped `views/rps/solo_play._RpsView`
  EDITED the picker message into the result embed; v1's quickplay move
  buttons dispatch `rps.solo_play` directly with a `RESULT_CARD` and answer
  with a `followup_send` TEXT line instead of editing the picker message in
  place. Route the quickplay move buttons through a new `rps.solo_click`
  handler that runs the audited op and refreshes the session view IN PLACE
  (the shipped safe_defer + safe_edit loop — the blackjack `table_click`
  precedent, sb/domain/blackjack), terminal expires the session with the
  move buttons disabled (the PvP terminal's ledgered "hub re-entry stays one
  !rps away" posture in place of the shipped play-again button).** · files:
  `sb/domain/rps/handlers.py`, `sb/domain/rps/panels.py`,
  `tests/unit/band6/test_band6_rps_quickplay.py`,
  `parity/goldens/rps_tournament/rps_tournament_quickplay_bet_settle_write.json`
  · 2026-07-18
