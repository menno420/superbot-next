"""Pre-provider safety checks + untrusted-data containment (K10).

Ported verbatim from shipped ``disbot/core/runtime/ai/safety.py``
@7f7628e1. Deterministic and cheap; never depends on an LLM. A precheck
that fires returns a textual reason; the gateway short-circuits with a
degraded :class:`AIResponse` and never sends the request.
"""

from __future__ import annotations

import json
import re

from sb.kernel.ai.contracts import AIRequest

__all__ = [
    "MAX_PAYLOAD_BYTES",
    "claims_are_grounded",
    "precheck",
    "wrap_untrusted_text",
]

# Conservative ceiling for the serialised payload size in bytes.
MAX_PAYLOAD_BYTES = 256 * 1024


def precheck(request: AIRequest) -> str | None:
    """Run safety checks; return the first failure reason or ``None``."""
    if not request.system_prompt or not request.system_prompt.strip():
        return "safety: empty system_prompt"
    if not request.payload:
        return "safety: empty payload"
    try:
        size = len(json.dumps(request.payload, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return "safety: payload is not JSON-serialisable"
    if size > MAX_PAYLOAD_BYTES:
        return f"safety: payload {size}B exceeds {MAX_PAYLOAD_BYTES}B cap"
    return None


# ---------------------------------------------------------------------------
# Prompt-injection containment
# ---------------------------------------------------------------------------
# Untrusted text (user messages, instruction bodies, source snippets) must
# be wrapped before it is folded into a prompt so a hostile string like
# "Ignore previous instructions" becomes data the model can describe rather
# than instructions it follows. Official API / source data is also data —
# both go through the same wrapper.

_CONTAIN_OPEN = "\n<<<UNTRUSTED_DATA__{kind}__BEGIN>>>\n"
_CONTAIN_CLOSE = "\n<<<UNTRUSTED_DATA__{kind}__END>>>\n"

# Strip control characters that would let untrusted text close the
# delimiter or open a fake system tag. Keep TAB / LF / CR only.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def wrap_untrusted_text(text: str, *, kind: str) -> str:
    """Return ``text`` wrapped in containment delimiters.

    ``kind`` is a short stable label (e.g. ``"user_message"``,
    ``"channel_instruction"``, ``"source_snippet"``) recorded in the
    delimiter for observability. Strips ASCII control characters and
    disarms any literal delimiter substring so the wrapper cannot be
    forged. Nested untrusted regions wrap independently.
    """
    if not isinstance(text, str):
        raise TypeError(f"wrap_untrusted_text expected str, got {type(text).__name__}")
    safe_kind = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in kind)[:32]
    cleaned = _CONTROL_RE.sub("", text)
    # Disarm any literal delimiter substring the attacker might inject.
    cleaned = cleaned.replace("<<<UNTRUSTED_DATA", "<<<<UNTRUSTED_DATA")
    cleaned = cleaned.replace("UNTRUSTED_DATA__", "UNTRUSTED_DATA___")
    return (
        _CONTAIN_OPEN.format(kind=safe_kind)
        + cleaned
        + _CONTAIN_CLOSE.format(kind=safe_kind)
    )


_NUMERIC_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def claims_are_grounded(answer: str, allowed_facts: list[str]) -> bool:
    """Cheap, deterministic grounding floor: every numeric token in
    ``answer`` must appear in at least one ``allowed_facts`` string.

    Catches the common failure mode where the model invents a stat or
    number absent from the retrieved context. The K10 grounding engine
    (:mod:`sb.kernel.ai.grounding`) layers the structured name/number/
    absence validators on top; this floor keeps the injection/grounding
    pin tests honest on their own.
    """
    haystack = " ".join(allowed_facts)
    return all(token in haystack for token in _NUMERIC_TOKEN_RE.findall(answer))
