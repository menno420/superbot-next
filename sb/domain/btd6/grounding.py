"""BTD6 answer-faithfulness verifier (band 7) — the domain half of
shipped ``services/btd6_grounding_service.py`` @7f7628e1, registered
into the K10 grounded-answer registry (owner ruling PR #30 / D-0033:
this registry is where btd6 knowledge tasks plug in).

The kernel hoisted the LOOP (``verify_and_regenerate_once``), the
matchers (``name_guard``), and the absence guard; this module supplies
the BTD6 pieces: the dataset-backed proper-name index, the
name+number+absence validator, and the paragon existence attribute
(the documented "Monkey Buccaneer has no paragon" repro)."""

from __future__ import annotations

import logging
import re
import threading

from sb.domain.btd6 import dataset, keywords, paragon_math
from sb.kernel.ai.contracts import PolicyDenialReason
from sb.kernel.ai.grounding import absence_guard, name_guard, verify

logger = logging.getLogger("sb.domain.btd6.grounding")

__all__ = [
    "general_path_should_verify",
    "paragon_existence_attribute",
    "register_grounding",
    "validate_btd6_reply",
]

_index_lock = threading.Lock()
_NAME_INDEX: name_guard.NameMatchers | None = None


def _name_index() -> name_guard.NameMatchers:
    """Memoized BTD6 proper-name matchers (shipped ``_name_index``
    discipline: heroes + bosses single-token; towers/bloons multi-word
    only; all 13 paragon names; multi-word upgrade names)."""
    global _NAME_INDEX
    if _NAME_INDEX is not None:
        return _NAME_INDEX
    with _index_lock:
        if _NAME_INDEX is not None:
            return _NAME_INDEX
        try:
            canonicals: set[str] = set()
            aliases: set[str] = set()

            for hero in dataset.heroes():
                canonicals.add(hero.canonical)
                aliases.update(hero.aliases)
            for boss in dataset.bosses():
                canonicals.add(boss.canonical)
            for entry in (*dataset.towers(), *dataset.bloons()):
                if " " in entry.canonical:
                    canonicals.add(entry.canonical)
                for alias in entry.aliases:
                    if " " in alias:
                        aliases.add(alias)
            for paragon in paragon_math.PARAGONS:
                canonicals.add(paragon.name)
            for tower in dataset.towers():
                for path_upgrades in tower.upgrade_paths.values():
                    for upgrade in path_upgrades:
                        if " " in upgrade:
                            canonicals.add(upgrade)
        except Exception:  # noqa: BLE001 — dataset fault → empty index
            logger.warning(
                "btd6 grounding: dataset unavailable; empty name index",
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


def general_path_should_verify(prompt: str, answer: str) -> bool:
    """True when a general-path reply should run the BTD6 name guard
    (BTD6-themed turn, or a distinctive multi-word BTD6 name in the
    answer — never a bare common hero name)."""
    try:
        if keywords.has_btd6_context(f"{prompt} {answer}"):
            return True
        return bool(name_guard.multiword_names_present(answer, _name_index()))
    except Exception:  # noqa: BLE001 — a guard bug never breaks the path
        logger.warning(
            "btd6 grounding: general_path_should_verify raised; skipping",
            exc_info=True,
        )
        return False


def validate_btd6_reply(
    reply_text: str,
    facts: tuple[str, ...],
    tool_results: tuple[str, ...],
    *,
    check_numbers: bool = True,
) -> verify.GroundingResult:
    """Verify a model reply against the grounded haystack: every indexed
    BTD6 name present, every numeric token present (btd6.answer only —
    ``check_numbers``), and no grounding-contradicted absence claim.
    Never raises (the registry additionally fails closed)."""
    matchers = _name_index()
    haystack = " ".join((*facts, *tool_results))

    allowed_names = name_guard.names_present(haystack, matchers)
    answer_names = name_guard.names_present(reply_text, matchers)
    offending_names = tuple(sorted(answer_names - allowed_names))

    offending_numbers: tuple[str, ...] = ()
    if check_numbers:
        offending_numbers = name_guard.offending_numbers(reply_text, haystack)

    offending_absence = absence_guard.contradicted_absence_claims(
        reply_text,
        haystack,
    )

    if not offending_names and not offending_numbers and not offending_absence:
        return verify.GroundingResult(
            grounded=True,
            reason_code=PolicyDenialReason.NONE.value,
            used_fact_keys=(),
        )
    notes: list[str] = []
    if offending_names:
        notes.append("entity_name_unsupported")
    if offending_numbers:
        notes.append("numeric_claim_unsupported")
    if offending_absence:
        notes.append("absence_claim_contradicted")
    return verify.GroundingResult(
        grounded=False,
        reason_code=PolicyDenialReason.GROUNDING_FAILED.value,
        used_fact_keys=(),
        notes=tuple(notes),
        offending_names=offending_names,
        offending_numbers=offending_numbers,
        offending_absence_claims=offending_absence,
    )


# Apostrophe class covers the straight ' and the curly ' a model may emit.
_APOS = r"['’]"


def paragon_existence_attribute() -> absence_guard.ExistenceAttribute:
    """The shipped paragon existence attribute (utils/btd6/absence_guard
    ``_PARAGON`` verbatim) — the K10 ``register_existence_attribute``
    payload the K10 worker left as "band-7 data"."""
    return absence_guard.ExistenceAttribute(
        name="paragon",
        affirm_re=re.compile(
            r"([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)" + _APOS + r"s Paragon\b",
        ),
        deny_res=(
            re.compile(r"\bno\s+(?:\w+\s+){0,2}paragon\b"),
            re.compile(
                r"\b(?:does\s+not|doesn" + _APOS + r"?t|do\s+not|don" + _APOS
                + r"?t)\s+have\s+(?:a\s+|an\s+|any\s+)?(?:\w+\s+){0,2}paragon\b",
            ),
            re.compile(r"\blacks?\s+(?:a\s+|an\s+|any\s+)?(?:\w+\s+){0,2}paragon\b"),
            re.compile(r"\bwithout\s+(?:a\s+|an\s+|any\s+)?(?:\w+\s+){0,2}paragon\b"),
            re.compile(
                r"\bparagon\b(?:\s+\w+){0,3}\s+(?:does\s+not|doesn" + _APOS
                + r"?t)\s+exist\b",
            ),
            re.compile(
                r"\bparagon\b(?:\s+\w+){0,3}\s+(?:is\s+not|isn" + _APOS
                + r"?t)\s+available\b",
            ),
        ),
        exclude_qualifiers=frozenset(
            {"second", "another", "additional", "other", "more"},
        ),
        owner_subsystem="btd6",
    )


def _answer_verifier(
    reply_text: str,
    facts: tuple[str, ...],
    tool_results: tuple[str, ...],
) -> verify.GroundingResult:
    return validate_btd6_reply(reply_text, facts, tool_results, check_numbers=True)


def _strategy_verifier(
    reply_text: str,
    facts: tuple[str, ...],
    tool_results: tuple[str, ...],
) -> verify.GroundingResult:
    # Strategy reviews quote free prose; names + absence still guard,
    # numbers are the submitter's premise (shipped: numbers gated on
    # BTD6_ANSWER only).
    return validate_btd6_reply(reply_text, facts, tool_results, check_numbers=False)


def register_grounding() -> None:
    """Idempotent K10 registrations: verifiers for both btd6 tasks + the
    paragon existence attribute."""
    if "btd6.answer" not in verify.registered_verifier_tasks():
        verify.register_grounding_verifier(
            "btd6.answer", _answer_verifier, owner_subsystem="btd6",
        )
    if "btd6.strategy_review" not in verify.registered_verifier_tasks():
        verify.register_grounding_verifier(
            "btd6.strategy_review", _strategy_verifier, owner_subsystem="btd6",
        )
    attr = paragon_existence_attribute()
    if not any(
        a.name == "paragon" for a in absence_guard.registered_attributes()
    ):
        absence_guard.register_existence_attribute(attr)
