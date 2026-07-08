"""Pure, common-word-safe proper-name and number matching (K10) — hoisted
from shipped ``disbot/utils/btd6/name_guard.py`` @7f7628e1 with the one
domain datum parameterised: the alias stoplist is an argument with the
shipped default (:data:`DEFAULT_ALIAS_STOPLIST`), so a domain building its
matchers can supply its own collision list.

stdlib only. Canonical proper names match whole-word (single tokens) or
as substrings (multi-word phrases); generic aliases are length-filtered
and stop-listed so ordinary English words are never treated as
proper-name evidence. The caller (a domain grounding service) is
responsible for passing a SAFE set of names.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

__all__ = [
    "DEFAULT_ALIAS_STOPLIST",
    "NameMatchers",
    "build_matchers",
    "multiword_names_present",
    "names_present",
    "normalize_numbers",
    "offending_numbers",
]

# Short alias/token forms that collide with ordinary English or chat
# (shipped default). Even surviving the length filter they must never
# count as proper-name evidence.
DEFAULT_ALIAS_STOPLIST: frozenset[str] = frozenset(
    {
        "ace",
        "ice",
        "dart",
        "bomb",
        "tack",
        "glue",
        "boat",
        "sub",
        "gun",
        "hero",
        "tower",
        "round",
        "boss",
        "race",
        "event",
        "camo",
        "lead",
        "pink",
        "blue",
        "black",
        "white",
        "green",
        "purple",
        "yellow",
    },
)

_WORD_RE = re.compile(r"[a-z0-9]+")
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class NameMatchers:
    """Compiled matchers: multi-word phrases (substring) + single tokens."""

    multi: frozenset[str]
    single: frozenset[str]


def build_matchers(
    canonicals: Iterable[str],
    aliases: Iterable[str],
    *,
    stoplist: frozenset[str] = DEFAULT_ALIAS_STOPLIST,
) -> NameMatchers:
    """Split names into multi-word (substring) and single-token matchers.

    * Canonicals are proper nouns: single-word forms kept at length >= 3
      (distinctive short names survive), multi-word forms → phrases.
    * Aliases are generic: single-word forms kept only at length > 4 and
      not stop-listed.

    Stop-listed tokens are removed from the single set unconditionally,
    even if they arrived as a (short) canonical.
    """
    multi: set[str] = set()
    single: set[str] = set()

    for raw in canonicals:
        name = (raw or "").strip().lower()
        if not name:
            continue
        if " " in name:
            multi.add(name)
        elif len(name) >= 3:
            single.add(name)

    for raw in aliases:
        alias = (raw or "").strip().lower()
        if not alias:
            continue
        if " " in alias:
            multi.add(alias)
        elif len(alias) > 4 and alias not in stoplist:
            single.add(alias)

    single -= stoplist
    return NameMatchers(multi=frozenset(multi), single=frozenset(single))


def names_present(text: str, matchers: NameMatchers) -> set[str]:
    """All indexed names in ``text`` (whole-word + substring)."""
    lowered = (text or "").lower()
    found: set[str] = {phrase for phrase in matchers.multi if phrase in lowered}
    if matchers.single:
        tokens = set(_WORD_RE.findall(lowered))
        found |= tokens & matchers.single
    return found


def multiword_names_present(text: str, matchers: NameMatchers) -> set[str]:
    """Only the multi-word indexed names present in ``text`` (distinctive
    enough to trigger a general-path guard on their own)."""
    lowered = (text or "").lower()
    return {phrase for phrase in matchers.multi if phrase in lowered}


def normalize_numbers(text: str) -> set[str]:
    """Canonical numeric tokens, thousands-separators stripped
    ('48,210' and '48210' normalize the same). Decimals preserved."""
    return {match.replace(",", "") for match in _NUMBER_RE.findall(text or "")}


def offending_numbers(answer: str, haystack: str) -> tuple[str, ...]:
    """Numeric tokens in ``answer`` not present in ``haystack``
    (comma-normalized both sides; SUBSTRING test — mirrors the
    ``claims_are_grounded`` leniency so short integers inside a larger
    grounded number never false-positive; the trade: a fabricated number
    that is a substring of a real one passes)."""
    hay = (haystack or "").replace(",", "")
    out: list[str] = []
    for raw in _NUMBER_RE.findall(answer or ""):
        token = raw.replace(",", "")
        if token and token not in hay:
            out.append(token)
    return tuple(out)
