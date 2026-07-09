"""Bot-to-bot XP migration — the Discord-free parsing core, shipped
verbatim (disbot/utils/xp_migration.py @7f7628e1).

Turns raw level-up announcement text (+ mention ids) into (user, level)
records and reduces them to the highest level per user. The Discord I/O
(channel history scan) rides ``sb.domain.xp.service.
install_levelup_history_scanner`` (arms with the message band); the
audited write is the K7 ``xp.import_levels`` op (raise-only, no events).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from re import Pattern

__all__ = [
    "DEFAULT_FORMAT",
    "FORMATS",
    "AnnouncerFormat",
    "ParsedLevelUp",
    "format_keys",
    "get_format",
    "parse_level_message",
    "reduce_max_levels",
]


@dataclass(frozen=True)
class AnnouncerFormat:
    """A known leveling bot's level-up announcement shape.

    ``level_re`` exposes the reached level as group 1; ``name_re`` (group
    1 = display name) is the fallback for mention-less announcers.
    """

    key: str
    label: str
    level_re: Pattern[str]
    name_re: Pattern[str] | None


# Optional bold markers (``**``) surround the number/level in most
# announcers' markdown; tolerate 0-2 asterisks and arbitrary spacing.
_B = r"\*{0,2}"

FORMATS: dict[str, AnnouncerFormat] = {
    "arcane": AnnouncerFormat(
        key="arcane",
        label="Arcane",
        # "@User has reached level **3**. GG!"
        level_re=re.compile(rf"reached\s+level\s+{_B}(\d+)", re.IGNORECASE),
        name_re=re.compile(r"^\s*@?(.+?)\s+has\s+reached\s+level",
                           re.IGNORECASE),
    ),
    "mee6": AnnouncerFormat(
        key="mee6",
        label="MEE6",
        # "GG @User, you just advanced to level **3**!"
        level_re=re.compile(
            rf"(?:advanced\s+to|reached)\s+{_B}level\s+{_B}(\d+)",
            re.IGNORECASE,
        ),
        name_re=re.compile(
            r"(?:GG\s+)?@?([^,]+?),\s+you\s+just\s+advanced",
            re.IGNORECASE,
        ),
    ),
    "superbot": AnnouncerFormat(
        key="superbot",
        label="SuperBot",
        # SuperBot's own announce embed: "@User reached **Level 3**!"
        level_re=re.compile(rf"reached\s+{_B}level\s+{_B}(\d+)",
                            re.IGNORECASE),
        name_re=None,
    ),
    "generic": AnnouncerFormat(
        key="generic",
        label="Generic (any “level N”)",
        # Permissive: any "... level 3 ..." — for unknown announcers.
        level_re=re.compile(rf"\blevel\s+{_B}(\d+)", re.IGNORECASE),
        name_re=None,
    ),
}

DEFAULT_FORMAT = "arcane"


def get_format(key: str | None) -> AnnouncerFormat | None:
    if key is None:
        return None
    return FORMATS.get(key.strip().lower())


def format_keys() -> list[str]:
    return list(FORMATS.keys())


@dataclass(frozen=True)
class ParsedLevelUp:
    """One parsed announcement: level + (user_id | name | neither)."""

    level: int
    user_id: int | None = None
    name: str | None = None


def parse_level_message(
    content: str,
    mention_ids: Iterable[int] = (),
    *,
    fmt: AnnouncerFormat,
) -> ParsedLevelUp | None:
    """Parse one announcement, or ``None`` when it carries no level for
    ``fmt``. The subject is the FIRST mention id when present."""
    if not content:
        return None
    m = fmt.level_re.search(content)
    if m is None:
        return None
    level = int(m.group(1))

    for mid in mention_ids:
        return ParsedLevelUp(level=level, user_id=int(mid))

    if fmt.name_re is not None:
        nm = fmt.name_re.search(content)
        if nm is not None:
            name = nm.group(1).strip().strip("*").strip()
            if name:
                return ParsedLevelUp(level=level, name=name)

    return ParsedLevelUp(level=level)


def reduce_max_levels(records: Iterable[tuple[int, int]]) -> dict[int, int]:
    """Collapse (user_id, level) pairs to the highest level per user."""
    best: dict[int, int] = {}
    for user_id, level in records:
        if level > best.get(user_id, -1):
            best[user_id] = level
    return best
