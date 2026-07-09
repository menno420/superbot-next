"""Question normalization — shipped ``utils/ai_text_normalize.py``
@7f7628e1 VERBATIM: the single conservative normalizer the review-log
triage and the vetted-answer preset layer share (exact-normalized
equality only; a false fuzzy match would confidently serve the wrong
vetted answer). Stdlib-only leaf."""

from __future__ import annotations

import re
import unicodedata

# Discord entity tokens — user/role/channel mentions and custom emoji.
_DISCORD_TOKEN = re.compile(r"<a?:\w+:\d+>|<[@#][!&]?\d+>")
_WS = re.compile(r"\s+")
_EDGE = re.compile(r"^[^0-9a-z]+|[^0-9a-z]+$")


def normalize_question(text: str | None) -> str:
    """Stable, case-folded key for ``text`` (``""`` if empty): strip
    Discord tokens → NFKC → casefold → collapse whitespace → trim edge
    punctuation."""
    if not text:
        return ""
    without_tokens = _DISCORD_TOKEN.sub(" ", text)
    folded = unicodedata.normalize("NFKC", without_tokens).casefold()
    collapsed = _WS.sub(" ", folded).strip()
    if not collapsed:
        return ""
    return _EDGE.sub("", collapsed)


__all__ = ["normalize_question"]
