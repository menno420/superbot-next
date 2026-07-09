"""Curated Project Moon (Limbus) context keywords — shipped
``utils/projmoon/keywords.py`` @7f7628e1 VERBATIM (one list, no drift
between the route probe and the answer guard). Curated to avoid
over-routing: bare Sin words and ambiguous status words are deliberately
absent."""

from __future__ import annotations

import re

LIMBUS_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "limbus",
    "sinner",
    "sinners",
    "e.g.o",
    "ego grade",
    "mirror dungeon",
    "intervallo",
    # E.G.O / risk grades (Sephirah names) — distinctive in this context.
    "zayin",
    "teth",
    "waw",
    "aleph",
    # Distinctive Sinner proper names (the ambiguous "faust"/"don" rely on
    # the resolver + a co-occurring token, not this bare list).
    "yi sang",
    "ryoshu",
    "ryōshū",
    "meursault",
    "hong lu",
    "heathcliff",
    "ishmael",
    "rodion",
    "sinclair",
    "outis",
    "gregor",
    "don quixote",
)

_KEYWORD_RE = re.compile(
    r"(?<![\w.])(?:"
    + "|".join(re.escape(k) for k in LIMBUS_CONTEXT_KEYWORDS)
    + r")(?![\w])",
    re.IGNORECASE,
)


def has_limbus_context(text: str) -> bool:
    """True when ``text`` carries a distinctive Limbus Company token."""
    if not text:
        return False
    return _KEYWORD_RE.search(text) is not None


__all__ = ["LIMBUS_CONTEXT_KEYWORDS", "has_limbus_context"]
