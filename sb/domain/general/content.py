"""General-subsystem content pools — the shipped random-pick surface
(disbot/cogs/general_cog.py over disbot/data/json/general_content.json).

Provenance discipline: ONLY entries verified VERBATIM against the oracle
(menno420/superbot @ dc19b1e, data/json/general_content.json fragments)
are carried here. Pools whose shipped entries could not be read in this
slice ship EMPTY and fall back to the shipped empty-pool string
(general_cog.py, verbatim: ``f"No {label} available."``) — an honest
"content arrives with the pool import" surface, never invented content.
Importing the full shipped JSON byte-verbatim is a parked follow-up; no
golden pins any pool entry (the single general golden opens the panel and
clicks nothing).
"""

from __future__ import annotations

import random

__all__ = [
    "EIGHTBALL",
    "FACTS",
    "GREETINGS",
    "JOKES",
    "MOTIVATIONS",
    "QUOTES",
    "TRIVIA",
    "pick",
]

# oracle-verbatim (general_content.json "facts", head of the array)
FACTS: tuple[str, ...] = (
    "Honey never spoils — archaeologists found 3000-year-old honey in "
    "Egyptian tombs.",
    "Octopuses have three hearts and blue blood.",
    "Bananas are berries, but strawberries aren't.",
    "A day on Venus is longer than a year on Venus.",
    "Cleopatra lived closer in time to the Moon landing than to the "
    "construction of the Great Pyramid.",
)

# oracle-verbatim (general_content.json "jokes", head + tail fragments)
JOKES: tuple[str, ...] = (
    "Why can't skeletons fight each other? They don't have the guts.",
    "What do you call cheese that isn't yours? Nacho cheese.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "I bought some shoes from a drug dealer. I don't know what he laced "
    "them with, but I was tripping all day.",
)

# oracle-verbatim (general_content.json "quotes", head of the array)
QUOTES: tuple[str, ...] = (
    '"The only way to do great work is to love what you do." — Steve Jobs',
)

# oracle-verbatim (general_content.json "trivia", head of the array);
# entries carry the shipped `question || answer` separator.
TRIVIA: tuple[str, ...] = (
    "What is the capital of Australia? || Canberra (not Sydney!)",
)

# shipped pools not yet recoverable verbatim — empty ⇒ the shipped
# empty-pool fallback (see module docstring).
MOTIVATIONS: tuple[str, ...] = ()
GREETINGS: tuple[str, ...] = ()
EIGHTBALL: tuple[str, ...] = ()


def pick(pool: tuple[str, ...], label: str) -> str:
    """The shipped random-pick rule (general_cog.py, verbatim fallback)."""
    return random.choice(pool) if pool else f"No {label} available."
