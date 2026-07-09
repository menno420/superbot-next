"""Deathmatch duel core (band 6) — the shipped ``_Duel`` +
``pick_bot_action`` made HEADLESS (player ids instead of Members;
injectable rng). Constants verbatim: 100 base HP, 15 attack, 30 crit
(10%), defend halves the next hit once, armor is flat reduction floored
at 1.

Equipment tilt (``equipment.EffectiveStats``) rides the deferred
equipment/wear system (the D-0043 mining successor port) — every
fighter duels at the shipped all-zero baseline exactly like a bare
shipped fighter."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

__all__ = [
    "BASE_ATTACK_DAMAGE",
    "BASE_CRIT_DAMAGE",
    "BASE_HP",
    "DuelState",
    "pick_bot_action",
    "set_rng_for_tests",
]

BASE_HP = 100
BASE_ATTACK_DAMAGE = 15
BASE_CRIT_DAMAGE = 30

_rng = random.Random()


def set_rng_for_tests(rng) -> None:
    global _rng
    _rng = rng


@dataclass
class DuelState:
    """One duel: hp / turn / one-shot defense flags, keyed by user id."""

    player1: int
    player2: int
    player1_hp: int = BASE_HP
    player2_hp: int = BASE_HP
    player1_max_hp: int = BASE_HP
    player2_max_hp: int = BASE_HP
    turn: int = 0                       # user id; 0 => player1 opens
    is_over: bool = False
    defense: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.turn:
            self.turn = self.player1
        self.defense.setdefault(self.player1, False)
        self.defense.setdefault(self.player2, False)

    def attack(self, attacker_id: int, defender_id: int) -> tuple[int, bool]:
        critical = _rng.random() < 0.1
        damage = BASE_CRIT_DAMAGE if critical else BASE_ATTACK_DAMAGE
        if self.defense.get(defender_id, False):
            damage = damage // 2
            self.defense[defender_id] = False
        # Armor (equipment defense) is flat reduction floored at 1 — at
        # the zero-equipment baseline it is a no-op; the floor stays so
        # the equipment port slots in without touching this method.
        damage = max(1, damage)
        if defender_id == self.player1:
            self.player1_hp -= damage
        else:
            self.player2_hp -= damage
        return damage, critical

    def defend(self, player_id: int) -> None:
        self.defense[player_id] = True

    def hp_of(self, player_id: int) -> int:
        return (self.player1_hp if player_id == self.player1
                else self.player2_hp)

    def opponent_of(self, player_id: int) -> int:
        return self.player2 if player_id == self.player1 else self.player1

    def to_state(self) -> dict:
        return {"p1": self.player1, "p2": self.player2,
                "p1_hp": self.player1_hp, "p2_hp": self.player2_hp,
                "p1_max": self.player1_max_hp, "p2_max": self.player2_max_hp,
                "turn": self.turn, "is_over": self.is_over,
                "defense": {str(k): v for k, v in self.defense.items()}}

    @classmethod
    def from_state(cls, state: dict) -> "DuelState":
        duel = cls(player1=int(state["p1"]), player2=int(state["p2"]),
                   player1_hp=int(state["p1_hp"]),
                   player2_hp=int(state["p2_hp"]),
                   player1_max_hp=int(state.get("p1_max", BASE_HP)),
                   player2_max_hp=int(state.get("p2_max", BASE_HP)),
                   turn=int(state["turn"]),
                   is_over=bool(state.get("is_over", False)))
        for key, value in (state.get("defense") or {}).items():
            duel.defense[int(key)] = bool(value)
        return duel


def pick_bot_action(bot_hp: int) -> str:
    """Bot AI v1 (shipped verbatim): 70% attack / 30% defend at full
    health; biases defensive as HP drops below 50%."""
    choices: tuple[str, ...]
    if bot_hp < 25:
        choices = ("attack", "defend", "defend")
    elif bot_hp < 50:
        choices = ("attack", "attack", "defend")
    else:
        choices = ("attack", "attack", "attack", "defend")
    return _rng.choice(choices)
