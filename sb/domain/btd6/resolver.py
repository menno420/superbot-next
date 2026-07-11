"""Deterministic NL → structured intent resolver for BTD6 — the focused
port of shipped ``services/btd6_resolver_service.py`` @7f7628e1 over the
entity families the grounding layer consumes (towers / heroes / bloons /
bosses / maps / modes + round numbers). No AI, no DB; aliases come from
the validated dataset.

Shipped matching semantics carried: multi-word aliases match as
substrings; single-word aliases match whole-token, with the naive-plural
fold (``alias + "s"`` — the BUG-0003 "despos" fix). Maps and modes ride
the SAME alias-map discipline (id + canonical + aliases, the shipped
``for game_map in dataset.maps`` / ``for mode in dataset.modes`` loops)
— including the shipped quirk that common-word mode names ("hard",
"reverse", "standard") token-match inside ordinary sentences. CT relics
/ live NK entity vocabulary ride the deep-reference successor port
(D-0046); in the oracle, matched maps/modes ALSO feed the ``btd6_facts``
DB grounding pass — that pass is the same D-0046 successor, so here they
ground nothing and only drive answer/introspection surfaces."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sb.domain.btd6 import dataset

__all__ = ["ResolvedIntent", "resolve"]

_ROUND_PATTERNS = (
    re.compile(r"\bround\s+(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\br\s*(\d{1,3})\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class ResolvedIntent:
    """Structured view of what the user appears to be asking about."""

    raw_text: str
    confidence: float
    towers: tuple[dataset.TowerEntry, ...] = ()
    heroes: tuple[dataset.HeroEntry, ...] = ()
    maps: tuple[dataset.MapEntry, ...] = ()
    modes: tuple[dataset.ModeEntry, ...] = ()
    bloons: tuple[dataset.BloonEntry, ...] = ()
    bosses: tuple[dataset.BossEntry, ...] = ()
    candidate_round_numbers: tuple[int, ...] = ()


def _word_iter(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def _match_terms(text: str, name_aliases: dict[str, str]) -> set[str]:
    """Matching ids: multi-word aliases as substrings, single words on
    token boundaries with the +s plural fold (shipped)."""
    text_lower = text.lower()
    tokens = set(_word_iter(text))
    found: set[str] = set()
    for alias, owner_id in name_aliases.items():
        hit = (
            (alias in text_lower)
            if " " in alias
            else (alias in tokens or f"{alias}s" in tokens)
        )
        if hit:
            found.add(owner_id)
    return found


def _alias_map(entries) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in entries:
        out[entry.id] = entry.id
        out[entry.canonical.lower()] = entry.id
        for alias in entry.aliases:
            out[alias.lower()] = entry.id
    return out


def _boss_alias_map() -> dict[str, str]:
    # Boss canonicals are distinctive words; bosses.json carries no alias
    # column, so canonical + id only (shipped name-index discipline).
    out: dict[str, str] = {}
    for boss in dataset.bosses():
        out[boss.id] = boss.id
        out[boss.canonical.lower()] = boss.id
    return out


def resolve(text: str) -> ResolvedIntent:
    """Resolve free-form ``text`` into a :class:`ResolvedIntent`."""
    if not text or not text.strip():
        return ResolvedIntent(raw_text=text, confidence=0.0)

    tower_ids = _match_terms(text, _alias_map(dataset.towers()))
    hero_ids = _match_terms(text, _alias_map(dataset.heroes()))
    map_ids = _match_terms(text, _alias_map(dataset.maps()))
    mode_ids = _match_terms(text, _alias_map(dataset.modes()))
    bloon_ids = _match_terms(text, _alias_map(dataset.bloons()))
    boss_ids = _match_terms(text, _boss_alias_map())

    candidate_rounds: list[int] = []
    for pattern in _ROUND_PATTERNS:
        for match in pattern.finditer(text):
            try:
                value = int(match.group(1))
            except ValueError:
                continue
            if 1 <= value <= 200 and value not in candidate_rounds:
                candidate_rounds.append(value)

    matched_count = (
        len(tower_ids)
        + len(hero_ids)
        + len(map_ids)
        + len(mode_ids)
        + len(bloon_ids)
        + len(boss_ids)
        + len(candidate_rounds)
    )
    confidence = min(1.0, matched_count / 3.0) if matched_count else 0.0

    return ResolvedIntent(
        raw_text=text,
        confidence=confidence,
        towers=tuple(t for t in dataset.towers() if t.id in tower_ids),
        heroes=tuple(h for h in dataset.heroes() if h.id in hero_ids),
        maps=tuple(m for m in dataset.maps() if m.id in map_ids),
        modes=tuple(m for m in dataset.modes() if m.id in mode_ids),
        bloons=tuple(b for b in dataset.bloons() if b.id in bloon_ids),
        bosses=tuple(b for b in dataset.bosses() if b.id in boss_ids),
        candidate_round_numbers=tuple(candidate_rounds),
    )
