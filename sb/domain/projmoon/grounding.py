"""Project Moon (Limbus) answer-faithfulness verifier — shipped
``services/projmoon_grounding_service.py`` @7f7628e1, registered on the
K10 verify registry as the projmoon names-only twin of the BTD6
validator.

Names-only (Limbus exact numbers aren't ingested — the StaticData lane
is the D-0047 successor); common-word discipline verbatim (only the 12
Sinners + the four non-ambiguous grade letters index; Sins / damage
types / statuses are ordinary English and never single-token matched).
Fail-open on an internal verifier error (projmoon faithfulness is
additive hardening, not a hard safety floor — shipped posture, unlike
the BTD6 numeric path)."""

from __future__ import annotations

import logging
import threading

from sb.domain.projmoon import dataset
from sb.kernel.ai.contracts import PolicyDenialReason
from sb.kernel.ai.grounding import name_guard, verify

logger = logging.getLogger("sb.domain.projmoon.grounding")

__all__ = [
    "no_data_refusal",
    "register_grounding",
    "reset_index_for_tests",
    "validate_projmoon_reply",
]

# "HE" is the ordinary English pronoun — grounds only via "he grade".
_AMBIGUOUS_EGO_CANONICALS: frozenset[str] = frozenset({"he"})

_index_lock = threading.Lock()
_NAME_INDEX: name_guard.NameMatchers | None = None


def _name_index() -> name_guard.NameMatchers:
    global _NAME_INDEX
    if _NAME_INDEX is not None:
        return _NAME_INDEX
    with _index_lock:
        if _NAME_INDEX is not None:
            return _NAME_INDEX
        canonicals: set[str] = set()
        aliases: set[str] = set()
        try:
            for entry in dataset.get_entries("sinner"):
                canonicals.add(entry.canonical)
                aliases.update(entry.aliases)
            for entry in dataset.get_entries("ego_grade"):
                if entry.canonical.casefold() not in _AMBIGUOUS_EGO_CANONICALS:
                    canonicals.add(entry.canonical)
                aliases.update(alias for alias in entry.aliases if " " in alias)
        except Exception:  # noqa: BLE001 — load fault → empty index (pass)
            logger.warning(
                "projmoon grounding: fixtures unavailable; empty name index",
                exc_info=True,
            )
            return name_guard.NameMatchers(multi=frozenset(), single=frozenset())
        index = name_guard.build_matchers(canonicals, aliases)
        _NAME_INDEX = index
        return index


def reset_index_for_tests() -> None:
    global _NAME_INDEX
    with _index_lock:
        _NAME_INDEX = None


def validate_projmoon_reply(
    answer_text: str,
    *,
    facts: tuple[str, ...] = (),
) -> verify.GroundingResult:
    """Names-only check against the grounded haystack. Fails OPEN on an
    internal error (shipped posture)."""
    try:
        matchers = _name_index()
        haystack = " ".join(facts)

        allowed_names = name_guard.names_present(haystack, matchers)
        answer_names = name_guard.names_present(answer_text, matchers)
        offending_names = tuple(sorted(answer_names - allowed_names))

        if not offending_names:
            return verify.GroundingResult(
                grounded=True,
                reason_code=PolicyDenialReason.NONE.value,
                used_fact_keys=(),
            )
        return verify.GroundingResult(
            grounded=False,
            reason_code=PolicyDenialReason.GROUNDING_FAILED.value,
            used_fact_keys=(),
            notes=("entity_name_unsupported",),
            offending_names=offending_names,
        )
    except Exception:  # noqa: BLE001 — fail open (shipped)
        logger.warning(
            "projmoon grounding: validate raised; failing open",
            exc_info=True,
        )
        return verify.GroundingResult(
            grounded=True,
            reason_code=PolicyDenialReason.NONE.value,
            used_fact_keys=(),
            notes=("verifier_error",),
        )


def no_data_refusal() -> str:
    """Deterministic Project Moon refusal — never model prose (shipped
    verbatim)."""
    return (
        "I don't have verified Project Moon (Limbus) details to answer that "
        "confidently. I won't state Sinner or E.G.O facts I can't ground in my "
        "data — try asking about a specific Sinner (e.g. Faust, Don Quixote) or "
        "one of the E.G.O grades."
    )


def _verifier(
    reply_text: str,
    facts: tuple[str, ...],
    tool_results: tuple[str, ...],
) -> verify.GroundingResult:
    return validate_projmoon_reply(
        reply_text, facts=(*facts, *tool_results),
    )


def register_grounding() -> None:
    """Idempotent K10 registration for projmoon.answer."""
    if "projmoon.answer" not in verify.registered_verifier_tasks():
        verify.register_grounding_verifier(
            "projmoon.answer", _verifier, owner_subsystem="projmoon",
        )
