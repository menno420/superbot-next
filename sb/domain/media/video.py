"""Video URL context supplier (band 7) — the deterministic half of
shipped ``services/youtube_context_service.py`` @7f7628e1: URL
extraction (the shipped regex verbatim), untrusted-metadata
sanitisation, and the fact rendering — over an INSTALLABLE metadata
reader port.

The shipped fetch path (YouTube Data API + transcript fetch +
``video_reference_cache`` DB cache, YOUTUBE_API_KEY-gated) is network
ingestion: it rides the named successor port (D-0047) and installs a
real reader at the composition root (its YOUTUBE_API_KEY row joins the
S13 CREDENTIAL_REGISTRY with that port). Until then the gatherer
returns the shipped empty-facts short-circuit reasons
(``video_feature_disabled`` / ``video_grounding_failed``) and the NL
shell serves the deterministic floor."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "VideoFacts",
    "YOUTUBE_URL_RE",
    "build",
    "extract_video_ids",
    "install_video_metadata_reader",
    "reset_video_reader_for_tests",
]

# Shipped verbatim (watch / shorts / youtu.be, 11-char id).
YOUTUBE_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})",
)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_MENTION_RE = re.compile(r"(@everyone|@here|<@[!&]?\d+>)")

_MAX_DESCRIPTION_CHARS = 500
_MAX_TRANSCRIPT_CHARS = 1500
_MAX_TITLE_CHARS = 200
_MAX_CHANNEL_CHARS = 100


def _sanitise(text: object, max_chars: int = 500) -> str | None:
    if text is None:
        return None
    out = _CONTROL_CHAR_RE.sub(" ", str(text))
    out = _MENTION_RE.sub("[mention]", out)
    return out[:max_chars].strip() or None


def extract_video_ids(text: str) -> tuple[str, ...]:
    """Distinct video ids in ``text``, order-preserved, capped at 2
    (shipped)."""
    return tuple(dict.fromkeys(YOUTUBE_URL_RE.findall(text or "")))[:2]


@dataclass(frozen=True)
class VideoFacts:
    """The gatherer's outcome (shipped YouTubeContext, facts-focused)."""

    facts: tuple[str, ...]
    source_summary: str
    confidence: float
    error_reason: str | None = None


#: reader(video_id) -> metadata mapping (title/channel_name/published/
#: duration_seconds/description/transcript_excerpt/canonical_url), an
#: error-reason string, or None on transient failure. Installed by the
#: ingestion successor port at the composition root.
VideoMetadataReader = Callable[[str], Awaitable[dict[str, Any] | str | None]]

_READER: VideoMetadataReader | None = None


def install_video_metadata_reader(reader: VideoMetadataReader) -> None:
    global _READER
    _READER = reader


def reset_video_reader_for_tests() -> None:
    global _READER
    _READER = None


def _render_facts(contexts: list[tuple[str, dict[str, Any]]]) -> list[str]:
    """Shipped ``_render_facts`` over sanitised metadata mappings."""
    facts: list[str] = []
    for i, (video_id, m) in enumerate(contexts, 1):
        label = f"Video {i}" if len(contexts) > 1 else "Video"
        title = _sanitise(m.get("title"), _MAX_TITLE_CHARS)
        channel = _sanitise(m.get("channel_name"), _MAX_CHANNEL_CHARS)
        if title:
            facts.append(f"{label} title: {title}")
        if channel:
            facts.append(f"{label} channel: {channel}")
        if m.get("published"):
            facts.append(f"{label} published: {_sanitise(m['published'], 40)}")
        if m.get("duration_seconds") is not None:
            facts.append(f"{label} duration: {m['duration_seconds']}s")
        description = _sanitise(m.get("description"), _MAX_DESCRIPTION_CHARS)
        if description:
            facts.append(f"{label} description: {description}")
        transcript = _sanitise(m.get("transcript_excerpt"), _MAX_TRANSCRIPT_CHARS)
        if transcript:
            facts.append(f"{label} transcript excerpt: {transcript}")
        else:
            facts.append(f"{label} transcript: unavailable")
        facts.append(
            f"{label} URL: https://www.youtube.com/watch?v={video_id}",
        )
    return facts


async def build(text: str) -> VideoFacts:
    """Video grounding for ``text`` (shipped ``build`` order: reader
    armed? → URLs present? → per-video resolve → facts). Never raises."""
    if _READER is None:
        # The ingestion port isn't armed — the shipped feature-off /
        # key-missing short-circuit class.
        return VideoFacts(
            facts=(), source_summary="feature_disabled", confidence=0.0,
            error_reason="video_feature_disabled",
        )
    video_ids = extract_video_ids(text)
    if not video_ids:
        return VideoFacts(
            facts=(), source_summary="no_urls", confidence=0.0,
            error_reason="video_grounding_failed",
        )
    contexts: list[tuple[str, dict[str, Any]]] = []
    last_error: str | None = None
    for video_id in video_ids:
        try:
            resolved = await _READER(video_id)
        except Exception:  # noqa: BLE001 — reader faults degrade, never raise
            resolved = None
        if resolved is None:
            last_error = last_error or "fetch_error"
            continue
        if isinstance(resolved, str):
            last_error = resolved
            continue
        contexts.append((video_id, resolved))
    if not contexts:
        return VideoFacts(
            facts=(), source_summary=last_error or "fetch_error",
            confidence=0.0, error_reason=last_error or "fetch_error",
        )
    return VideoFacts(
        facts=tuple(_render_facts(contexts)),
        source_summary="ok",
        confidence=0.8,
    )
