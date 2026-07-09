"""Project Moon (Limbus) → AI grounding context — shipped
``services/projmoon_context_service.py`` @7f7628e1 VERBATIM: entity +
roster matching over the committed fixtures, provenanced length-bounded
fact lines, deterministic order, ``_MAX_FACTS`` cap. Read-only; no DB,
no live state."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sb.domain.projmoon import dataset
from sb.kernel.ai.grounding.format import sanitise

_FACT_TEXT_CAP = 400
_MAX_FACTS = 16
_PROVENANCE = "Limbus Company structural data (committed fixture)"

# Ambiguous bare tokens that are ordinary English and must NOT match on
# their own (shipped curation: "don"/"sang" resolve via their multi-word
# forms; the E.G.O grade "HE" via "he grade").
_AMBIGUOUS_BARE_TOKENS: frozenset[str] = frozenset({"he", "don", "sang"})

_ROSTER_TRIGGERS: dict[str, tuple[str, ...]] = {
    "sinner": (
        "sinners",
        "all sinners",
        "the sinners",
        "every sinner",
        "12 sinners",
        "twelve sinners",
        "list of sinners",
    ),
    "sin": (
        "seven sins",
        "7 sins",
        "the sins",
        "all sins",
        "sin affinities",
        "sin affinity",
    ),
    "damage_type": (
        "damage types",
        "all damage types",
        "three damage types",
        "the damage types",
    ),
    "ego_grade": (
        "ego grades",
        "e.g.o grades",
        "all ego grades",
        "the ego grades",
        "ego grade list",
    ),
    "status": (
        "status effects",
        "all statuses",
        "status keywords",
    ),
    "mechanic": (
        "combat mechanics",
        "game mechanics",
        "combat system",
        "how does combat work",
        "how combat works",
        "all mechanics",
        "list of mechanics",
    ),
}


@dataclass(frozen=True)
class ProjmoonContext:
    """Retrieved Limbus facts ready for the instruction stack."""

    facts: tuple[str, ...]
    source_summary: str = _PROVENANCE
    confidence: float = 0.6


def _normalise(text: str) -> str:
    folded = re.sub(r"[^\w]+", " ", text.casefold()).strip()
    return f" {folded} "


def _match_tokens(entry: dataset.LimbusEntry) -> tuple[str, ...]:
    tokens = (entry.canonical.casefold(), *entry.aliases)
    return tuple(
        token
        for token in dict.fromkeys(tokens)
        if token and token not in _AMBIGUOUS_BARE_TOKENS
    )


def _matched_entries(text: str) -> list[dataset.LimbusEntry]:
    needle = _normalise(text)
    matched: list[dataset.LimbusEntry] = []
    for entry in dataset.all_entries():
        for token in _match_tokens(entry):
            if f" {token} " in needle:
                matched.append(entry)
                break
    return matched


def _rostered_kinds(text: str) -> list[str]:
    needle = _normalise(text)
    kinds: list[str] = []
    for kind, triggers in _ROSTER_TRIGGERS.items():
        if any(f" {_normalise(trigger).strip()} " in needle for trigger in triggers):
            kinds.append(kind)
    return kinds


def _body(entry: dataset.LimbusEntry) -> str:
    base = f"{entry.canonical}: {entry.description}"
    if entry.entity_kind == "sinner":
        origin = entry.extra.get("literary_origin")
        if isinstance(origin, dict) and origin.get("work") and origin.get("author"):
            base = f"{base} (literary origin: {origin['work']} by {origin['author']})"
    elif entry.entity_kind == "sin":
        color = entry.extra.get("color")
        if color:
            base = f"{entry.canonical} ({color} Sin affinity): {entry.description}"
    elif entry.entity_kind == "ego_grade":
        rank = entry.extra.get("rank")
        if rank:
            base = (
                f"{entry.canonical} (E.G.O grade, rank {rank}/5): {entry.description}"
            )
    elif entry.entity_kind == "mechanic":
        category = entry.extra.get("category")
        if category:
            base = (
                f"{entry.canonical} (combat mechanic — {category}): "
                f"{entry.description}"
            )
    return base


def _grounding_line(entry: dataset.LimbusEntry) -> str:
    suffix = f" (source: {_PROVENANCE})"
    budget = max(1, _FACT_TEXT_CAP - len(suffix))
    return f"{sanitise(_body(entry), cap=budget)}{suffix}"


def build(text: str) -> ProjmoonContext:
    """Return the Limbus grounding facts for ``text``. Never raises: a
    fixture-load fault degrades to an empty context."""
    try:
        entries: list[dataset.LimbusEntry] = list(_matched_entries(text))
        roster_kinds = _rostered_kinds(text)
        if roster_kinds:
            seen_ids = {entry.id for entry in entries}
            for kind in dataset.entity_kinds():
                if kind not in roster_kinds:
                    continue
                for entry in dataset.get_entries(kind):
                    if entry.id not in seen_ids:
                        entries.append(entry)
                        seen_ids.add(entry.id)
    except Exception:  # noqa: BLE001 — grounding is best-effort
        return ProjmoonContext(facts=())

    facts = tuple(_grounding_line(entry) for entry in entries[:_MAX_FACTS])
    return ProjmoonContext(facts=facts)


__all__ = ["ProjmoonContext", "build"]
