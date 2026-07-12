# Claim

- `fix/rps-tournament-cross-game-guard` · **RPS cross-game tournament guard** — restore the dropped-in-port `get_active` refusal so `!rpsregister` cannot clobber a live blackjack tournament's shared `active_tournament` flag (stranded-pot bug) · `sb/domain/rps/handlers.py` + `tests/unit/band6/test_band6_rps_tournament.py` · 2026-07-12
