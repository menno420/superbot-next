"""Per-intent channel recommendation scoring — the NATIVE recommender
port (menno420/superbot @bbc524e: ``disbot/services/channel_recommender
.py``, scoring + intent catalogue + reason strings verbatim; the full
``disbot/utils/channel_classify.py`` pattern table rides along as the
consumed heuristic).

Given a perms-bearing guild snapshot (sb/domain/platform/guild_snapshot
— the compiled ``services.guild_snapshot`` twin; duck-read here, no
runtime import) and a target intent (``"bot_commands"``,
``"mod_logs"``, …), returns a ranked list of channels with a numeric
score, a confidence bucket, and a human-readable reason list. The
scorer is intentionally simple and deterministic (oracle doctrine):

* +50 if the channel's name matches a classifier tag the intent cares
  about; +25 for the softer keyword-hint fallback;
* +20 if the bot has view + send + embed permission; +10 for the
  partial tiers; −10 when a send-requiring intent can't send;
* channels the bot cannot VIEW are excluded outright; non-positive
  scores are dropped.

Confidence buckets: ``high`` (≥60), ``medium`` (≥30), ``low``.

Kernel-idiom divergences, ledgered:

* the shared classifier is carried PRIVATELY (``_classify_channel_name``
  — the FULL 11-tag oracle pattern table, patterns verbatim): the
  public ``classify_channel_name`` symbol in this package stays
  cleanup.py's consumed subset (test-pinned bytes; the shadowing
  guard's one-public-name-per-package rule 2);
* the module is PURE — no port, no I/O: the perms-bearing snapshot
  arrives from ``sb.domain.platform.guild_snapshot.snapshot_for`` (the
  guild-id-keyed source seam this slice arms; the discord adapter's
  ``setup_reads`` fill builds it live).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from sb.domain.platform.guild_snapshot import ChannelMeta, GuildSnapshot

__all__ = [
    "INTENTS",
    "ChannelRecommendation",
    "Intent",
    "get_intent",
    "intent_for_binding",
    "known_intent_slugs",
    "recommend",
    "recommend_all",
    "top_pick",
]

Confidence = Literal["high", "medium", "low"]
Action = Literal["bind", "create"]


@dataclass(frozen=True)
class ChannelRecommendation:
    """One channel suggested for one binding intent (oracle shape)."""

    channel_id: int
    channel_name: str
    intent: str
    score: int
    confidence: Confidence
    reasons: tuple[str, ...]
    action: Action  # "bind" = pick existing; "create" = create new


# --- the consumed channel classifier (utils/channel_classify.py, FULL table, verbatim) -------

_NAME_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "likely_log": (
        re.compile(r"\blogs?\b"),
        re.compile(r"\baudit\b"),
        re.compile(r"\bmod[-_]?logs?\b"),
        re.compile(r"\bbot[-_]?logs?\b"),
    ),
    "likely_mod_log": (
        re.compile(r"\bmod[-_]?logs?\b"),
        re.compile(r"\bmoderation[-_]?logs?\b"),
        re.compile(r"\bstaff[-_]?logs?\b"),
    ),
    "likely_bot_cmd": (
        re.compile(r"\bbot[-_]?(?:cmd|cmds|commands?|spam)\b"),
        re.compile(r"\bcmds?\b"),
        re.compile(r"\bcommands?\b"),
    ),
    "likely_admin": (
        re.compile(r"\badmin\b"),
        re.compile(r"\bowner\b"),
        re.compile(r"\bstaff[-_]?only\b"),
    ),
    "likely_mod": (
        re.compile(r"\bmods?\b"),
        re.compile(r"\bmoderation\b"),
        re.compile(r"\bstaff\b"),
    ),
    "likely_proof": (
        re.compile(r"\bproofs?\b"),
        re.compile(r"\bevidence\b"),
    ),
    "likely_counting": (
        re.compile(r"\bcounting\b"),
        re.compile(r"\bcount\b"),
    ),
    "likely_mining": (
        re.compile(r"\bmining\b"),
        re.compile(r"\bmine\b"),
    ),
    "likely_game": (
        re.compile(r"\bgames?\b"),
        re.compile(r"\bbet(?:s|ting)?\b"),
        re.compile(r"\bcasino\b"),
        re.compile(r"\bblackjack\b"),
        re.compile(r"\brps\b"),
        re.compile(r"\bdeathmatch\b"),
        re.compile(r"\btournament\b"),
    ),
    "likely_general": (
        re.compile(r"\bgeneral\b"),
        re.compile(r"\blobby\b"),
        re.compile(r"\bchat\b"),
    ),
    "likely_welcome": (
        re.compile(r"\bwelcome\b"),
        re.compile(r"\bintro\b"),
        re.compile(r"\bgreetings?\b"),
    ),
}


def _classify_channel_name(name: str) -> tuple[str, ...]:
    """channel_classify.classify_channel_name, full table — sorted for
    deterministic output (the shipped contract; private per the module
    docstring ledger)."""
    if not name:
        return ()
    lowered = name.lower()
    return tuple(sorted(
        tag for tag, patterns in _NAME_PATTERNS.items()
        if any(p.search(lowered) for p in patterns)))


# --- the intent catalogue (oracle INTENTS, data verbatim) -------------------------------------

@dataclass(frozen=True)
class Intent:
    slug: str
    label: str
    tags: tuple[str, ...]
    requires_send: bool  # intents that need write access score perms harder
    keyword_hints: tuple[str, ...] = ()


INTENTS: dict[str, Intent] = {
    "bot_commands": Intent(
        slug="bot_commands",
        label="Bot commands / spam",
        tags=("likely_bot_cmd",),
        requires_send=True,
        keyword_hints=("bot", "commands", "cmds", "spam"),
    ),
    "logs": Intent(
        slug="logs",
        label="General log channel",
        tags=("likely_log",),
        requires_send=True,
        keyword_hints=("log", "audit"),
    ),
    "mod_logs": Intent(
        slug="mod_logs",
        label="Moderation log",
        tags=("likely_mod_log", "likely_log"),
        requires_send=True,
        keyword_hints=("mod-log", "mod_log", "moderation"),
    ),
    "welcome": Intent(
        slug="welcome",
        label="Welcome / intro",
        tags=("likely_welcome",),
        requires_send=True,
        keyword_hints=("welcome", "intro"),
    ),
    "general": Intent(
        slug="general",
        label="General chat",
        tags=("likely_general",),
        requires_send=False,
        keyword_hints=("general", "lobby", "chat"),
    ),
    "moderation": Intent(
        slug="moderation",
        label="Moderation chat",
        tags=("likely_mod",),
        requires_send=True,
        keyword_hints=("mod-chat", "staff", "admin", "moderation"),
    ),
    "proof": Intent(
        slug="proof",
        label="Proof / reports / appeals",
        tags=("likely_proof",),
        requires_send=True,
        keyword_hints=("proof", "evidence", "report", "appeal"),
    ),
    "games": Intent(
        slug="games",
        label="Games / leaderboards",
        tags=("likely_game",),
        requires_send=True,
        keyword_hints=("game", "casino", "bet", "tournament", "leaderboard"),
    ),
    "counting": Intent(
        slug="counting",
        label="Counting",
        tags=("likely_counting",),
        requires_send=True,
        keyword_hints=("counting", "count"),
    ),
    "mining": Intent(
        slug="mining",
        label="Mining / economy gameplay",
        tags=("likely_mining",),
        requires_send=True,
        keyword_hints=("mining", "mine", "ore"),
    ),
}


def known_intent_slugs() -> frozenset[str]:
    return frozenset(INTENTS.keys())


def get_intent(slug: str) -> Intent | None:
    return INTENTS.get(slug)


#: binding name → intent slug (oracle _BINDING_TO_INTENT, verbatim —
#: kept separate from the wizard's binding registry so the intent
#: catalogue evolves independently, the oracle comment's contract).
_BINDING_TO_INTENT: dict[str, str] = {
    "mod_channel": "mod_logs",
    "cleanup_channel": "logs",
    "debug_channel": "logs",
    "info_channel": "logs",
    "warning_channel": "logs",
    "error_channel": "logs",
    "audit_channel": "logs",
    "log_channel": "logs",
    "announce_channel": "general",
    "welcome_channel": "welcome",
}


def intent_for_binding(binding_name: str) -> str | None:
    return _BINDING_TO_INTENT.get(binding_name)


# --- scoring (oracle constants + tiers, verbatim) ---------------------------------------------

_TAG_MATCH_BONUS = 50
_KEYWORD_HINT_BONUS = 25
_PERMS_OK_BONUS = 20
_PERMS_PARTIAL_BONUS = 10
_PERMS_NONE_PENALTY = -30


def _confidence_bucket(score: int) -> Confidence:
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _channel_score(
    channel: ChannelMeta,
    intent: Intent,
) -> tuple[int, tuple[str, ...]] | None:
    """``(score, reasons)`` for ``channel`` against ``intent``, or
    ``None`` when the channel does not qualify (text channels only,
    bot must be able to view, score must be positive) — oracle body
    verbatim over the perms-bearing snapshot fields."""
    if channel.type != "text":
        return None
    # Hard exclusion: if the bot can't see the channel at all, it cannot
    # be a useful recommendation regardless of name match.
    if not channel.bot_can_view:
        return None

    name = channel.name or ""
    tags = _classify_channel_name(name)
    score = 0
    reasons: list[str] = []

    tag_match = next((t for t in intent.tags if t in tags), None)
    if tag_match:
        score += _TAG_MATCH_BONUS
        reasons.append(f"Name matches `{tag_match}` pattern")
    else:
        # Fall back to a softer keyword check so channels without
        # canonical naming (e.g. "bot-shenanigans") still surface.
        lowered = name.lower()
        hit = next(
            (h for h in intent.keyword_hints if h in lowered),
            None,
        )
        if hit:
            score += _KEYWORD_HINT_BONUS
            reasons.append(f"Name contains `{hit}`")

    if score == 0:
        # Channel doesn't match the intent at all.
        return None

    # bot_can_view is guaranteed by the hard exclusion above.
    if channel.bot_can_send and channel.bot_can_embed:
        score += _PERMS_OK_BONUS
        reasons.append("Bot has view + send + embed")
    elif channel.bot_can_send:
        score += _PERMS_PARTIAL_BONUS
        reasons.append("Bot can send but not embed")
    elif not intent.requires_send:
        score += _PERMS_PARTIAL_BONUS
        reasons.append("Bot can view (intent does not require send)")
    else:
        # Can view but not send; if the intent needs send, mild penalty.
        score += -10
        reasons.append("Bot cannot send in this channel")

    if score <= 0:
        return None
    return score, tuple(reasons)


def recommend(
    intent_slug: str,
    snapshot: GuildSnapshot,
) -> list[ChannelRecommendation]:
    """Ranked recommendations for ``intent_slug``, highest score first;
    empty when the intent is unknown or no channel scores positively."""
    intent = INTENTS.get(intent_slug)
    if intent is None:
        return []

    matches: list[ChannelRecommendation] = []
    for ch in snapshot.channels:
        scored = _channel_score(ch, intent)
        if scored is None:
            continue
        score, reasons = scored
        matches.append(
            ChannelRecommendation(
                channel_id=ch.id,
                channel_name=ch.name,
                intent=intent.slug,
                score=score,
                confidence=_confidence_bucket(score),
                reasons=reasons,
                action="bind",
            ),
        )
    matches.sort(key=lambda r: (-r.score, r.channel_name))
    return matches


def top_pick(
    intent_slug: str,
    snapshot: GuildSnapshot,
) -> ChannelRecommendation | None:
    """The single top recommendation, or ``None`` with no matches."""
    ranked = recommend(intent_slug, snapshot)
    return ranked[0] if ranked else None


def recommend_all(
    snapshot: GuildSnapshot,
    intents: Iterable[str] | None = None,
) -> dict[str, list[ChannelRecommendation]]:
    """``{intent_slug: ranked_recommendations}`` for every intent in
    ``intents`` (or every documented intent when ``None``)."""
    slugs = list(intents) if intents is not None else list(INTENTS.keys())
    return {slug: recommend(slug, snapshot) for slug in slugs}
