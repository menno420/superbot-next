"""Grounding verification + the verify-and-regenerate-once loop (K10).

The ``GroundingResult`` shape and the reject → regenerate-once-with-
constraint → deterministic-floor discipline, hoisted from shipped
``services/btd6_grounding_service.py`` + the faithfulness sections of
``core/runtime/ai/natural_language_stage.py`` (the BTD6 and projmoon
paths implemented the SAME loop twice — here it exists once).

Domain verifiers REGISTER per task id (:func:`register_grounding_verifier`
— band 7 registers the BTD6 name+number+absence validator over its name
index, and the projmoon names-only validator). A task without a verifier
is vacuously grounded (the shipped general-path default). Verifiers MUST
never raise; the dispatcher fails CLOSED (not-grounded → the refusal
floor) if one does — the shipped ``validate_btd6_reply`` posture.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

__all__ = [
    "GroundingResult",
    "RegenerateOutcome",
    "build_grounding_constraint",
    "clear_verifiers_for_tests",
    "register_grounding_verifier",
    "registered_verifier_tasks",
    "verify_and_regenerate_once",
    "verify_reply",
]

logger = logging.getLogger("sb.kernel.ai.grounding")


@dataclass(frozen=True)
class GroundingResult:
    """Shipped shape (btd6_grounding_service.GroundingResult @7f7628e1);
    ``reason_code`` is 'none' or a PolicyDenialReason value."""

    grounded: bool
    reason_code: str
    used_fact_keys: tuple[str, ...]
    notes: tuple[str, ...] = ()
    offending_names: tuple[str, ...] = ()
    offending_numbers: tuple[str, ...] = ()
    offending_absence_claims: tuple[str, ...] = ()


GROUNDED = GroundingResult(grounded=True, reason_code="none", used_fact_keys=())

#: verifier(reply_text, facts, tool_results) -> GroundingResult.
#: Deterministic, cheap, and internally fault-tolerant.
VerifierFn = Callable[[str, tuple[str, ...], tuple[str, ...]], GroundingResult]

_VERIFIERS: dict[str, tuple[str, VerifierFn]] = {}


def register_grounding_verifier(
    task_id: str,
    verifier: VerifierFn,
    *,
    owner_subsystem: str,
) -> None:
    prior = _VERIFIERS.get(task_id)
    if prior is not None and prior != (owner_subsystem, verifier):
        raise ValueError(
            f"grounding verifier for task {task_id!r} already registered "
            f"by {prior[0]!r}",
        )
    _VERIFIERS[task_id] = (owner_subsystem, verifier)


def registered_verifier_tasks() -> tuple[str, ...]:
    return tuple(sorted(_VERIFIERS))


def clear_verifiers_for_tests() -> None:
    _VERIFIERS.clear()


def verify_reply(
    task_id: str,
    reply_text: str,
    *,
    facts: tuple[str, ...] = (),
    tool_results: tuple[str, ...] = (),
) -> GroundingResult:
    """Run the registered verifier for ``task_id``. No verifier →
    vacuously grounded. A RAISING verifier fails CLOSED (not-grounded,
    ``verifier_error`` note) so the caller floors to the deterministic
    refusal — never raises."""
    entry = _VERIFIERS.get(task_id)
    if entry is None:
        return GROUNDED
    owner, verifier = entry
    try:
        return verifier(reply_text, facts, tool_results)
    except Exception:  # noqa: BLE001 — fail closed to the refusal floor
        logger.warning(
            "grounding: verifier for task %s (owner %s) raised; failing closed",
            task_id,
            owner,
            exc_info=True,
        )
        return GroundingResult(
            grounded=False,
            reason_code="grounding_failed",
            used_fact_keys=(),
            notes=("verifier_error",),
        )


def build_grounding_constraint(
    verdict: GroundingResult,
    *,
    domain_label: str = "the",
) -> str:
    """The do-not-state constraint appended to the system prompt on the
    regenerate-once retry (shipped ``_build_grounding_constraint``,
    domain-label parameterised)."""
    bits: list[str] = []
    if verdict.offending_names:
        bits.append("names not in the data: " + ", ".join(verdict.offending_names))
    if verdict.offending_numbers:
        bits.append("numbers not in the data: " + ", ".join(verdict.offending_numbers))
    if verdict.offending_absence_claims:
        bits.append(
            "false 'does not have' claims the data refutes: "
            + " | ".join(verdict.offending_absence_claims),
        )
    detail = "; ".join(bits) if bits else f"unsupported {domain_label} claims"
    correction = (
        "GROUNDING CORRECTION: your previous reply contained "
        f"{detail}. Do NOT state these. Use only {domain_label} names and "
        "numbers present in the provided data and tool results. If the data "
        "does not support an answer, say you don't have that information."
    )
    if verdict.offending_absence_claims:
        correction += (
            " The provided data DOES list the thing you said is missing — "
            "state what the data shows instead of claiming it does not exist."
        )
    return correction


@dataclass(frozen=True)
class RegenerateOutcome:
    """What the verify+regenerate-once loop decided.

    ``reply_text`` is the deliverable text when ``grounded`` (the original
    or the rescued retry). When not grounded, the caller serves its
    deterministic floor: ``degraded=True`` means the RETRY was a provider
    outage (audit 'degraded'/PROVIDER_UNAVAILABLE — never blamed on
    grounding); otherwise it is a healthy grounding failure (audit
    'denied'/GROUNDING_FAILED). ``retry_attempted``/``retry_rescued``
    carry the shipped log semantics.
    """

    grounded: bool
    reply_text: str
    verdict: GroundingResult
    retry_attempted: bool = False
    retry_rescued: bool = False
    degraded: bool = False


async def verify_and_regenerate_once(
    task_id: str,
    reply_text: str,
    *,
    facts: tuple[str, ...] = (),
    tool_results: tuple[str, ...] = (),
    regenerate: Callable[[str], Awaitable[tuple[str, bool]]],
    domain_label: str = "the",
) -> RegenerateOutcome:
    """THE loop (shipped twice, hoisted once): verify → if not grounded,
    regenerate ONCE with an explicit do-not-state constraint → re-verify →
    grounded reply or floor.

    ``regenerate(constraint)`` re-invokes the gateway with the constraint
    appended to the system stack and returns ``(retry_text, degraded)``
    (degraded = the retry response was a provider fault, not a grounding
    verdict). Never raises.
    """
    verdict = verify_reply(task_id, reply_text, facts=facts, tool_results=tool_results)
    if verdict.grounded:
        return RegenerateOutcome(grounded=True, reply_text=reply_text, verdict=verdict)

    constraint = build_grounding_constraint(verdict, domain_label=domain_label)
    try:
        retry_text, retry_degraded = await regenerate(constraint)
    except Exception:  # noqa: BLE001 — the loop never breaks the reply path
        logger.warning("grounding: regenerate callback raised", exc_info=True)
        retry_text, retry_degraded = "", False
    retry_text = (retry_text or "").strip()

    if retry_text:
        retry_verdict = verify_reply(
            task_id,
            retry_text,
            facts=facts,
            tool_results=tool_results,
        )
        if retry_verdict.grounded:
            logger.info("grounding: retry_rescued task=%s", task_id)
            return RegenerateOutcome(
                grounded=True,
                reply_text=retry_text,
                verdict=retry_verdict,
                retry_attempted=True,
                retry_rescued=True,
            )

    logger.warning(
        "grounding: blocked task=%s guard=%s names=%s numbers=%s "
        "retry_attempted=True retry_rescued=False degraded=%s",
        task_id,
        ",".join(verdict.notes),
        list(verdict.offending_names),
        list(verdict.offending_numbers),
        retry_degraded,
    )
    return RegenerateOutcome(
        grounded=False,
        reply_text=reply_text,
        verdict=verdict,
        retry_attempted=True,
        retry_rescued=False,
        degraded=retry_degraded,
    )
