"""RPS rules engine — pure functions, ported VERBATIM from the shipped
``cogs/rps_tournament/rules.py`` (four game modes; alias and
win-condition tables are closed data)."""

from __future__ import annotations

__all__ = [
    "GAME_MODES",
    "MOVE_ALIASES",
    "WIN_CONDITIONS",
    "determine_winner",
    "normalize_move",
]

MOVE_ALIASES: dict[str, list[str]] = {
    "rock": ["rock", "stone", "pebble", "boulder", "🪨", "🤜", "✊"],
    "paper": ["paper", "sheet", "page", "📄", "📰", "✋"],
    "scissors": ["scissors", "shears", "✂️", "✌️"],
    "lizard": ["lizard", "🦎"],
    "spock": ["spock", "🖖"],
    "pawn": ["pawn", "♟️"],
    "knight": ["knight", "horse", "♞"],
    "queen": ["queen", "♛"],
    "fire": ["fire", "flame", "🔥"],
    "water": ["water", "💧", "🌊"],
    "grass": ["grass", "leaf", "🌿", "🍃"],
}

GAME_MODES: dict[str, list[str]] = {
    "classic": ["rock", "paper", "scissors"],
    "lizard_spock": ["rock", "paper", "scissors", "lizard", "spock"],
    "chess": ["pawn", "knight", "queen"],
    "elemental": ["fire", "water", "grass"],
}

WIN_CONDITIONS: dict[str, dict[str, list[str]]] = {
    "classic": {"rock": ["scissors"], "paper": ["rock"],
                "scissors": ["paper"]},
    "lizard_spock": {
        "rock": ["scissors", "lizard"],
        "paper": ["rock", "spock"],
        "scissors": ["paper", "lizard"],
        "lizard": ["spock", "paper"],
        "spock": ["scissors", "rock"],
    },
    "chess": {"pawn": ["knight"], "knight": ["queen"], "queen": ["pawn"]},
    "elemental": {"fire": ["grass"], "water": ["fire"],
                  "grass": ["water"]},
}


def normalize_move(input_move: str, mode: str) -> str | None:
    """Resolve an alias to the canonical move under *mode*, or None."""
    for move, aliases in MOVE_ALIASES.items():
        if input_move in aliases and move in GAME_MODES[mode]:
            return move
    return None


def determine_winner(move1: str, move2: str, mode: str) -> int:
    """0 (tie), 1 (move1 wins), or 2 (move2 wins) under *mode*. Assumes
    canonical moves (post-normalize_move)."""
    if move1 == move2:
        return 0
    if move2 in WIN_CONDITIONS[mode][move1]:
        return 1
    return 2
