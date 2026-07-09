"""Curated BTD6 context keywords — shared by the route probe and the
answer-faithfulness guard (shipped ``utils/btd6/keywords.py`` @7f7628e1,
VERBATIM: one list, no drift between the router fast-path and the
general-path leak guard)."""

from __future__ import annotations

import re

# The "in ABR" qualifier (BUG-0010): one cue shared by the grounding round
# legs and the round-cash workflow so they can never drift.
ABR_CUE_RE = re.compile(r"\babr\b|\balternate\s+bloons?\b", re.IGNORECASE)

# A paragon "degree" named in a query (BUG-0015): "degree 67", "deg 67", or
# the shorthand "d67" players type. Only paragons have degrees (1-100), so a
# match is only acted on when a paragon is also in scope.
DEGREE_CUE_RE = re.compile(
    r"\bdegrees?\s*-?\s*(\d{1,3})\b"  # "degree 67", "degree-67", "degrees 67"
    r"|\bdeg\.?\s*(\d{1,3})\b"  # "deg 67", "deg.67", "deg67"
    r"|\bd(\d{1,3})\b",  # the bare "d67" shorthand
    re.IGNORECASE,
)


def degree_in_text(text: str) -> int | None:
    """The paragon degree (1-100) named in ``text``, or None (shipped:
    out-of-range values never read as a degree; callers gate on a paragon
    also being in scope)."""
    for match in DEGREE_CUE_RE.finditer(text or ""):
        raw = next((group for group in match.groups() if group is not None), None)
        if raw is None:
            continue
        value = int(raw)
        if 1 <= value <= 100:
            return value
    return None


BTD6_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "btd6",
    "bloons",
    "bloon",
    "moab",
    "ddt",
    "bfb",
    "zomg",
    "tower",
    "hero",
    "monkey",
    "chimps",
    "round ",
    "freeplay",
    "deflation",
    "apopalypse",
    "impop",
    "half cash",
    "double cash",
    "2x cash",
    "primary only",
    "military only",
    "magic only",
    "support only",
    "boss bloon",
    "boss event",
    "current boss",
    "current race",
    "current event",
    "what boss",
    "what race",
    "what odyssey",
    "active boss",
    "active race",
    "ninja kiwi",
    "ninjakiwi",
    "odyssey",
    "contested territory",
    "race ",
    "banned hero",
    "banned tower",
    "obyn",
    "desperado",
    "despo",
    "banana",
)


def has_btd6_context(text: str) -> bool:
    """True when ``text`` contains any curated BTD6 context keyword
    (case-insensitive substring scan — the router's fast-path test)."""
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in BTD6_CONTEXT_KEYWORDS)


__all__ = [
    "ABR_CUE_RE",
    "BTD6_CONTEXT_KEYWORDS",
    "DEGREE_CUE_RE",
    "degree_in_text",
    "has_btd6_context",
]
