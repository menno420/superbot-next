"""BTD6 damage-type & status-effect INTERACTION grounding — shipped
``services/btd6_interaction_service.py`` @7f7628e1 VERBATIM (the single
most error-prone BTD6 topic: the model invents interaction rules — the
live "Lead resists glue" hallucination — unless the wiki-verified rule
from ``damage_types.json`` is grounded explicitly).

Read-only, no DB, no network."""

from __future__ import annotations

import re
import threading
from typing import Any

from sb.domain.btd6 import dataset

_DATA_FILE = "damage_types.json"
_SOURCE = "BTD6 damage-type interaction data (wiki-verified)"

_cache_lock = threading.Lock()
_CACHE: dict[str, Any] | None = None

# Most facts a single interaction question should ground.
_MAX_FACTS = 6

# An interaction-question cue (genuine VERBS only — shipped curation).
_INTERACTION_CUE_RE = re.compile(
    r"\b(?:pop|pops|popped|popping|deal|deals|dealt|handle|handles|counter|"
    r"counters|work|works|working|affect|affects|hit|hits|immune|immunit|"
    r"resist|resists|resistant|resistance|weak|beat|beats|stop|stops|slow|"
    r"slows|knock|able\s+to|against|vs|versus|"
    r"good\s+(?:against|vs|into)|effective|useless|bypass)\b",
    re.I,
)

# Property/bloon match tokens for the pop_guide entries (kept here, not in
# the JSON, so the data file stays a clean knowledge table).
_POP_GUIDE_TOKENS: dict[str, tuple[str, ...]] = {
    "lead": ("lead", "leads", "lead bloon", "lead bloons"),
    "black": ("black", "blacks", "black bloon", "black bloons"),
    "white": ("white", "whites", "white bloon", "white bloons"),
    "purple": ("purple", "purples", "purple bloon", "purple bloons"),
    "zebra": ("zebra", "zebras", "zebra bloon", "zebra bloons"),
    "camo": ("camo", "camos", "camo bloon", "camo bloons", "camouflage"),
    "frozen": ("frozen", "frozen bloon", "frozen bloons"),
    "moab_class": (
        "moab-class",
        "moab class",
        "moabclass",
        "moab",
        "moabs",
        "blimp",
        "blimps",
    ),
    "ddt": ("ddt", "ddts", "dark dirigible titan"),
}


def _load() -> dict[str, Any]:
    global _CACHE
    with _cache_lock:
        if _CACHE is None:
            raw = dataset.read_blob(_DATA_FILE)
            _CACHE = raw if isinstance(raw, dict) else {}
        return _CACHE


def reset_interactions_cache() -> None:
    """Drop the cached data (test seam / provider swap)."""
    global _CACHE
    with _cache_lock:
        _CACHE = None


def _word_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(token)}\b", re.I)


def _alias_hit(entry: dict[str, Any], text_lower: str) -> bool:
    return any(
        _word_re(str(alias)).search(text_lower) for alias in entry.get("aliases", ())
    )


def _pop_guide_hit(entry: dict[str, Any], text_lower: str) -> bool:
    return any(
        _word_re(token).search(text_lower)
        for token in _POP_GUIDE_TOKENS.get(str(entry.get("id", "")), ())
    )


def _damage_type_fact(entry: dict[str, Any]) -> str:
    blocked = entry.get("blocked_by_properties") or []
    blocked_txt = (
        f"cannot pop {', '.join(blocked)}" if blocked else "pops every bloon type"
    )
    return (
        f"[btd6_damage_type] {entry['name']} damage — {entry.get('summary', '')} "
        f"({blocked_txt}.) (source: {_SOURCE})"
    )


def _status_fact(entry: dict[str, Any]) -> str:
    return (
        f"[btd6_interaction] {entry['name']} is a status effect (not damage) — "
        f"{entry.get('summary', '')} Lead: {entry.get('lead', 'n/a')}. "
        f"MOAB-class: {entry.get('moab_class', 'n/a')}. "
        f"BAD: {entry.get('bad', 'n/a')}. (source: {_SOURCE})"
    )


def _pop_guide_fact(entry: dict[str, Any]) -> str:
    label = entry.get("property", entry.get("id", ""))
    return (
        f"[btd6_interaction] To deal with {label} — needs {entry.get('needs', '')}; "
        f"{entry.get('blocked', '')}. {entry.get('note', '')} (source: {_SOURCE})"
    )


# NOTE (shipped): an auto-derived "towers that can damage a DDT" fact was
# tried and reverted — the derivation grounded wrong recommendations. The
# MOAB-class subtlety is curated prose in damage_types.json instead.


def interaction_facts(message_text: str) -> list[str]:
    """Grounding facts for a damage-type / status-effect / property
    question. Fires only on a clear interaction question: an entity named
    AND (an interaction cue OR a damage-type + property pairing). Returns
    ``[]`` for plain lookups. Capped at ``_MAX_FACTS``."""
    text = (message_text or "").strip().lower()
    if not text:
        return []
    data = _load()

    matched_damage = [dt for dt in data.get("damage_types", ()) if _alias_hit(dt, text)]
    matched_status = [s for s in data.get("status_effects", ()) if _alias_hit(s, text)]
    matched_props = [p for p in data.get("pop_guide", ()) if _pop_guide_hit(p, text)]
    if not (matched_damage or matched_status or matched_props):
        return []

    cue = bool(_INTERACTION_CUE_RE.search(text))
    # A damage type + a bloon property named together is itself an
    # interaction question even without a verb ("sharp vs lead"); a status
    # name alone never fires (shipped false-positive guard).
    pairing = bool(matched_damage and matched_props)
    if not (cue or pairing):
        return []

    facts: list[str] = []
    for status in matched_status:
        facts.append(_status_fact(status))
    for prop in matched_props:
        facts.append(_pop_guide_fact(prop))
    for damage in matched_damage:
        facts.append(_damage_type_fact(damage))

    seen: set[str] = set()
    deduped: list[str] = []
    for fact in facts:
        if fact not in seen:
            seen.add(fact)
            deduped.append(fact)
    return deduped[:_MAX_FACTS]


__all__ = ["interaction_facts", "reset_interactions_cache"]
